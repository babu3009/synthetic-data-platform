"""
DDL parsing module using sqlglot.

Parses DDL files from multiple SQL dialects (Postgres, MySQL, MSSQL, HANA)
and extracts schema information including tables, columns, constraints, and foreign keys.
"""
import re
from typing import Dict, List, Optional, Set, Tuple

import sqlglot
from sqlglot import exp, parse
from sqlglot.dialects import Dialect

from app.schemas.schema import (
    CanonicalSchema,
    CheckConstraint,
    ColumnSchema,
    ForeignKey,
    TableSchema,
)


# SQL dialect mapping
DIALECT_MAP = {
    "postgres": "postgres",
    "postgresql": "postgres",
    "mysql": "mysql",
    "mssql": "tsql",
    "sqlserver": "tsql",
    "hana": "hana",
}


def normalize_dtype(dtype_expr: exp.DataType, dialect: str) -> str:
    """
    Normalize data type to a canonical string representation.
    
    Args:
        dtype_expr: sqlglot DataType expression
        dialect: SQL dialect name
        
    Returns:
        Normalized data type string
    """
    dtype_str = dtype_expr.sql(dialect=dialect)
    
    # Normalize common types
    dtype_lower = dtype_str.lower()
    
    # Integer types
    if dtype_lower in ("int", "integer", "int4", "serial"):
        return "INTEGER"
    if dtype_lower in ("bigint", "int8", "bigserial"):
        return "BIGINT"
    if dtype_lower in ("smallint", "int2", "smallserial"):
        return "SMALLINT"
    if dtype_lower in ("tinyint", "int1"):
        return "TINYINT"
    
    # String types
    if dtype_lower.startswith("varchar") or dtype_lower.startswith("character varying"):
        match = re.search(r"\((\d+)\)", dtype_str)
        length = match.group(1) if match else "255"
        return f"VARCHAR({length})"
    if dtype_lower.startswith("char") or dtype_lower.startswith("character("):
        match = re.search(r"\((\d+)\)", dtype_str)
        length = match.group(1) if match else "1"
        return f"CHAR({length})"
    if dtype_lower in ("text", "clob", "ntext"):
        return "TEXT"
    
    # Numeric types
    if dtype_lower.startswith("decimal") or dtype_lower.startswith("numeric"):
        match = re.search(r"\((\d+)(?:,\s*(\d+))?\)", dtype_str)
        if match:
            precision = match.group(1)
            scale = match.group(2) if match.group(2) else "0"
            return f"DECIMAL({precision},{scale})"
        return "DECIMAL"
    if dtype_lower in ("real", "float4"):
        return "REAL"
    if dtype_lower in ("double", "double precision", "float8", "float"):
        return "DOUBLE"
    
    # Boolean
    if dtype_lower in ("boolean", "bool", "bit"):
        return "BOOLEAN"
    
    # Date/Time types
    if dtype_lower in ("date",):
        return "DATE"
    if dtype_lower in ("time",):
        return "TIME"
    if dtype_lower.startswith("timestamp"):
        return "TIMESTAMP"
    if dtype_lower in ("datetime", "datetime2"):
        return "DATETIME"
    
    # Binary types
    if dtype_lower.startswith("bytea") or dtype_lower.startswith("varbinary") or dtype_lower.startswith("blob"):
        return "BINARY"
    
    # JSON types
    if dtype_lower in ("json", "jsonb"):
        return "JSON"
    
    # UUID
    if dtype_lower in ("uuid", "uniqueidentifier"):
        return "UUID"
    
    # Array types (PostgreSQL)
    if "[]" in dtype_str or dtype_lower.startswith("array"):
        return dtype_str.upper()
    
    # Default: return uppercased original
    return dtype_str.upper()


