"""gta6-twitch-ccu-forecast-01 entry (Python 3.13, standard library only).

Forecasts a big game launch's Twitch category viewers for hours 2..24 of its
release day, given everything recorded up to the end of hour 1.

Method — the release-day shape of past launches, in log space:

  1. From the case's `comparables`, take each past launch's release-day hourly
     curve and its log-ratio curve lr(h) = ln v(h) - ln v(1). Two shape screens,
     both computed from the comparable's own data, keep only launches whose day
     1 is comparable to a rolling-midnight console launch with no early access:
       - already live at hour 1: v(1) is at least 3% of the day's peak (a single
         global unlock later in the day starts the day near zero instead);
       - not early-access contaminated: 14-48 hours before day_start the
         category was still below half of the day's peak (an early-access
         launch has effectively already happened by then).
  2. The forecast for hour h is the distribution of lr(h) across the surviving
     comparables, anchored at the case's own hour-1 print p:
       - the five levels' empirical percentiles of lr(h), blended 30% toward a
         normal curve (median + z * IQR/1.349, sigma floored at 0.12) to steady
         the tails of a ~20-launch sample;
       - q_tau(h) = p * exp(that), clamped to (0, 1e9] and made non-decreasing.

Nothing is hardcoded per game: every number comes from the case file at run
time. The program is deterministic (two runs byte-identical), reads every
*.in in $MAKEFUN_INPUT_DIR (else /input) and writes <id>.out to
$MAKEFUN_OUTPUT_DIR (else /output).
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first (as the starter does).
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]

MIN_V1_SHARE = 0.03   # hour 1 must hold at least 3% of the comparable's day peak
MAX_PRE_FAR = 0.5     # 14-48h before launch, below half the day peak
SIGMA_FLOOR = 0.12    # never report a tighter log spread than this
TAIL_BLEND = 0.3      # weight of the normal curve in the tail blend


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up (as the house baseline rounds)."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def percentile(sorted_vals: list[float], tau: float) -> float:
    """Linear-interpolation percentile of an ascending list."""
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def comparable_ratios(comp: dict) -> dict[int, float] | None:
    """{hour: lr(hour)} for one comparable, or None if a shape screen drops it."""
    day_start = parse_ts(comp["day_start"])
    points = {}
    for pt in comp["hourly"]:
        points[parse_ts(pt["from"])] = pt["viewers"]
    day = {}
    for h in range(1, 25):
        v = points.get(day_start + timedelta(hours=h - 1))
        if v is not None:
            day[h] = v
    if 1 not in day or day[1] <= 0 or not day:
        return None
    peak = max(day.values())
    if peak <= 0 or day[1] / peak < MIN_V1_SHARE:
        return None
    pre_far = 0.0
    for k in range(14, 49):
        v = points.get(day_start - timedelta(hours=k))
        if v is not None and v > pre_far:
            pre_far = v
    if pre_far / peak > MAX_PRE_FAR:
        return None
    lv1 = math.log(day[1])
    return {h: math.log(v) - lv1 for h, v in day.items() if h >= 2 and v > 0}


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1.0, first["viewers"])

    ratios: dict[int, list[float]] = {h: [] for h in range(2, 25)}
    for comp in case["comparables"]:
        lr = comparable_ratios(comp)
        if lr is None:
            continue
        for h, val in lr.items():
            ratios[h].append(val)

    rows = []
    for h in range(2, 25):
        vals = sorted(ratios[h])
        if not vals:
            # No comparable covers this hour: flat at hour 1 with the floor spread.
            log_qs = [z * SIGMA_FLOOR for z in Z]
        else:
            med = percentile(vals, 0.5)
            iqr = percentile(vals, 0.75) - percentile(vals, 0.25)
            sigma = max(SIGMA_FLOOR, iqr / 1.349)
            log_qs = []
            for tau, z in zip(LEVELS, Z):
                emp = percentile(vals, tau)
                log_qs.append((1.0 - TAIL_BLEND) * emp + TAIL_BLEND * (med + z * sigma))
        q = []
        prev = 0.0
        for lq in log_qs:
            v = p1 * math.exp(lq)
            v = min(1e9, max(0.01, v))
            v = max(v, prev)  # quantiles never decrease
            q.append(round2(v))
            prev = v
        rows.append({"hour": h, "q": q})
    return {"hours": rows}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
