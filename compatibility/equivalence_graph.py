from __future__ import annotations

import hashlib
from collections import defaultdict

from compatibility.models import Candidate
from compatibility.normalization import normalize_code


class EquivalenceGraph:
    """
    Agrupa códigos relacionados sem propagar aplicação.

    O cluster é evidência de família de referência, nunca uma autorização para
    copiar veículo/ano/motor de um nó para outro.
    """

    def __init__(self):
        self.parent: dict[str, str] = {}
        self.sources: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.oem_nodes: set[str] = set()

    def _add(self, node: str) -> None:
        if node and node not in self.parent:
            self.parent[node] = node

    def find(self, node: str) -> str:
        self._add(node)
        if self.parent[node] != node:
            self.parent[node] = self.find(self.parent[node])
        return self.parent[node]

    def union(self, left: str, right: str, source: str | None = None) -> None:
        left = normalize_code(left)
        right = normalize_code(right)
        if not left or not right or left == right:
            return
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left
        edge = tuple(sorted((left, right)))
        if source:
            self.sources[edge].add(source)

    def add_candidate(self, candidate: Candidate) -> None:
        self._add(candidate.normalized_code)
        for reference in candidate.references:
            target = normalize_code(reference.code)
            self.union(candidate.normalized_code, target, reference.source)
            if reference.is_oem:
                self.oem_nodes.add(target)

    def cluster_nodes(self, code: str) -> set[str]:
        normalized = normalize_code(code)
        if not normalized:
            return set()
        root = self.find(normalized)
        return {node for node in self.parent if self.find(node) == root}

    def cluster_id(self, code: str) -> str | None:
        nodes = sorted(self.cluster_nodes(code))
        if len(nodes) <= 1:
            return None
        digest = hashlib.sha1("|".join(nodes).encode("utf-8")).hexdigest()[:12]
        return f"eq-{digest}"

    def oem_refs(self, code: str) -> set[str]:
        return self.cluster_nodes(code) & self.oem_nodes

    def independent_source_count(self, code: str) -> int:
        nodes = self.cluster_nodes(code)
        sources: set[str] = set()
        for edge, edge_sources in self.sources.items():
            if edge[0] in nodes and edge[1] in nodes:
                sources.update(edge_sources)
        return len(sources)
