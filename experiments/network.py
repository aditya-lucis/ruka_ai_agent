import numpy as np

class TwoLayerNetwork:
    """Jaringan klasifikasi 3 -> 4 (ReLU) -> 2 (softmax).
    Atribut W1/b1/W2/b2 adalah parameter yang dipelajari.
    Intermediate values (X, Z1, A1) disimpan saat forward()
    untuk dipakai backward() — kontrak dari PART VI.
    """

    def __init__(self, n_in=3, n_hidden=4, n_out=2, seed=42):
        rng = np.random.default_rng(seed)
        self.W1 = rng.normal(0.0, np.sqrt(2.0 / n_in), (n_hidden, n_in))
        self.b1 = np.zeros(n_hidden)
        self.W2 = rng.normal(0.0, np.sqrt(2.0 / n_hidden), (n_out, n_hidden))
        self.b2 = np.zeros(n_out)

    def relu(self, z):
        return np.maximum(0.0, z)

    def softmax(self, z):
        z = z - z.max(axis=1, keepdims=True) # stabilitas numerik
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    def forward(self, X):
        """X: (batch, n_in) -> probabilitas (batch, n_out)."""
        if X.ndim != 2 or X.shape[1] != self.W1.shape[1]:
            raise ValueError(f"X shape {X.shape} tidak cocok")
        self.X = X # simpan untuk backprop
        self.Z1 = X @ self.W1.T + self.b1 # (batch, 4)
        self.A1 = np.maximum(0.0, self.Z1) # (batch, 4)
        self.Z2 = self.A1 @ self.W2.T + self.b2 # (batch, 2)
        z = self.Z2 - self.Z2.max(axis=1, keepdims=True)
        e = np.exp(z)
        self.P = e / e.sum(axis=1, keepdims=True)
        return self.P # (batch, 2)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Kelas ber-probabilitas tertinggi."""
        return self.forward(X).argmax(axis=1)

net = TwoLayerNetwork()
X = np.array([[1.0, 2.0, 0.5], [0.2, 0.1, 1.0]])
probs = net.forward(X)
print(probs)
print("sum per baris (harus 1.0):", probs.sum(axis=1))