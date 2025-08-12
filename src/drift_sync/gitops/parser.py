from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List

import yaml


class DesiredStateLoader:
    """Loads YAML manifests from provided directories within a repo."""

    def _iter_yaml_files(self, base: Path, rel_paths: Iterable[str]) -> Iterable[Path]:
        for rel in rel_paths:
            root = (base / rel).resolve()
            if root.is_file() and root.suffix in {".yml", ".yaml"}:
                yield root
            if root.is_dir():
                for dirpath, _, filenames in os.walk(root):
                    for fn in filenames:
                        if fn.endswith((".yml", ".yaml")):
                            yield Path(dirpath) / fn

    def _iter_yaml_docs(self, path: Path) -> Iterable[Dict]:
        with path.open("r", encoding="utf-8") as f:
            for doc in yaml.safe_load_all(f):
                if isinstance(doc, dict) and doc.get("kind") and doc.get("apiVersion"):
                    doc.setdefault("metadata", {})
                    yield doc

    def load_desired_objects(self, repo_dir: Path, rel_paths: Iterable[str]) -> List[Dict]:
        objects: List[Dict] = []
        for file in self._iter_yaml_files(repo_dir, rel_paths):
            for doc in self._iter_yaml_docs(file):
                # Keep track of origin for reporting
                doc.setdefault("_origin", str(file.relative_to(repo_dir)))
                objects.append(doc)
        return objects 