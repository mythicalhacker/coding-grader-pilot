## Probe 6e4b06c for sympy__sympy-12419

Sum of the elements of an identity matrix is zero
I think this is a bug.

I created a matrix by M.T * M under an assumption that M is orthogonal.  SymPy successfully recognized that the result is an identity matrix.  I tested its identity-ness by element-wise, queries, and sum of the diagonal elements and received expected results.

However, when I attempt to evaluate the total sum of the elements the result was 0 while 'n' is expected.

```
from sympy import *
from sympy import Q as Query

n = Symbol('n', integer=True, positive=True)
i, j = symbols('i j', integer=True)
M = MatrixSymbol('M', n, n)

e = None
with assuming(Query.orthogonal(M)):
    e = refine((M.T * M).doit())

# Correct: M.T * M is an identity matrix.
print(e, e[0, 0], e[0, 1], e[1, 0], e[1, 1])

# Correct: The output is True True
print(ask(Query.diagonal(e)), ask(Query.integer_elements(e)))

# Correct: The sum of the diagonal elements is n
print(Sum(e[i, i], (i, 0, n-1)).doit())

# So far so good
# Total sum of the elements is expected to be 'n' but the answer is 0!
print(Sum(Sum(e[i, j], (i, 0, n-1)), (j, 0, n-1)).doit())
```

Proposed test

```python
from sympy import Identity, Sum, symbols

i = symbols("i", integer=True)
matrix = Identity(3)
assert Sum(matrix[i, 2 - i], (i, 0, 2)).doit() == 1
```

base: fail
  from collections import Mapping
/replay/trees/sympy__sympy-12419/base/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-12419/base/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert Sum(matrix[i, 2 - i], (i, 0, 2)).doit() == 1
AssertionError

gold: pass
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-12419/gold/sympy/core/basic.py:3: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Mapping
/replay/trees/sympy__sympy-12419/gold/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-12419/gold/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

candidate 1: fail
  from collections import Mapping
/replay/trees/sympy__sympy-12419/haiku/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-12419/haiku/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert Sum(matrix[i, 2 - i], (i, 0, 2)).doit() == 1
AssertionError

candidate 2: fail
  from collections import Mapping
/replay/trees/sympy__sympy-12419/sonnet/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-12419/sonnet/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert Sum(matrix[i, 2 - i], (i, 0, 2)).doit() == 1
AssertionError

## Probe dbb99d8 for sympy__sympy-14531

StrPrinter setting are not respected by certain subexpressions
For example, 
```
>>> sstr(x + S(1)/2, sympy_integers=True)
'x + S(1)/2'
>>> sstr(Eq(x, S(1)/2), sympy_integers=True)
'Eq(x, 1/2)'
```

The first output is correct, the second is not: the setting was ignored. Another example:
```
>>> sstr(Limit(x, x, S(1)/2), sympy_integers=True)
'Limit(x, x, 1/2)'
```
instead of the expected `Limit(x, x, S(1)/2)`. 

This also affects code generation:
```
>>> python(Eq(x, y))
'e = Eq(x, y)'
```
instead of the expected `x = Symbol('x')\ny = Symbol('y')\ne = Eq(x, y)`.  (Strangely, this behavior is asserted by a test.)

A fix is forthcoming.

Proposed test

```python
from sympy import Eq, Function, Limit, Symbol
from sympy.printing import python

x, y, z = map(Symbol, ('x', 'y', 'z'))
f = Function('f')
expr = Eq(Limit(f(x), x, y), z)
namespace = dict(Eq=Eq, Function=Function, Limit=Limit, Symbol=Symbol)
exec(python(expr), namespace)
assert namespace['e'] == expr
```

base: fail
/replay/trees/sympy__sympy-14531/base/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-14531/base/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 8, in <module>
    exec(python(expr), namespace)
  File "<string>", line 1, in <module>
NameError: name 'f' is not defined

gold: pass
  from collections import Mapping, defaultdict
