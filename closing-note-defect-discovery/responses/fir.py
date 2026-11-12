from sympy import Max, Min, oo

values = ()
assert (Min(*values), Max(*values)) == (oo, -oo)
