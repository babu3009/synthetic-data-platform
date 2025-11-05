"""
DDL Parser for extracting schema information from SQL DDL statements.

Supports: PostgreSQL, MySQL, MSSQL, HANA subset
"""
from typing import Any, Dict, List, Optional, Set
import sqlglot
from sqlglot import exp, parse_one
from sqlglot.dialects.dialect import Dialects


class DDLParser:
    """Parse DDL statements and extract schema information."""
    
    # Map sqlglot dialects
    DIALECT_MAP = {
        "postgres": Dialects.POSTGRES,
        "postgresql": Dialects.POSTGRES,
        "mysql": Dialects.MYSQL,
        "mssql": Dialects.TSQL,
        "sqlserver": Dialects.TSQL,
        "hana": Dialects.HANA,
    }
    
    # Map SQL types to canonical types
    TYPE_MAP = {
        # Numeric types
        "INT": "INTEGER",
        "INTEGER": "INTEGER",
        "SMALLINT": "SMALLINT",
        "BIGINT": "BIGINT",
        "DECIMAL": "DECIMAL",
        "NUMERIC": "NUMERIC",
        "REAL": "REAL",
        "DOUBLE": "DOUBLE",
        "FLOAT": "FLOAT",
        "SERIAL": "SERIAL",
        "BIGSERIAL": "BIGSERIAL",
        
        # String types
        "VARCHAR": "VARCHAR",
        "CHAR": "CHAR",
        "TEXT": "TEXT",
        "NVARCHAR": "NVARCHAR",
        "NCHAR": "NCHAR",
        "CLOB": "CLOB",
        
        # Date/Time types
        "DATE": "DATE",
        "TIME": "TIME",
        "TIMESTAMP": "TIMESTAMP",
        "DATETIME": "DATETIME",
        "DATETIME2": "DATETIME",
        
        # Boolean
        "BOOLEAN": "BOOLEAN",
        "BOOL": "BOOLEAN",
        "BIT": "BOOLEAN",
        
        # Binary
        "BYTEA": "BYTEA",
        "BLOB": "BLOB",
        "VARBINARY": "VARBINARY",
        
        # JSON
        "JSON": "JSON",
        "JSONB": "JSONB",
        
        # UUID
        "UUID": "UUID",
        "UNIQUEIDENTIFIER": "UUID",
    }
    
    def __init__(self, dialect: str = "postgres"):
        """
        Initialize parser with specific SQL dialect.
        
        Args:
            dialect: SQL dialect (postgres, mysql, mssql, hana)
        """
        self.dialect = self.DIALECT_MAP.get(dialect.lower(), Dialects.POSTGRES)
        self.warnings: List[str] = []
        self.tables: Dict[str, Dict[str, Any]] = {}
    
    def parse_ddl(self, ddl_sql: str) -> Dict[str, Any]:
        """
        Parse DDL SQL and extract schema information.
        
        Args:
            ddl_sql: DDL SQL statements
            
        Returns:
            Dictionary containing parsed schema information
        """
        self.warnings = []
        self.tables = {}
        
        try:
            # Parse all statements
            statements = sqlglot.parse(ddl_sql, dialect=self.dialect)
            
            for stmt in statements:
                if stmt is None:
                    continue
                    
                if isinstance(stmt, exp.Create) and isinstance(stmt.this, exp.Schema):
                    self._parse_create_table(stmt)
                elif isinstance(stmt, exp.AlterTable):
                    self._parse_alter_table(stmt)
                    
        except Exception as e:
            self.warnings.append(f"Parse error: {str(e)}")
        
        return {
            "tables": list(self.tables.values()),
            "warnings": self.warnings
        }
    
    def _parse_create_table(self, stmt: exp.Create) -> None:
        """Parse CREATE TABLE statement."""
        table_name = self._get_table_name(stmt.this)
        
        if not table_name:
            self.warnings.append("Found CREATE TABLE without table name")
            return
        
        table_info = {
            "name": table_name,
            "columns": [],
            "primary_key": [],
            "unique_constraints": [],
            "check_constraints": [],
            "foreign_keys": []
        }
        
        # Parse column definitions
        for column_def in stmt.this.expressions:
            if isinstance(column_def, exp.ColumnDef):
                col_info = self._parse_column_def(column_def, table_name)
                if col_info:
                    table_info["columns"].append(col_info)
            
            # Table-level constraints
            elif isinstance(column_def, exp.PrimaryKey):
                table_info["primary_key"].extend(
                    self._get_column_names(column_def.expressions)
                )
            elif isinstance(column_def, exp.UniqueColumnConstraint) or \
                 isinstance(column_def, exp.Unique):
                constraint_name = self._get_constraint_name(column_def)
                columns = self._get_column_names(column_def.expressions)
                table_info["unique_constraints"].append({
                    "name": constraint_name,
                    "columns": columns
                })
            elif isinstance(column_def, exp.ForeignKey):
                fk_info = self._parse_foreign_key(column_def, table_name)
                if fk_info:
                    table_info["foreign_keys"].append(fk_info)
            elif isinstance(column_def, exp.Check):
                check_info = self._parse_check_constraint(column_def)
                if check_info:
                    table_info["check_constraints"].append(check_info)
        
        self.tables[table_name] = table_info
    
    def _parse_column_def(self, column_def: exp.ColumnDef, table_name: str) -> Optional[Dict[str, Any]]:
        """Parse column definition."""
        col_name = column_def.this.name if column_def.this else None
        if not col_name:
            self.warnings.append(f"Column without name in table {table_name}")
            return None
        
        # Get data type
        dtype = None
        if column_def.kind:
            dtype = self._normalize_type(column_def.kind)
        
        # Check nullable
        nullable = True
        is_primary = False
        is_unique = False
        default_value = None
        
        # Parse constraints
        for constraint in column_def.constraints or []:
            if isinstance(constraint, exp.NotNullColumnConstraint):
                nullable = False
            elif isinstance(constraint, exp.PrimaryKeyColumnConstraint):
                is_primary = True
                nullable = False
            elif isinstance(constraint, exp.UniqueColumnConstraint):
                is_unique = True
            elif isinstance(constraint, exp.DefaultColumnConstraint):
                default_value = str(constraint.this) if constraint.this else None
        
        col_info = {
            "name": col_name,
            "dtype": dtype or "UNKNOWN",
            "nullable": nullable,
        }
        
        # Add optional fields
        if default_value:
            col_info["default"] = default_value
        
        # PII tag detection (basic heuristics)
        pii_tag = self._detect_pii(col_name.lower())
        if pii_tag:
            col_info["pii_tag"] = pii_tag
        
        return col_info
    
    def _parse_alter_table(self, stmt: exp.AlterTable) -> None:
        """Parse ALTER TABLE statement for constraints."""
        table_name = self._get_table_name(stmt.this)
        
        if not table_name or table_name not in self.tables:
            self.warnings.append(
                f"ALTER TABLE for unknown table: {table_name}"
            )
            return
        
        table_info = self.tables[table_name]
        
        for action in stmt.actions or []:
            if isinstance(action, exp.AddConstraint):
                constraint = action.this
                
                if isinstance(constraint, exp.PrimaryKey):
                    columns = self._get_column_names(constraint.expressions)
                    table_info["primary_key"].extend(columns)
                    
                elif isinstance(constraint, exp.Unique):
                    constraint_name = self._get_constraint_name(constraint)
                    columns = self._get_column_names(constraint.expressions)
                    table_info["unique_constraints"].append({
                        "name": constraint_name,
                        "columns": columns
                    })
                    
                elif isinstance(constraint, exp.ForeignKey):
                    fk_info = self._parse_foreign_key(constraint, table_name)
                    if fk_info:
                        table_info["foreign_keys"].append(fk_info)
                        
                elif isinstance(constraint, exp.Check):
                    check_info = self._parse_check_constraint(constraint)
                    if check_info:
                        table_info["check_constraints"].append(check_info)
    
    def _parse_foreign_key(
        self, fk_constraint: exp.ForeignKey, table_name: str
    ) -> Optional[Dict[str, Any]]:
        """Parse foreign key constraint."""
        # Get source columns
        from_cols = self._get_column_names(fk_constraint.expressions)
        
        # Get reference table and columns
        reference = fk_constraint.reference
        if not reference:
            self.warnings.append(
                f"Foreign key without reference in table {table_name}"
            )
            return None
        
        to_table = self._get_table_name(reference.this) if reference.this else None
        to_cols = self._get_column_names(reference.expressions) if reference.expressions else []
        
        if not to_table:
            self.warnings.append(
                f"Foreign key without target table in {table_name}"
            )
            return None
        
        # If no target columns specified, assume same as source columns
        if not to_cols:
            to_cols = from_cols
        
        constraint_name = self._get_constraint_name(fk_constraint)
        
        return {
            "name": constraint_name,
            "from_columns": from_cols,
            "to_table": to_table,
            "to_columns": to_cols
        }
    
    def _parse_check_constraint(self, check: exp.Check) -> Optional[Dict[str, Any]]:
        """Parse check constraint."""
        constraint_name = self._get_constraint_name(check)
        expression = str(check.this) if check.this else ""
        
        if not expression:
            return None
        
        return {
            "name": constraint_name,
            "expression": expression
        }
    
    def _get_table_name(self, table_expr: Any) -> Optional[str]:
        """Extract table name from expression."""
        if isinstance(table_expr, exp.Table):
            return table_expr.name
        elif isinstance(table_expr, exp.Schema):
            return self._get_table_name(table_expr.this)
        elif hasattr(table_expr, 'name'):
            return table_expr.name
        return None
    
    def _get_column_names(self, expressions: List[Any]) -> List[str]:
        """Extract column names from expressions."""
        names = []
        for expr in expressions or []:
            if isinstance(expr, exp.Column):
                names.append(expr.name)
            elif hasattr(expr, 'name'):
                names.append(expr.name)
            elif isinstance(expr, str):
                names.append(expr)
        return names
    
    def _get_constraint_name(self, constraint: Any) -> Optional[str]:
        """Extract constraint name."""
        if hasattr(constraint, 'name') and constraint.name:
            return constraint.name
        return None
    
    def _normalize_type(self, type_expr: exp.DataType) -> str:
        """Normalize SQL data type to canonical form."""
        type_name = type_expr.this.name.upper() if type_expr.this else "UNKNOWN"
        
        # Handle parameterized types
        canonical = self.TYPE_MAP.get(type_name, type_name)
        
        # Add size/precision if present
        if type_expr.expressions:
            params = [str(e) for e in type_expr.expressions]
            canonical = f"{canonical}({','.join(params)})"
        
        return canonical
    
    def _detect_pii(self, col_name: str) -> Optional[str]:
        """Detect PII data types based on column name heuristics."""
        pii_patterns = {
            "email": ["email", "e_mail", "mail"],
            "phone": ["phone", "mobile", "tel", "fax"],
            "ssn": ["ssn", "social_security"],
            "name": ["first_name", "last_name", "full_name", "firstname", "lastname"],
            "address": ["address", "street", "city", "zip", "postal"],
            "credit_card": ["credit_card", "card_number", "cc_number"],
            "ip_address": ["ip_address", "ip_addr"],
        }
        
        for pii_type, patterns in pii_patterns.items():
            if any(pattern in col_name for pattern in patterns):
                return pii_type
        
        return None
    
    def get_table_names(self) -> List[str]:
        """Get list of table names."""
        return list(self.tables.keys())
    
    def get_table(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get table information by name."""
        return self.tables.get(table_name)
