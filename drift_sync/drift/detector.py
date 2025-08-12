from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

from deepdiff import DeepDiff
from kubernetes.dynamic import DynamicClient

from .models import DriftItem, DriftReport, DriftSummary, ResourceKey
from ..k8s.fetcher import fetch_live_for_desired, get_resource_handle


def _make_key(obj: Dict) -> ResourceKey:
    md = obj.get("metadata", {})
    return ResourceKey(
        api_version=obj.get("apiVersion"),
        kind=obj.get("kind"),
        namespace=md.get("namespace"),
        name=md.get("name"),
    )


def _prune(obj: Dict, ignore_fields: Iterable[str]) -> Dict:
    def delete_path(d: Dict, path: List[str]):
        cur = d
        for i, part in enumerate(path):
            if isinstance(cur, dict) and part in cur:
                if i == len(path) - 1:
                    del cur[part]
                else:
                    cur = cur[part]
            else:
                return

    copy = {} if obj is None else dict(obj)
    # Deep copy manually to avoid importing more libs
    import copy as _copy

    clean = _copy.deepcopy(copy)
    for field in ignore_fields:
        delete_path(clean, field.split("."))
    return clean


class DriftDetector:
    def __init__(self, ignore_fields: Iterable[str]):
        self.ignore_fields = list(ignore_fields)

    def detect(self, dyn: DynamicClient, desired_objects: List[Dict], include_extras: bool = True) -> DriftReport:
        report = DriftReport()
        summary = report.summary

        desired_index = {str(_make_key(o)): o for o in desired_objects}
        desired_keys = list(desired_index.keys())

        # Evaluate desired vs live
        for key_str, desired in desired_index.items():
            key = _make_key(desired)
            live = fetch_live_for_desired(dyn, desired)
            if live is None:
                report.items.append(DriftItem(key=key, status="MissingInCluster", desired_object=desired))
                summary.missing += 1
                continue

            desired_clean = _prune(desired, self.ignore_fields)
            live_clean = _prune(live, self.ignore_fields)
            diff = DeepDiff(desired_clean, live_clean, ignore_order=True).to_dict()
            if diff:
                report.items.append(DriftItem(key=key, status="Changed", desired_object=desired, live_object=live, diff=diff))
                summary.changed += 1
            else:
                report.items.append(DriftItem(key=key, status="NoDrift", desired_object=desired, live_object=live, diff=None))
                summary.no_drift += 1

        if include_extras:
            # Detect cluster resources that are not in desired, but only for GVKs present in desired
            from collections import defaultdict

            by_gvk_ns_to_names = defaultdict(lambda: defaultdict(set))
            for desired in desired_objects:
                key = _make_key(desired)
                gvk = (key.api_version, key.kind)
                ns = key.namespace or "__cluster__"
                by_gvk_ns_to_names[gvk][ns].add(key.name)

            for (api_version, kind), ns_to_names in by_gvk_ns_to_names.items():
                res = get_resource_handle(dyn, api_version, kind)
                for ns, desired_names in ns_to_names.items():
                    try:
                        if ns == "__cluster__":
                            listed = res.list().items
                        else:
                            listed = res.list(namespace=ns).items
                    except Exception:
                        continue
                    for item in listed:
                        live_obj = item.to_dict() if hasattr(item, "to_dict") else item
                        name = live_obj.get("metadata", {}).get("name")
                        namespace = None if ns == "__cluster__" else ns
                        key = ResourceKey(api_version=api_version, kind=kind, namespace=namespace, name=name)
                        if name not in desired_names:
                            report.items.append(DriftItem(key=key, status="ExtraInCluster", desired_object=None, live_object=live_obj))
                            summary.extra += 1

        return report 