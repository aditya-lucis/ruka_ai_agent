import math

def log_odds_to_prob(log_odds: float) -> float:
    """Konversi log-odds ke probabilitas (fungsi sigmoid)."""
    # sigmoid = 1 / (1 + e^-x)
    return 1.0 / (1.0 + math.exp(-log_odds))

def prob_to_log_odds(prob: float) -> float:
    """Konversi probabilitas ke log-odds."""
    if prob <= 0.0 or prob >= 1.0:
        raise ValueError("Probabilitas harus dalam range (0, 1)")
    return math.log(prob / (1.0 - prob))

def bayes_update_logodds(prior_prob: float, total_llr: float) -> float:
    """
    Menghitung log-odds posterior dari prior probability dan total LLR.
    posterior_logodds = prior_logodds + sum(LLR_i)
    """
    prior_lo = prob_to_log_odds(prior_prob)
    return prior_lo + total_llr
