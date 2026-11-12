from sympy import Identity, Sum, symbols

i = symbols('i', integer=True)
total = Sum(Identity(5)[i, i**2], (i, 0, 2)).doit()
assert total == 2
