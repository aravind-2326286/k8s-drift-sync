from pathlib import Path

from drift_sync.config import load_config


def test_load_template_config(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text((Path("config/config.yaml").read_text()))
    clusters, settings = load_config(cfg_path)
    assert len(clusters) >= 1
    assert settings.output_dir == "out" 