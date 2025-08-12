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

## Directory structure
```
.
├─ config/
│  ├─ config.yaml                   # Default runtime config (edit this)
│  ├─ config-dev.yml                # Optional dev config (use with --config)
│  ├─ config-uat.yml                # Optional UAT config (use with --config)
│  ├─ config-prod.yml               # Optional prod config (use with --config)
│  └─ config-local.yml              # Optional local override (gitignored; create locally)
├─ src/
│  └─ drift_sync/                    # Application package (src/ layout)
│     ├─ cli.py                      # Typer CLI entrypoint
│     ├─ config.py                   # YAML config loader and dataclasses
│     ├─ drift/                      # Drift models and detection logic
│     ├─ gitops/                     # Git repo and manifest parsing helpers
│     ├─ k8s/                        # Kubernetes client and live operations
│     ├─ report/                     # Report writers (JSON/Markdown)
│     └─ utils/                      # Utilities
├─ deploy/                           # K8s RBAC and CronJob examples
│  ├─ rbac/
│  │  ├─ scan-only.yaml
│  │  ├─ namespace-scan.yaml
│  │  └─ remediation.yaml
│  └─ cronjob.yaml
├─ .github/workflows/drift-scan.yml  # GitHub Actions workflow (manual trigger)
├─ pyproject.toml                    # Package config (src layout)
├─ requirements.txt                  # Python dependencies
├─ Dockerfile                        # Container build
├─ Makefile                          # Common tasks
├─ README.md                         # This guide
└─ tests/                            # Unit tests
```

## Module overview
- `drift_sync/cli.py`: Typer-based CLI with commands:
  - `scan`: detect drift and write reports
  - `remediate`: apply desired state (dry-run by default) and optionally delete extras
  - `list-clusters`: list configured clusters and kubeconfig contexts
- `drift_sync/config.py`: Dataclasses for `RepoConfig`, `ClusterConfig`, `Settings`; YAML loader; default ignore fields.
- `drift_sync/gitops/repo.py`: `RepoManager.ensure_repo` clones/updates repos into `.cache/repos/<name>`, checks out and hard-resets to the configured branch.
- `drift_sync/gitops/parser.py`: Recursively discovers `.yaml`/`.yml` files in configured paths and yields valid Kubernetes objects (adds `_origin`).
- `drift_sync/k8s/client.py`: Builds a Kubernetes `DynamicClient` using a kubeconfig context.
- `drift_sync/k8s/fetcher.py`: Gets live resource matching a desired object (by GVK, name, namespace). Returns dict or `None` if not found.
- `drift_sync/k8s/apply.py`: `Remediator` applies desired resources (create or replace) and deletes extras; honors dry-run via `dry_run=All`.
- `drift_sync/drift/models.py`: Drift data structures: `ResourceKey`, `DriftItem`, `DriftReport`, `DriftSummary`.
- `drift_sync/drift/detector.py`: Core detection logic using DeepDiff and ignore fields; can detect extras for GVKs present in desired.
- `drift_sync/report/writer.py`: Writes JSON and Markdown reports, including cluster name and a summary section.

## Configuration
- Default file: `config/config.yaml` (already present). Edit `kubeconfig_context` and `repos`.
- Local development (optional, preferred locally):
  - Use `config/config-local.yml` for personal overrides/secrets (gitignored).
  - If you don’t see this file, create it by copying the default and editing:
    - macOS/Linux: `cp config/config.yaml config/config-local.yml`
    - Windows PowerShell: `Copy-Item config\config.yaml config\config-local.yml`
  - Discovery order when you do not pass `--config`:
    1) `config/config-local.yml`
    2) `config/config.local.yaml`
    3) `config/config.yaml`
- Environment-specific files (optional):
  - `config/config-dev.yml`, `config/config-uat.yml`, `config/config-prod.yml`
  - Run with a specific file using `--config`, e.g.: `k8s-drift-sync scan --config config/config-dev.yml`

## Usage
- Install and run:
```bash
pip install -e .
k8s-drift-sync scan                 # uses config/config-local.yml if present, else config/config.yaml
k8s-drift-sync remediate --cluster-name dev
```

## How it works (end-to-end)
1. Config loading
   - The CLI reads `config.yaml` via `load_config` in `config.py`.
   - Default ignore fields are applied to skip non-declarative K8s metadata (resourceVersion, uid, managedFields, status, etc.).
2. GitOps desired state
   - For each configured repo, `RepoManager.ensure_repo` clones/updates into `.cache/repos/<name>` and checks out the configured branch.
   - `DesiredStateLoader.load_desired_objects` scans `paths[]` for `.yml`/`.yaml`, loads valid Kubernetes documents, and adds `_origin` for traceability.
3. Kubernetes live state
   - `build_dynamic_client` creates a `DynamicClient` from your kubeconfig context.
   - `fetch_live_for_desired` retrieves the live resource for each desired object by GVK/name/namespace; returns `None` when not found.
4. Drift detection
   - For each desired object:
     - The detector prunes configured ignore fields from both desired and live copies.
     - It runs DeepDiff (`ignore_order=True`) to classify as `NoDrift`, `Changed`, or `MissingInCluster`.
   - If `include_extras=True`:
     - For every GVK present in desired objects, it lists live objects (namespaced or cluster-scoped) and marks any not present in Git as `ExtraInCluster`.
5. Reporting
   - A `DriftReport` is produced per cluster, with `summary` counts and `items`.
   - `ReportWriter` writes JSON and Markdown reports in `out/<timestamp>/`.
6. Remediation
   - For `MissingInCluster` and `Changed`, `Remediator.apply_desired` creates or replaces the resource.
   - For `ExtraInCluster`, `Remediator.delete_live` deletes only when `--delete-extras` is passed.
   - All operations are dry-run by default (uses `dry_run=All`); pass `--apply` to enforce.