/replay/trees/sympy__sympy-14531/gold/sympy/core/expr.py:12: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import defaultdict, Iterable
/replay/trees/sympy__sympy-14531/gold/sympy/core/containers.py:271: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  class OrderedSet(collections.MutableSet):
/replay/trees/sympy__sympy-14531/gold/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-14531/gold/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

candidate 1: fail
  File "[checkout]/sympy/printing/python.py", line 53, in python
    exprp = printer.doprint(expr)
  File "[checkout]/sympy/printing/printer.py", line 236, in doprint
    return self._str(self._print(expr))
  File "[checkout]/sympy/printing/printer.py", line 274, in _print
    return getattr(self, printmethod)(expr, *args, **kwargs)
  File "[checkout]/sympy/printing/str.py", line 655, in _print_Relational
    del settings['sympy_integers']
KeyError: 'sympy_integers'

candidate 2: pass
  from collections import Mapping, defaultdict
/replay/trees/sympy__sympy-14531/sonnet/sympy/core/expr.py:12: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import defaultdict, Iterable
/replay/trees/sympy__sympy-14531/sonnet/sympy/core/containers.py:271: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  class OrderedSet(collections.MutableSet):
/replay/trees/sympy__sympy-14531/sonnet/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-14531/sonnet/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

## Probe a1c2cb2 for sympy__sympy-12419

Sum of the elements of an identity matrix is zero
I think this is a bug.

I created a matrix by M.T * M under an assumption that M is orthogonal.  SymPy successfully recognized that the result is an identity matrix.  I tested its identity-ness by element-wise, queries, and sum of the diagonal elements and received expected results.

However, when I attempt to evaluate the total sum of the elements the result was 0 while 'n' is expected.

```
from sympy import *
from sympy import Q as Query

n = Symbol('n', integer=True, positive=True)
i, j = symbols('i j', integer=True)
M = MatrixSymbol('M', n, n)

e = None
with assuming(Query.orthogonal(M)):
    e = refine((M.T * M).doit())

# Correct: M.T * M is an identity matrix.
print(e, e[0, 0], e[0, 1], e[1, 0], e[1, 1])

# Correct: The output is True True
print(ask(Query.diagonal(e)), ask(Query.integer_elements(e)))

# Correct: The sum of the diagonal elements is n
print(Sum(e[i, i], (i, 0, n-1)).doit())

# So far so good
# Total sum of the elements is expected to be 'n' but the answer is 0!
print(Sum(Sum(e[i, j], (i, 0, n-1)), (j, 0, n-1)).doit())
```

Proposed test

```python
from sympy import Identity, Sum, symbols

i = symbols('i', integer=True)
total = Sum(Identity(7)[i, 2*i], (i, 0, 3)).doit()
assert total == 1, total
```

base: fail
  from collections import Mapping
/replay/trees/sympy__sympy-12419/base/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-12419/base/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert total == 1, total
AssertionError: 0

gold: pass
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-12419/gold/sympy/core/basic.py:3: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Mapping
/replay/trees/sympy__sympy-12419/gold/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-12419/gold/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

candidate 1: fail
  from collections import Mapping
/replay/trees/sympy__sympy-12419/haiku/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-12419/haiku/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert total == 1, total
AssertionError: 0

candidate 2: fail
  from collections import Mapping
/replay/trees/sympy__sympy-12419/sonnet/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-12419/sonnet/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert total == 1, total
AssertionError: Piecewise((1, (2*i >= 0) & (2*i <= 3)), (0, True))

## Probe b3d4035 for sympy__sympy-15809

Zero-argument Min() and Max()
Right now `Min()` and `Max()` with no arguments raise `ValueError: The Max/Min functions must have arguments.`. It might be mathematically more convenient to have them return `oo` and `-oo`, respectively. See https://en.wikipedia.org/wiki/Empty_set#Extended_real_numbers for why these are valid answers mathematically.

Proposed test

```python
from sympy import Max, Min, oo

values = ()
assert (Min(*values), Max(*values)) == (oo, -oo)
```

base: fail
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/base/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
Traceback (most recent call last):
  File "[submitted probe]", line 4, in <module>
    assert (Min(*values), Max(*values)) == (oo, -oo)
  File "[checkout]/sympy/functions/elementary/miscellaneous.py", line 343, in __new__
    raise ValueError("The Max/Min functions must have arguments.")
