from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table

from .config import load_config, Settings
from .gitops.repo import RepoManager
from .gitops.parser import DesiredStateLoader
from .k8s.client import build_dynamic_client
from .drift.detector import DriftDetector
from .report.writer import ReportWriter
from .k8s.apply import Remediator

app = typer.Typer(add_completion=False, help="Detect, report, and remediate Kubernetes configuration drift across clusters.")
console = Console()


def _timestamp_folder(base_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = base_dir / ts
    out.mkdir(parents=True, exist_ok=True)
    return out


@app.command()
def scan(
    config: Path = typer.Option(Path("config.yaml"), help="Path to config file"),
    output_dir: Optional[Path] = typer.Option(None, help="Output directory for reports"),
    formats: List[str] = typer.Option(["json", "md"], help="Report formats: json, md"),
    include_extras: bool = typer.Option(True, help="Detect resources present in cluster but not in Git"),
):
    """Scan clusters and generate drift reports."""
    cfg, settings = load_config(config)
    base_out = Path(output_dir or settings.output_dir)
    run_out = _timestamp_folder(base_out)

    repo_mgr = RepoManager(base_cache_dir=Path(".cache/repos"))
    desired_loader = DesiredStateLoader()
    report_writer = ReportWriter()

    for cluster in cfg:
        console.rule(f"[bold]Cluster: {cluster.name}")
        try:
            dyn = build_dynamic_client(cluster.kubeconfig_context)
        except Exception as exc:
            console.print(f"[red]Failed to connect cluster '{cluster.name}': {exc}")
            continue

        desired_objects = []
        for repo in cluster.repos:
            repo_path = repo_mgr.ensure_repo(repo)
            desired_objects.extend(desired_loader.load_desired_objects(repo_path, repo.paths))

        detector = DriftDetector(ignore_fields=settings.ignore_k8s_fields)
        report = detector.detect(dyn, desired_objects, include_extras=include_extras)

        # Write reports
        if "json" in formats:
            report_writer.write_json(report, run_out / f"{cluster.name}.json")
        if "md" in formats:
            report_writer.write_markdown(report, run_out / f"{cluster.name}.md")

        # Console summary table
        table = Table(title=f"Drift Summary - {cluster.name}")
        table.add_column("Status")
        table.add_column("Count", justify="right")
        table.add_row("NoDrift", str(report.summary.no_drift))
        table.add_row("Changed", str(report.summary.changed))
        table.add_row("MissingInCluster", str(report.summary.missing))
        table.add_row("ExtraInCluster", str(report.summary.extra))
        console.print(table)

    console.print(f"Reports written to: [bold]{run_out}[/bold]")


@app.command()
def remediate(
    config: Path = typer.Option(Path("config.yaml"), help="Path to config file"),
    cluster_name: Optional[str] = typer.Option(None, help="Only remediate a specific cluster"),
    apply: bool = typer.Option(False, help="Actually apply changes (otherwise dry-run)"),
    delete_extras: bool = typer.Option(False, help="Delete resources that are only in cluster (not in Git)"),
):
    """Apply desired state to remediate drift."""
    cfg, settings = load_config(config)

    repo_mgr = RepoManager(base_cache_dir=Path(".cache/repos"))
    desired_loader = DesiredStateLoader()

    for cluster in cfg:
        if cluster_name and cluster.name != cluster_name:
            continue
        console.rule(f"[bold]Remediation - Cluster: {cluster.name}")
        try:
            dyn = build_dynamic_client(cluster.kubeconfig_context)
        except Exception as exc:
            console.print(f"[red]Failed to connect cluster '{cluster.name}': {exc}")
            continue

        desired_objects = []
        for repo in cluster.repos:
            repo_path = repo_mgr.ensure_repo(repo)
            desired_objects.extend(desired_loader.load_desired_objects(repo_path, repo.paths))

        detector = DriftDetector(ignore_fields=settings.ignore_k8s_fields)
        report = detector.detect(dyn, desired_objects, include_extras=True)

        remediator = Remediator(dyn)
        changes = 0
        for item in report.items:
            if item.status in ("MissingInCluster", "Changed"):
                changes += 1
                console.print(f"[yellow]Applying: {item.key}")
                remediator.apply_desired(item.desired_object, dry_run=not apply)
            elif delete_extras and item.status == "ExtraInCluster":
                changes += 1
                console.print(f"[yellow]Deleting extra: {item.key}")
                remediator.delete_live(item.live_object, dry_run=not apply)

        if changes == 0:
            console.print("[green]No changes required.")
        elif not apply:
            console.print("[cyan]Dry-run complete. Re-run with --apply to enforce changes.")
        else:
            console.print("[green]Remediation complete.")


@app.command()
def list_clusters(
    config: Path = typer.Option(Path("config.yaml"), help="Path to config file"),
):
    """List clusters configured in the tool."""
    cfg, _ = load_config(config)
    for cluster in cfg:
        console.print(f"- {cluster.name} (context={cluster.kubeconfig_context})")


if __name__ == "__main__":
    app() 