from sympy import Eq, Function, Limit, Symbol
from sympy.printing import python

x, y, z = map(Symbol, ('x', 'y', 'z'))
f = Function('f')
expr = Eq(Limit(f(x), x, y), z)
namespace = dict(Eq=Eq, Function=Function, Limit=Limit, Symbol=Symbol)
exec(python(expr), namespace)
assert namespace['e'] == expr
