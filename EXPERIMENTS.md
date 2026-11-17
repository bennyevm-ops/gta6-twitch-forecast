# Experiments — gta6-twitch-ccu-forecast-01

All numbers are practice loss (mean pinball loss on the log scale over the 4
practice cases × hours 2–24 × 5 quantiles; lower is better), computed locally
with `tools/scorer.py` against the SullyGnome hourly averages fetched by
`tools/fetch_answers.py`. The scorer was validated first: run on the kit's
starter it gives loss **0.387097**, 90% coverage **0.783** — the house
baseline's published practice figures (RULES.txt: "about 0.387", "about
0.783"). The fetched hour-1 prints reproduce each case's `known` print
exactly, confirming the answer series is the one the cases were built from.

## Experiment table

| variant | change | practice loss | coverage | verdict |
|---|---|---:|---:|---|
| baseline | house starter: flat at hour 1, spread 0.15·√(h−1) | 0.387097 | 0.783 | reference |
| v1 | median lr(h), all 37 usable comparables, IQR spread | 0.310144 | 0.957 | keep direction |
| v2 | v1 but empirical percentiles instead of normal spread | 0.323970 | 0.967 | worse; tails noisy |
| v3 | + live-at-hour-1 screen (v1/peak ≥ 0.03, 29 kept), IQR spread | 0.303517 | 0.826 | screen helps 3 cases, hurts Wolverine |
| v4 | v3 with empirical percentiles | 0.285249 | 0.891 | keep |
| v5–v7 | screen threshold 0.02 / 0.05 / 0.08 | 0.285249 | 0.891 | identical — no comparable sits between 0.012 and 0.082, so the cut is not knife-edge |
| v8 | v4 with shrinkage α = 0.9 on the ratios | 0.291033 | 0.815 | worse |
| v9 | v4 with α = 1.1 | 0.285663 | 0.935 | neutral |
| v10 | v3 with trimmed-mean centre | 0.288872 | 0.837 | worse than v4 |
| v11 | v4 + early-access screen (level 14–48h pre-launch ≤ 0.5 × day peak, 20 kept) | 0.263753 | 0.924 | keep — drops exactly the launches whose notes say early access (Hogwarts, Starfield, Diablo IV, AC Shadows, DOOM, Death Stranding 2, Forza Horizon 5, …) |
| v12 | v3 with σ scale 1.3 | 0.304297 | 0.902 | IQR spread stays worse than empirical |
| v13 | all comparables, empirical, α = 0.8 | 0.296299 | 0.924 | screens beat shrinkage |
| v14 | all comparables, IQR spread × 1.2 | 0.338629 | 0.978 | worse |
| v15/v16 | EA screen at 0.4 / 0.6 | 0.263753 | 0.924 | identical to 0.5 (no comparable in between) |
| v17 | EA screen at 0.7 (also keeps Diablo IV, CoD MW4) | 0.262761 | 0.924 | coin-flip vs 0.5; 0.5 kept for the cleaner rule |
| v18 | v11 with α = 1.05 | 0.264690 | 0.924 | neutral |
| v19 | v11 screens but IQR spread | 0.266695 | 0.848 | empirical still better |
| v20 | v19 with σ scale 1.15 | 0.270633 | 0.902 | worse |
| v21 | v11 + pooling lr from hours h±1 | 0.268311 | 0.935 | worse; shape moves too fast to pool |
| v22 | v11 + tail blend 0.5 toward normal curve | 0.262471 | 0.880 | ≈ |
| **v23** | **v11 + tail blend 0.3** | **0.262069** | **0.902** | **WINNER — frozen into `main.py`** |
| v24 | EA screen 0.7 + blend 0.3 | 0.260181 | 0.902 | within noise of v23 (±0.002 on 4 cases); not taken |

Ideas tested and dropped on evidence: weighting by the case's pre-launch ramp
(the practice categories carry launch-eve marketing events — e.g. Wolverine's
category held ~41k viewers the hour *before* day_start, above its own hour-1
print — so pre-ramp features measure events, not unlock mechanics); parsing
the free-text `unlock` notes (the two data-driven screens recover the same
split without fragile text matching); a channels-based adjustment (no signal
found worth its complexity on 4 cases).

## Final entry (`main.py` = v23)

Practice loss **0.262069** vs house baseline **0.387097** (−32%). Per case:

| case | launch | loss | coverage | typical miss |
|---|---|---:|---:|---:|
| p00 | Marvel's Wolverine (2026-09-15) | 0.481187 | 0.826 | 130.6% |
| p01 | Red Dead Redemption 2 (2018-10-26) | 0.196391 | 0.957 | 32.4% |
| p02 | God of War Ragnarök (2022-11-09) | 0.169885 | 1.000 | 24.6% |
| p03 | Marvel's Spider-Man 2 (2023-10-20) | 0.200812 | 0.826 | 26.4% |
| **all** | | **0.262069** | **0.902** | **48.1%** |

Wolverine is the hard case: its day ramped ~9× from hour 1, in the top tail of
the screened comparables' shapes (their peak/hour-1 ratios run 1.0–12×). The
other three launches sit mid-distribution and score 0.17–0.20. With only four
practice cases, differences below ~±0.005 between variants are noise; the
winner was chosen for a clean, defensible configuration at the plateau, not
for the last decimal.

## Self-checks on the final `main.py`

- Determinism: two full runs over the 4 practice cases → byte-identical
  outputs (`diff -r` clean). Grader-style single-case runs
  (`python3 -P -s main.py`, one case per input dir, `PYTHONHASHSEED=0`)
  reproduce the batch outputs byte for byte.
- Runtime: 0.08–0.12 s per case (limit: 8 s), 1 CPU.
- Format, validated programmatically for every output: single key `hours`;
  exactly 23 rows, hours 2–24 each once; each row exactly `{hour, q}` with 5
  finite quantiles, non-decreasing, each in (0, 1e9]; file ≈1.5 KB
  (limit 65,536 bytes).
- No network, no randomness, standard library only; all inputs read from the
  case file at run time (no hardcoded answers or practice specifics).

Caveat: practice performance is measured on the historical source's hourly
averages; the final is graded on the house recorder's minute-read means for
2026-11-19, and must also beat the house model forecast, whose practice loss
is not published. Nothing here guarantees a prize — it is a verified
0.262-against-0.387 practice result with an honest 0.902 coverage.
