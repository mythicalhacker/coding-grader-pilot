from sympy import Function, Limit, Symbol
from sympy.printing import python

t = Symbol('t')
a = Symbol('a')
expr = Limit(Function('f')(t), t, a)
namespace = {'Function': Function, 'Limit': Limit, 'Symbol': Symbol}
exec(python(expr), namespace)
assert namespace['e'] == expr
