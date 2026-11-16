"""Adoption by arm with item-clustered bootstrap CIs, paired differences, benefit retained, 2 figures.

    python analyze.py --runs runs.jsonl --wording W0
"""
import argparse

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--runs", default="runs.jsonl")
ap.add_argument("--wording", default="W0")
ap.add_argument("--boot", type=int, default=5000)
a = ap.parse_args()

df = pd.read_json(a.runs, lines=True)
df = df[df.wording == a.wording]
print(f"{len(df)} runs; no-answer rate {df.choice.isna().mean():.3f}; errors {df.error.notna().sum()}; "
      f"total logged cost ${df.cost.sum():.3f}")
rng = np.random.default_rng(0)

adopt = df.groupby(["item_id", "arm"]).adopted_false.mean().unstack()
acc = df.groupby(["item_id", "arm"]).correct.mean().unstack()


def boot(P, fn, arms):
    """Bootstrap over items that have all `arms`."""
    sub = P[arms].dropna()
    n = len(sub)
    vals = []
    for _ in range(a.boot):
        s = sub.iloc[rng.integers(0, n, n)]
        vals.append(fn(s.mean()))
    vals = np.array(vals, dtype=float)
    pt = fn(sub.mean())
    return pt, np.nanpercentile(vals, 2.5), np.nanpercentile(vals, 97.5), n


lines = ["| Arm | Adoption of false answer | 95% CI | Accuracy | n items |", "| --- | --- | --- | --- | --- |"]
res = {}
for arm in sorted(adopt.columns):
    p, lo, hi, n = boot(adopt, lambda m, arm=arm: m[arm], [arm])
    ac = acc[arm].mean()
    res[arm] = (p, lo, hi)
    lines.append(f"| {arm} | {p:.3f} | [{lo:.3f}, {hi:.3f}] | {ac:.3f} | {n} |")

lines += ["", "Paired difference vs A0 (negative = fewer false answers adopted):", "",
          "| Arm | Diff | 95% CI |", "| --- | --- | --- |"]
for arm in sorted(adopt.columns):
    if arm == "A0" or "A0" not in adopt.columns:
        continue
    p, lo, hi, _ = boot(adopt, lambda m, arm=arm: m[arm] - m["A0"], ["A0", arm])
    lines.append(f"| {arm} | {p:+.3f} | [{lo:+.3f}, {hi:+.3f}] |")


def retained(m, forged, honest):
    den = m["A0"] - m[honest]
    return np.nan if den < 0.05 else (m["A0"] - m[forged]) / den


ret = {}
for name, forged, honest in [("In-band (A4 vs A1)", "A4", "A1"), ("Out-of-band (A6 vs A3)", "A6", "A3")]:
    if all(x in adopt.columns for x in ["A0", forged, honest]):
        p, lo, hi, n = boot(adopt, lambda m: retained(m, forged, honest), ["A0", forged, honest])
        ret[name] = (p, lo, hi)
        lines.append(f"\nBenefit retained under forgery, {name}: {p:.2f} [{lo:.2f}, {hi:.2f}] (n={n}; "
                     f"NaN resamples dropped when honest benefit < 0.05)")
if "A7" in adopt.columns and "A0" in acc.columns:
    lines.append(f"\nCost of labels when truth is on low-tier sources: accuracy A7 {acc['A7'].mean():.3f} "
                 f"vs A0 {acc['A0'].mean():.3f}")
open("results.md", "w").write("\n".join(lines))
print("\n".join(lines))

arms = sorted(res)
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(arms, [res[x][0] for x in arms],
       yerr=[[res[x][0] - res[x][1] for x in arms], [res[x][2] - res[x][0] for x in arms]], capsize=4, color="#534AB7")
ax.set_ylabel("False-answer adoption rate"); ax.set_ylim(0, 1); ax.set_title("Adoption of planted false answer by arm")
fig.tight_layout(); fig.savefig("fig1_adoption.png", dpi=200)

if ret:
    fig, ax = plt.subplots(figsize=(5, 4))
    names = list(ret)
    ax.bar(names, [ret[n][0] for n in names],
           yerr=[[ret[n][0] - ret[n][1] for n in names], [ret[n][2] - ret[n][0] for n in names]], capsize=4,
           color=["#993C1D", "#0F6E56"][:len(names)])
    ax.set_ylabel("Share of label benefit retained under forgery"); ax.axhline(1, ls="--", c="gray")
    ax.set_title("Benefit retained: in-band vs out-of-band")
    fig.tight_layout(); fig.savefig("fig2_retained.png", dpi=200)