ValueError: The Max/Min functions must have arguments.

gold: pass
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-15809/gold/sympy/plotting/plot.py:520: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/gold/sympy/plotting/plot.py:540: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/gold/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/gold/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':

candidate 1: fail
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/haiku/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/haiku/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
Traceback (most recent call last):
  File "[submitted probe]", line 4, in <module>
    assert (Min(*values), Max(*values)) == (oo, -oo)
AssertionError

candidate 2: pass
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-15809/sonnet/sympy/plotting/plot.py:520: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/sonnet/sympy/plotting/plot.py:540: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/sonnet/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/sonnet/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':

## Probe f51ece4 for sympy__sympy-15809

Zero-argument Min() and Max()
Right now `Min()` and `Max()` with no arguments raise `ValueError: The Max/Min functions must have arguments.`. It might be mathematically more convenient to have them return `oo` and `-oo`, respectively. See https://en.wikipedia.org/wiki/Empty_set#Extended_real_numbers for why these are valid answers mathematically.

Proposed test

```python
from sympy import Max, Min, oo

assert (Min(), Max()) == (oo, -oo)
```

base: fail
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/base/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
Traceback (most recent call last):
  File "[submitted probe]", line 3, in <module>
    assert (Min(), Max()) == (oo, -oo)
  File "[checkout]/sympy/functions/elementary/miscellaneous.py", line 343, in __new__
    raise ValueError("The Max/Min functions must have arguments.")
ValueError: The Max/Min functions must have arguments.

gold: pass
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-15809/gold/sympy/plotting/plot.py:520: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/gold/sympy/plotting/plot.py:540: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/gold/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/gold/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':

candidate 1: fail
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/haiku/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/haiku/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
Traceback (most recent call last):
  File "[submitted probe]", line 3, in <module>
    assert (Min(), Max()) == (oo, -oo)
AssertionError

candidate 2: pass
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-15809/sonnet/sympy/plotting/plot.py:520: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/sonnet/sympy/plotting/plot.py:540: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/sonnet/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
/replay/trees/sympy__sympy-15809/sonnet/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':

## Probe e2e59d2 for sympy__sympy-14976

lambdify(modules='mpmath') doesn't wrap rationals
```py
>>> eqn = Eq(rf(18,x), 77 + S(1)/3)
>>> f = lambdify(x, eqn.lhs - eqn.rhs, 'mpmath')
>>> print(inspect.getsource(f))
def _lambdifygenerated(x):
    return (  # Not supported in Python:
  # RisingFactorial
RisingFactorial(18, x) - 232/3)
```

This results in reduced precision results from `nsolve`, because the 232/3 isn't evaluated at full precision. 

```py
>>> eqn = Eq(rf(18,x), 77 + S(1)/3)
>>> x0 = nsolve(eqn, Float('1.5', 64), prec=64)
>>> rf(18, x0).evalf(64)
77.33333333333332859638176159933209419250488281250000000000000000
```

Originally reported at https://github.com/sympy/sympy/pull/14971

Proposed test

```python
from sympy import Rational, Symbol, nsolve

x = Symbol('x')
root = nsolve(x - Rational(1, 3), 0, prec=64)
assert abs(3 * Rational(root) - 1) < Rational(1, 10**60)
```

base: fail
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-14976/base/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert abs(3 * Rational(root) - 1) < Rational(1, 10**60)
AssertionError

gold: pass
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:892: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-14976/gold/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2

candidate 1: fail
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-14976/haiku/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert abs(3 * Rational(root) - 1) < Rational(1, 10**60)
AssertionError

candidate 2: pass
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:892: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-14976/sonnet/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2

## Probe 1f14b0b for sympy__sympy-14531

StrPrinter setting are not respected by certain subexpressions
For example, 
```
>>> sstr(x + S(1)/2, sympy_integers=True)
'x + S(1)/2'
>>> sstr(Eq(x, S(1)/2), sympy_integers=True)
'Eq(x, 1/2)'
```

