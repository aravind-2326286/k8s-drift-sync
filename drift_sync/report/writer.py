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
        lines.append("# Drift Report")
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