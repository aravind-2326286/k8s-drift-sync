# k8s-drift-sync

A Python CLI to detect, report, and remediate configuration drift between Kubernetes clusters and the desired state defined in Git repositories.

### Features
- Detect drift by comparing live cluster resources with Git-managed manifests
- Report results to JSON and Markdown
- Optionally include extras found only in the cluster
- Remediate drift via apply (create/replace) and optional delete of extras
- Multi-cluster, multi-repo support

### Requirements
- Python 3.10+
- Access to Kubernetes clusters via kubeconfig contexts
- Git access to the desired state repositories

### Quick start
1. Create and activate a virtual environment
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Copy and edit the example config
```bash
cp config.example.yaml config.yaml
# Edit contexts, repos, and paths
```

3. Run a drift scan
```bash
python -m drift_sync.cli scan --config config.yaml
```
Outputs are written under `out/<timestamp>/` as JSON and Markdown.

4. Remediate (dry-run by default)
```bash
python -m drift_sync.cli remediate --config config.yaml --cluster-name dev
```
Apply for real by adding `--apply`. To delete extras found only in the cluster, add `--delete-extras`.

### Configuration
See `config.example.yaml`:
- `clusters[].kubeconfig_context`: name of context from your kubeconfig
- `clusters[].repos[]`: Git repo with desired state
  - `branch`: branch to track
  - `paths[]`: directories or files containing Kubernetes YAML
- `settings.output_dir`: where reports are written
- `settings.ignore_k8s_fields`: fields ignored in diffing (non-declarative fields)

### How it works
- Git repos are cloned/updated to `.cache/repos/<name>`
- YAML manifests are loaded from configured paths
- The tool queries the live cluster using the Kubernetes dynamic client
- A DeepDiff comparison detects changes, ignoring configured fields
- Reports summarize NoDrift, Changed, MissingInCluster, ExtraInCluster
- Remediation uses server-side create/replace and optional delete

### Commands
- `scan`: produce drift reports
  - `--formats [json md]`
  - `--include-extras / --no-include-extras`
  - `--output-dir <dir>`
- `remediate`: apply desired state and optionally delete extras
  - `--apply` to actually apply changes
  - `--delete-extras` to delete cluster-only resources
  - `--cluster-name <name>` to limit scope
- `list-clusters`: show clusters from config

### Notes & limitations
- CRDs must be installed in the cluster for CRs to be listed/fetched
- Namespaced vs cluster-scoped resources are handled by presence of `metadata.namespace`
- The dynamic client may require extra RBAC permissions (get, list, create, update, delete)
- Replace operations might fail for immutable fields; adjust manifests as needed

### Development
- Run tests
```bash
pytest -q
```

- Code layout
```
drift_sync/
  cli.py                # Typer CLI entrypoint
  config.py             # YAML config loader
  gitops/               # Git clone/update and manifest loading
  k8s/                  # K8s dynamic client helpers
  drift/                # Drift models and detector
  report/               # Report writers (JSON/Markdown)
  utils/                # Utilities
```

### Roadmap
- Pluggable ignore rules per-kind
- Parallelized cluster and repo operations
- Output SARIF and HTML reports
- GitHub Actions integration example