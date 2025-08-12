from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ResourceKey:
    api_version: str
    kind: str
    namespace: str | None
    name: str

    def __str__(self) -> str:
        ns = self.namespace or "<cluster>"
        return f"{self.api_version}:{self.kind}:{ns}:{self.name}"


@dataclass
class DriftItem:
    key: ResourceKey
    status: str  # NoDrift | Changed | MissingInCluster | ExtraInCluster
    desired_object: Dict | None = None
    live_object: Dict | None = None
    diff: Dict | None = None


@dataclass
class DriftSummary:
    no_drift: int = 0
    changed: int = 0
    missing: int = 0
    extra: int = 0


@dataclass
class DriftReport:
    cluster_name: str | None = None
    items: List[DriftItem] = field(default_factory=list)
    summary: DriftSummary = field(default_factory=DriftSummary) 