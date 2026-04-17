# Aether-9 v3.2.0 Final Readiness Report

## Decision

Aether-9 v3.2.0 is ready for final release.

## Release Theme

Integration-Ready Platform.

## Delivered

- Integration API pack
- Machine-readable CLI pack
- Artifact contract v2 cleanup
- Integrator docs and examples
- Validation v2 package
- RC2 metadata reporting patch
- Final release packaging

## Manual RC Validation Summary

Validated locally on Windows in a clean virtual environment:

- wheel install
- upgrade from RC1 to RC2
- version check
- Python API import and calls
- binary artifact export / inspect / VM execution
- JSON artifact export / inspect / VM execution
- runtime failure diagnostics
- signature verification JSON

## RC2 Fix Confirmed

`vm --json` now reports JSON artifact metadata correctly as JSON, while binary artifacts continue to report binary metadata correctly.
