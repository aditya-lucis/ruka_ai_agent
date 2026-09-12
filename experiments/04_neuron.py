import numpy as np

class Neuron:
    """Single artificial neuron: y = activation(Wx + b)."""
    def __init__(self, n_inputs: int, seed: int = 42):
        rng = np.random.default_rng(seed)
        # inisialisasi kecil: nilai besar membunuh gradient (Part IV & VI)
        self.W = rng.normal(0.0, 0.01, size=(1, n_inputs))
        self.b = np.zeros(1)

    def forward(self, x: np.ndarray) -> float:
        """x: shape (n_inputs,) -> skalar pre-activation"""
        z = float((self.W @ x + self.b)[0])
        return 1.0 / (1.0 + np.exp(-z)) # sigmoid: (0, 1)

neuron = Neuron(n_inputs=3)
x = np.array([2.0, 1.0, 0.5])

print(f"z (pre-activation) = {neuron.W @ x + neuron.b}")
print(f"y (output sigmoid) = {neuron.forward(x):.4f}")

X = np.array([[2.0, 1.0, 0.5], [0.5, 3.0, 1.0], [1.0, 1.0, 1.0]]) # shape (3, 3): 3 sampel
Z = X @ neuron.W.T + neuron.b # shape (3, 1)
Y = 1.0 / (1.0 + np.exp(-Z)) # sigmoid per baris

print(Y)