"""
Dependency graph implementation with topological sorting.

Provides dependency management and ordering using Kahn's algorithm
for resource deployment sequencing.
"""

from typing import Dict, List, Set
from collections import deque
import logging

logger = logging.getLogger(__name__)


class CyclicDependencyError(Exception):
    """Raised when a circular dependency is detected"""
    def __init__(self, cycle_path: List[str]):
        self.cycle_path = cycle_path
        cycle_str = " → ".join(cycle_path)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class DependencyGraph:
    """
    Manages dependency relationships and provides topological sorting.
    
    Uses Kahn's algorithm for topological sort to determine correct
    deployment order for Azure resources.
    """
    
    def __init__(self):
        """Initialize empty dependency graph"""
        self.graph: Dict[str, List[str]] = {}  # node -> [dependent nodes]
        self.reverse_graph: Dict[str, List[str]] = {}  # node -> [dependency nodes]
        self.nodes: Set[str] = set()
    
    def add_node(self, node: str) -> None:
        """
        Add a node to the graph.
        
        Args:
            node: Node identifier (e.g., resource ID)
        """
        if node not in self.nodes:
            self.nodes.add(node)
            self.graph[node] = []
            self.reverse_graph[node] = []
            logger.debug(f"Added node: {node}")
    
    def add_dependency(self, node: str, depends_on: str) -> None:
        """
        Add a dependency relationship.
        
        Args:
            node: The dependent node
            depends_on: The node that must be deployed first
        """
        # Ensure both nodes exist
        self.add_node(node)
        self.add_node(depends_on)
        
        # Add edge: depends_on -> node
        if node not in self.graph[depends_on]:
            self.graph[depends_on].append(node)
        
        # Add reverse edge for tracking: node <- depends_on
        if depends_on not in self.reverse_graph[node]:
            self.reverse_graph[node].append(depends_on)
        
        logger.debug(f"Added dependency: {node} depends on {depends_on}")
    
    def get_ordered_resources(self) -> List[str]:
        """
        Get resources in topological order using Kahn's algorithm.
        
        Returns:
            List of resource IDs in deployment order
            
        Raises:
            CyclicDependencyError: If circular dependencies detected
        """
        # Calculate in-degree for each node
        in_degree: Dict[str, int] = {node: len(self.reverse_graph[node]) for node in self.nodes}
        
        # Queue of nodes with no dependencies
        queue = deque([node for node in self.nodes if in_degree[node] == 0])
        
        # Result list
        ordered = []
        
        while queue:
            # Remove node with no dependencies
            node = queue.popleft()
            ordered.append(node)
            
            # Reduce in-degree for dependent nodes
            for dependent in self.graph[node]:
                in_degree[dependent] -= 1
                
                # If dependent now has no dependencies, add to queue
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for cycles (remaining nodes with non-zero in-degree)
        remaining = [node for node in self.nodes if in_degree[node] > 0]
        if remaining:
            # Find a cycle path for error message
            cycle_path = self._find_cycle_path(remaining)
            raise CyclicDependencyError(cycle_path)
        
        logger.info(f"Topological sort complete: {len(ordered)} nodes ordered")
        return ordered
    
    def _find_cycle_path(self, nodes_in_cycle: List[str]) -> List[str]:
        """
        Find a representative cycle path from nodes involved in a cycle.
        
        Args:
            nodes_in_cycle: Nodes that are part of circular dependencies
            
        Returns:
            List of nodes forming a cycle
        """
        if not nodes_in_cycle:
            return []
        
        # Start from any node in the cycle
        start = nodes_in_cycle[0]
        path = [start]
        visited = {start}
        current = start
        
        # Follow dependencies until we revisit a node
        while True:
            # Get next node in cycle
            dependencies = [dep for dep in self.reverse_graph[current] if dep in nodes_in_cycle]
            
            if not dependencies:
                # Dead end, try different starting node
                if len(nodes_in_cycle) > 1:
                    return self._find_cycle_path(nodes_in_cycle[1:])
                return path  # Return what we found
            
            next_node = dependencies[0]
            
            if next_node in visited:
                # Found cycle - extract the cycle portion
                cycle_start = path.index(next_node)
                return path[cycle_start:] + [next_node]
            
            path.append(next_node)
            visited.add(next_node)
            current = next_node
            
            # Safety: prevent infinite loops
            if len(path) > len(nodes_in_cycle) * 2:
                return path[:10]  # Return first 10 nodes as sample
    
    def has_cycle(self) -> bool:
        """
        Check if the graph contains any cycles.
        
        Returns:
            True if cycles detected, False otherwise
        """
        try:
            self.get_ordered_resources()
            return False
        except CyclicDependencyError:
            return True
    
    def get_cycle_path(self) -> List[str]:
        """
        Get the cycle path if one exists.
        
        Returns:
            List of nodes forming a cycle, or empty list if no cycle
        """
        try:
            self.get_ordered_resources()
            return []
        except CyclicDependencyError as e:
            return e.cycle_path
    
    def get_dependencies(self, node: str) -> List[str]:
        """
        Get all nodes that the given node depends on.
        
        Args:
            node: Node to query
            
        Returns:
            List of dependency nodes
        """
        return self.reverse_graph.get(node, [])
    
    def get_dependents(self, node: str) -> List[str]:
        """
        Get all nodes that depend on the given node.
        
        Args:
            node: Node to query
            
        Returns:
            List of dependent nodes
        """
        return self.graph.get(node, [])
    
    def get_deployment_batches(self) -> List[List[str]]:
        """
        Get resources grouped into deployment batches.
        
        Resources in the same batch have no dependencies on each other
        and can be deployed in parallel.
        
        Returns:
            List of batches, where each batch is a list of resource IDs
        """
        ordered = self.get_ordered_resources()
        batches: List[List[str]] = []
        deployed: Set[str] = set()
        
        while len(deployed) < len(ordered):
            # Find all resources whose dependencies are satisfied
            batch = []
            for resource in ordered:
                if resource in deployed:
                    continue
                
                # Check if all dependencies are deployed
                dependencies = self.get_dependencies(resource)
                if all(dep in deployed for dep in dependencies):
                    batch.append(resource)
            
            if not batch:
                # This shouldn't happen if topological sort succeeded
                raise RuntimeError("Unable to form deployment batch")
            
            batches.append(batch)
            deployed.update(batch)
        
        logger.info(f"Created {len(batches)} deployment batches")
        return batches
    
    def clear(self) -> None:
        """Clear all nodes and edges from the graph"""
        self.graph.clear()
        self.reverse_graph.clear()
        self.nodes.clear()
        logger.debug("Graph cleared")
