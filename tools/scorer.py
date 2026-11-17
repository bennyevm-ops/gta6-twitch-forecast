#!/usr/bin/env python3
"""Score forecast outputs on the practice cases with the contest's exact rule.

Loss (RULES.txt "Scoring"): for every case, every printed hour h in 2..24 and every
level tau in (0.05, 0.25, 0.5, 0.75, 0.95), with y the hour's print (below 1 counts
as 1) and q the forecast quantile:

    d = ln(y) - ln(q);  item loss = 2 * max(tau * d, (tau - 1) * d)

The score is the mean over all items of all cases. Lower is better.
Also reports the 90% coverage (share of scored hours with q05 <= y <= q95) and the
typical miss (100 * (exp(mean |ln(y) - ln(q50)|) - 1), in percent).

Usage:
    python3 tools/scorer.py <out_dir> [--answers tools/answers.json]
where <out_dir> holds p00.out .. p03.out. Prints per-case and overall numbers.
"""

import json
import math
import sys
from pathlib import Path

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
CASES = ["p00", "p01", "p02", "p03"]


def pinball(y: float, q: float, tau: float) -> float:
    d = math.log(max(1.0, y)) - math.log(q)
    return 2.0 * max(tau * d, (tau - 1.0) * d)


def score_case(out: dict, answers: dict) -> dict:
    rows = {r["hour"]: r["q"] for r in out["hours"]}
    total, n = 0.0, 0
    covered, scored_hours = 0, 0
    abs_med = 0.0
    for h in range(2, 25):
        if str(h) not in answers:
            continue  # hour has no print: not scored
        y = answers[str(h)]
        q = rows[h]
        scored_hours += 1
        if q[0] <= y <= q[4]:
            covered += 1
        abs_med += abs(math.log(max(1.0, y)) - math.log(q[2]))
        for tau, qv in zip(LEVELS, q):
            total += pinball(y, qv, tau)
            n += 1
    return {
        "loss": total / n,
        "coverage": covered / scored_hours,
        "typical_miss_pct": 100.0 * (math.exp(abs_med / scored_hours) - 1.0),
        "hours": scored_hours,
    }


def main() -> None:
    out_dir = Path(sys.argv[1])
    ans_path = Path(__file__).with_name("answers.json")
    if "--answers" in sys.argv:
        ans_path = Path(sys.argv[sys.argv.index("--answers") + 1])
    answers = json.loads(ans_path.read_text(encoding="utf-8"))
    losses, covs = [], []
    pooled_abs, pooled_hours = 0.0, 0
    for cid in CASES:
        out = json.loads((out_dir / f"{cid}.out").read_text(encoding="utf-8"))
        r = score_case(out, answers[cid]["hours"])
        losses.append(r["loss"])
        covs.append(r["coverage"])
        # Recompute the pooled median error exactly as RULES.txt defines it.
        rows = {row["hour"]: row["q"] for row in out["hours"]}
        for h in range(2, 25):
            if str(h) in answers[cid]["hours"]:
                pooled_abs += abs(math.log(max(1.0, answers[cid]["hours"][str(h)]))
                                  - math.log(rows[h][2]))
                pooled_hours += 1
        print(f"{cid} {answers[cid]['game']:<28} loss {r['loss']:.6f}  "
              f"coverage {r['coverage']:.3f}  typical miss {r['typical_miss_pct']:.1f}%")
    # Overall loss is the mean over items; every case has 23*5 items, so the plain
    # mean of per-case losses equals it.
    pooled_miss = 100.0 * (math.exp(pooled_abs / pooled_hours) - 1.0)
    print(f"OVERALL loss {sum(losses) / len(losses):.6f}  "
          f"coverage {sum(covs) / len(covs):.3f}  "
          f"typical miss {pooled_miss:.1f}%")


if __name__ == "__main__":
    main()