def detect_pii_tag(column_name: str, dtype: str) -> Optional[str]:
    """
    Heuristic PII detection based on column name and data type.
    
    Args:
        column_name: Column name
        dtype: Normalized data type
        
    Returns:
        PII tag or None
    """
    col_lower = column_name.lower()
    
    # Email detection
    if "email" in col_lower or "e_mail" in col_lower:
        return "EMAIL"
    
    # Phone detection
    if "phone" in col_lower or "mobile" in col_lower or "tel" in col_lower:
        return "PHONE"
    
    # Name detection
    if any(x in col_lower for x in ["first_name", "last_name", "full_name", "given_name", "surname"]):
        return "NAME"
    
    # Address detection
    if any(x in col_lower for x in ["address", "street", "city", "postal", "zip_code"]):
        return "ADDRESS"
    
    # SSN/ID detection
    if any(x in col_lower for x in ["ssn", "social_security", "national_id", "passport"]):
        return "IDENTIFIER"
    
    # Credit card detection
    if any(x in col_lower for x in ["credit_card", "card_number", "cc_number"]):
        return "PAYMENT"
    
    return None


def parse_create_table(
    statement: exp.Create,
    dialect: str,
    warnings: List[str]
) -> Optional[TableSchema]:
    """
    Parse a CREATE TABLE statement.
    
    Args:
        statement: sqlglot Create expression
        dialect: SQL dialect
        warnings: List to append warnings to
        
    Returns:
        TableSchema or None if parsing fails
    """
    if not isinstance(statement.this, exp.Schema):
        warnings.append(f"Skipping non-table CREATE: {statement.sql(dialect=dialect)[:50]}")
        return None
    
    table_name = statement.this.this.name
    columns: List[ColumnSchema] = []
    pk_cols: List[str] = []
    unique_constraints: List[List[str]] = []
    check_constraints: List[CheckConstraint] = []
    foreign_keys: List[ForeignKey] = []
    
    # Parse column definitions
    for col_def in statement.this.expressions:
        if isinstance(col_def, exp.ColumnDef):
            col_name = col_def.this.name
            
            # Extract data type
            if col_def.kind:
                dtype = normalize_dtype(col_def.kind, dialect)
            else:
                dtype = "UNKNOWN"
                warnings.append(f"Table {table_name}.{col_name}: No data type specified")
            
            # Check nullability (default is True unless NOT NULL is specified)
            nullable = True
            for constraint in col_def.constraints:
                # Constraints are wrapped in ColumnConstraint with a 'kind' attribute
                if isinstance(constraint, exp.ColumnConstraint):
                    if isinstance(constraint.kind, exp.NotNullColumnConstraint):
                        nullable = False
                elif isinstance(constraint, exp.NotNullColumnConstraint):
                    # Direct constraint (fallback)
                    nullable = False
            
            # Detect PII
            pii_tag = detect_pii_tag(col_name, dtype)
            
            columns.append(ColumnSchema(
                name=col_name,
                dtype=dtype,
                nullable=nullable,
                pii_tag=pii_tag
            ))
            
            # Check for column-level constraints
            for constraint in col_def.constraints:
                # Constraints are wrapped in ColumnConstraint with a 'kind' attribute
                constraint_kind = constraint.kind if isinstance(constraint, exp.ColumnConstraint) else constraint
                
                if isinstance(constraint_kind, exp.PrimaryKeyColumnConstraint):
                    pk_cols.append(col_name)
                elif isinstance(constraint_kind, exp.UniqueColumnConstraint):
                    unique_constraints.append([col_name])
                elif isinstance(constraint_kind, exp.CheckColumnConstraint):
                    # Column-level CHECK constraint
                    check_expr = constraint_kind.this.sql(dialect=dialect) if constraint_kind.this else ""
                    check_constraints.append(CheckConstraint(
                        name=None,  # Column-level CHECKs typically don't have names
                        expression=check_expr
                    ))
    
    # Parse table-level constraints
    for expr in statement.this.expressions:
        # Handle named constraints (CONSTRAINT name ...)
        # These are wrapped in exp.Constraint with the actual constraint in expressions
        constraints_to_process = []
        constraint_name = None
        
        if isinstance(expr, exp.Constraint):
            # Named constraint wrapper
            constraint_name = expr.this.name if hasattr(expr.this, 'name') else None
            constraints_to_process = expr.expressions
        elif not isinstance(expr, exp.ColumnDef):
            # Direct constraint (not wrapped)
            constraints_to_process = [expr]
        
        for constraint in constraints_to_process:
            if isinstance(constraint, exp.PrimaryKey):
                # Table-level primary key
                pk_cols = [col.name for col in constraint.expressions]
            
            elif isinstance(constraint, exp.UniqueColumnConstraint):
                # Table-level unique constraint
                if constraint.this and hasattr(constraint.this, 'expressions'):
                    unique_cols = [col.name for col in constraint.this.expressions]
                    unique_constraints.append(unique_cols)
            
            elif isinstance(constraint, exp.Check):
                # Table-level Check constraint (unnamed or with exp.Check wrapper)
                check_expr = constraint.this.sql(dialect=dialect) if constraint.this else ""
                check_constraints.append(CheckConstraint(
                    name=constraint_name,
                    expression=check_expr
                ))
            
            elif isinstance(constraint, exp.CheckColumnConstraint):
                # Table-level Check constraint (named with CONSTRAINT keyword)
                check_expr = constraint.this.sql(dialect=dialect) if constraint.this else ""
                check_constraints.append(CheckConstraint(
                    name=constraint_name,
                    expression=check_expr
                ))
            
            elif isinstance(constraint, exp.ForeignKey):
                # Foreign key constraint
                from_cols = [col.name for col in constraint.expressions]
                ref = constraint.args.get('reference')
                if ref and hasattr(ref, 'this'):
                    # ref.this is a Schema object containing table and columns
                    to_table = ref.this.this.name if hasattr(ref.this, 'this') and hasattr(ref.this.this, 'name') else None
                    # Columns are in ref.this.expressions (Schema.expressions)
                    to_cols = [col.name for col in ref.this.expressions] if hasattr(ref.this, 'expressions') and ref.this.expressions else []
                    
                    if to_table and len(from_cols) == len(to_cols):
                        for from_col, to_col in zip(from_cols, to_cols):
                            foreign_keys.append(ForeignKey(
                                from_col=from_col,
                                to_table=to_table,
                                to_col=to_col
                            ))
                    else:
                        warnings.append(f"Table {table_name}: Invalid FK constraint")
    
    return TableSchema(
        name=table_name,
        columns=columns,
        pk=pk_cols,
        uniques=unique_constraints,
        checks=check_constraints,
        fks=foreign_keys
    )


