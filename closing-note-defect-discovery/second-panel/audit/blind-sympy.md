## Probe 52a9207 for sympy__sympy-12419

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
total = Sum(Identity(5)[i, i**2], (i, 0, 2)).doit()
assert total == 2
```

base: fail
  from collections import Mapping
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert total == 2
AssertionError

gold: pass
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
[checkout]/sympy/core/basic.py:3: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Mapping
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

candidate 1: fail
  from collections import Mapping
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert total == 2
AssertionError

candidate 2: fail
  from collections import Mapping
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 5, in <module>
    assert total == 2
AssertionError

## Probe f32a321 for sympy__sympy-14531

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
from sympy import Function, Limit, Symbol
from sympy.printing import python

t = Symbol('t')
a = Symbol('a')
expr = Limit(Function('f')(t), t, a)
namespace = {'Function': Function, 'Limit': Limit, 'Symbol': Symbol}
exec(python(expr), namespace)
assert namespace['e'] == expr
```

base: fail
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 8, in <module>
    exec(python(expr), namespace)
  File "<string>", line 1, in <module>
NameError: name 'f' is not defined

gold: pass
  from collections import Mapping, defaultdict
[checkout]/sympy/core/expr.py:12: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import defaultdict, Iterable
[checkout]/sympy/core/containers.py:271: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  class OrderedSet(collections.MutableSet):
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

candidate 1: fail
  File "[checkout]/sympy/printing/python.py", line 53, in python
    exprp = printer.doprint(expr)
  File "[checkout]/sympy/printing/printer.py", line 236, in doprint
    return self._str(self._print(expr))
  File "[checkout]/sympy/printing/printer.py", line 274, in _print
    return getattr(self, printmethod)(expr, *args, **kwargs)
  File "[checkout]/sympy/printing/str.py", line 222, in _print_Limit
    del settings['sympy_integers']
KeyError: 'sympy_integers'

candidate 2: pass
  from collections import Mapping, defaultdict
[checkout]/sympy/core/expr.py:12: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import defaultdict, Iterable
[checkout]/sympy/core/containers.py:271: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  class OrderedSet(collections.MutableSet):
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

## Probe d915e45 for sympy__sympy-12419

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
matrix = Identity(5)
total = Sum(matrix[i, i**2], (i, 0, 2)).doit()
assert total == 2, total
```

base: fail
  from collections import Mapping
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 6, in <module>
    assert total == 2, total
AssertionError: 0

gold: pass
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
[checkout]/sympy/core/basic.py:3: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Mapping
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

candidate 1: fail
  from collections import Mapping
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 6, in <module>
    assert total == 2, total
AssertionError: 0

candidate 2: fail
  from collections import Mapping
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 6, in <module>
    assert total == 2, total
AssertionError: Piecewise((1, i**2 <= 2), (0, True))

## Probe 1159b7f for sympy__sympy-15809

Zero-argument Min() and Max()
Right now `Min()` and `Max()` with no arguments raise `ValueError: The Max/Min functions must have arguments.`. It might be mathematically more convenient to have them return `oo` and `-oo`, respectively. See https://en.wikipedia.org/wiki/Empty_set#Extended_real_numbers for why these are valid answers mathematically.

Proposed test

```python
from sympy import Max, Min, oo

assert (Min(), Max()) == (oo, -oo)
```

base: fail
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
Traceback (most recent call last):
  File "[submitted probe]", line 3, in <module>
    assert (Min(), Max()) == (oo, -oo)
  File "[checkout]/sympy/functions/elementary/miscellaneous.py", line 343, in __new__
    raise ValueError("The Max/Min functions must have arguments.")
ValueError: The Max/Min functions must have arguments.

gold: pass
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:520: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:540: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':

candidate 1: fail
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
Traceback (most recent call last):
  File "[submitted probe]", line 3, in <module>
    assert (Min(), Max()) == (oo, -oo)
AssertionError

candidate 2: pass
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:520: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:540: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':

## Probe a9d045f for sympy__sympy-15809

Zero-argument Min() and Max()
Right now `Min()` and `Max()` with no arguments raise `ValueError: The Max/Min functions must have arguments.`. It might be mathematically more convenient to have them return `oo` and `-oo`, respectively. See https://en.wikipedia.org/wiki/Empty_set#Extended_real_numbers for why these are valid answers mathematically.

Proposed test

```python
from sympy import Max, Min, oo

