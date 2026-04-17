"""
Aether-9 Compiler v2.0
جديد: if/else + for loops + رسائل خطأ ملونة
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional

# ══════════════════════════════════════════════
# COLORS
# ══════════════════════════════════════════════
R="\033[31m"; Y="\033[33m"; G="\033[32m"; B="\033[34m"; X="\033[0m"; BOLD="\033[1m"

def _fmt_error(kind: str, msg: str, line: int = None, hint: str = None) -> str:
    loc  = f" at line {line}" if line else ""
    out  = f"\n  {BOLD}{R}[{kind}]{X}{loc}\n"
    out += f"  {msg}\n"
    if hint:
        out += f"  {Y}hint:{X} {hint}\n"
    return out

class LexError(Exception):
    def __init__(self, msg, line=None, hint=None):
        super().__init__(_fmt_error("LexError", msg, line, hint))

class ParseError(Exception):
    def __init__(self, msg, line=None, hint=None):
        super().__init__(_fmt_error("ParseError", msg, line, hint))

class CompileError(Exception):
    def __init__(self, msg, line=None, hint=None):
        super().__init__(_fmt_error("CompileError", msg, line, hint))


# ══════════════════════════════════════════════
# STAGE 1 — LEXER  (أضفنا: IF, ELSE, FOR, IN, OR)
# ══════════════════════════════════════════════

class TT(Enum):
    NUMBER=auto(); STRING=auto(); IDENT=auto()
    LATTICE=auto(); USES=auto(); PURE=auto(); RETURN=auto()
    IF=auto(); ELSE=auto(); FOR=auto(); IN=auto(); OR=auto(); AND=auto()
    WHILE=auto()
    LBRACKET=auto(); RBRACKET=auto(); LPAREN=auto(); RPAREN=auto()
    COLON=auto(); COMMA=auto(); ASSIGN=auto()
    PLUS=auto(); MINUS=auto(); STAR=auto(); SLASH=auto(); PERCENT=auto()
    EQ=auto(); NEQ=auto(); LT=auto(); GT=auto(); LTE=auto(); GTE=auto()
    NEWLINE=auto(); INDENT=auto(); DEDENT=auto(); EOF=auto()

KEYWORDS = {
    'lattice': TT.LATTICE, 'uses': TT.USES,   'pure':   TT.PURE,
    'return':  TT.RETURN,  'if':   TT.IF,      'else':   TT.ELSE,
    'for':     TT.FOR,     'in':   TT.IN,      'or':     TT.OR,
    'and':     TT.AND,     'while': TT.WHILE,
}

STDLIB_BUILTINS = {
    'abs', 'min', 'max', 'len', 'str', 'concat', 'dr', 'mod',
    'print', 'write', 'read', 'input',
}

@dataclass
class Token:
    type: TT; value: Any; line: int
    def __repr__(self): return f"Token({self.type.name},{self.value!r},L{self.line})"

class Lexer:
    def __init__(self, source: str):
        self.src=source; self.pos=0; self.line=1
        self.tokens: List[Token]=[]
        self.indent_stack=[0]

    def _cur(self)  -> str: return self.src[self.pos] if self.pos<len(self.src) else '\0'
    def _peek(self) -> str:
        p=self.pos+1; return self.src[p] if p<len(self.src) else '\0'
    def _add(self,t,v=None): self.tokens.append(Token(t,v,self.line))

    def tokenize(self) -> List[Token]:
        while self.pos<len(self.src): self._scan_line()
        while len(self.indent_stack)>1: self.indent_stack.pop(); self._add(TT.DEDENT)
        self._add(TT.EOF); return self.tokens

    def _scan_line(self):
        indent=0
        while self._cur()==' ': indent+=1; self.pos+=1
        if self._cur() in ('\n','\0','#'):
            while self._cur() not in ('\n','\0'): self.pos+=1
            if self._cur()=='\n': self.pos+=1; self.line+=1
            return
        prev=self.indent_stack[-1]
        if indent>prev: self.indent_stack.append(indent); self._add(TT.INDENT)
        while indent<self.indent_stack[-1]: self.indent_stack.pop(); self._add(TT.DEDENT)
        while self._cur() not in ('\n','\0'):
            c=self._cur()
            if c=='#':
                while self._cur() not in ('\n','\0'): self.pos+=1; break
            if c==' ': self.pos+=1; continue
            if c.isdigit() or (c=='-' and self._peek().isdigit()): self._scan_number(); continue
            if c in ('"',"'"): self._scan_string(c); continue
            if c.isalpha() or c=='_': self._scan_ident(); continue
            # two-char operators
            two = self.src[self.pos:self.pos+2]
            two_map = {'==':TT.EQ,'!=':TT.NEQ,'<=':TT.LTE,'>=':TT.GTE}
            if two in two_map: self._add(two_map[two],two); self.pos+=2; continue
            simple = {
                '[':TT.LBRACKET,']':TT.RBRACKET,'(':TT.LPAREN,')':TT.RPAREN,
                ':':TT.COLON,   ',':TT.COMMA,   '=':TT.ASSIGN,
                '+':TT.PLUS,    '-':TT.MINUS,   '*':TT.STAR,
                '/':TT.SLASH,   '%':TT.PERCENT, '<':TT.LT, '>':TT.GT,
            }
            if c in simple: self._add(simple[c],c); self.pos+=1; continue
            raise LexError(f"unexpected character {c!r}", self.line,
                           "remove or replace this character")
        if self._cur()=='\n': self._add(TT.NEWLINE); self.pos+=1; self.line+=1

    def _scan_number(self):
        s=self.pos
        if self._cur()=='-': self.pos+=1
        while self._cur().isdigit(): self.pos+=1
        self._add(TT.NUMBER,int(self.src[s:self.pos]))

    def _scan_string(self,q):
        self.pos+=1; s=self.pos
        while self._cur()!=q and self._cur()!='\0': self.pos+=1
        self._add(TT.STRING,self.src[s:self.pos]); self.pos+=1

    def _scan_ident(self):
        s=self.pos
        while self._cur().isalnum() or self._cur()=='_': self.pos+=1
        w=self.src[s:self.pos]; self._add(KEYWORDS.get(w,TT.IDENT),w)


# ══════════════════════════════════════════════
# STAGE 2 — AST NODES  (أضفنا: IfNode, ForNode)
# ══════════════════════════════════════════════

@dataclass
class ProgramNode:  body: List[Any]
@dataclass
class ArrayNode:    name:str; elements:List[int]; line:int
@dataclass
class LatticeNode:  name:str; params:List[str]; binding:Optional[str]; body:List[Any]; line:int
@dataclass
class AssignNode:   name:str; value:Any; line:int
@dataclass
class ReturnNode:   value:Any; line:int
@dataclass
class CallNode:     func:str; args:List[Any]; line:int
@dataclass
class IfNode:       cond:Any; then_body:List[Any]; else_body:List[Any]; line:int
@dataclass
class ForNode:      var:str; iterable:str; body:List[Any]; line:int
@dataclass
class WhileNode:    cond:Any; body:List[Any]; line:int
@dataclass
class BinOpNode:    op:str; left:Any; right:Any
@dataclass
class NumberNode:   value:int
@dataclass
class StringNode:   value:str
@dataclass
class IdentNode:    name:str


# ══════════════════════════════════════════════
# STAGE 3 — PARSER
# ══════════════════════════════════════════════

class Parser:
    def __init__(self,tokens):
        self.tokens=tokens; self.pos=0

    def _cur(self)->Token: return self.tokens[self.pos]
    def _peek(self,n=1)->Token:
        p=self.pos+n; return self.tokens[p] if p<len(self.tokens) else self.tokens[-1]

    def _expect(self,tt)->Token:
        t=self._cur()
        if t.type!=tt:
            raise ParseError(
                f"expected {tt.name}, got {t.type.name} ({t.value!r})",
                t.line,
                f"add missing '{tt.name.lower()}' before this token"
            )
        self.pos+=1; return t

    def _skip(self,*tts):
        while self._cur().type in tts: self.pos+=1

    def parse(self)->ProgramNode:
        body=[]; self._skip(TT.NEWLINE)
        while self._cur().type!=TT.EOF:
            n=self._stmt()
            if n: body.append(n)
            self._skip(TT.NEWLINE)
        return ProgramNode(body)

    def _stmt(self):
        t=self._cur()
        if t.type==TT.LATTICE: return self._lattice()
        if t.type==TT.RETURN:  return self._return()
        if t.type==TT.IF:      return self._if()
        if t.type==TT.FOR:     return self._for()
        if t.type==TT.WHILE:   return self._while()
        if t.type==TT.IDENT:
            if self._peek().type==TT.ASSIGN: return self._assign()
            if self._peek().type==TT.LPAREN:
                n=self._call(); self._skip(TT.NEWLINE); return n
        self._skip(TT.NEWLINE,TT.INDENT,TT.DEDENT)
        return None

    def _assign(self):
        name=self._expect(TT.IDENT).value; line=self._cur().line
        self._expect(TT.ASSIGN)
        if self._cur().type==TT.LBRACKET:
            elems=self._array_literal(); self._skip(TT.NEWLINE)
            return ArrayNode(name,elems,line)
        v=self._expr(); self._skip(TT.NEWLINE)
        return AssignNode(name,v,line)

    def _array_literal(self)->List[int]:
        self._expect(TT.LBRACKET); elems=[]
        while self._cur().type!=TT.RBRACKET:
            if   self._cur().type==TT.NUMBER: elems.append(self._cur().value); self.pos+=1
            elif self._cur().type==TT.COMMA:  self.pos+=1
            else: break
        self._expect(TT.RBRACKET); return elems

    def _lattice(self)->LatticeNode:
        line=self._cur().line; self._expect(TT.LATTICE)
        name=self._expect(TT.IDENT).value
        self._expect(TT.LPAREN); params=[]
        while self._cur().type!=TT.RPAREN:
            if   self._cur().type==TT.IDENT:  params.append(self._cur().value); self.pos+=1
            elif self._cur().type==TT.COMMA:  self.pos+=1
            else: break
        self._expect(TT.RPAREN)
        binding=None
        if self._cur().type==TT.USES:
            self.pos+=1; binding=self._expect(TT.IDENT).value
        elif self._cur().type==TT.PURE:
            self.pos+=1
        else:
            t=self._cur()
            raise ParseError(
                f"lattice '{name}' has no binding",
                t.line,
                "add 'uses <array>' or 'pure' after the parameter list"
            )
        self._expect(TT.COLON); self._skip(TT.NEWLINE)
        return LatticeNode(name,params,binding,self._block(),line)

    def _if(self)->IfNode:
        line=self._cur().line; self._expect(TT.IF)
        cond=self._cmp(); self._expect(TT.COLON); self._skip(TT.NEWLINE)
        then_body=self._block()
        else_body=[]
        if self._cur().type==TT.ELSE:
            self.pos+=1; self._expect(TT.COLON); self._skip(TT.NEWLINE)
            else_body=self._block()
        return IfNode(cond,then_body,else_body,line)

    def _for(self)->ForNode:
        line=self._cur().line; self._expect(TT.FOR)
        var=self._expect(TT.IDENT).value
        self._expect(TT.IN)
        iterable=self._expect(TT.IDENT).value
        self._expect(TT.COLON); self._skip(TT.NEWLINE)
        return ForNode(var,iterable,self._block(),line)

    def _while(self)->WhileNode:
        line=self._cur().line; self._expect(TT.WHILE)
        cond=self._expr(); self._expect(TT.COLON); self._skip(TT.NEWLINE)
        return WhileNode(cond,self._block(),line)

    def _block(self)->List[Any]:
        self._expect(TT.INDENT); stmts=[]
        while self._cur().type not in (TT.DEDENT,TT.EOF):
            s=self._stmt()
            if s: stmts.append(s)
            self._skip(TT.NEWLINE)
        if self._cur().type==TT.DEDENT: self.pos+=1
        return stmts

    def _return(self)->ReturnNode:
        line=self._cur().line; self._expect(TT.RETURN)
        v=self._expr(); self._skip(TT.NEWLINE)
        return ReturnNode(v,line)

    def _call(self)->CallNode:
        line=self._cur().line; name=self._expect(TT.IDENT).value
        self._expect(TT.LPAREN); args=[]
        while self._cur().type!=TT.RPAREN:
            args.append(self._expr())
            if self._cur().type==TT.COMMA: self.pos+=1
        self._expect(TT.RPAREN); return CallNode(name,args,line)

    # expr → cmp (handles 'or' keyword as Python 'or')
    def _expr(self):
        left=self._cmp()
        while self._cur().type in (TT.OR, TT.AND):
            op='or' if self._cur().type==TT.OR else 'and'
            self.pos+=1; right=self._cmp()
            left=BinOpNode(op,left,right)
        return left

    CMP_OPS={TT.EQ:'==',TT.NEQ:'!=',TT.LT:'<',TT.GT:'>',TT.LTE:'<=',TT.GTE:'>='}
    def _cmp(self):
        left=self._add()
        while self._cur().type in self.CMP_OPS:
            op=self.CMP_OPS[self._cur().type]; self.pos+=1
            left=BinOpNode(op,left,self._add())
        return left

    def _add(self):
        left=self._mul()
        while self._cur().type in (TT.PLUS,TT.MINUS):
            op='+' if self._cur().type==TT.PLUS else '-'; self.pos+=1
            left=BinOpNode(op,left,self._mul())
        return left

    def _mul(self):
        left=self._primary()
        while self._cur().type in (TT.STAR,TT.SLASH,TT.PERCENT):
            ops={TT.STAR:'*',TT.SLASH:'/',TT.PERCENT:'%'}
            op=ops[self._cur().type]; self.pos+=1
            left=BinOpNode(op,left,self._primary())
        return left

    def _primary(self):
        t=self._cur()
        if t.type==TT.NUMBER:  self.pos+=1; return NumberNode(t.value)
        if t.type==TT.STRING:  self.pos+=1; return StringNode(t.value)
        if t.type==TT.IDENT:
            if self._peek().type==TT.LPAREN: return self._call()
            self.pos+=1; return IdentNode(t.value)
        if t.type==TT.LPAREN:
            self.pos+=1; e=self._expr(); self._expect(TT.RPAREN); return e
        raise ParseError(
            f"unexpected token {t.type.name} ({t.value!r})",
            t.line,
            "check for missing operator or unmatched parenthesis"
        )


# ══════════════════════════════════════════════
# STAGE 4 — CODE GENERATOR
# ══════════════════════════════════════════════

_RUNTIME = '''\
# generated by aether-9 compiler v2.0 — do not edit
import time, os

def _a9_write(filename, value):
    with open(filename, 'w') as f:
        f.write(str(value) + chr(10))
    return 9

def _a9_read(filename):
    with open(filename) as f:
        content = f.read().strip()
    try:
        return int(content)
    except ValueError:
        return content

def _a9_input(prompt=''):
    val = input(prompt)
    try:
        return int(val)
    except ValueError:
        return val

def _a9_concat(a, b):
    return str(a) + str(b)

def _a9_dr(v):
    s=str(abs(int(v))); d=sum(int(c) for c in s)
    while d>9: d=sum(int(c) for c in str(d))
    return 9 if d in (9,0) else d

def _a9_mod(a, b):
    return a % b or 9

def _a9_str(v):
    return str(v)

def _a9_len(v):
    return len(str(v))


def _dr(v):
    s=str(abs(int(v))); d=sum(int(c) for c in s)
    while d>9: d=sum(int(c) for c in str(d))
    return 9 if d in (9,0) else d

def _pulse(timeout_ms=100):
    start=time.time_ns()
    while True:
        if _dr(time.time_ns())==9: return True
        if (time.time_ns()-start)>timeout_ms*1_000_000: return False
        time.sleep(0.000005)

def _vortex_seal(data):
    SEQ=[1,2,4,8,7,5]; n,sig=len(data),0
    for step in range(n):
        idx=(step*SEQ[step%6])%n
        sig=(sig*31+(data[idx]*(step+1))+step)%(2**32)
    return sig

def _lattice_gate(func,vortex_data=None,expected_sig=None):
    def wrapper(*args,**kwargs):
        if vortex_data is not None:
            actual=_vortex_seal(vortex_data)
            if expected_sig is not None and actual!=expected_sig:
                raise RuntimeError(f"Vortex tampered: got={actual}, expected={expected_sig}")
        _pulse()
        result=func(*args,**kwargs)
        if result!=0 and _dr(result)!=9:
            raise RuntimeError(f"Lattice asymmetry: root={_dr(result)}, expected=9")
        return result
    return wrapper

'''

class CodeGenerator:
    def __init__(self,registry):
        self.registry=registry; self._lines=[]; self._ind=0

    def _w(self,s=''):  self._lines.append('    '*self._ind+s)
    def _wi(self,s=''): self._ind+=1; self._w(s)   # unused helper

    def generate(self,ast:ProgramNode)->str:
        self._lines=[_RUNTIME]
        for n in ast.body: self._gen(n)
        return '\n'.join(self._lines)

    def _gen(self,node):
        if   isinstance(node,ArrayNode):   self._gen_array(node)
        elif isinstance(node,LatticeNode): self._gen_lattice(node)
        elif isinstance(node,AssignNode):  self._gen_assign(node)
        elif isinstance(node,ReturnNode):  self._gen_return(node)
        elif isinstance(node,IfNode):      self._gen_if(node)
        elif isinstance(node,ForNode):     self._gen_for(node)
        elif isinstance(node,WhileNode):    self._gen_while(node)
        elif isinstance(node,CallNode):    self._w(self._expr(node))

    def _gen_array(self,n:ArrayNode):
        self._w(f"{n.name} = {n.elements}")

    def _gen_lattice(self,n:LatticeNode):
        params=', '.join(n.params); impl=f"_{n.name}_impl"
        self._w(f"def {impl}({params}):")
        self._ind+=1
        for s in n.body: self._gen(s)
        if not n.body: self._w("pass")
        self._ind-=1; self._w()
        if n.binding and n.binding in self.registry:
            info=self.registry[n.binding]
            self._w(f"{n.name} = _lattice_gate({impl}, vortex_data={info['data']}, expected_sig={info['raw_sig']})")
        else:
            self._w(f"{n.name} = _lattice_gate({impl})")
        self._w()

    def _gen_assign(self,n:AssignNode):
        self._w(f"{n.name} = {self._expr(n.value)}")

    def _gen_return(self,n:ReturnNode):
        self._w(f"return ({self._expr(n.value)}) or 9")

    def _gen_if(self,n:IfNode):
        self._w(f"if {self._expr(n.cond)}:")
        self._ind+=1
        for s in n.then_body: self._gen(s)
        if not n.then_body: self._w("pass")
        self._ind-=1
        if n.else_body:
            self._w("else:")
            self._ind+=1
            for s in n.else_body: self._gen(s)
            self._ind-=1

    def _gen_for(self,n:ForNode):
        self._w(f"for {n.var} in {n.iterable}:")
        self._ind+=1
        for s in n.body: self._gen(s)
        if not n.body: self._w("pass")
        self._ind-=1

    def _gen_while(self,n:WhileNode):
        self._w(f"while {self._expr(n.cond)}:")
        self._ind+=1
        for s in n.body: self._gen(s)
        if not n.body: self._w("pass")
        self._ind-=1

    def _expr(self,node)->str:
        if isinstance(node,NumberNode): return str(node.value)
        if isinstance(node,StringNode):  return repr(node.value)
        if isinstance(node,IdentNode):  return node.name
        if isinstance(node,BinOpNode):
            l,r=self._expr(node.left),self._expr(node.right)
            return f"({l} {node.op} {r})"
        if isinstance(node,CallNode):
            args=', '.join(self._expr(a) for a in node.args)
            _map = {
                'write':'_a9_write','read':'_a9_read','input':'_a9_input',
                'concat':'_a9_concat','dr':'_a9_dr','mod':'_a9_mod',
                'str':'_a9_str','len':'_a9_len',
            }
            fn = _map.get(node.func, node.func)
            return f"{fn}({args})"
        return repr(node)


# ══════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════

def _vortex_seal(data):
    SEQ=[1,2,4,8,7,5]; n,sig=len(data),0
    for step in range(n):
        idx=(step*SEQ[step%6])%n
        sig=(sig*31+(data[idx]*(step+1))+step)%(2**32)
    return sig

# ══════════════════════════════════════════════
# SEMANTIC ANALYZER
# ══════════════════════════════════════════════

class SemanticAnalyzer:
    """يتحقق من forward references وأسماء الدوال غير المعرّفة"""

    def analyze(self, ast: ProgramNode, registry: dict):
        all_lattices  = [n.name for n in ast.body if isinstance(n, LatticeNode)]
        defined_so_far: set = set()

        for node in ast.body:
            if isinstance(node, LatticeNode):
                self._check_body(node.body, defined_so_far,
                                 all_lattices, node.name)
                defined_so_far.add(node.name)

    def _check_body(self, body, defined, all_lattices, in_fn):
        for node in body:
            self._check_node(node, defined, all_lattices, in_fn)

    def _check_node(self, node, defined, all_lattices, in_fn):
        if isinstance(node, CallNode):
            IO_BUILTINS = STDLIB_BUILTINS
            if node.func not in IO_BUILTINS:
                if node.func in all_lattices and node.func not in defined:
                    raise CompileError(
                        f"'{in_fn}' calls '{node.func}' before it is defined",
                        node.line,
                        f"move 'lattice {node.func}' above 'lattice {in_fn}'"
                    )
            for a in node.args:
                self._check_node(a, defined, all_lattices, in_fn)
        elif isinstance(node, IfNode):
            self._check_node(node.cond, defined, all_lattices, in_fn)
            self._check_body(node.then_body, defined, all_lattices, in_fn)
            self._check_body(node.else_body, defined, all_lattices, in_fn)
        elif isinstance(node, ForNode):
            self._check_body(node.body, defined, all_lattices, in_fn)
        elif isinstance(node, WhileNode):
            self._check_node(node.cond, defined, all_lattices, in_fn)
            self._check_body(node.body, defined, all_lattices, in_fn)
        elif isinstance(node, AssignNode):
            self._check_node(node.value, defined, all_lattices, in_fn)
        elif isinstance(node, ReturnNode):
            self._check_node(node.value, defined, all_lattices, in_fn)
        elif isinstance(node, BinOpNode):
            self._check_node(node.left,  defined, all_lattices, in_fn)
            self._check_node(node.right, defined, all_lattices, in_fn)


class Aether9Compiler:
    def compile(self,source:str):
        tokens  = Lexer(source).tokenize()
        ast     = Parser(tokens).parse()
        reg     = self._build_registry(ast)
        self._validate(ast,reg)
        SemanticAnalyzer().analyze(ast, reg)
        code    = CodeGenerator(reg).generate(ast)
        return code, reg

    def _build_registry(self,ast):
        reg={}
        for n in ast.body:
            if isinstance(n,ArrayNode):
                sig=_vortex_seal(n.elements)
                dr=9 if sig%9==0 else sig%9
                reg[n.name]={'data':n.elements,'raw_sig':sig,'seal':dr}
        return reg

    def _validate(self,ast,reg):
        for n in ast.body:
            if isinstance(n,LatticeNode) and n.binding and n.binding not in reg:
                avail=list(reg.keys()) or ['none']
                raise CompileError(
                    f"'{n.name}' uses '{n.binding}' which is not defined",
                    n.line,
                    f"available arrays: {avail}"
                )

