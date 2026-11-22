# Energy Meter Insights

Energy Meter Insights is a small, reproducible data pipeline for exploring interval meter readings. It validates CSV input, calculates daily and meter-level indicators, flags unusual readings with a transparent baseline rule, and writes concise CSV and Markdown outputs. It is designed as a general data engineering portfolio example; it is not tied to a particular employer or meter vendor.

## What it demonstrates

- A documented CSV contract and row-level validation with actionable findings.
- Deterministic synthetic interval data that can be regenerated locally.
- Aggregations by meter and day, including energy total, peak interval, average load, and load factor.
- Explainable anomaly signals based on each meter's median for the same interval-of-day.
- Separate pipeline stages for parsing, validation, aggregation, and reporting.
- No private, customer, or employer data. All included readings are synthetic.

## Run it

Python 3.11 or later; only the standard library is used.

```powershell
python -m pip install -e .
energy-insights analyze --input data/demo_readings.csv --output-dir output
```

Regenerate the sample readings:

```powershell
energy-insights make-demo --output data/demo_readings.csv
```

Run the end-to-end sample:

```powershell
energy-insights demo --output-dir output
```

## Input contract

CSV columns: `meter_id`, `timestamp`, `energy_kwh`. Timestamps are ISO 8601 and readings are non-negative interval consumption in kWh. Each `(meter_id, timestamp)` pair must be unique. The current demonstration assumes regular 15-minute intervals; the pipeline reports gaps and does not impute missing values.

## Outputs

- `daily_summary.csv`: daily energy, peak interval and load-factor indicators per meter.
- `anomalies.csv`: readings that exceed the configurable same-meter, same-quarter-hour baseline.
- `quality_report.md`: input counts, validation findings, summary indicators, and method limitations.
- `run_summary.json`: machine-readable run metadata and counts.

The anomaly rule compares a reading with the historical median for that meter and quarter-hour of day. It is a review signal, not a fault diagnosis or predictive model. Too little history is reported as insufficient baseline rather than treated as normal.

## Scope and next steps

This project is a local prototype over a small synthetic CSV. It has no MQTT, cloud, database, authentication, web UI, deployment, monitoring, or operational support integration. Natural next steps are a database-backed ingestion layer, API, configurable meter metadata, and load tests with representative data volumes.

See [the method note](docs/method.md) and [roadmap](docs/roadmap.md).

