# Aether-9 v3.3.0 Release Notes

## Release theme

**Release Packaging & v3.3.0 Preparation**

This release packages the work completed across the hardening stages into a clean public-ready release.

## Highlights

### VM hardening

- Added explicit `UNARY_NEG` support.
- Added stack underflow protection.
- Added stricter comparison and binary operator validation.
- Added fallback guard for unsupported opcodes.
- Fixed `.a9b` save/load behavior so two-element arrays remain lists and are not converted into tuples.

### CLI hardening

- Formalized subcommands:
  - `compile`
  - `run`
  - `export`
  - `inspect`
  - `disasm`
  - `verify`
- Added `.a9b` support for run, inspect, disasm, and verify.
- Added `export --format json` and `export --format binary`.

### Binary `.a9b` support

- Added binary container magic bytes: `A9B9`.
- Added auto-detection between JSON and binary `.a9b` files.
- Preserved backward compatibility with JSON `.a9b` files.

### Testing

- Added end-to-end VM integration tests.
- Added CLI subprocess tests.
- Added binary container tests.
- Release validation covers source imports, wheel imports, CLI execution, JSON bytecode, and binary bytecode.

## Compatibility

- Python: `>=3.9`
- Existing JSON `.a9b` files remain supported.
- Existing `.a9s` source signature flow remains supported.

## Recommended next step

After v3.3.0, the next major engineering track should be **v4 Rust Runtime**, using this release as the stable behavioral reference.
