# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/bennyevm-ops/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/bennyevm-ops/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A program (`main.py`, Python 3.13, standard library only) that forecasts how
many people watch a big game launch on Twitch in each hour of its release day.
Given a case file with everything recorded up to the end of hour 1 — that
hour's viewer count included — plus 38–42 past big launches' hourly curves, it
writes, for hours 2–24, five quantiles (5%, 25%, 50%, 75%, 95%) of each hour's
viewer count. It is scored by mean pinball loss on the log scale; lower is
better.

## Approach

The forecast is the *shape* of past release days, transferred in log space:

1. **Log-ratio curves.** For every comparable launch in the case file, build
   its release-day (UTC) hourly curve and the ratios
   `lr(h) = ln v(h) − ln v(1)`. Ratios make a 20,000-viewer launch and a
   900,000-viewer launch directly comparable.
2. **Shape screens.** Two screens, both computed from each comparable's own
   data, keep only launches whose day 1 is shaped like the target's (a
   rolling-midnight console launch with no early access):
   - *already live at hour 1* — `v(1)` is at least 3% of the day's peak.
     Launches with a single global unlock later in the day (e.g. 14:00 UTC)
     start the day near zero and ramp a hundredfold; their ratios describe a
     different event.
   - *not early-access contaminated* — 14–48 hours before `day_start`, the
     category was still below half of the day's peak. An early-access launch
     has effectively already happened by then, and its "day 1" is a second
     wave, not a launch.
   The Grand Theft Auto VI category's own pre-release history (one of the
   comparables) has no release day and is dropped by construction.
3. **Quantiles.** For each hour, the forecast distribution is the empirical
   percentiles of `lr(h)` across the surviving comparables (about 20 of them),
   blended 30% toward a normal curve (median + z · IQR/1.349, σ floored at
   0.12) to steady the 5%/95% tails of a small sample. The result is anchored
   at the case's own hour-1 print: `q_tau(h) = p1 · exp(lr_tau(h))`, clamped
   to (0, 1e9] and made non-decreasing.

Nothing is hardcoded per game — every number comes from the case file at run
time, so the same program forecasts the practice cases and the final.

## Running it

```
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

It reads every `*.in` in the input directory and writes one `<id>.out` per
case: `{"hours": [{"hour": h, "q": [q05, q25, q50, q75, q95]} for h in 2..24]}`.
Deterministic: two runs are byte-identical. Runtime is ~0.1 s per case.

## Development

`tools/` holds the local scoring harness (not used by `main.py`):

- `tools/fetch_answers.py` — fetches the four practice launches' release-day
  hourly viewers from SullyGnome (the source the cases were built from, per
  the kit's `NOTICE.txt`) into `tools/answers.json`. The fetched hour-1 values
  reproduce the cases' `known` prints exactly.
- `tools/scorer.py` — the contest's exact pinball-loss rule, plus 90% coverage
  and typical miss. It reproduces the house baseline's published practice
  numbers (loss 0.387, coverage 0.783) on the kit's starter.
- `tools/model.py` — the parameterized model the variants in
  `EXPERIMENTS.md` were run with; `main.py` is the winning configuration,
  frozen as a standalone file.

See `EXPERIMENTS.md` for the experiment table and final practice results
(loss **0.262** vs the house baseline's 0.387; 90% coverage 0.902).

Data: SullyGnome.com hourly Twitch category averages, quoted with attribution
(see the kit's `NOTICE.txt` for terms).

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=af_sixaels&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
