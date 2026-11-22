"""CSV validation, interval analytics, and report writing."""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

REQUIRED = ("meter_id", "timestamp", "energy_kwh")
INTERVAL = timedelta(minutes=15)


@dataclass(frozen=True)
class Reading:
    meter_id: str
    timestamp: datetime
    energy_kwh: float


@dataclass(frozen=True)
class Finding:
    row: int
    code: str
    message: str


def load_readings(path: Path) -> tuple[list[Reading], list[Finding], int]:
    """Load valid records and retain row-specific reasons for rejected input."""
    readings: list[Reading] = []
    findings: list[Finding] = []
    seen: set[tuple[str, datetime]] = set()
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or [])
        missing = [column for column in REQUIRED if column not in headers]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        row_count = 0
        for row_count, row in enumerate(reader, start=2):
            meter = (row.get("meter_id") or "").strip()
            if not meter:
                findings.append(Finding(row_count, "missing_meter_id", "meter_id is empty"))
                continue
            try:
                timestamp = datetime.fromisoformat((row.get("timestamp") or "").strip())
            except ValueError:
                findings.append(Finding(row_count, "invalid_timestamp", "timestamp is not valid ISO 8601"))
                continue
            try:
                energy = float((row.get("energy_kwh") or "").strip())
            except ValueError:
                findings.append(Finding(row_count, "invalid_energy", "energy_kwh is not numeric"))
                continue
            if energy < 0:
                findings.append(Finding(row_count, "negative_energy", "energy_kwh must be non-negative"))
                continue
            key = (meter, timestamp)
            if key in seen:
                findings.append(Finding(row_count, "duplicate_reading", "meter_id and timestamp already occurred"))
                continue
            seen.add(key)
            readings.append(Reading(meter, timestamp, energy))
    return readings, findings, max(0, row_count - 1)


def find_gaps(readings: Iterable[Reading]) -> list[Finding]:
    findings: list[Finding] = []
    grouped: dict[str, list[datetime]] = defaultdict(list)
    for reading in readings:
        grouped[reading.meter_id].append(reading.timestamp)
    for meter, stamps in sorted(grouped.items()):
        stamps = sorted(set(stamps))
        for previous, current in zip(stamps, stamps[1:]):
            delta = current - previous
            if delta > INTERVAL:
                missing = int(delta / INTERVAL) - 1
                findings.append(Finding(0, "interval_gap", f"{meter}: {missing} interval(s) missing between {previous.isoformat()} and {current.isoformat()}"))
    return findings


def calculate_daily(readings: Iterable[Reading]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[Reading]] = defaultdict(list)
    for reading in readings:
        grouped[(reading.meter_id, reading.timestamp.date().isoformat())].append(reading)
    results: list[dict[str, object]] = []
    for (meter, day), items in sorted(grouped.items()):
        total = sum(item.energy_kwh for item in items)
        peak = max(items, key=lambda item: item.energy_kwh)
        average_kw = statistics.mean(item.energy_kwh for item in items) * 4
        peak_kw = peak.energy_kwh * 4
        results.append({
            "meter_id": meter,
            "date": day,
            "interval_count": len(items),
            "energy_kwh": round(total, 3),
            "average_load_kw": round(average_kw, 3),
            "peak_load_kw": round(peak_kw, 3),
            "peak_timestamp": peak.timestamp.isoformat(),
            "load_factor": round(average_kw / peak_kw, 4) if peak_kw else None,
        })
    return results


def find_anomalies(readings: Iterable[Reading], multiplier: float = 3.0, min_baseline: int = 4) -> list[dict[str, object]]:
    """Flag large readings relative to a same-meter, same-time-of-day median."""
    groups: dict[tuple[str, int], list[float]] = defaultdict(list)
    for item in readings:
        quarter = item.timestamp.hour * 4 + item.timestamp.minute // 15
        groups[(item.meter_id, quarter)].append(item.energy_kwh)
    flagged: list[dict[str, object]] = []
    for item in sorted(readings, key=lambda r: (r.meter_id, r.timestamp)):
        quarter = item.timestamp.hour * 4 + item.timestamp.minute // 15
        history = groups[(item.meter_id, quarter)]
        baseline = statistics.median(history)
        if len(history) < min_baseline:
            continue
        # A zero baseline needs an absolute floor to avoid flagging tiny readings.
        threshold = max(baseline * multiplier, baseline + 0.5)
        if item.energy_kwh > threshold:
            flagged.append({
                "meter_id": item.meter_id,
                "timestamp": item.timestamp.isoformat(),
                "energy_kwh": round(item.energy_kwh, 3),
                "baseline_median_kwh": round(baseline, 3),
                "threshold_kwh": round(threshold, 3),
                "reason": "Reading exceeds the same meter and quarter-hour median threshold",
            })
    return flagged


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def run(input_path: Path, output_dir: Path, multiplier: float = 3.0) -> dict[str, object]:
    readings, rejected, input_rows = load_readings(input_path)
    gap_findings = find_gaps(readings)
    daily = calculate_daily(readings)
    anomalies = find_anomalies(readings, multiplier=multiplier)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "daily_summary.csv", daily)
    write_csv(output_dir / "anomalies.csv", anomalies)
    all_findings = rejected + gap_findings
    summary = {
        "input_file": input_path.name,
        "input_rows": input_rows,
        "accepted_readings": len(readings),
        "rejected_readings": len(rejected),
        "interval_gaps": len(gap_findings),
        "anomaly_signals": len(anomalies),
        "meters": len({r.meter_id for r in readings}),
        "days": len({r.timestamp.date() for r in readings}),
        "findings": [asdict(f) for f in all_findings],
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    report = [
        "# Meter Reading Quality Report", "",
        f"- Input rows: {input_rows}", f"- Accepted readings: {len(readings)}",
        f"- Rejected readings: {len(rejected)}", f"- Detected interval gaps: {len(gap_findings)}",
        f"- Anomaly review signals: {len(anomalies)}", "",
        "## Daily overview", "", "| Meter | Date | kWh | Average kW | Peak kW | Load factor |", "|---|---|---:|---:|---:|---:|",
    ]
    for item in daily:
        report.append(f"| {item['meter_id']} | {item['date']} | {item['energy_kwh']} | {item['average_load_kw']} | {item['peak_load_kw']} | {item['load_factor']} |")
    report += ["", "## Findings", ""]
    report += [f"- Row {f.row} `{f.code}`: {f.message}" for f in all_findings] or ["No validation or interval-gap findings."]
    report += ["", "## Interpretation", "", "Anomaly rows are triage signals based on a historical median for the same meter and quarter-hour. They are not diagnoses. The demo uses synthetic data and does not infer equipment faults or business causes.", ""]
    (output_dir / "quality_report.md").write_text("\n".join(report), encoding="utf-8")
    return summary
