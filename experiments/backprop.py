import numpy as np

from experiments.network import TwoLayerNetwork # PART III
from experiments.losses import cce # PART V

def backward(net: TwoLayerNetwork, Y: np.ndarray):
    """Gradient CCE+softmax untuk jaringan 2-layer.
    Prasyarat: net.forward(X) sudah dipanggil sehingga
    intermediate values (X, Z1, A1, P) terisi.
    Y: label one-hot, shape sama dengan P.
    Returns: {'W1','b1','W2','b2'} — masing-masing shape
    identik dengan parameter aslinya.
    """
    P = net.P
    B = P.shape[0]
    if P.shape != Y.shape:
        raise ValueError(f"shape Y {Y.shape} != P {P.shape}")
    dZ2 = (P - Y) / B # softmax-CCE (5.3)
    dW2 = dZ2.T @ net.A1 # (n_out, n_hidden)
    db2 = dZ2.sum(axis=0) # (n_out,)
    dA1 = dZ2 @ net.W2 # (B, n_hidden)
    dZ1 = dA1 * (net.Z1 > 0) # ReLU mask (4.2)
    dW1 = dZ1.T @ net.X # (n_hidden, n_in)
    db1 = dZ1.sum(axis=0) # (n_hidden,)
    return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}

def gradient_check(net, X, Y, *, n_checks=10, eps=1e-5, rng_seed=0) -> bool:
    """Validasi mutlak: analitik vs numerik pada koordinat acak."""
    rng = np.random.default_rng(rng_seed)
    net.forward(X)
    grads = backward(net, Y)
    params = {"W1": net.W1, "b1": net.b1,
    "W2": net.W2, "b2": net.b2}
    for name, arr in params.items():
        flat = arr.ravel()
        for idx in rng.choice(flat.size, size=n_checks, replace=False):
            orig = flat[idx]
            flat[idx] = orig + eps
            lp = _cce(net.forward(X), Y)
            flat[idx] = orig - eps
            lm = _cce(net.forward(X), Y)
            flat[idx] = orig
            numeric = (lp - lm) / (2 * eps)
            analytic = grads[name].ravel()[idx]
            if abs(numeric - analytic) > 1e-6:
                return False
            return True

def _cce(P, Y, eps=1e-12):
    P = np.clip(P, eps, 1.0)
    return float(-(Y * np.log(P)).sum(axis=1).mean())

def numerical_grad(net, X, Y, param, idx, eps=1e-5):
    orig = param[idx]
    param[idx] = orig + eps
    lp = cce(Y, net.forward(X))
    param[idx] = orig - eps
    lm = cce(Y, net.forward(X))
    param[idx] = orig # pulihkan
    return (lp - lm) / (2 * eps)

net = TwoLayerNetwork()
X = np.array([[1.0, 2.0, 0.5], [0.3, 0.1, 1.0]])
Y = np.array([[1.0, 0.0], [0.0, 1.0]])
net.forward(X) # isi intermediate
grads = backward(net, Y)
w_idx = (0, 0)
analytic = grads["W1"][w_idx]
numeric = numerical_grad(net, X, Y, net.W1, w_idx)
print(f"analytic={analytic:.8f} numeric={numeric:.8f}")
assert abs(analytic - numeric) < 1e-6, "gradient check GAGAL"