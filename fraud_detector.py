"""Graph-based fraud detection engine powered by NetworkX."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import networkx as nx


TRANSACTION_RELATIONSHIP = "TRANSACTION"
IDENTIFIER_RELATIONSHIPS = {"USES_PHONE", "USES_IP", "USES_EMAIL", "USES_DEVICE"}


@dataclass(frozen=True)
class SharedIdentifierFinding:
    """A high-degree identifier hub connected to many accounts."""

    identifier: str
    identifier_type: str
    accounts: list[str]
    degree: int


class FraudDetector:
    """Detect suspicious financial activity using graph algorithms.

    The detector stores all relationships in one directed graph. For each
    algorithm, it projects the relevant subgraph:
    - Transactions: account -> account directed edges for cycle detection.
    - Identifiers: account -> phone/IP/device edges for hub detection.
    """

    def __init__(self, edges: Iterable[dict[str, Any]]) -> None:
        self.graph = nx.DiGraph()
        self._load_edges(edges)

    def _load_edges(self, edges: Iterable[dict[str, Any]]) -> None:
        """Load edge dictionaries into the NetworkX graph."""

        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            relationship = edge["relationship"]

            self.graph.add_node(source, node_type=self._infer_node_type(source))
            self.graph.add_node(target, node_type=self._infer_node_type(target))
            self.graph.add_edge(
                source,
                target,
                relationship=relationship,
                amount=edge.get("amount"),
                currency=edge.get("currency"),
                timestamp=edge.get("timestamp"),
                metadata=edge.get("metadata") or {},
            )

    @staticmethod
    def _infer_node_type(node_id: str) -> str:
        """Infer a node type from the identifier naming convention."""

        if node_id.startswith("ACC-"):
            return "account"
        if node_id.startswith("MERCHANT-"):
            return "merchant"
        if node_id.startswith("PHONE-"):
            return "phone"
        if node_id.startswith("IP-"):
            return "ip"
        if node_id.startswith("EMAIL-"):
            return "email"
        if node_id.startswith("DEVICE-"):
            return "device"
        return "unknown"

    def _transaction_subgraph(self) -> nx.DiGraph:
        """Return only account-to-account transaction edges."""

        transaction_graph = nx.DiGraph()
        for source, target, attributes in self.graph.edges(data=True):
            if attributes.get("relationship") != TRANSACTION_RELATIONSHIP:
                continue
            if self.graph.nodes[source].get("node_type") != "account":
                continue
            if self.graph.nodes[target].get("node_type") != "account":
                continue

            transaction_graph.add_edge(source, target, **attributes)

        return transaction_graph

    def detect_circular_transactions(self, max_cycle_length: int = 6) -> list[list[str]]:
        """Find account transaction loops that may indicate laundering.

        Args:
            max_cycle_length: Safety limit that keeps reports readable and avoids
                very large, low-signal cycles in dense graphs.

        Returns:
            A list of cycles. Each cycle is represented as an ordered list of
            account node IDs with the start node repeated at the end.

        Complexity:
            NetworkX simple_cycles is based on Johnson's algorithm. Its worst-case
            complexity is O((V + E) * (C + 1)), where C is the number of cycles.
        """

        transaction_graph = self._transaction_subgraph()
        cycles: list[list[str]] = []

        for cycle in nx.simple_cycles(transaction_graph):
            if 2 <= len(cycle) <= max_cycle_length:
                cycles.append(self._canonicalize_cycle(cycle))

        return sorted(cycles, key=lambda cycle: (len(cycle), cycle))

    @staticmethod
    def _canonicalize_cycle(cycle: list[str]) -> list[str]:
        """Rotate a cycle so equivalent cycles have stable display ordering."""

        smallest_node = min(cycle)
        start_index = cycle.index(smallest_node)
        ordered = cycle[start_index:] + cycle[:start_index]
        return ordered + [ordered[0]]

    def detect_shared_identifiers(
        self,
        min_accounts: int = 3,
        relationships: set[str] | None = None,
    ) -> list[SharedIdentifierFinding]:
        """Find identifier nodes shared by many accounts.

        Args:
            min_accounts: Minimum number of distinct accounts required to flag a
                phone/IP/device/email node as suspicious.
            relationships: Identifier edge types to consider.

        Returns:
            Sorted shared identifier findings.

        Complexity:
            O(V + E) because each relevant edge is inspected once and grouped by
            target identifier.
        """

        relationships = relationships or IDENTIFIER_RELATIONSHIPS
        identifier_to_accounts: dict[str, set[str]] = {}

        for source, target, attributes in self.graph.edges(data=True):
            if attributes.get("relationship") not in relationships:
                continue
            if self.graph.nodes[source].get("node_type") != "account":
                continue

            identifier_to_accounts.setdefault(target, set()).add(source)

        findings: list[SharedIdentifierFinding] = []
        for identifier, accounts in identifier_to_accounts.items():
            if len(accounts) >= min_accounts:
                findings.append(
                    SharedIdentifierFinding(
                        identifier=identifier,
                        identifier_type=self.graph.nodes[identifier].get(
                            "node_type", "unknown"
                        ),
                        accounts=sorted(accounts),
                        degree=len(accounts),
                    )
                )

        return sorted(findings, key=lambda item: (-item.degree, item.identifier))

    def build_flagged_subgraph(
        self,
        cycles: list[list[str]],
        shared_identifier_findings: list[SharedIdentifierFinding],
    ) -> nx.DiGraph:
        """Build a smaller graph containing only flagged fraud evidence."""

        flagged_nodes: set[str] = set()
        flagged_edges: set[tuple[str, str]] = set()

        for cycle in cycles:
            flagged_nodes.update(cycle)
            for source, target in zip(cycle, cycle[1:]):
                flagged_edges.add((source, target))

        for finding in shared_identifier_findings:
            flagged_nodes.add(finding.identifier)
            flagged_nodes.update(finding.accounts)
            for account in finding.accounts:
                flagged_edges.add((account, finding.identifier))

        subgraph = nx.DiGraph()
        for node in flagged_nodes:
            subgraph.add_node(node, **self.graph.nodes[node])

        for source, target in flagged_edges:
            if self.graph.has_edge(source, target):
                subgraph.add_edge(source, target, **self.graph.edges[source, target])

        return subgraph
