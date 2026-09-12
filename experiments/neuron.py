import numpy as np

X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
y = np.array([0, 0, 0, 1], dtype=float) # AND
W = np.zeros(2)
b = 0.0
lr = 0.1

for epoch in range(20):
    errors = 0
    for xi, yi in zip(X, y):
        pred = 1.0 if (W @ xi + b) > 0 else 0.0
        update = lr * (yi - pred) # 0 jika benar
        W += update * xi
        b += update
        errors += int(update != 0.0)
    if errors == 0:
        break

print(f"W = {W}, b = {b}, epochs = {epoch}")
print("prediksi:", [1 if (W @ xi + b) > 0 else 0 for xi in X])