def parse_alter_table(
    statement: exp.Alter,
    tables: Dict[str, TableSchema],
    dialect: str,
    warnings: List[str]
) -> None:
    """
    Parse ALTER TABLE statements to extract additional constraints.
    
    Args:
        statement: sqlglot AlterTable expression
        tables: Dictionary of table schemas to update
        dialect: SQL dialect
        warnings: List to append warnings to
    """
    table_name = statement.this.name
    
    if table_name not in tables:
        warnings.append(f"ALTER TABLE references non-existent table: {table_name}")
        return
    
    table = tables[table_name]
    
    for action in statement.actions:
        if isinstance(action, exp.AddConstraint):
            # AddConstraint has expressions list containing Constraint wrappers
            constraints_list = action.expressions if hasattr(action, 'expressions') else []
            
            for constraint_wrapper in constraints_list:
                # Handle named constraints (wrapped in exp.Constraint)
                constraint_name = None
                actual_constraints = []
                
                if isinstance(constraint_wrapper, exp.Constraint):
                    # Named constraint
                    constraint_name = constraint_wrapper.this.name if hasattr(constraint_wrapper.this, 'name') else None
                    actual_constraints = constraint_wrapper.expressions
                else:
                    # Direct constraint (shouldn't happen in ALTER TABLE ADD CONSTRAINT)
                    actual_constraints = [constraint_wrapper]
                
                for constraint in actual_constraints:
                    if isinstance(constraint, exp.PrimaryKey):
                        # Add primary key
                        pk_cols = [col.name for col in constraint.expressions]
                        table.pk = pk_cols
                    
                    elif isinstance(constraint, exp.UniqueColumnConstraint):
                        # Add unique constraint
                        if constraint.this and hasattr(constraint.this, 'expressions'):
                            unique_cols = [col.name for col in constraint.this.expressions]
                            table.uniques.append(unique_cols)
                    
                    elif isinstance(constraint, exp.ForeignKey):
                        # Add foreign key
                        from_cols = [col.name for col in constraint.expressions]
                        ref = constraint.args.get('reference')
                        if ref and hasattr(ref, 'this'):
                            # ref.this is a Schema object containing table and columns
                            to_table = ref.this.this.name if hasattr(ref.this, 'this') and hasattr(ref.this.this, 'name') else None
                            # Columns are in ref.this.expressions (Schema.expressions)
                            to_cols = [col.name for col in ref.this.expressions] if hasattr(ref.this, 'expressions') and ref.this.expressions else []
                            
                            if to_table and len(from_cols) == len(to_cols):
                                for from_col, to_col in zip(from_cols, to_cols):
                                    table.fks.append(ForeignKey(
                                        from_col=from_col,
                                        to_table=to_table,
                                        to_col=to_col
                                    ))


