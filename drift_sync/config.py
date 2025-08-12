from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import yaml


@dataclass
class RepoConfig:
    name: str
    url: str
    branch: str = "main"
    paths: List[str] = None


@dataclass
class ClusterConfig:
    name: str
    kubeconfig_context: str
    repos: List[RepoConfig]


@dataclass
class Settings:
    output_dir: str = "out"
    ignore_k8s_fields: List[str] = None


DEFAULT_IGNORES = [
    "metadata.resourceVersion",
    "metadata.uid",
    "metadata.creationTimestamp",
    "metadata.generation",
    "metadata.managedFields",
    "metadata.annotations.kubectl.kubernetes.io/last-applied-configuration",
    "status",
]


def _dict_to_repo(d: dict) -> RepoConfig:
    return RepoConfig(
        name=d["name"],
        url=d["url"],
        branch=d.get("branch", "main"),
        paths=d.get("paths", []),
    )


def _dict_to_cluster(d: dict) -> ClusterConfig:
    repos = [_dict_to_repo(x) for x in d.get("repos", [])]
    return ClusterConfig(
        name=d["name"],
        kubeconfig_context=d["kubeconfig_context"],
        repos=repos,
    )


def _dict_to_settings(d: dict | None) -> Settings:
    if not d:
        return Settings(ignore_k8s_fields=DEFAULT_IGNORES)
    return Settings(
        output_dir=d.get("output_dir", "out"),
        ignore_k8s_fields=d.get("ignore_k8s_fields", DEFAULT_IGNORES),
    )


def load_config(path: Path) -> Tuple[List[ClusterConfig], Settings]:
    """Load YAML configuration and return clusters and settings."""
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    clusters = [_dict_to_cluster(x) for x in raw.get("clusters", [])]
    settings = _dict_to_settings(raw.get("settings"))
    return clusters, settings 