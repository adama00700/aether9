# Changelog

All notable changes to Aether-9 are documented here.

---

## [2.4.0] — 2026-04-10

### Added
- `while` loop with `and` / `or` compound conditions
- Standard library: `abs`, `min`, `max`, `mod`, `dr`, `str`, `len`, `concat`
- `and` / `or` operators in all boolean expressions

### Fixed
- `while` conditions now correctly support compound expressions

---

## [2.3.0] — 2026-04-09

### Added
- I/O support: `write(filename, value)`, `read(filename)`, `input(prompt)`
- `StringNode` in AST — string literals usable in function arguments
- `_a9_str`, `_a9_len` runtime functions

---

## [2.2.0] — 2026-04-09

### Added
- Nested lattice calls — a `lattice` can call another `lattice`
- `SemanticAnalyzer` — detects forward references at compile time
- Three-level call chains (a → b → c)
- Nested calls inside `if/else` and `for` loops

---

## [2.1.0] — 2026-04-08

### Added
- `if / else` control flow inside lattice functions
- `for` loops over defined arrays
- Colored error messages with `hint:` suggestions
- `and` / `or` keywords (initial support)

---

## [2.0.0] — 2026-04-08

### Breaking
- Replaced regex-based `Transpiler` with a full compiler pipeline

### Added
- `Lexer` — tokenizes Aether-9 source with indentation tracking
- `Parser` — builds a typed AST
- `CodeGenerator` — emits standalone Python with embedded runtime
- `BindingError`, `ParseError`, `LexError`, `CompileError` with line numbers

### Removed
- `AetherTranspiler` (replaced by `Aether9Compiler`)

---

## [1.0.0] — 2026-04-07

### Added
- Initial release
- `AetherTranspiler` — regex-based source transformation
- `VortexSequencer` — non-commutative spatial hash
- `lattice_equilibrium` decorator
- `.a9s` signature file system (SHA-256 + VortexSeal + global seal)
- CLI: `compile`, `run`, `verify`, `inspect`
- Published to PyPI
