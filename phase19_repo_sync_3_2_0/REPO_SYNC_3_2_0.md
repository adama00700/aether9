# Repository Sync — Aether-9 v3.2.0

This package is the GitHub-ready repository sync for **Aether-9 v3.2.0**.

## Include in GitHub

Copy these into the clean repository:

- `aether9/`
- `docs/`
- `examples/`
- `planning/`
- `tests/`
- `validation/`
- `README.md`
- `CHANGELOG.md`
- `RELEASE_NOTES_3_2_0.md`
- `FINAL_READINESS_REPORT_3_2_0.md`
- `pyproject.toml`
- `MANIFEST.in`
- `.gitignore`
- `REPO_SYNC_3_2_0.md`

## Do not commit

The `.gitignore` excludes wheels, build outputs, zip files, generated `.a9b` artifacts, generated `.a9s` signatures, local virtual environments, cache files, and local secrets.

## Recommended Git commands

From a clean clone:

```bat
cd /d D:\aether_core\aether9-clean
robocopy "D:\aether_core\phase19_repo_sync_3_2_0" "D:\aether_core\aether9-clean" /E
git status
git add .
git commit -m "Sync repository for Aether-9 v3.2.0"
git push origin main
git tag v3.2.0
git push origin v3.2.0
```

If tag `v3.2.0` already exists locally or remotely:

```bat
git tag -d v3.2.0
git tag v3.2.0
git push --force origin v3.2.0
```

## GitHub Release title

```text
Aether-9 v3.2.0 — Integration-Ready Platform
```

## PyPI

```bash
pip install aether9==3.2.0
```
