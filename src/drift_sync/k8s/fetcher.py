from __future__ import annotations

from typing import Any, Dict, Optional

from kubernetes.dynamic import DynamicClient


def get_resource_handle(dyn: DynamicClient, api_version: str, kind: str):
    return dyn.resources.get(api_version=api_version, kind=kind)


def fetch_live_for_desired(dyn: DynamicClient, desired: Dict) -> Optional[Dict]:
    api_version = desired.get("apiVersion")
    kind = desired.get("kind")
    metadata = desired.get("metadata", {})
    name = metadata.get("name")
    namespace = metadata.get("namespace")
    res = get_resource_handle(dyn, api_version, kind)
    try:
        if namespace:
            live = res.get(name=name, namespace=namespace)
        else:
            live = res.get(name=name)
    except Exception:
        return None
    return live.to_dict() if hasattr(live, "to_dict") else live 