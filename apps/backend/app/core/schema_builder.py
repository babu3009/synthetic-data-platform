"""
Canonical schema builder for normalizing parsed DDL into standard JSON format.
"""
from typing import Dict, List, Any, Optional
from .ddl_parser import DDLParser
from .schema_graph import build_schema_graph, SchemaGraph


class SchemaBuilder:
    """Build canonical schema JSON from DDL or parsed tables."""
    
    def __init__(self):
        """Initialize schema builder."""
        self.warnings: List[str] = []
    
    def build_from_ddl(
        self,
        ddl_sql: str,
        dialect: str = "postgres"
    ) -> Dict[str, Any]:
        """
        Build canonical schema from DDL SQL.
        
        Args:
            ddl_sql: DDL SQL statements
            dialect: SQL dialect (postgres, mysql, mssql, hana)
            
        Returns:
            Canonical schema dictionary
        """
        # Parse DDL
        parser = DDLParser(dialect=dialect)
        parsed = parser.parse_ddl(ddl_sql)
        
        # Collect warnings from parser
        self.warnings = parsed.get("warnings", [])
        
        # Build schema
        return self.build_from_tables(parsed.get("tables", []))
    
    def build_from_json(self, schema_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build canonical schema from existing schema JSON.
        
        Args:
            schema_json: Schema JSON (may be partial or non-canonical)
            
        Returns:
            Canonical schema dictionary
        """
        tables = schema_json.get("tables", [])
        
        # Collect any existing warnings
        if "warnings" in schema_json:
            self.warnings = schema_json["warnings"]
        
        return self.build_from_tables(tables)
    
    def build_from_tables(self, tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build canonical schema from parsed table definitions.
        
        Args:
            tables: List of table definitions
            
        Returns:
            Canonical schema dictionary with tables, DAG, and warnings
        """
        self.warnings = self.warnings or []
        
        # Normalize tables
        normalized_tables = []
        tables_dict = {table["name"]: table for table in tables}
        
        for table in tables:
            normalized = self._normalize_table(table, tables_dict)
            normalized_tables.append(normalized)
        
        # Build dependency graph
        graph = build_schema_graph(normalized_tables)
        dag = graph.to_dict()
        
        # Detect junction tables
        junction_tables = [
            table["name"] for table in normalized_tables
            if graph.is_junction_table(table["name"], tables_dict)
        ]
        
        # Add warnings for cycles
        if dag["has_cycles"]:
            for cycle in dag["cycles"]:
                self.warnings.append(
                    f"Circular dependency detected: {' -> '.join(cycle)}"
                )
        
        # Validate foreign keys
        self._validate_foreign_keys(normalized_tables, tables_dict)
        
        # Build canonical schema
        canonical = {
            "tables": normalized_tables,
            "dag": dag,
            "metadata": {
                "table_count": len(normalized_tables),
                "total_columns": sum(
                    len(table.get("columns", [])) for table in normalized_tables
                ),
                "junction_tables": junction_tables,
            },
            "warnings": self.warnings
        }
        
        return canonical
    
    def _normalize_table(
        self,
        table: Dict[str, Any],
        tables_dict: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Normalize table definition to canonical format."""
        normalized = {
            "name": table["name"],
            "columns": self._normalize_columns(table.get("columns", [])),
            "primary_key": table.get("primary_key", []),
            "unique_constraints": self._normalize_constraints(
                table.get("unique_constraints", [])
            ),
            "check_constraints": self._normalize_constraints(
                table.get("check_constraints", [])
            ),
            "foreign_keys": self._normalize_foreign_keys(
                table.get("foreign_keys", [])
            )
        }
        
        # Remove empty collections
        if not normalized["unique_constraints"]:
            del normalized["unique_constraints"]
        if not normalized["check_constraints"]:
            del normalized["check_constraints"]
        if not normalized["foreign_keys"]:
            del normalized["foreign_keys"]
        
        return normalized
    
    def _normalize_columns(self, columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize column definitions."""
        normalized = []
        
        for col in columns:
            norm_col = {
                "name": col["name"],
                "dtype": col.get("dtype", "UNKNOWN"),
                "nullable": col.get("nullable", True)
            }
            
            # Add optional fields if present
            if "default" in col:
                norm_col["default"] = col["default"]
            if "pii_tag" in col:
                norm_col["pii_tag"] = col["pii_tag"]
            
            normalized.append(norm_col)
        
        return normalized
    
    def _normalize_constraints(
        self,
        constraints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Normalize constraint definitions."""
        normalized = []
        
        for constraint in constraints:
            norm_constraint = {}
            
            # Add name if present
            if "name" in constraint and constraint["name"]:
                norm_constraint["name"] = constraint["name"]
            
            # Add columns for unique constraints
            if "columns" in constraint:
                norm_constraint["columns"] = constraint["columns"]
            
            # Add expression for check constraints
            if "expression" in constraint:
                norm_constraint["expression"] = constraint["expression"]
            
            if norm_constraint:
                normalized.append(norm_constraint)
        
        return normalized
    
    def _normalize_foreign_keys(
        self,
        foreign_keys: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Normalize foreign key definitions."""
        normalized = []
        
        for fk in foreign_keys:
            norm_fk = {
                "from_columns": fk.get("from_columns", []),
                "to_table": fk["to_table"],
                "to_columns": fk.get("to_columns", [])
            }
            
            # Add name if present
            if "name" in fk and fk["name"]:
                norm_fk["name"] = fk["name"]
            
            normalized.append(norm_fk)
        
        return normalized
    
    def _validate_foreign_keys(
        self,
        tables: List[Dict[str, Any]],
        tables_dict: Dict[str, Dict]
    ) -> None:
        """Validate foreign key references."""
        table_names = {table["name"] for table in tables}
        
        for table in tables:
            table_name = table["name"]
            
            for fk in table.get("foreign_keys", []):
                to_table = fk["to_table"]
                
                # Check if referenced table exists
                if to_table not in table_names:
                    self.warnings.append(
                        f"Table '{table_name}': Foreign key references "
                        f"unknown table '{to_table}'"
                    )
                    continue
                
                # Check if referenced columns exist
                if to_table in tables_dict:
                    ref_table = tables_dict[to_table]
                    ref_col_names = {
                        col["name"] for col in ref_table.get("columns", [])
                    }
                    
                    for to_col in fk["to_columns"]:
                        if to_col not in ref_col_names:
                            self.warnings.append(
                                f"Table '{table_name}': Foreign key references "
                                f"unknown column '{to_col}' in table '{to_table}'"
                            )
                
                # Check if source columns exist
                source_col_names = {
                    col["name"] for col in table.get("columns", [])
                }
                
                for from_col in fk["from_columns"]:
                    if from_col not in source_col_names:
                        self.warnings.append(
                            f"Table '{table_name}': Foreign key uses "
                            f"unknown column '{from_col}'"
                        )
                
                # Check if column count matches
                if len(fk["from_columns"]) != len(fk["to_columns"]):
                    self.warnings.append(
                        f"Table '{table_name}': Foreign key column count mismatch "
                        f"({len(fk['from_columns'])} vs {len(fk['to_columns'])})"
                    )


def build_canonical_schema(
    ddl_sql: Optional[str] = None,
    schema_json: Optional[Dict[str, Any]] = None,
    dialect: str = "postgres"
) -> Dict[str, Any]:
    """
    Build canonical schema from DDL or existing schema JSON.
    
    Args:
        ddl_sql: DDL SQL statements (optional)
        schema_json: Existing schema JSON (optional)
        dialect: SQL dialect for DDL parsing
        
    Returns:
        Canonical schema dictionary
        
    Raises:
        ValueError: If neither ddl_sql nor schema_json is provided
    """
    builder = SchemaBuilder()
    
    if ddl_sql:
        return builder.build_from_ddl(ddl_sql, dialect=dialect)
    elif schema_json:
        return builder.build_from_json(schema_json)
    else:
        raise ValueError("Either ddl_sql or schema_json must be provided")
