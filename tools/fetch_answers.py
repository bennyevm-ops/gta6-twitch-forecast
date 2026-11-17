#!/usr/bin/env python3
"""Fetch the practice answers (release-day hourly average viewers) from SullyGnome.

Source: SullyGnome.com hourly Twitch category averages, via the JSON behind each
game's page, exactly as NOTICE.txt documents:

  GET https://sullygnome.com/api/charts/linecharts/getconfig/GameViewers/30/0/<id>/<name>/%20/%20/<YYYY>/<M>/%20/0/

One request per game (its release month). Writes tools/answers.json:
  {case_id: {"game": name, "day": "YYYY-MM-DD", "hours": {"1": v1, ..., "24": v24}}}
Hours are UTC hours of the release day; a point at label "YYYY-MM-DD HH:00" is the
average over [HH:00, HH+1:00). Missing (null) hours are omitted.

This is a development tool only; main.py never reads it.
"""

import json
import subprocess
import sys
from pathlib import Path

GAMES = {
    # case_id: (sullygnome id, url name, release date YYYY-MM-DD)
    "p00": (117671, "Marvel's_Wolverine", "2026-09-15"),
    "p01": (28264, "Red_Dead_Redemption_2", "2018-10-26"),
    "p02": (65645, "God_of_War_Ragnar%C3%B6k", "2022-11-09"),
    "p03": (97296, "Marvel's_Spider-Man_2", "2023-10-20"),
}

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def fetch(sg_id: int, name: str, year: int, month: int) -> dict:
    url = (
        "https://sullygnome.com/api/charts/linecharts/getconfig/GameViewers"
        f"/30/0/{sg_id}/{name}/%20/%20/{year}/{month}/%20/0/"
    )
    out = subprocess.run(
        ["curl", "-s", "-m", "60", "-A", UA, url],
        capture_output=True, text=True, check=True,
    ).stdout
    d = json.loads(out)
    labels = d["data"]["labels"]
    avg = None
    for ds in d["data"]["datasets"]:
        if ds.get("label") == "Average viewers":
            avg = ds["data"]
    if avg is None:
        raise RuntimeError(f"no 'Average viewers' dataset for {name}")
    return dict(zip(labels, avg))


def main() -> None:
    answers = {}
    for case_id, (sg_id, name, day) in GAMES.items():
        year, month, _ = (int(x) for x in day.split("-"))
        series = fetch(sg_id, name, year, month)
        hours = {}
        for hh in range(1, 25):
            label = f"{day} {hh - 1:02d}:00"
            v = series.get(label)
            if v is not None:
                hours[str(hh)] = v
        answers[case_id] = {"game": name, "day": day, "hours": hours}
        print(f"{case_id} {name} {day}: {len(hours)} hours fetched", file=sys.stderr)
    out_path = Path(__file__).with_name("answers.json")
    out_path.write_text(json.dumps(answers, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
