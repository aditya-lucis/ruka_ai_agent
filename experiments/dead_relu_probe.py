import numpy as np
from experiments.network import TwoLayerNetwork

net = TwoLayerNetwork()
net.b1 = np.full(4, -5.0) # skenario miskin
rng = np.random.default_rng(0)
X = rng.normal(0, 1, (200, 3))
net.forward(X)
dead = (net.Z1 <= 0).all(axis=0) # neuron tanpa aktivasi
print("neuron mati:", dead.sum(), "dari", len(dead))
print("rata-rata |z1|:", np.abs(net.Z1).mean(axis=0))