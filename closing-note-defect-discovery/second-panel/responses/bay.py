from mpmath import mp
from sympy import Rational, lambdify

denominator = 2**60
with mp.workprec(100):
    evaluate = lambdify((), Rational(denominator + 1, denominator), 'mpmath')
    assert (evaluate() - 1) * denominator == 1
