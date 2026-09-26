# -*- coding: utf-8 -*-
from .network import MLP
from .layers import Dense
from .activations import ACTIVATIONS, relu, sigmoid, tanh, softmax
from .losses import LOSSES, mse, bce_with_logits, cce_with_logits
from .optimizers import SGD, Momentum, Adam, clip_by_global_norm
from .trainer import Trainer, TrainingReport, EpochStats
from .features import hashed_trigram_features, lexical_overlap
from .datasets import (
    INTENTS, INTENT_ID, make_intent_dataset, make_complexity_dataset, split_stratified
)
from .intent_classifier import (
    RuleBasedIntentClassifier, CentroidIntentClassifier, MLPIntentClassifier, Prediction
)
from .gradcheck import numerical_gradient, check_gradients, relative_error

__all__ = [
    "MLP", "Dense", "ACTIVATIONS", "LOSSES",
    "SGD", "Momentum", "Adam", "clip_by_global_norm",
    "Trainer", "TrainingReport", "EpochStats",
    "hashed_trigram_features", "lexical_overlap",
    "INTENTS", "INTENT_ID", "make_intent_dataset", "make_complexity_dataset", "split_stratified",
    "RuleBasedIntentClassifier", "CentroidIntentClassifier", "MLPIntentClassifier", "Prediction",
    "numerical_gradient", "check_gradients", "relative_error"
]
