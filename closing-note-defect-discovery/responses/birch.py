from sympy import Identity, Sum, symbols

i = symbols('i', integer=True)
total = Sum(Identity(7)[i, 2*i], (i, 0, 3)).doit()
assert total == 1, total
