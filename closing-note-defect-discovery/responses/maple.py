from sympy import Rational, lambdify

denominator = 2**1100
evaluate = lambdify((), Rational(1, denominator), modules="mpmath")
assert evaluate() * denominator == 1
