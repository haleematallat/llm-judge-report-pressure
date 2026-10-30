"""Metrics. Everything takes plain lists and returns plain numbers."""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import minimize

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float, float]:
    """(point, lo, hi) for a binomial proportion."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half)


def auroc(scores, labels) -> float:
    """AUROC of `scores` for predicting label 1. NaN if one class is absent."""
    s, y = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    ranks = np.argsort(np.argsort(np.concatenate([pos, neg]), kind="stable"), kind="stable") + 1
    # average ranks over ties
    order = np.argsort(np.concatenate([pos, neg]), kind="stable")
    vals = np.concatenate([pos, neg])[order]
    r = ranks.astype(float)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[j + 1] == vals[i]:
            j += 1
        if j > i:
            mean_rank = (i + j + 2) / 2
            r[order[i : j + 1]] = mean_rank
        i = j + 1
    return (r[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def ece(probs, labels, bins: int = 10) -> float:
    """Expected calibration error with equal-width bins."""
    p, y = np.asarray(probs, float), np.asarray(labels, int)
    if len(p) == 0:
        return float("nan")
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p > lo) & (p <= hi) if lo > 0 else (p >= lo) & (p <= hi)
        if not m.any():
            continue
        total += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(total)


def paired_bootstrap(a, b, n_boot: int = 10_000, seed: int = 42) -> dict:
    """Mean of a-b with a percentile CI, resampling items (paired)."""
    x, y = np.asarray(a, float), np.asarray(b, float)
    assert x.shape == y.shape
    d = x - y
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    draws = d[idx].mean(axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    p = 2 * min((draws <= 0).mean(), (draws >= 0).mean())
    # floored at one resample: a bootstrap cannot report a p below 1/n_boot
    p = min(1.0, max(p, 1.0 / n_boot))
    return {"diff": float(d.mean()), "lo": float(lo), "hi": float(hi), "p": float(p)}


def fit_n50(ns, correct, n_max: int = 16) -> dict:
    """accuracy = logistic(a + b*log2 N) fitted on item-level correctness.

    Returns the fitted a, b and N50; n50 is None when the curve never reaches 50%
    at or below n_max ("> 16" in the tables).
    """
    x = np.log2(np.asarray(ns, float))
    y = np.asarray(correct, float)
    if len(y) == 0 or len(set(y.tolist())) == 1:
        return {"a": float("nan"), "b": float("nan"), "n50": None, "note": "degenerate"}

    def nll(theta):
        z = theta[0] + theta[1] * x
        return float(np.logaddexp(0, z).sum() - (y * z).sum())

    res = minimize(nll, x0=np.array([0.0, 0.0]), method="BFGS")
    a, b = float(res.x[0]), float(res.x[1])
    if b >= 0:
        return {"a": a, "b": b, "n50": None, "note": "no decline"}
    n50 = 2 ** (-a / b)
    if n50 > n_max:
        return {"a": a, "b": b, "n50": None, "note": f"> {n_max}"}
    return {"a": a, "b": b, "n50": float(n50), "note": ""}


def router_threshold(dev_confidences, human_frac: float = 0.30) -> float:
    """tau set on dev-C0 so the lowest-confidence `human_frac` of items go to a human."""
    c = np.asarray(dev_confidences, float)
    if len(c) == 0:
        return 0.0
    return float(np.quantile(c, human_frac))


def router_miss(correct, confidence, tau: float) -> dict:
    """Share of wrong answers that the router would keep (confidence >= tau)."""
    y, c = np.asarray(correct, int), np.asarray(confidence, float)
    wrong = y == 0
    n_wrong = int(wrong.sum())
    kept = int((wrong & (c >= tau)).sum())
    return {
        "n": len(y),
        "n_wrong": n_wrong,
        "missed": kept,
        "miss_rate": (kept / n_wrong) if n_wrong else float("nan"),
        "share_of_items": kept / len(y) if len(y) else float("nan"),
        "routed_to_human": float((c < tau).mean()) if len(c) else float("nan"),
    }


def confidently_wrong(samples_list, golds) -> dict:
    """Share of items where every sample agrees and the agreed answer is wrong."""
    n = len(golds)
    hits = 0
    for samples, gold in zip(samples_list, golds):
        if samples and len(set(samples)) == 1 and samples[0] != gold:
            hits += 1
    return {"n": n, "k": hits, "rate": hits / n if n else float("nan")}


def phi(e1, e2) -> dict:
    """Pairwise phi and covariance of two 0/1 error indicators."""
    a, b = np.asarray(e1, int), np.asarray(e2, int)
    n11 = int(((a == 1) & (b == 1)).sum())
    n10 = int(((a == 1) & (b == 0)).sum())
    n01 = int(((a == 0) & (b == 1)).sum())
    n00 = int(((a == 0) & (b == 0)).sum())
    den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    return {
        "phi": (n11 * n00 - n10 * n01) / den if den else float("nan"),
        "cov": float(np.cov(a, b)[0, 1]) if len(a) > 1 else float("nan"),
        "n": len(a),
    }


def holm(pvals: dict) -> dict:
    """Holm-Bonferroni adjusted p-values within one family."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (key, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[key] = running
    return out
