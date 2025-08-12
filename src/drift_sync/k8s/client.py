from __future__ import annotations

from kubernetes import config
from kubernetes.dynamic import DynamicClient
from kubernetes import client as k8s_client


def build_dynamic_client(context_name: str) -> DynamicClient:
    """Build a DynamicClient using the provided kubeconfig context."""
    config.load_kube_config(context=context_name)
    api_client = k8s_client.ApiClient()
    return DynamicClient(api_client) 