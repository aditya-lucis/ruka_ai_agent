import numpy as np
A = np.array([[1.0, 2.0], [3.0, 4.0]])
B = np.array([[5.0, 6.0], [7.0, 8.0]])
x = np.array([1.0, 0.0])

print(A @ B) # perkalian matriks (BUKAN A*B element-wise)
print(A * B) # element-wise — objek yang BERBEDA
print(A @ x) # transformasi vektor: ruang diputar-dipampat
print(A.T) # transpose: baris jadi kolom
print(x @ x) # dot product ditulis sebagai x^T x = 1.0