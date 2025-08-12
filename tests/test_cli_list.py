from pathlib import Path

from typer.testing import CliRunner

from drift_sync.cli import app


def test_list_clusters_outputs_names(tmp_path: Path):
    cfg = {
        "clusters": [
            {
                "name": "dev",
                "kubeconfig_context": "dev-context",
                "repos": [],
            },
            {
                "name": "prod",
                "kubeconfig_context": "prod-context",
                "repos": [],
            },
        ]
    }
    cfg_path = tmp_path / "config.yaml"
    import yaml

    cfg_path.write_text(yaml.safe_dump(cfg))

    runner = CliRunner()
    result = runner.invoke(app, ["list-clusters", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "dev (context=dev-context)" in result.stdout
    assert "prod (context=prod-context)" in result.stdout 