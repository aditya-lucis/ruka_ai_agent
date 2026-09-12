import numpy as np

rng = np.random.default_rng(42)
# data: dua gugus linier-separable + noise

n = 60
X = np.vstack([
    rng.normal([2.0, 2.0], 0.7, (n // 2, 2)),
    rng.normal([-2.0, -2.0], 0.7, (n - n // 2, 2)),
])

y = np.array([1.0] * (n // 2) + [0.0] * (n - n // 2))
W = rng.normal(0, 0.01, 2)
b = 0.0
lr = 0.1

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))

for epoch in range(200):
    p = sigmoid(X @ W + b) # forward
    eps = 1e-12
    p = np.clip(p, eps, 1 - eps)
    loss = float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())
    grad_W = X.T @ (p - y) / len(y) # gradient BCE (Part V!)
    grad_b = float((p - y).mean())
    W -= lr * grad_W # update (Part VII)
    b -= lr * grad_b

acc = ((p > 0.5).astype(float) == y).mean()
print(f"loss akhir = {loss:.4f} akurasi = {acc:.3f}")
print(f"W = {W}, b = {b:.4f}")