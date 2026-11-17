#!/usr/bin/env python3
"""Parameterized forecast model for experimentation (the frozen winner is copied
into ../main.py as a standalone file; main.py never imports this).

Model family: log-ratio curves of past launches.
For each comparable, lr(h) = ln v(h) - ln v(1) over its release day (UTC hours
1..24). The case forecast is ln q50(h) = ln(p1) + alpha * agg_h(lr), with the
spread taken from the cross-comparable dispersion of lr(h) (normal z times an
IQR-based sigma, or empirical percentiles), optionally after screening
comparables by the shape of their own curve.
"""

import json
import math
from datetime import datetime, timedelta

Z = [-1.645, -0.674, 0.0, 0.674, 1.645]


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def percentile(sorted_vals, tau):
    """Linear-interpolation percentile of an ascending list (deterministic)."""
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def median(vals):
    return percentile(sorted(vals), 0.5)


def day_curve(comp):
    """{hour 1..24: viewers} of the comparable's release day, plus context."""
    ds = parse_ts(comp["day_start"])
    pts = {}
    for p in comp["hourly"]:
        pts[parse_ts(p["from"])] = p["viewers"]
    day = {}
    for h in range(1, 25):
        v = pts.get(ds + timedelta(hours=h - 1))
        if v is not None:
            day[h] = v
    pre = {}
    for k in range(1, 49):
        v = pts.get(ds - timedelta(hours=k))
        if v is not None:
            pre[k] = v
    return day, pre


def comparable_features(comp):
    day, pre = day_curve(comp)
    if 1 not in day or not day:
        return None
    peak = max(day.values())
    if peak <= 0 or day[1] <= 0:
        return None
    return {
        "day": day,
        "v1_over_peak": day[1] / peak,
        # Highest level in the 14..48h before day_start, relative to day peak:
        # an early-access launch is already big there; a rolling-midnight one is not.
        "pre_far_over_peak": max([pre[k] for k in pre if k >= 14] + [0]) / peak,
    }


def lr_table(case, min_v1_share=0.0, max_pre_far=None):
    """Per hour h=2..24, the list of lr(h) over the comparables that pass the
    shape screen (and have both v(1) and v(h) positive)."""
    table = {h: [] for h in range(2, 25)}
    kept, dropped = 0, 0
    for comp in case["comparables"]:
        f = comparable_features(comp)
        if f is None:
            dropped += 1
            continue
        if f["v1_over_peak"] < min_v1_share:
            dropped += 1
            continue
        if max_pre_far is not None and f["pre_far_over_peak"] > max_pre_far:
            dropped += 1
            continue
        kept += 1
        day = f["day"]
        lv1 = math.log(day[1])
        for h in range(2, 25):
            if h in day and day[h] > 0:
                table[h].append(math.log(day[h]) - lv1)
    return table, kept, dropped


def forecast(case, alpha=1.0, spread="iqr", sigma_floor=0.12, sigma_scale=1.0,
             min_v1_share=0.0, max_pre_far=None, center="median", smooth=0,
             blend=0.0):
    first = next(k for k in case["known"] if k["hour"] == 1)
    p1 = max(1.0, first["viewers"])
    table, kept, dropped = lr_table(case, min_v1_share, max_pre_far)
    rows = []
    for h in range(2, 25):
        vals = sorted(table[h])
        if smooth:  # pool neighbouring hours (shape evolves slowly) for stability
            pooled = list(vals)
            for dh in range(1, smooth + 1):
                if h - dh >= 2:
                    pooled += table[h - dh]
                if h + dh <= 24:
                    pooled += table[h + dh]
            vals = sorted(pooled)
        if not vals:  # no comparable covers this hour: fall back to flat
            med, sig = 0.0, sigma_floor
            qs = [med + z * sig for z in Z]
        else:
            med = median(vals) if center == "median" else (
                sum(sorted(vals)[2:-2]) / max(1, len(vals) - 4) if len(vals) > 4 else median(vals))
            if spread == "empirical":
                qs = [alpha * percentile(vals, t) for t in (0.05, 0.25, 0.5, 0.75, 0.95)]
                if blend:  # shrink empirical tails toward the normal approx
                    iqr = percentile(vals, 0.75) - percentile(vals, 0.25)
                    sig = max(sigma_floor, iqr / 1.349)
                    qs = [(1 - blend) * q + blend * (alpha * med + z * sig)
                          for q, z in zip(qs, Z)]
            else:
                iqr = percentile(vals, 0.75) - percentile(vals, 0.25)
                sig = max(sigma_floor, sigma_scale * iqr / 1.349)
                qs = [alpha * med + z * sig for z in Z]
        row = []
        prev = 0.0
        for q in qs:
            v = p1 * math.exp(q)
            v = min(1e9, max(0.01, v))
            v = max(v, prev)  # non-decreasing
            row.append(v)
            prev = v
        rows.append({"hour": h, "q": row})
    return {"hours": rows}, kept, dropped


def run_dir(in_dir, out_dir, **params):
    import os
    from pathlib import Path
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = {}
    for path in sorted(Path(in_dir).glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        fc, kept, dropped = forecast(case, **params)
        (out_dir / f"{path.stem}.out").write_text(
            json.dumps(fc, separators=(",", ":")) + "\n", encoding="utf-8")
        stats[path.stem] = (kept, dropped)
    return stats
