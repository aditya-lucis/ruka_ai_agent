# -*- coding: utf-8 -*-
"""Deterministic synthetic datasets for Ruka's narrow classifiers.
Rules of the house (Part VI of the book):
- every dataset is a pure function of (seed, size): no network, no
  wall-clock, no global RNG state;
- class balance is documented and controllable;
- the generator *knows* the concept it encodes, so the "ground truth"
  is honest — synthetic data can prove a pipeline works, never that a
  problem is solved in the wild.
"""
from __future__ import annotations
import numpy as np

INTENTS = ("question", "command", "chitchat", "lookup", "code_help")
INTENT_ID = {name: i for i, name in enumerate(INTENTS)}

_TEMPLATES: dict[str, list[str]] = {
    "question": [
        "apa itu {t}?", "bagaimana cara kerja {t}?", "kenapa {t} penting?",
        "kapan {t} digunakan?", "siapa yang membuat {t}?",
        "jelaskan perbedaan {t} dan sistem lain", "what is {t} exactly?",
        "how does {t} work internally?",
    ],
    "command": [
        "jalankan {t} sekarang", "buatkan laporan {t} untukku",
        "hapus file {t} lama", "kirim hasil {t} ke tim",
        "update {t} ke versi terbaru", "atur ulang konfigurasi {t}",
        "run {t} and show output", "delete {t} logs please",
    ],
    "chitchat": [
        "hai, apa kabar?", "senang ngobrol sama kamu hari ini",
        "kamu lucu deh", "cuaca hari ini enak ya",
        "cerita dong apa saja", "aku capek nih", "hey how are you?",
        "that was fun, thanks!",
    ],
    "lookup": [
        "cari referensi tentang {t}", "temukan dokumen {t} di arsip",
        "tampilkan catatan {t} terbaru", "buka halaman {t}",
        "where can i find {t}?", "search the archive for {t}",
        "carikan saya link {t}", "show recent notes about {t}",
    ],
    "code_help": [
        "perbaiki bug di fungsi {t}", "refactor modul {t} agar lebih bersih",
        "tulis unit test untuk {t}", "debug error di {t}",
        "kenapa kode {t} throw exception?", "optimize {t} hot path",
        "review pull request untuk {t}", "help me fix this {t} traceback",
    ],
}

_TOPICS = ["embedding", "agent", "memori", "vstore", "retry", "budget",
           "loopguard", "regresi", "api", "parser", "cache", "sanity"]

def _noise(rng: np.random.Generator, text: str, level: float) -> str:
    """Typos and filler — makes the task non-trivial but learnable."""
    if rng.random() > level:
        return text
    ops = rng.integers(0, 3)
    chars = list(text)
    if not chars:
        return text
        
    if ops == 0 and len(chars) > 5:          # drop a char
        i = int(rng.integers(2, len(chars) - 1))
        del chars[i]
    elif ops == 1:                           # swap two chars
        i = int(rng.integers(2, len(chars) - 2))
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
    else:                                    # filler word
        filler = ("ya", "dong", "kira-kira", "sih", "please", "quickly")
        return f"{text} {filler[int(rng.integers(0, len(filler)))]}"
        
    return "".join(chars)

def make_intent_dataset(per_class: int = 120, noise: float = 0.35,
                        seed: int = 7) -> tuple[list[str], np.ndarray]:
    """Balanced intent utterances + integer labels (INTENT_ID order)."""
    rng = np.random.default_rng(seed)
    texts: list[str] = []
    labels: list[int] = []
    
    for intent, templates in _TEMPLATES.items():
        label = INTENT_ID[intent]
        for k in range(per_class):
            tpl = templates[int(rng.integers(0, len(templates)))]
            topic = _TOPICS[int(rng.integers(0, len(_TOPICS)))]
            texts.append(_noise(rng, tpl.format(t=topic), noise))
            labels.append(label)
            
    order = rng.permutation(len(texts))
    return [texts[i] for i in order], np.asarray([labels[i] for i in order])

def make_complexity_dataset(n: int = 600, seed: int = 11
                            ) -> tuple[list[str], np.ndarray]:
    """Task complexity labels: 0 = single-step, 1 = multi-step.
    Signal is honest and structural: multi-step utterances combine
    several verbs/dependencies ("lalu", "kemudian", "setelah itu",
    "then", "after that") or reference multiple artifacts.
    """
    rng = np.random.default_rng(seed)
    simple = [
        "baca file {a}", "cek status {a}", "tampilkan {a}",
        "hitung total {a}", "print the {a} config", "open {a}",
    ]
    multi = [
        "baca {a} lalu ringkas isinya", "cek {a} kemudian update {b}",
        "ambil {a}, bandingkan dengan {b}, lalu tulis laporan",
        "setelah migrasi {a}, jalankan tes untuk {b}",
        "read {a} then summarize it for me", "fetch {a} and {b} then merge",
    ]
    arts = ["log", "config", "dataset", "modul", "tabel", "doc", "index"]
    texts, labels = [], []
    
    for _ in range(n):
        if rng.random() < 0.5:
            tpl = simple[int(rng.integers(0, len(simple)))]
            texts.append(tpl.format(a=arts[int(rng.integers(0, len(arts)))]))
            labels.append(0)
        else:
            tpl = multi[int(rng.integers(0, len(multi)))]
            texts.append(tpl.format(a=arts[int(rng.integers(0, len(arts)))],
                                    b=arts[int(rng.integers(0, len(arts)))]))
            labels.append(1)
            
    order = rng.permutation(len(texts))
    return [texts[i] for i in order], np.asarray([labels[i] for i in order])

def split_stratified(texts: list[str], labels: np.ndarray,
                     val_fraction: float = 0.2, test_fraction: float = 0.2,
                     seed: int = 3) -> dict:
    """Class-balanced train/val/test split — never random-shuffle a
    skewed dataset and call the result a metric."""
    rng = np.random.default_rng(seed)
    out = {"train_x": [], "train_y": [], "val_x": [], "val_y": [],
           "test_x": [], "test_y": []}
           
    for c in np.unique(labels):
        idx = np.flatnonzero(labels == c)
        idx = idx[rng.permutation(len(idx))]
        n_val = max(1, int(len(idx) * val_fraction))
        n_test = max(1, int(len(idx) * test_fraction))
        
        for name, chunk in (("val", idx[:n_val]),
                            ("test", idx[n_val:n_val + n_test]),
                            ("train", idx[n_val + n_test:])):
            out[f"{name}_x"].extend(texts[i] for i in chunk)
            out[f"{name}_y"].extend(labels[i] for i in chunk)
            
    order = rng.permutation(len(out["train_x"]))
    out["train_x"] = [out["train_x"][i] for i in order]
    out["train_y"] = [out["train_y"][i] for i in order]
    
    for key in ("train_y", "val_y", "test_y"):
        out[key] = np.asarray(out[key], dtype=np.int64)
        
    return out