## Testing
Run the test suite:
- Windows PowerShell:
```powershell
py -3.10 -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```
- macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```
What tests cover:
- `test_basic.py`: loads the example config and validates settings
- `test_cli_list.py`: runs `list-clusters` and checks output
- `test_gitops_loader.py`: ensures YAML is discovered recursively and `_origin` is set
- `test_detector.py`: exercises all drift paths using monkeypatched K8s calls
- `test_report_writer.py`: validates JSON/Markdown contents

## RBAC and prerequisites
- The kubeconfig context used must allow:
  - `get`, `list` for all resource kinds in scope (to detect/live fetch)
  - `create`, `update`, `delete` to remediate (if you use `--apply` and `--delete-extras`)
- CRDs must be installed to list/fetch their custom resources.

## RBAC options
- Cluster-wide read-only scanning: `deploy/rbac/scan-only.yaml`
- Namespace-scoped read-only scanning: `deploy/rbac/namespace-scan.yaml` (replace `your-namespace`)
- Remediation (create/update/delete): `deploy/rbac/remediation.yaml` (tighten to specific namespaces/kinds in production)

## Report formats
- JSON: machine-readable summary and items
- Markdown: simple human-readable summary
- HTML: richer human-readable report
- SARIF: standardized results for code scanning integrations

Examples:
```bash
# Default (json + md)
k8s-drift-sync scan

# Include HTML and SARIF
k8s-drift-sync scan --formats json md html sarif
```

In GitHub Actions, the provided workflow combines per-cluster `.sarif` files and uploads them to Code Scanning for repository-level visibility.

## Troubleshooting
- Cannot load kubeconfig/context:
  - Verify `kubectl config get-contexts` lists the context in `config.yaml`.
- Permissions errors:
  - Ensure your user/service account has required RBAC for the targeted namespaces/kinds.
- Replace failures due to immutable fields:
  - Update manifests to avoid immutable fields changing; you may need to delete and recreate.
- Git clone/checkout failures:
  - Confirm repo URL/branch and network access; delete `.cache/repos/<name>` and retry.

## CI/CD usage
See ready-to-use workflow in `.github/workflows/drift-scan.yml` (manual trigger; uploads JSON/MD/SARIF artifacts, and SARIF to Code Scanning).

### GitHub Actions (scan nightly and fail on drift)
```yaml
name: Drift Scan
on:
  schedule:
    - cron: '0 2 * * *'  # nightly at 02:00 UTC
  workflow_dispatch: {}

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install .
      - name: Provide kubeconfig
        env:
          KUBECONFIG_B64: ${{ secrets.KUBECONFIG_B64 }}
        run: |
          mkdir -p ~/.kube
          echo "$KUBECONFIG_B64" | base64 -d > ~/.kube/config
      - name: Run scan
        run: |
          k8s-drift-sync scan --config config/config.yaml --formats json md --output-dir out
      - name: Upload reports
        uses: actions/upload-artifact@v4
        with:
          name: drift-reports
          path: out/**
      - name: Fail if drift found (Changed/Missing/Extra > 0)
        run: |
          set -e
          # assumes one JSON file per cluster in the most recent timestamp folder
          latest=$(ls -1d out/* | sort | tail -n1)
          found=0
          for f in "$latest"/*.json; do
            changed=$(jq '.summary.changed' "$f")
            missing=$(jq '.summary.missing' "$f")
            extra=$(jq '.summary.extra' "$f")
            echo "$f => changed=$changed missing=$missing extra=$extra"
            if [ $changed -gt 0 ] || [ $missing -gt 0 ] || [ $extra -gt 0 ]; then
              found=1
            fi
          done
          if [ $found -eq 1 ]; then
            echo "Drift detected. Failing the build." >&2
            exit 1
          fi
```
Notes:
- Provide cluster access securely. Example above uses a base64-encoded kubeconfig in `KUBECONFIG_B64` secret. Prefer cloud-native auth (OIDC to EKS/GKE/AKS) where possible.
- You can run on `pull_request` to gate changes, or on a schedule.

### GitLab CI
```yaml
stages: [scan]

drift_scan:
  stage: scan
  image: python:3.10
  script:
    - pip install -r requirements.txt
    - pip install .
    - mkdir -p ~/.kube && echo "$KUBECONFIG" > ~/.kube/config
    - k8s-drift-sync scan --config config/config.yaml --formats json md --output-dir out
    - | # fail if any drift
      latest=$(ls -1d out/* | sort | tail -n1)
      found=0
      apt-get update && apt-get install -y jq
      for f in "$latest"/*.json; do
        changed=$(jq '.summary.changed' "$f")
        missing=$(jq '.summary.missing' "$f")
        extra=$(jq '.summary.extra' "$f")
        echo "$f => changed=$changed missing=$missing extra=$extra"
        if [ $changed -gt 0 ] || [ $missing -gt 0 ] || [ $extra -gt 0 ]; then
          found=1
        fi
      done
      if [ $found -eq 1 ]; then
        echo "Drift detected. Failing the pipeline." >&2
        exit 1
      fi
  artifacts:
    when: always
    paths:
      - out/
```

## Helm/templated manifests
This tool compares Kubernetes objects as YAML. For Helm-managed apps, use one of these patterns:
- Commit rendered manifests: Use `helm template` (or Helmfile) during your delivery process to produce fully-rendered YAML in a Git directory that `config.yaml` points to.
- Render in CI to a dedicated repo/branch: A CI job renders charts and pushes to a "rendered-manifests" branch; configure `repos[].branch` and `