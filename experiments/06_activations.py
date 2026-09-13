import numpy as np

def sigmoid(z): return 1.0 / (1.0 + np.exp(-z))
def d_sigmoid(z): s = sigmoid(z); return s * (1.0 - s)
def tanh(z): return np.tanh(z)
def d_tanh(z): return 1.0 - np.tanh(z) ** 2
def relu(z): return np.maximum(0.0, z)
def d_relu(z): return (z > 0).astype(float)
def leaky(z, alpha=0.01): return np.where(z > 0, z, alpha * z)
def d_leaky(z, alpha=0.01): return np.where(z > 0, 1.0, alpha)

def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)

# Demonstrasi vanishing: produk turunan sigmoid pada 10 layer
z = np.linspace(-4, 4, 9)
prod = np.prod(d_sigmoid(z))
print(f"produk 9 turunan sigmoid : {prod:.2e}")
print(f"produk 9 turunan relu : {np.prod(d_relu(z)):.2f}")