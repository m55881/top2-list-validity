"""Statistical helpers: Wilson CI, LR+ (log method), DeLong AUC and paired test, Cochran-Armitage."""
import numpy as np
from scipy import stats


def wilson(k, n, z=1.959964):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, c - h, c + h


def lr_pos(tp, fn, fp, tn, z=1.959964):
    sens = tp / (tp + fn); spec = tn / (tn + fp)
    lr = sens / (1 - spec)
    se = np.sqrt(1 / tp - 1 / (tp + fn) + 1 / fp - 1 / (fp + tn))
    return lr, lr * np.exp(-z * se), lr * np.exp(z * se)


def _midrank(x):
    J = np.argsort(x); Z = x[J]; N = len(x); T = np.zeros(N); i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]:
            j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1
        i = j
    T2 = np.empty(N); T2[J] = T
    return T2


def delong(y, scores):
    """AUCs and covariance (DeLong 1988, fast algorithm of Sun & Xu 2014) for one or more score vectors."""
    y = np.asarray(y).astype(bool)
    S = np.atleast_2d(np.asarray(scores, dtype=float))
    pos, neg = S[:, y], S[:, ~y]
    m, n = pos.shape[1], neg.shape[1]
    k = S.shape[0]
    tx = np.array([_midrank(r) for r in pos]); ty = np.array([_midrank(r) for r in neg])
    tz = np.array([_midrank(r) for r in np.hstack([pos, neg])])
    auc = tz[:, :m].sum(1) / m / n - (m + 1) / 2 / n
    v01 = (tz[:, :m] - tx) / n
    v10 = 1 - (tz[:, m:] - ty) / m
    cov = np.atleast_2d(np.cov(v01)) / m + np.atleast_2d(np.cov(v10)) / n
    return auc, cov


def auc_ci(y, s, z=1.959964):
    a, c = delong(y, [s]); se = np.sqrt(c[0, 0])
    return a[0], a[0] - z * se, a[0] + z * se


def delong_paired(y, s1, s2):
    a, c = delong(y, [s1, s2])
    d = a[0] - a[1]; se = np.sqrt(c[0, 0] + c[1, 1] - 2 * c[0, 1])
    zv = d / se
    return a[0], a[1], d, 2 * stats.norm.sf(abs(zv))


def cochran_armitage(counts, totals, scores=None):
    counts = np.asarray(counts, float); totals = np.asarray(totals, float)
    s = np.arange(len(counts)) if scores is None else np.asarray(scores, float)
    N = totals.sum(); p = counts.sum() / N
    T = (s * (counts - totals * p)).sum()
    V = p * (1 - p) * ((totals * s * s).sum() - (totals * s).sum() ** 2 / N)
    z = T / np.sqrt(V)
    return z, 2 * stats.norm.sf(abs(z))
