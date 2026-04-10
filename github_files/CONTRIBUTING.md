# Contributing to Aether-9

## Setup

```bash
git clone https://github.com/adama00700/aether9
cd aether9
pip install -e .
```

## Running tests

```bash
python -m pytest tests/
```

## Adding a new language feature

1. Add token to `TT` enum in `compiler.py`
2. Add keyword to `KEYWORDS` dict (if applicable)
3. Add AST node dataclass
4. Add parse method in `Parser`
5. Add codegen method in `CodeGenerator`
6. Add to `SemanticAnalyzer` if it affects scoping
7. Add test in `tests/`

## Adding a stdlib function

1. Add `_a9_<name>` function to `_RUNTIME` string in `compiler.py`
2. Add mapping in `CodeGenerator._expr` → `_map` dict
3. Add to `STDLIB_BUILTINS` set
4. Add example in `examples/`

## File structure

```
aether9/
├── aether9/
│   ├── compiler.py     ← Lexer + Parser + AST + CodeGen
│   ├── core.py         ← Aether9Core, VortexSequencer
│   ├── signature.py    ← .a9s file system
│   └── cli.py          ← CLI commands
├── examples/           ← .a9 example programs
├── tests/              ← pytest test suite
├── CHANGELOG.md
└── README.md
```
