from sympy import Function, Limit, Symbol
from sympy.printing import python

x = Symbol('x')
a = Symbol('a')
f = Function('f')
expr = Limit(f(x), x, a, dir='-')

namespace = {'Limit': Limit, 'Symbol': Symbol, 'Function': Function}
exec(python(expr), namespace)
assert namespace['e'] == expr
