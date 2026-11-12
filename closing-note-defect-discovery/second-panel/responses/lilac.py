from sympy import Identity, Sum, symbols

i = symbols("i", integer=True)
matrix = Identity(5)
total = Sum(matrix[i, i**2], (i, 0, 2)).doit()
assert total == 2, total
