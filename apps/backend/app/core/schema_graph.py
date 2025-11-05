"""
Schema graph utilities for analyzing table dependencies via foreign keys.

Provides:
- FK dependency graph construction
- Topological sort for dependency ordering
- Cycle detection
"""
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque


class SchemaGraph:
    """Build and analyze foreign key dependency graph."""
    
    def __init__(self):
        """Initialize empty graph."""
        self.edges: List[Tuple[str, str]] = []  # (from_table, to_table)
        self.adjacency: Dict[str, List[str]] = defaultdict(list)
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self.tables: Set[str] = set()
        self._cycles: List[List[str]] = []
    
    def add_table(self, table_name: str) -> None:
        """Add a table to the graph."""
        self.tables.add(table_name)
    
    def add_foreign_key(
        self,
        from_table: str,
        to_table: str,
        from_columns: List[str],
        to_columns: List[str]
    ) -> None:
        """
        Add a foreign key relationship.
        
        Args:
            from_table: Source table with FK
            to_table: Referenced table
            from_columns: FK columns in source table
            to_columns: Referenced columns in target table
        """
        # Add tables
        self.tables.add(from_table)
        self.tables.add(to_table)
        
        # Add edge (from_table depends on to_table)
        edge = (from_table, to_table)
        if edge not in self.edges:
            self.edges.append(edge)
            self.adjacency[from_table].append(to_table)
            self.reverse_adjacency[to_table].append(from_table)
    
    def build_from_schema(self, tables: List[Dict]) -> None:
        """
        Build graph from parsed schema tables.
        
        Args:
            tables: List of table definitions with foreign_keys
        """
        # Add all tables first
        for table in tables:
            self.add_table(table["name"])
        
        # Add foreign key edges
        for table in tables:
            table_name = table["name"]
            for fk in table.get("foreign_keys", []):
                self.add_foreign_key(
                    from_table=table_name,
                    to_table=fk["to_table"],
                    from_columns=fk["from_columns"],
                    to_columns=fk["to_columns"]
                )
    
    def topological_sort(self) -> Tuple[List[str], bool]:
        """
        Perform topological sort on the dependency graph.
        
        Returns tables in dependency order (tables with no dependencies first).
        
        Returns:
            Tuple of (sorted_tables, has_cycles)
            - sorted_tables: List of table names in topological order
            - has_cycles: True if graph contains cycles
        """
        # Count incoming edges for each node
        in_degree = {table: 0 for table in self.tables}
        for from_table in self.adjacency:
            for to_table in self.adjacency[from_table]:
                if to_table in in_degree:
                    in_degree[to_table] += 1
        
        # Find nodes with no incoming edges
        queue = deque([table for table in self.tables if in_degree[table] == 0])
        sorted_tables = []
        
        while queue:
            # Remove node with no incoming edges
            table = queue.popleft()
            sorted_tables.append(table)
            
            # Reduce in-degree for dependent tables
            for dependent in self.reverse_adjacency[table]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check if all tables were processed (no cycles)
        has_cycles = len(sorted_tables) != len(self.tables)
        
        if has_cycles:
            # Find cycles
            self._detect_cycles()
        
        return sorted_tables, has_cycles
    
    def _detect_cycles(self) -> None:
        """Detect cycles in the graph using DFS."""
        self._cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            """DFS helper to detect cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    self._cycles.append(cycle)
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for table in self.tables:
            if table not in visited:
                dfs(table)
    
    def get_cycles(self) -> List[List[str]]:
        """
        Get detected cycles in the graph.
        
        Returns:
            List of cycles, each cycle is a list of table names
        """
        if not self._cycles:
            # Run topological sort to detect cycles
            self.topological_sort()
        return self._cycles
    
    def get_dependencies(self, table_name: str) -> List[str]:
        """
        Get direct dependencies for a table.
        
        Args:
            table_name: Table to get dependencies for
            
        Returns:
            List of table names that this table depends on
        """
        return self.adjacency.get(table_name, [])
    
    def get_dependents(self, table_name: str) -> List[str]:
        """
        Get tables that depend on this table.
        
        Args:
            table_name: Table to get dependents for
            
        Returns:
            List of table names that depend on this table
        """
        return self.reverse_adjacency.get(table_name, [])
    
    def get_all_dependencies(self, table_name: str) -> Set[str]:
        """
        Get all transitive dependencies for a table (BFS).
        
        Args:
            table_name: Table to get all dependencies for
            
        Returns:
            Set of all table names in the dependency tree
        """
        if table_name not in self.tables:
            return set()
        
        visited = set()
        queue = deque([table_name])
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            
            visited.add(current)
            
            # Add dependencies to queue
            for dep in self.adjacency.get(current, []):
                if dep not in visited:
                    queue.append(dep)
        
        # Remove the table itself
        visited.discard(table_name)
        return visited
    
    def get_all_dependents(self, table_name: str) -> Set[str]:
        """
        Get all tables that transitively depend on this table.
        
        Args:
            table_name: Table to get all dependents for
            
        Returns:
            Set of all table names that depend on this table
        """
        if table_name not in self.tables:
            return set()
        
        visited = set()
        queue = deque([table_name])
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            
            visited.add(current)
            
            # Add dependents to queue
            for dependent in self.reverse_adjacency.get(current, []):
                if dependent not in visited:
                    queue.append(dependent)
        
        # Remove the table itself
        visited.discard(table_name)
        return visited
    
    def is_junction_table(self, table_name: str, tables_dict: Dict[str, Dict]) -> bool:
        """
        Detect if a table is a junction/bridge table.
        
        A junction table typically has:
        - 2 or more foreign keys
        - Compound primary key consisting of the FK columns
        - Few or no additional columns
        
        Args:
            table_name: Table to check
            tables_dict: Dictionary of table definitions keyed by name
            
        Returns:
            True if table appears to be a junction table
        """
        if table_name not in tables_dict:
            return False
        
        table = tables_dict[table_name]
        foreign_keys = table.get("foreign_keys", [])
        primary_key = table.get("primary_key", [])
        columns = table.get("columns", [])
        
        # Must have at least 2 FKs
        if len(foreign_keys) < 2:
            return False
        
        # Get all FK columns
        fk_columns = set()
        for fk in foreign_keys:
            fk_columns.update(fk["from_columns"])
        
        # Check if PK is composed of FK columns
        pk_set = set(primary_key)
        if pk_set and pk_set.issubset(fk_columns):
            # Check if table has few additional columns
            non_fk_columns = [
                col for col in columns 
                if col["name"] not in fk_columns
            ]
            # Allow up to 2 additional columns (e.g., created_at, metadata)
            if len(non_fk_columns) <= 2:
                return True
        
        return False
    
    def to_dict(self) -> Dict:
        """
        Export graph as dictionary for JSON serialization.
        
        Returns:
            Dictionary with edges and metadata
        """
        sorted_tables, has_cycles = self.topological_sort()
        
        return {
            "edges": [
                {"from": edge[0], "to": edge[1]}
                for edge in self.edges
            ],
            "topological_order": sorted_tables,
            "has_cycles": has_cycles,
            "cycles": self._cycles if has_cycles else []
        }


def build_schema_graph(tables: List[Dict]) -> SchemaGraph:
    """
    Build a schema graph from parsed table definitions.
    
    Args:
        tables: List of table definitions with foreign_keys
        
    Returns:
        SchemaGraph instance
    """
    graph = SchemaGraph()
    graph.build_from_schema(tables)
    return graph
