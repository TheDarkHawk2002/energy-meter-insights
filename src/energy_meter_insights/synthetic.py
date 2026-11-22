"""Deterministic generator for the public synthetic example dataset."""

from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta
from pathlib import Path


def generate(path: Path, days: int = 14) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 5)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["meter_id", "timestamp", "energy_kwh"])
        for meter, scale in (("site-north", 0.85), ("site-south", 1.15)):
            for index in range(days * 96):
                stamp = start + timedelta(minutes=15 * index)
                hour = stamp.hour + stamp.minute / 60
                daytime = max(0, math.sin((hour - 6) * math.pi / 14))
                weekly = 0.75 if stamp.weekday() >= 5 else 1.0
                base = scale * weekly * (0.22 + 0.9 * daytime)
                noise = ((index * 17 + (0 if meter == "site-north" else 11)) % 13 - 6) * 0.006
                energy = max(0.05, base + noise)
                if stamp == start + timedelta(days=5, hours=13, minutes=30) and meter == "site-north":
                    energy *= 5
                writer.writerow([meter, stamp.isoformat(timespec="seconds"), f"{energy:.3f}"])
                count += 1
    return count
