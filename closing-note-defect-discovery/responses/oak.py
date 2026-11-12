from sympy import Rational, Symbol, nsolve

x = Symbol('x')
root = nsolve(x - Rational(1, 3), 0, prec=64)
assert abs(3 * Rational(root) - 1) < Rational(1, 10**60)
