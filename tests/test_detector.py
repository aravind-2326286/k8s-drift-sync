from pathlib import Path

import pytest

from drift_sync.drift.detector import DriftDetector
from drift_sync.drift.models import ResourceKey


class FakeListResult:
    def __init__(self, items):
        self.items = items


class FakeResource:
    def __init__(self, items_by_ns):
        # items_by_ns: dict ns -> list of dicts
        self.items_by_ns = items_by_ns

    def list(self, namespace=None):
        if namespace is None:
            # cluster-scoped resources case
            return FakeListResult(self.items_by_ns.get("__cluster__", []))
        return FakeListResult(self.items_by_ns.get(namespace, []))


@pytest.fixture
def desired_configmaps():
    return [
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cm-nodrift", "namespace": "ns1"},
            "data": {"k": "v"},
        },
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cm-changed", "namespace": "ns1"},
            "data": {"k": "v1"},
        },
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cm-missing", "namespace": "ns1"},
            "data": {"k": "v"},
        },
    ]


def test_drift_detector_paths(monkeypatch, desired_configmaps):
    # Mock live fetch based on name
    from drift_sync import k8s as _ignored  # ensure module path

    def fake_fetch_live_for_desired(dyn, desired):
        name = desired["metadata"]["name"]
        if name == "cm-nodrift":
            return desired
        if name == "cm-changed":
            live = {**desired, "data": {"k": "v2"}}
            return live
        if name == "cm-missing":
            raise Exception("not found")  # fetcher handles and returns None; here simulate exception path
        return None

    def fake_fetcher_fetch_live(dyn, desired):
        try:
            return fake_fetch_live_for_desired(dyn, desired)
        except Exception:
            return None

    # Fake extras: list returns cm-nodrift and an extra cm-extra
    fake_items = [
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "cm-nodrift", "namespace": "ns1"}},
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "cm-extra", "namespace": "ns1"}},
    ]

    def fake_get_resource_handle(dyn, api_version, kind):
        assert api_version == "v1" and kind == "ConfigMap"
        return FakeResource({"ns1": fake_items})

    # Apply monkeypatches
    monkeypatch.setattr("drift_sync.k8s.fetcher.fetch_live_for_desired", fake_fetcher_fetch_live)
    monkeypatch.setattr("drift_sync.k8s.fetcher.get_resource_handle", fake_get_resource_handle)

    detector = DriftDetector(ignore_fields=["metadata.resourceVersion", "status"])
    report = detector.detect(dyn=None, desired_objects=desired_configmaps, include_extras=True)

    statuses = {str(item.key): item.status for item in report.items}

    def key(api_version, kind, ns, name):
        ns_val = ns if ns is not None else None
        return str(ResourceKey(api_version=api_version, kind=kind, namespace=ns_val, name=name))

    assert statuses[key("v1", "ConfigMap", "ns1", "cm-nodrift")] == "NoDrift"
    assert statuses[key("v1", "ConfigMap", "ns1", "cm-changed")] == "Changed"
    assert statuses[key("v1", "ConfigMap", "ns1", "cm-missing")] == "MissingInCluster"
    assert statuses[key("v1", "ConfigMap", "ns1", "cm-extra")] == "ExtraInCluster"

    s = report.summary
    assert s.no_drift == 1
    assert s.changed == 1
    assert s.missing == 1
    assert s.extra == 1 