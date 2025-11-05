"""
Schema graph utilities for building and analyzing table dependency DAGs.

Provides functions to build directed acyclic graphs from foreign key relationships
and perform topological sorting for data generation ordering.
"""
from typing import Dict, List, Set, Tuple

from app.schemas.schema import DAGSchema, ForeignKey, TableSchema


def build_dag(tables: List[TableSchema]) -> DAGSchema:
    """
    Build a directed acyclic graph from table foreign key relationships.
    
    Args:
        tables: List of table schemas
        
    Returns:
        DAGSchema with nodes and edges
    """
    nodes = [table.name for table in tables]
    edges: List[List[str]] = []
    
    # Build edges from foreign keys
    for table in tables:
        for fk in table.fks:
            # Edge from table to referenced table (table depends on fk.to_table)
            edges.append([table.name, fk.to_table])
    
    return DAGSchema(nodes=nodes, edges=edges)


def detect_cycles(dag: DAGSchema) -> List[List[str]]:
    """
    Detect cycles in the dependency graph.
    
    Self-referential edges (table → itself) are excluded as they can be handled
    specially during data generation.
    
    Args:
        dag: DAG schema
        
    Returns:
        List of cycles (each cycle is a list of table names)
    """
    # Build adjacency list, excluding self-referential edges
    graph: Dict[str, List[str]] = {node: [] for node in dag.nodes}
    for from_table, to_table in dag.edges:
        # Skip self-referential edges - they're not problematic cycles
        if from_table != to_table and from_table in graph:
            graph[from_table].append(to_table)
    
    cycles: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    current_path: List[str] = []
    
    def dfs(node: str) -> bool:
        """DFS to detect cycles."""
        visited.add(node)
        rec_stack.add(node)
        current_path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = current_path.index(neighbor)
                cycle = current_path[cycle_start:] + [neighbor]
                cycles.append(cycle)
                return True
        
        current_path.pop()
        rec_stack.remove(node)
        return False
    
    for node in dag.nodes:
        if node not in visited:
            dfs(node)
    
    return cycles


def topological_sort(dag: DAGSchema) -> Tuple[List[str], bool]:
    """
    Perform topological sort on the dependency graph.
    
    Returns tables in an order where dependencies come before dependents.
    This is the proper order for data generation.
    
    Args:
        dag: DAG schema
        
    Returns:
        Tuple of (sorted table names, is_valid)
        - sorted table names: List in topological order
        - is_valid: False if cycles exist, True otherwise
    """
    # Check for cycles first
    cycles = detect_cycles(dag)
    if cycles:
        # Return nodes in original order if cycles exist
        return dag.nodes, False
    
    # Build adjacency list and in-degree map, excluding self-referential edges
    graph: Dict[str, List[str]] = {node: [] for node in dag.nodes}
    in_degree: Dict[str, int] = {node: 0 for node in dag.nodes}
    
    for from_table, to_table in dag.edges:
        # Skip self-referential edges - they don't affect generation order
        if from_table != to_table and from_table in graph and to_table in graph:
            graph[from_table].append(to_table)
            in_degree[to_table] += 1
    
    # Kahn's algorithm for topological sort
    queue: List[str] = [node for node in dag.nodes if in_degree[node] == 0]
    sorted_nodes: List[str] = []
    
    while queue:
        # Sort queue to ensure deterministic ordering
        queue.sort()
        node = queue.pop(0)
        sorted_nodes.append(node)
        
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Reverse the order - we want dependencies first
    # (In our edge representation, A->B means A depends on B)
    sorted_nodes.reverse()
    
    return sorted_nodes, True


def get_table_dependencies(table_name: str, dag: DAGSchema) -> List[str]:
    """
    Get all direct dependencies for a table.
    
    Args:
        table_name: Name of the table
        dag: DAG schema
        
    Returns:
        List of table names that this table depends on
    """
    dependencies = []
    for from_table, to_table in dag.edges:
        if from_table == table_name:
            dependencies.append(to_table)
    return dependencies


