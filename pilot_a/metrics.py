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


def paired_group_bootstrap(a, b, groups, n_boot: int = 10_000, seed: int = 42) -> dict:
    """Mean of a-b with a percentile CI, resampling whole GROUPS with replacement.

    Items from one source scenario are not independent, so resampling rows gives
    intervals that are too narrow (amendment 1, fix 4). The cluster bootstrap draws
    groups, then takes every item in each drawn group.
    """
    x, y = np.asarray(a, float), np.asarray(b, float)
    g = np.asarray(groups)
    assert x.shape == y.shape == g.shape
    d = x - y
    keys = np.unique(g)
    members = [np.flatnonzero(g == k) for k in keys]
    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.integers(0, len(members), size=len(members))
        idx = np.concatenate([members[j] for j in pick])
        draws[i] = d[idx].mean()
    lo, hi = np.percentile(draws, [2.5, 97.5])
    p = 2 * min((draws <= 0).mean(), (draws >= 0).mean())
    p = min(1.0, max(p, 1.0 / n_boot))
    return {
        "diff": float(d.mean()),
        "lo": float(lo),
        "hi": float(hi),
        "p": float(p),
        "n_items": len(d),
        "n_groups": len(keys),
    }


def fit_n50(ns, correct, n_max: int | None = None) -> dict:
    """accuracy = logistic(a + b*log2 N) fitted on item-level correctness.

    Returns the fitted a, b and N50; n50 is None when the curve never reaches 50%
    at or below n_max, which defaults to the largest N actually run (extrapolating
    a 50% crossing beyond the ladder is not something the data supports).

    Disabled in the amendment 1 run config; kept because the code and its test are
    still correct and the ladder may grow again.
    """
    if n_max is None:
        n_max = int(max(ns)) if len(ns) else 1
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


def review_threshold(dev_confidences, target_rate: float = 0.30) -> float:
    """tau for the review rule: flag an item when self-consistency <= tau.

    Self-consistency over K=5 samples only takes the values {0.2, ..., 1.0}, so a
    quantile cannot hit an arbitrary target rate and a strict `< quantile` rule can
    flag nothing at all. Pick the achievable threshold whose dev review rate is
    closest to the target, preferring the smaller rate on a tie, and report the
    rate actually achieved alongside it.
    """
    c = np.asarray(dev_confidences, float)
    if len(c) == 0:
        return -1.0
    best, best_key = -1.0, None
    for v in [-1.0, *np.unique(c).tolist()]:
        rate = float((c <= v).mean())
        key = (abs(rate - target_rate), rate)
        if best_key is None or key < best_key:
            best, best_key = float(v), key
    return best


def review_outcome(correct, confidence, tau: float) -> dict:
    """What the review rule does: what it catches, what it misses, what it wastes."""
    y, c = np.asarray(correct, int), np.asarray(confidence, float)
    flagged = c <= tau
    wrong = y == 0
    n, n_wrong, n_right = len(y), int(wrong.sum()), int((~wrong).sum())
    caught = int((flagged & wrong).sum())
    missed = int((~flagged & wrong).sum())
    false_pos = int((flagged & ~wrong).sum())
    return {
        "n": n,
        "review_rate": float(flagged.mean()) if n else float("nan"),
        "n_wrong": n_wrong,
        "errors_caught": caught,
        "errors_unflagged": missed,
        "errors_unflagged_rate": missed / n_wrong if n_wrong else None,
        "false_positives": false_pos,
        "false_positive_rate": false_pos / n_right if n_right else None,
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
