# Compatibility Policy

## Release family
v3.2.0 builds on the public runtime/tooling foundation of v3.1.1.

## Compatibility goals
- preserve existing core CLI commands where possible
- continue loading supported v3.1.x artifact forms unless explicitly documented otherwise
- prefer additive JSON output fields over breaking renames
- make new integration APIs additive first

## Breaking-change standard
A change is considered breaking if it:
- removes an existing CLI command or flag in common use
- changes artifact loading behavior without explicit documentation
- changes key output structure relied on by examples/tests
- breaks existing validation workflows without replacement guidance
