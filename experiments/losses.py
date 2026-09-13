import numpy as np

def mse(y_true, y_pred):
    """Regresi: hukuman kuadratik. y: (N,), yhat: (N,)."""
    d = np.asarray(y_true) - np.asarray(y_pred)
    return float((d ** 2).mean())

def bce(y_true, y_pred, eps: float = 1e-12):
    """Biner: clip sebelum log — tanpa ini, log(0) = -inf."""
    p = np.clip(np.asarray(y_pred), eps, 1 - eps)
    t = np.asarray(y_true)
    return float(-(t * np.log(p) + (1 - t) * np.log(1 - p)).mean())

def cce(y_true, y_pred, eps: float = 1e-12):
    """Multi-kelas: y one-hot (N, K), yhat probabilitas (N, K)."""
    p = np.clip(np.asarray(y_pred), eps, 1.0)
    t = np.asarray(y_true)
    return float(-(t * np.log(p)).sum(axis=1).mean())

def dice_loss(y_true, y_pred, smooth: float = 1.0):
    """Contoh loss domain-spesifik (segmentasi) — desain loss
    adalah keputusan rekayasa, bukan menu tetap."""
    inter = (y_true * y_pred).sum()
    return 1 - (2 * inter + smooth) / (y_true.sum() + y_pred.sum() + smooth)

print("prediksi benar yakin :", bce(1, 0.9), mse(1, 0.9))
print("prediksi salah yakin :", bce(1, 0.1), mse(1, 0.1))
print("prediksi ragu-ragu :", bce(1, 0.5), mse(1, 0.5))