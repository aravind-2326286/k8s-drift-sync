from __future__ import annotations

import json
from pathlib import Path
from typing import List

from . import __name__ as _pkg
from ..drift.models import DriftReport


class ReportWriter:
    def write_json(self, report: DriftReport, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "cluster": report.cluster_name,
                    "summary": report.summary.__dict__,
                    "items": [
                        {
                            "key": str(item.key),
                            "status": item.status,
                            "diff": item.diff,
                        }
                        for item in report.items
                    ],
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

    def write_markdown(self, report: DriftReport, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: List[str] = []
        title = f"Drift Report - {report.cluster_name}" if report.cluster_name else "Drift Report"
        lines.append(f"# {title}")
        s = report.summary
        lines.append("")
        lines.append("## Summary")
        lines.append(f"- NoDrift: {s.no_drift}")
        lines.append(f"- Changed: {s.changed}")
        lines.append(f"- MissingInCluster: {s.missing}")
        lines.append(f"- ExtraInCluster: {s.extra}")
        lines.append("")
        lines.append("## Items")
        for item in report.items:
            lines.append(f"- **{item.status}**: `{item.key}`")
        with path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def write_html(self, report: DriftReport, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        title = f"Drift Report - {report.cluster_name}" if report.cluster_name else "Drift Report"
        s = report.summary
        rows = []
        for item in report.items:
            rows.append(
                f"<tr><td>{item.status}</td><td><code>{str(item.key)}</code></td></tr>"
            )
        html = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
h1 {{ font-size: 20px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f2f2f2; }}
.summary {{ margin: 12px 0; }}
.badge {{ display: inline-block; padding: 2px 6px; margin-right: 6px; border-radius: 4px; background: #eee; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class=\"summary\">
  <span class=\"badge\">NoDrift: {s.no_drift}</span>
  <span class=\"badge\">Changed: {s.changed}</span>
  <span class=\"badge\">MissingInCluster: {s.missing}</span>
  <span class=\"badge\">ExtraInCluster: {s.extra}</span>
</div>
<table>
  <thead><tr><th>Status</th><th>Resource</th></tr></thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
</body>
</html>
"""
        with path.open("w", encoding="utf-8") as f:
            f.write(html)

    def write_sarif(self, report: DriftReport, path: Path) -> None:
        """Write a minimal SARIF v2.1.0 file representing drift items as results.
        - Changed/Missing/Extra are treated as "errors"; NoDrift omitted.
        - Rule ids correspond to drift status.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        rules = [
            {
                "id": "Changed",
                "name": "Desired and live differ",
                "shortDescription": {"text": "Resource differs from desired state"},
                "defaultConfiguration": {"level": "error"},
            },
            {
                "id": "MissingInCluster",
                "name": "Desired missing in cluster",
                "shortDescription": {"text": "Resource from Git is missing in cluster"},
                "defaultConfiguration": {"level": "error"},
            },
            {
                "id": "ExtraInCluster",
                "name": "Extra in cluster",
                "shortDescription": {"text": "Resource exists in cluster but not in Git"},
                "defaultConfiguration": {"level": "warning"},
            },
        ]
        results = []
        for item in report.items:
            if item.status == "NoDrift":
                continue
            message = f"{item.status}: {str(item.key)}"
            results.append(
                {
                    "ruleId": item.status,
                    "level": "error" if item.status in ("Changed", "MissingInCluster") else "warning",
                    "message": {"text": message},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": (report.cluster_name or "cluster"),
                                }
                            }
                        }
                    ],
                }
            )
        sarif = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "k8s-drift-sync",
                            "rules": rules,
                        }
                    },
                    "results": results,
                }
            ],
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(sarif, f, indent=2) 