def get_table_dependents(table_name: str, dag: DAGSchema) -> List[str]:
    """
    Get all direct dependents of a table.
    
    Args:
        table_name: Name of the table
        dag: DAG schema
        
    Returns:
        List of table names that depend on this table
    """
    dependents = []
    for from_table, to_table in dag.edges:
        if to_table == table_name:
            dependents.append(from_table)
    return dependents


def get_root_tables(dag: DAGSchema) -> List[str]:
    """
    Get tables with no dependencies (can be generated first).
    
    Args:
        dag: DAG schema
        
    Returns:
        List of root table names
    """
    has_dependencies = {from_table for from_table, _ in dag.edges}
    return [node for node in dag.nodes if node not in has_dependencies]


def get_leaf_tables(dag: DAGSchema) -> List[str]:
    """
    Get tables that no other tables depend on (can be deleted first).
    
    Args:
        dag: DAG schema
        
    Returns:
        List of leaf table names
    """
    has_dependents = {to_table for _, to_table in dag.edges}
    return [node for node in dag.nodes if node not in has_dependents]


def compute_table_levels(dag: DAGSchema) -> Dict[str, int]:
    """
    Compute the dependency level for each table.
    
    Level 0 = no dependencies (root tables)
    Level 1 = depends only on level 0 tables
    Level N = depends on at least one level N-1 table
    
    Args:
        dag: DAG schema
        
    Returns:
        Dictionary mapping table name to level
    """
    # Build adjacency list, excluding self-referential edges
    graph: Dict[str, List[str]] = {node: [] for node in dag.nodes}
    for from_table, to_table in dag.edges:
        # Skip self-referential edges for level computation
        if from_table != to_table and from_table in graph and to_table in graph:
            graph[from_table].append(to_table)
    
    levels: Dict[str, int] = {}
    
    def compute_level(node: str, visited: Set[str]) -> int:
        """Recursively compute level for a node."""
        if node in levels:
            return levels[node]
        
        if node in visited:
            # Cycle detected, return -1
            return -1
        
        visited.add(node)
        dependencies = graph.get(node, [])
        
        if not dependencies:
            level = 0
        else:
            dep_levels = [compute_level(dep, visited.copy()) for dep in dependencies]
            if -1 in dep_levels:
                level = -1  # Cycle in dependencies
            else:
                level = max(dep_levels) + 1
        
        levels[node] = level
        return level
    
    for node in dag.nodes:
        if node not in levels:
            compute_level(node, set())
    
    return levels


def get_generation_order(dag: DAGSchema) -> List[List[str]]:
    """
    Get tables grouped by dependency level for parallel generation.
    
    Returns tables in groups where all tables in a group can be generated
    in parallel (they have the same dependency level).
    
    Args:
        dag: DAG schema
        
    Returns:
        List of groups, where each group is a list of table names
    """
    levels = compute_table_levels(dag)
    
    # Group tables by level
    level_groups: Dict[int, List[str]] = {}
    for table, level in levels.items():
        if level >= 0:  # Skip tables in cycles
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(table)
    
    # Sort groups by level and return
    sorted_levels = sorted(level_groups.keys())
    return [sorted(level_groups[level]) for level in sorted_levels]


def find_junction_tables(tables: List[TableSchema]) -> List[str]:
    """
    Identify junction/bridge tables (many-to-many relationship tables).
    
    A junction table typically has:
    - Two or more foreign keys
    - A composite primary key consisting of the foreign key columns
    - Few or no additional columns
    
    Args:
        tables: List of table schemas
        
    Returns:
        List of junction table names
    """
    junction_tables = []
    
    for table in tables:
        if len(table.fks) >= 2:
            fk_cols = {fk.from_col for fk in table.fks}
            pk_set = set(table.pk)
            
            # Check if PK is composed of FK columns
            if pk_set and fk_cols and pk_set.issubset(fk_cols):
                # Check if there are few non-FK columns
                non_fk_cols = len([c for c in table.columns if c.name not in fk_cols])
                if non_fk_cols <= 2:  # Allow up to 2 extra columns (e.g., timestamps)
                    junction_tables.append(table.name)
    
    return junction_tables
