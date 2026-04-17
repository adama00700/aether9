# Language Reference

Aether-9 is a compact execution language with explicit support for arrays, lattice functions, assignments, control flow, calls, and a small built-in library.

## Arrays

Arrays are declared using square brackets.

```aether
data = [54, 36, 72]
```

Empty arrays are allowed:

```aether
data = []
```

## Assignments

```aether
x = 42
label = "hello"
result = x + 9
```

## Lattice Functions

A lattice function is the core callable unit in Aether-9.

### Bound lattice

A lattice can be bound to an array using `uses`:

```aether
data = [54, 36, 72]

lattice verify(x) uses data:
    return dr(x) or 9
```

### Pure lattice

A lattice can also be defined as `pure`:

```aether
lattice normalize(x) pure:
    return dr(x) or 9
```

### Binding rules

A lattice must be either:

- `uses <array>`
- or `pure`

A bare lattice definition without one of those forms is a parse error.

## Control Flow

### If / else

```aether
if result == 9:
    print(result)
else:
    print(0)
```

### For loop

```aether
for item in data:
    print(item)
```

### While loop

```aether
counter = 0
while counter < 9:
    counter = counter + 1
```

Boolean expressions with `and` and `or` are supported.

## Calls

### Builtin call

```aether
x = str(9)
```

### Lattice call

```aether
result = verify(54)
```

### Nested call

```aether
result = outer(inner(9))
```

## Operators

### Arithmetic

- `+`
- `-`
- `*`
- `/`
- `%`

### Comparison

- `==`
- `!=`
- `<`
- `>`
- `<=`
- `>=`

### Logical

- `and`
- `or`

## Standard Library

| Function | Purpose |
|---|---|
| `dr(x)` | digital-root style normalization |
| `abs(x)` | absolute value |
| `min(a, b)` | minimum |
| `max(a, b)` | maximum |
| `mod(a, b)` | modulo with Aether-style normalization |
| `len(x)` | length of string representation |
| `str(x)` | convert to string |
| `concat(a, b)` | concatenate values as strings |
| `print(x)` | print value(s) |
| `write(path, value)` | write to file |
| `read(path)` | read from file |

## Notes

- The public language is intentionally small and reviewable.
- The runtime model is discussed in [VM Architecture](vm-architecture.md).
- Artifact export is covered in [Artifact Format](artifact-format.md).
