# -*- coding: utf-8 -*-
"""Trainer: mini-batch loop with early stopping, L2, clipping, history.
Everything that can make training non-reproducible is explicit here:
seed control, deterministic shuffling, fixed batch logic, and a
metrics history that records train/val loss and accuracy per epoch so
overfitting is *visible*, not discovered in production.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable
import numpy as np

from .losses import LOSSES
from .network import MLP
from .optimizers import Adam, Momentum, SGD, clip_by_global_norm

_OPTIMIZERS = {"sgd": SGD, "momentum": Momentum, "adam": Adam}

class TrainerConfigError(ValueError):
    pass

@dataclass
class EpochStats:
    epoch: int
    train_loss: float
    val_loss: float
    val_acc: float
    grad_norm: float
    seconds: float

@dataclass
class TrainingReport:
    epochs: int
    best_epoch: int
    best_val_loss: float
    final_val_acc: float
    stopped_early: bool
    history: list[EpochStats] = field(default_factory=list)

class Trainer:
    def __init__(self, network: MLP, loss: str = "cce",
                 optimizer: str = "adam", lr: float = 0.01,
                 batch_size: int = 32, max_epochs: int = 200,
                 patience: int = 15, l2: float = 0.0,
                 grad_clip: float | None = 5.0, seed: int = 0) -> None:
        if loss not in LOSSES:
            raise TrainerConfigError(f"unknown loss {loss!r}")
        if optimizer not in _OPTIMIZERS:
            raise TrainerConfigError(f"unknown optimizer {optimizer!r}")
        if batch_size <= 0 or max_epochs <= 0 or patience <= 0:
            raise TrainerConfigError("batch_size/epochs/patience must be > 0")
            
        self.net = network
        self._loss_fwd, self._loss_bwd = LOSSES[loss]
        self.opt = _OPTIMIZERS[optimizer](lr=lr, weight_decay=l2)
        self.batch_size = batch_size
        self.max_epochs = max_epochs
        self.patience = patience
        self.grad_clip = grad_clip
        self.seed = seed

    def _accuracy(self, logits: np.ndarray, y: np.ndarray) -> float:
        pred = logits.argmax(axis=-1)
        return float((pred == y).mean())

    def _epoch_pass(self, x: np.ndarray, y: np.ndarray,
                    train: bool) -> tuple[float, float]:
        logits = self.net.forward(x)
        if not train:
            return self._loss_fwd(logits, y), self._accuracy(logits, y)
            
        loss = self._loss_fwd(logits, y)
        d = self._loss_bwd(logits, y)
        self.net.backward(d)
        return loss, self._accuracy(logits, y)

    def fit(self, x_train: np.ndarray, y_train: np.ndarray,
            x_val: np.ndarray, y_val: np.ndarray) -> TrainingReport:
        rng = np.random.default_rng(self.seed)
        n = x_train.shape[0]
        history: list[EpochStats] = []
        best_val = float("inf")
        best_epoch = 0
        stale = 0
        stopped_early = False
        
        t0 = time.perf_counter()
        for epoch in range(1, self.max_epochs + 1):
            order = rng.permutation(n)
            batch_losses: list[float] = []
            gn_accum: list[float] = []
            
            for start in range(0, n, self.batch_size):
                idx = order[start:start + self.batch_size]
                xb, yb = x_train[idx], y_train[idx]
                
                loss, _ = self._epoch_pass(xb, yb, train=True)
                grads = self.net.grads
                
                if self.grad_clip is not None:
                    gn = clip_by_global_norm(grads, self.grad_clip)
                    gn_accum.append(gn)
                    
                self.opt.step(self.net.params, grads)
                batch_losses.append(loss)
                
            val_loss, val_acc = self._epoch_pass(x_val, y_val, train=False)
            
            stats = EpochStats(
                epoch=epoch,
                train_loss=float(np.mean(batch_losses)),
                val_loss=val_loss,
                val_acc=val_acc,
                grad_norm=float(np.mean(gn_accum)) if gn_accum else 0.0,
                seconds=time.perf_counter() - t0,
            )
            history.append(stats)
            
            if val_loss < best_val - 1e-6:
                best_val, best_epoch, stale = val_loss, epoch, 0
            else:
                stale += 1
                if stale >= self.patience:
                    stopped_early = True
                    break
                    
        return TrainingReport(
            epochs=len(history), best_epoch=best_epoch, best_val_loss=best_val,
            final_val_acc=history[-1].val_acc,
            stopped_early=stopped_early, history=history,
        )