def parse_ddl(ddl_content: str, dialect: str = "postgres") -> CanonicalSchema:
    """
    Parse DDL content and extract schema information.
    
    Args:
        ddl_content: DDL SQL content
        dialect: SQL dialect (postgres/mysql/mssql/hana)
        
    Returns:
        CanonicalSchema with parsed tables and metadata
    """
    warnings: List[str] = []
    tables: Dict[str, TableSchema] = {}
    
    # Normalize dialect
    dialect = DIALECT_MAP.get(dialect.lower(), dialect.lower())
    
    try:
        # Parse all statements
        statements = parse(ddl_content, dialect=dialect)
        
        if not statements:
            warnings.append("No valid SQL statements found in DDL")
            return CanonicalSchema(tables=[], warnings=warnings)
        
        # First pass: parse CREATE TABLE statements
        for statement in statements:
            if isinstance(statement, exp.Create):
                table_schema = parse_create_table(statement, dialect, warnings)
                if table_schema:
                    tables[table_schema.name] = table_schema
        
        # Second pass: parse ALTER TABLE statements
        for statement in statements:
            if isinstance(statement, exp.Alter):
                parse_alter_table(statement, tables, dialect, warnings)
        
        # Build DAG (will be populated by schema_graph utilities)
        from app.utils.schema_graph import build_dag
        
        table_list = list(tables.values())
        dag = build_dag(table_list)
        
        return CanonicalSchema(
            tables=table_list,
            dag=dag,
            warnings=warnings
        )
    
    except Exception as e:
        warnings.append(f"DDL parsing error: {str(e)}")
        return CanonicalSchema(
            tables=list(tables.values()),
            warnings=warnings
        )


def validate_schema(schema: CanonicalSchema) -> List[str]:
    """
    Validate parsed schema and return additional warnings.
    
    Args:
        schema: Canonical schema to validate
        
    Returns:
        List of validation warnings
    """
    warnings: List[str] = []
    table_names = {t.name for t in schema.tables}
    
    for table in schema.tables:
        # Check if table has columns
        if not table.columns:
            warnings.append(f"Table {table.name} has no columns")
        
        # Check if PK columns exist
        for pk_col in table.pk:
            if pk_col not in {c.name for c in table.columns}:
                warnings.append(f"Table {table.name}: PK column '{pk_col}' not found")
        
        # Check if unique constraint columns exist
        for unique_cols in table.uniques:
            for col in unique_cols:
                if col not in {c.name for c in table.columns}:
                    warnings.append(f"Table {table.name}: Unique column '{col}' not found")
        
        # Check if FK references exist
        for fk in table.fks:
            if fk.from_col not in {c.name for c in table.columns}:
                warnings.append(f"Table {table.name}: FK column '{fk.from_col}' not found")
            if fk.to_table not in table_names:
                warnings.append(f"Table {table.name}: FK references non-existent table '{fk.to_table}'")
    
    return warnings
