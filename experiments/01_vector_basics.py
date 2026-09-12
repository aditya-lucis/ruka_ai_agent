import numpy as np
# Scalar, vector, matrix, tensor — dan bentuk memorinya

x = np.array([1.0, 2.0, 3.0])
y = np.array([4.0, 5.0, 6.0])
dot_xy = np.dot(x, y)                   # 32.0
norm_x = np.linalg.norm(x)              # 3.7417
norm_y = np.linalg.norm(y)              # 8.7749

cos_theta = dot_xy / (norm_x * norm_y)  # 0.97463
print(f"x·y = {dot_xy}")
print(f"cos theta = {cos_theta:.5f} (~12.9 deg)")