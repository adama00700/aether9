# Changelog

---

## [3.0.0] — 2026-04-14  🚀 VM Release

### Added
- `AetherVM` — stack-based bytecode interpreter, no `exec()`, no Python runtime
- `BytecodeCompiler` — AST → flat instruction list
- `.a9b` bytecode format (JSON-serializable, save/load)
- `aether vm <file.a9>` — execute via VM directly
- `aether disasm <file.a9>` — show bytecode instructions
- 14 opcodes: LOAD_CONST, LOAD_NAME, STORE_NAME, BINARY_OP, COMPARE,
  JUMP, JUMP_IF_FALSE, JUMP_BACK, FOR_START, FOR_NEXT, FOR_END,
  CALL_FUNC, CALL_BUILTIN, RETURN, PRINT, WRITE, READ, HALT

---

## [2.9.0] — 2026-04-13

### Added
- `ExecutionPolicy` — policy layer controlling what code can do
- Write whitelist: files must be explicitly listed in `.a9policy`
- AST Guard hardening: `type()`, `object()`, dunder attributes blocked
- Memory limit via `resource.setrlimit`
- `ExecutionPolicy.from_file()` / `to_file()` for `.a9policy` files

---

## [2.8.0] — 2026-04-12

### Added
- `Sandbox` — subprocess-based isolated execution
- AST Guard: pre-execution scan blocks `import`, `eval`, `exec`, `open`
- Python `-I -E` flags for isolated subprocess
- `ASTGuardError` with colored messages

---

## [2.7.0] — 2026-04-11

### Changed
- Replaced `digital_root` seals with **HMAC-SHA256**
- `global_seal` → `global_mac` (cryptographically bound to all arrays)
- Per-array `hmac` field replaces `seal` field in `.a9s`
- Signing key configurable via `AETHER9_KEY` env variable

### Removed
- `digital_root` as a security primitive (kept as stdlib function `dr()`)

---

## [2.6.0] — 2026-04-11

### Added
- `pytest` test suite — 84 tests across 4 modules
- `tests/test_lexer.py`, `test_parser.py`, `test_compiler.py`, `test_signature.py`

---

## [2.5.0] — 2026-04-10

### Added
- `aether shell` — interactive REPL with persistent state
- `.help`, `.vars`, `.clear`, `.exit` commands
- Multi-line block support (indent detection)

---

## [2.4.0] — 2026-04-10

### Added
- `while` loops with `and` / `or` compound conditions
- Standard library: `abs`, `min`, `max`, `mod`, `dr`, `str`, `len`, `concat`

---

## [2.3.0] — 2026-04-09

### Added
- I/O: `write(filename, value)`, `read(filename)`, `input(prompt)`
- `StringNode` in AST — string literals in function arguments

---

## [2.2.0] — 2026-04-09

### Added
- Nested lattice calls
- `SemanticAnalyzer` — forward reference detection at compile time

---

## [2.1.0] — 2026-04-08

### Added
- `if / else`, `for` loops
- Colored error messages with `hint:` suggestions

---

## [2.0.0] — 2026-04-08

### Breaking
- Replaced regex `Transpiler` with full compiler pipeline

### Added
- `Lexer` → `Parser` → `AST` → `CodeGenerator`
- Typed error classes with line numbers

---

## [1.0.0] — 2026-04-07

### Added
- Initial release: Parser + CLI + `.a9s` signature files
- `VortexSequencer` spatial hash
- PyPI publication
