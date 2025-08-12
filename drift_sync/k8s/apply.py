from __future__ import annotations

from typing import Dict, Optional

from kubernetes.dynamic import DynamicClient

from .fetcher import get_resource_handle


class Remediator:
    def __init__(self, dyn: DynamicClient):
        self.dyn = dyn

    def apply_desired(self, desired: Dict, dry_run: bool = True) -> None:
        api_version = desired.get("apiVersion")
        kind = desired.get("kind")
        metadata = desired.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace")
        res = get_resource_handle(self.dyn, api_version, kind)
        params = {"dry_run": "All"} if dry_run else {}
        try:
            if namespace:
                res.get(name=name, namespace=namespace)
            else:
                res.get(name=name)
            # exists -> replace
            if namespace:
                res.replace(body=desired, name=name, namespace=namespace, **params)
            else:
                res.replace(body=desired, name=name, **params)
        except Exception:
            # not found -> create
            if namespace:
                res.create(body=desired, namespace=namespace, **params)
            else:
                res.create(body=desired, **params)

    def delete_live(self, live: Dict, dry_run: bool = True) -> None:
        api_version = live.get("apiVersion")
        kind = live.get("kind")
        metadata = live.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace")
        res = get_resource_handle(self.dyn, api_version, kind)
        params = {"dry_run": "All"} if dry_run else {}
        if namespace:
            res.delete(name=name, namespace=namespace, **params)
        else:
            res.delete(name=name, **params) 