from sympy import Identity, Sum, symbols

i = symbols("i", integer=True)
matrix = Identity(3)
assert Sum(matrix[i, 2 - i], (i, 0, 2)).doit() == 1
