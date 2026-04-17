# JSON CLI Contract Notes

Validation v2 verifies machine-readable CLI outputs for:

- `inspect --json`
- `verify --json`
- `vm --json`
- `disasm --json`

## Expected behavior

The JSON payload should be parseable, contain a top-level `success` field, and include command-specific structured metadata.

## Stability rule

For v3.2.0 the JSON contract should evolve additively where possible rather than through breaking field renames.
