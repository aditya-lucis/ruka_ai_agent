import numpy as np
theta = np.pi / 6 # 30 derajat
R = np.array([[np.cos(theta), -np.sin(theta)],
              [np.sin(theta), np.cos(theta)]])
v = np.array([1.0, 0.0]) # vektor timur
print("v diputar 30\u00b0:", R @ v) # [0.866, 0.5]
# rotasi menjaga panjang (isometri)
print("panjang tetap:", np.allclose(np.linalg.norm(R @ v),
                                np.linalg.norm(v)))
# proyeksi ke sumbu-x: buang komponen y
P = np.array([[1.0, 0.0],
              [0.0, 0.0]])
w = np.array([3.0, 4.0])
print("w diproyeksikan:", P @ w) # [3, 0]