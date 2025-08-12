from pathlib import Path
import json

from drift_sync.drift.models import DriftReport, DriftItem, DriftSummary, ResourceKey
from drift_sync.report.writer import ReportWriter


def test_report_writer_outputs(tmp_path: Path):
    report = DriftReport(
        cluster_name="dev",
        items=[
            DriftItem(key=ResourceKey("v1", "ConfigMap", "ns", "cm1"), status="NoDrift"),
            DriftItem(key=ResourceKey("v1", "ConfigMap", "ns", "cm2"), status="Changed", diff={"values_changed": {}}),
        ],
        summary=DriftSummary(no_drift=1, changed=1, missing=0, extra=0),
    )

    writer = ReportWriter()
    json_path = tmp_path / "dev.json"
    md_path = tmp_path / "dev.md"

    writer.write_json(report, json_path)
    writer.write_markdown(report, md_path)

    data = json.loads(json_path.read_text())
    assert data["cluster"] == "dev"
    assert data["summary"]["changed"] == 1
    assert any(item["status"] == "Changed" for item in data["items"]) 

    md = md_path.read_text()
    assert "Drift Report - dev" in md
    assert "- Changed: 1" in md 