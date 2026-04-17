"""
Aether-9 REPL — interactive shell
Usage: aether shell
"""

import sys
import types
import traceback
from typing import Dict, Any

from .compiler import (
    Aether9Compiler, LexError, ParseError, CompileError,
    Lexer, Parser, ProgramNode,
    ArrayNode, LatticeNode, AssignNode, ReturnNode,
    CallNode, IfNode, ForNode, WhileNode,
    NumberNode, StringNode, IdentNode, BinOpNode,
    CodeGenerator, SemanticAnalyzer, STDLIB_BUILTINS,
    _RUNTIME,
)
from .core import VortexSequencer

# ── colors ──
R="\033[31m"; G="\033[32m"; Y="\033[33m"
C="\033[36m"; B="\033[34m"; DIM="\033[2m"
BOLD="\033[1m"; X="\033[0m"

BANNER = f"""
{BOLD}{C}
  ┌─────────────────────────────────────────┐
  │         Aether-9  interactive shell     │
  │         type .help for commands         │
  └─────────────────────────────────────────┘
{X}"""

HELP = f"""
{Y}Commands:{X}
  .help       show this message
  .vars       show defined variables and lattices
  .clear      reset session state
  .exit       exit the shell

{Y}Language:{X}
  data = [54, 36, 72]          define array
  lattice fn(x) uses data:     define lattice (multi-line)
      return x * 9             indent with 4 spaces, blank line to finish
  result = fn(54)              call lattice
  print(result)                print value

{Y}Tip:{X} Multi-line blocks end with a blank line.
"""


class ReplState:
    """Persists variables, lattices, and arrays across REPL lines."""

    def __init__(self):
        self.namespace: Dict[str, Any] = {}
        self.registry:  Dict[str, Dict] = {}
        self.defined_lattices = set()
        # inject runtime into namespace once
        exec(compile(_RUNTIME, '<runtime>', 'exec'), self.namespace)
        # inject stdlib builtins
        self.namespace['print'] = print

    def show_vars(self):
        arrays   = list(self.registry.keys())
        lattices = list(self.defined_lattices)
        HIDDEN = {'time', 'os', 'print', 'chr'}
        user_vars = {
            k: v for k, v in self.namespace.items()
            if not k.startswith('_')
            and k not in HIDDEN
            and not callable(v)
            and not isinstance(v, types.ModuleType)
        }
        print(f"\n{Y}Arrays:{X}    {arrays or '—'}")
        print(f"{Y}Lattices:{X}  {lattices or '—'}")
        print(f"{Y}Variables:{X} {user_vars or '—'}\n")

    def reset(self):
        self.__init__()
        print(f"{G}Session cleared.{X}")


class ReplCompiler:
    """
    Compiles a single REPL 'chunk' (one statement or block)
    and executes it against the shared ReplState.
    """

    def __init__(self, state: ReplState):
        self.state = state

    def run_chunk(self, source: str):
        source = source.strip()
        if not source:
            return

        try:
            tokens = Lexer(source).tokenize()
            ast    = Parser(tokens).parse()
        except (LexError, ParseError) as e:
            print(e)
            return

        # update registry from new arrays
        for node in ast.body:
            if isinstance(node, ArrayNode):
                raw, seal = VortexSequencer(node.elements).compute_seal()
                self.state.registry[node.name] = {
                    'data': node.elements, 'raw_sig': raw, 'seal': seal
                }

        # semantic check against already-defined + new lattices
        all_lattices = (
            list(self.state.defined_lattices) +
            [n.name for n in ast.body if isinstance(n, LatticeNode)]
        )
        try:
            SemanticAnalyzer().analyze(ast, self.state.registry)
        except CompileError as e:
            print(e)
            return

        # validate bindings
        for node in ast.body:
            if isinstance(node, LatticeNode) and node.binding:
                if node.binding not in self.state.registry:
                    avail = list(self.state.registry.keys()) or ['none']
                    print(
                        f"\n  {BOLD}{R}[CompileError]{X}\n"
                        f"  '{node.name}' uses '{node.binding}' which is not defined.\n"
                        f"  {Y}hint:{X} available arrays: {avail}\n"
                    )
                    return

        # generate code (no _RUNTIME header — already in namespace)
        gen = CodeGenerator(self.state.registry)
        gen._lines = []
        gen._ind   = 0
        for node in ast.body:
            gen._gen(node)
        chunk_code = '\n'.join(gen._lines)

        # track newly defined lattices
        for node in ast.body:
            if isinstance(node, LatticeNode):
                self.state.defined_lattices.add(node.name)

        # execute against persistent namespace
        try:
            exec(compile(chunk_code, '<repl>', 'exec'), self.state.namespace)
            # auto-print last expression result if it's an assignment
            for node in reversed(ast.body):
                if isinstance(node, AssignNode):
                    val = self.state.namespace.get(node.name)
                    if val is not None and not callable(val):
                        print(f"{DIM}→ {node.name} = {val}{X}")
                    break
        except RuntimeError as e:
            print(f"\n  {BOLD}{R}[RuntimeError]{X}\n  {e}\n")
        except Exception as e:
            print(f"\n  {BOLD}{R}[Error]{X}\n  {e}\n")


def _is_block_start(line: str) -> bool:
    """Does this line open an indented block?"""
    stripped = line.rstrip()
    return stripped.endswith(':') and not stripped.startswith('#')


def run_shell():
    """Main REPL loop."""
    print(BANNER)

    state    = ReplState()
    compiler = ReplCompiler(state)

    buffer    = []       # accumulated lines for multi-line input
    in_block  = False    # are we inside an indented block?

    while True:
        try:
            prompt = f"  {C}...{X} " if in_block else f"{BOLD}{C}a9>{X} "
            line   = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}bye.{X}")
            break

        # ── dot commands ──
        stripped = line.strip()
        if not in_block:
            if stripped == '.exit':
                print(f"{DIM}bye.{X}")
                break
            if stripped == '.help':
                print(HELP)
                continue
            if stripped == '.vars':
                state.show_vars()
                continue
            if stripped == '.clear':
                state.reset()
                buffer = []
                continue

        # ── multi-line block handling ──
        if in_block:
            if stripped == '':
                # blank line = end of block
                chunk = '\n'.join(buffer)
                buffer = []
                in_block = False
                compiler.run_chunk(chunk)
            else:
                buffer.append(line)
            continue

        if _is_block_start(line):
            buffer   = [line]
            in_block = True
            continue

        # ── single-line statement ──
        compiler.run_chunk(line)


def main():
    run_shell()


if __name__ == '__main__':
    main()
