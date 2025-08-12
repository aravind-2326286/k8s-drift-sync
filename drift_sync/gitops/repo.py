from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from git import Repo

from ..config import RepoConfig


@dataclass
class RepoManager:
    base_cache_dir: Path

    def ensure_repo(self, repo_cfg: RepoConfig) -> Path:
        repo_dir = self.base_cache_dir / repo_cfg.name
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        if not repo_dir.exists():
            Repo.clone_from(repo_cfg.url, repo_dir)
        repo = Repo(repo_dir)
        # fetch and checkout branch
        repo.remotes.origin.fetch()
        if repo_cfg.branch in repo.heads:
            repo.git.checkout(repo_cfg.branch)
        else:
            repo.git.checkout("-b", repo_cfg.branch, f"origin/{repo_cfg.branch}")
        repo.git.reset("--hard", f"origin/{repo_cfg.branch}")
        return repo_dir 