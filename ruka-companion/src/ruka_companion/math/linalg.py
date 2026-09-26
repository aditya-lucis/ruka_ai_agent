import numpy as np

def _as_vector(x, name):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError(f"{name} harus 1-D, dapat {x.ndim}-D")
    return x

def _as_matrix(X, name, min_rows=1):
    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2:
        raise ValueError(f"{name} harus 2-D, dapat {X.ndim}-D")
    if X.shape[0] < min_rows:
        raise ValueError(f"{name} butuh minimal {min_rows} baris")
    return X

def cosine_similarity(x: np.ndarray, y: np.ndarray) -> float:
    """cos(x, y) = ⟨x,y⟩ / (‖x‖₂‖y‖₂).
    Invarian (diuji): simetri; |cos| ≤ 1 (Cauchy–Schwarz); cos(αx, y) = cos(x, y)
    untuk α > 0 (invarian skala positif). Vektor nol → ValueError (embedding
    nol = bukti rusak, bukan bukti netral).
    """
    x = _as_vector(x, "x")
    y = _as_vector(y, "y")
    if x.shape != y.shape:
        raise ValueError(f"dimensi tak cocok: {x.shape} vs {y.shape}")
    
    nx, ny = np.linalg.norm(x), np.linalg.norm(y)
    if nx == 0.0 or ny == 0.0:
        raise ValueError("cosine tidak terdefinisi untuk vektor nol")
        
    return float(np.dot(x, y) / (nx * ny))

def euclidean_distance(x: np.ndarray, y: np.ndarray) -> float:
    """d(x, y) = ‖x − y‖₂.  x, y ∈ R^d → skalar ≥ 0."""
    x = _as_vector(x, "x")
    y = _as_vector(y, "y")
    if x.shape != y.shape:
        raise ValueError(f"dimensi tak cocok: {x.shape} vs {y.shape}")
    return float(np.linalg.norm(x - y))

def normalize_unit(x: np.ndarray) -> np.ndarray:
    """x / ‖x‖₂ — embedding ke bola satuan. Vektor nol → ValueError."""
    x = _as_vector(x, "x").copy()
    n = np.linalg.norm(x)
    if n == 0.0:
        raise ValueError("tidak bisa menormalkan vektor nol")
    return x / n

def project(x: np.ndarray, u: np.ndarray) -> np.ndarray:
    """proj_u(x) = (⟨x,u⟩/‖u‖²)·u — proyeksi ortogonal x ke arah u (u ≠ 0)."""
    x = _as_vector(x, "x")
    u = _as_vector(u, "u")
    if x.shape != u.shape:
        raise ValueError("Dimensi tak cocok")
        
    nu2 = np.dot(u, u)
    if nu2 == 0.0:
        raise ValueError("u tidak boleh nol")
        
    return (np.dot(x, u) / nu2) * u

def pca(X: np.ndarray, k: int) -> dict:
    """PCA via SVD: X ∈ R^(n×d) → komponen V_k ∈ R^(d×k), skalar λ."""
    X = _as_matrix(X, "X", min_rows=2)
    n, d = X.shape
    if not 1 <= k <= d:
        raise ValueError(f"k harus dalam [1, {d}], dapat {k}")
        
    mu = X.mean(axis=0, keepdims=True)
    Xc = X - mu
    
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    components = Vt[:k].T                       # d × k
    total_var = float(np.sum(S ** 2))
    eigvals = (S ** 2) / max(n - 1, 1)          # nilai eigen Σ
    explained = eigvals[:k]
    ratio = explained / total_var if total_var > 0 else np.zeros(k)
    
    return {
        "components": components,
        "explained_variance": explained,
        "explained_ratio": ratio,
        "mean": mu.ravel(),
    }

def pca_reconstruct(X: np.ndarray, k: int) -> np.ndarray:
    """Rekonstruksi rank-k: X̂ = μ + (X − μ)V_kV_kᵀ ∈ R^(n×d)."""
    res = pca(X, k)
    mu = res["mean"]
    Xc = np.asarray(X, dtype=np.float64) - mu
    Vk = res["components"]
    return mu + (Xc @ Vk) @ Vk.T

def rank(A: np.ndarray, tol: float = 1e-10) -> int:
    """rank(A) = jumlah nilai singular > tol. A ∈ R^(m×n) → int."""
    A = np.asarray(A, dtype=np.float64)
    if A.ndim != 2:
        raise ValueError("rank butuh matriks 2-D")
    s = np.linalg.svd(A, compute_uv=False)
    return int(np.sum(s > tol))
