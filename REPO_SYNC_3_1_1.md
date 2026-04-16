# Repo Sync Notes for 3.1.1

This file summarizes what should be committed to GitHub for the 3.1.1 repository sync.

## Commit now

- `README.md`
- `CHANGELOG.md`
- `RELEASE_NOTES_3_1_1.md`
- `pyproject.toml`
- `MANIFEST.in`
- `aether9/`
- `docs/`
- `examples/`
- `validation/`
- phase tests if you want the repo to preserve stabilization history:
  - `test_runtime_diagnostics_phase4.py`
  - `test_examples_phase5.py`
  - `test_docs_phase6.py`
  - `test_validation_phase7.py`
  - `test_release_phase8.py`

## Do not commit

These should stay out of the repo:

- `build/`
- `dist/`
- `__pycache__/`
- `*.pyc`
- `*.egg-info/`

## Suggested git flow

```bash
git checkout -b release/3.1.1-sync
git add README.md CHANGELOG.md RELEASE_NOTES_3_1_1.md pyproject.toml MANIFEST.in aether9 docs examples validation .gitignore
# optionally add tests
# git add test_runtime_diagnostics_phase4.py test_examples_phase5.py test_docs_phase6.py test_validation_phase7.py test_release_phase8.py
git commit -m "Sync repository to Aether-9 3.1.1 stabilization state"
```

## Suggested tag flow

After publication and final verification:

```bash
git tag v3.1.1
git push origin v3.1.1
```

## Notes

- This sync is documentation/repository alignment work. It does not change the core architecture direction.
- The main objective is to make GitHub reflect the actual 3.1.1 state already present in the release wheel and supporting packs.
- The next step after this sync is `3.2.0 planning`.
