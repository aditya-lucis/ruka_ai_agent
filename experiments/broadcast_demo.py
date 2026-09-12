import numpy as np

A = np.array([[1.0, 2.0, 3.0],
              [4.0, 5.0, 6.0]]) # (2, 3)
v = np.array([10.0, 20.0, 30.0]) # (3,)

print(A + v) # (2,3)+(3,) -> v ditambahkan ke tiap baris
w = np.array([[1.0], [2.0]]) # (2, 1)
print(A + w) # (2,3)+(2,1) -> w ditambahkan ke tiap kolom
# bug klasik: maksudnya vektor kolom, tertulis vektor baris
z = np.array([1.0, 2.0]) # (2,) <- maksud Anda (2, 1)
try:
    A + z # error: (2,3)+(2,)? tidak bisa
except ValueError as e:
    print('ValueError:', e)