The first output is correct, the second is not: the setting was ignored. Another example:
```
>>> sstr(Limit(x, x, S(1)/2), sympy_integers=True)
'Limit(x, x, 1/2)'
```
instead of the expected `Limit(x, x, S(1)/2)`. 

This also affects code generation:
```
>>> python(Eq(x, y))
'e = Eq(x, y)'
```
instead of the expected `x = Symbol('x')\ny = Symbol('y')\ne = Eq(x, y)`.  (Strangely, this behavior is asserted by a test.)

A fix is forthcoming.

Proposed test

```python
from sympy import Eq, Function, Limit, Symbol
from sympy.printing import python

x, y, z = map(Symbol, ('x', 'y', 'z'))
f = Function('f')
expression = Eq(Limit(f(x), x, y), z)
namespace = dict(Eq=Eq, Function=Function, Limit=Limit, Symbol=Symbol)
exec(python(expression), namespace)
assert namespace['e'] == expression
```

base: fail
/replay/trees/sympy__sympy-14531/base/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-14531/base/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 8, in <module>
    exec(python(expression), namespace)
  File "<string>", line 1, in <module>
NameError: name 'f' is not defined

gold: pass
  from collections import Mapping, defaultdict
/replay/trees/sympy__sympy-14531/gold/sympy/core/expr.py:12: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import defaultdict, Iterable
/replay/trees/sympy__sympy-14531/gold/sympy/core/containers.py:271: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  class OrderedSet(collections.MutableSet):
/replay/trees/sympy__sympy-14531/gold/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-14531/gold/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

candidate 1: fail
  File "[checkout]/sympy/printing/python.py", line 53, in python
    exprp = printer.doprint(expr)
  File "[checkout]/sympy/printing/printer.py", line 236, in doprint
    return self._str(self._print(expr))
  File "[checkout]/sympy/printing/printer.py", line 274, in _print
    return getattr(self, printmethod)(expr, *args, **kwargs)
  File "[checkout]/sympy/printing/str.py", line 655, in _print_Relational
    del settings['sympy_integers']
KeyError: 'sympy_integers'

candidate 2: pass
  from collections import Mapping, defaultdict
/replay/trees/sympy__sympy-14531/sonnet/sympy/core/expr.py:12: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import defaultdict, Iterable
/replay/trees/sympy__sympy-14531/sonnet/sympy/core/containers.py:271: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  class OrderedSet(collections.MutableSet):
/replay/trees/sympy__sympy-14531/sonnet/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
/replay/trees/sympy__sympy-14531/sonnet/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

## Probe f48e3b1 for sympy__sympy-14976

lambdify(modules='mpmath') doesn't wrap rationals
```py
>>> eqn = Eq(rf(18,x), 77 + S(1)/3)
>>> f = lambdify(x, eqn.lhs - eqn.rhs, 'mpmath')
>>> print(inspect.getsource(f))
def _lambdifygenerated(x):
    return (  # Not supported in Python:
  # RisingFactorial
RisingFactorial(18, x) - 232/3)
```

This results in reduced precision results from `nsolve`, because the 232/3 isn't evaluated at full precision. 

```py
>>> eqn = Eq(rf(18,x), 77 + S(1)/3)
>>> x0 = nsolve(eqn, Float('1.5', 64), prec=64)
>>> rf(18, x0).evalf(64)
77.33333333333332859638176159933209419250488281250000000000000000
```

Originally reported at https://github.com/sympy/sympy/pull/14971

Proposed test

```python
from sympy import Rational, lambdify

denominator = 2**1100
evaluate = lambdify((), Rational(1, denominator), modules="mpmath")
assert evaluate() * denominator == 1
```

base: fail
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-14976/base/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert evaluate() * denominator == 1
OverflowError: int too large to convert to float

gold: pass
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:892: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-14976/gold/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2

candidate 1: fail
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-14976/haiku/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert evaluate() * denominator == 1
AssertionError

candidate 2: pass
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:892: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/trees/sympy__sympy-14976/sonnet/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
