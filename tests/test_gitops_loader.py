from pathlib import Path

from drift_sync.gitops.parser import DesiredStateLoader


def test_desired_state_loader_reads_yaml(tmp_path: Path):
    repo_dir = tmp_path / "repo"
    (repo_dir / "a/b").mkdir(parents=True)
    # Single yaml file
    (repo_dir / "a" / "cm.yaml").write_text(
        """
apiVersion: v1
kind: ConfigMap
metadata:
  name: cm1
  namespace: ns
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: cm2
  namespace: ns
""".strip()
    )
    # Another file deeper
    (repo_dir / "a" / "b" / "cm3.yaml").write_text(
        """
apiVersion: v1
kind: ConfigMap
metadata:
  name: cm3
  namespace: ns
""".strip()
    )

    loader = DesiredStateLoader()
    objs = loader.load_desired_objects(repo_dir, ["a"])  # should recurse and find both files
    names = sorted(o["metadata"]["name"] for o in objs)
    assert names == ["cm1", "cm2", "cm3"]
    # Ensure _origin is set relative to repo
    origins = set(o.get("_origin") for o in objs)
    assert any(str(Path("a") / "cm.yaml") in orig for orig in origins) 