assert (Min(), Max()) == (oo, -oo)
```

base: fail
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
Traceback (most recent call last):
  File "[submitted probe]", line 3, in <module>
    assert (Min(), Max()) == (oo, -oo)
  File "[checkout]/sympy/functions/elementary/miscellaneous.py", line 343, in __new__
    raise ValueError("The Max/Min functions must have arguments.")
ValueError: The Max/Min functions must have arguments.

gold: pass
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:520: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:540: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':

candidate 1: fail
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
Traceback (most recent call last):
  File "[submitted probe]", line 3, in <module>
    assert (Min(), Max()) == (oo, -oo)
AssertionError

candidate 2: pass
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:520: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:540: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:553: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':
[checkout]/sympy/plotting/plot.py:560: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if self.xscale is 'log':

## Probe b4e431e for sympy__sympy-14976

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
from mpmath import mp
from sympy import Rational, lambdify

denominator = 2**60
with mp.workprec(100):
    evaluate = lambdify((), Rational(denominator + 1, denominator), 'mpmath')
    assert (evaluate() - 1) * denominator == 1
```

base: fail
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
Traceback (most recent call last):
  File "[submitted probe]", line 7, in <module>
    assert (evaluate() - 1) * denominator == 1
AssertionError

gold: pass
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:892: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2

candidate 1: fail
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
Traceback (most recent call last):
  File "[submitted probe]", line 7, in <module>
    assert (evaluate() - 1) * denominator == 1
AssertionError

candidate 2: pass
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:892: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2

## Probe a9644a8 for sympy__sympy-14531

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
from sympy import Function, Limit, Symbol
from sympy.printing import python

x = Symbol('x')
a = Symbol('a')
f = Function('f')
expr = Limit(f(x), x, a, dir='-')

namespace = {'Limit': Limit, 'Symbol': Symbol, 'Function': Function}
exec(python(expr), namespace)
assert namespace['e'] == expr
```

base: fail
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 10, in <module>
    exec(python(expr), namespace)
  File "<string>", line 1, in <module>
NameError: name 'f' is not defined

gold: fail
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable
Traceback (most recent call last):
  File "[submitted probe]", line 10, in <module>
    exec(python(expr), namespace)
  File "<string>", line 3
    - = Symbol('-')
      ^
SyntaxError: invalid syntax

candidate 1: fail
  File "[checkout]/sympy/printing/python.py", line 53, in python
    exprp = printer.doprint(expr)
  File "[checkout]/sympy/printing/printer.py", line 236, in doprint
    return self._str(self._print(expr))
  File "[checkout]/sympy/printing/printer.py", line 274, in _print
    return getattr(self, printmethod)(expr, *args, **kwargs)
  File "[checkout]/sympy/printing/str.py", line 222, in _print_Limit
    del settings['sympy_integers']
KeyError: 'sympy_integers'

candidate 2: pass
  from collections import Mapping, defaultdict
[checkout]/sympy/core/expr.py:12: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import defaultdict, Iterable
[checkout]/sympy/core/containers.py:271: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  class OrderedSet(collections.MutableSet):
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
[checkout]/sympy/plotting/plot.py:28: DeprecationWarning: Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.10 it will stop working
  from collections import Callable

## Probe 6e0e348 for sympy__sympy-14976

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
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
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
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2

candidate 1: fail
  if other is 0:
/replay/env38/lib/python3.8/site-packages/mpmath/ctx_mp_python.py:986: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if other is 0:
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
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
[checkout]/sympy/solvers/diophantine.py:3188: SyntaxWarning: "is" with a literal. Did you mean "=="?
  if feasible is 1:  # it's prime and k == 2
