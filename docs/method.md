# Analysis method

The pipeline first checks required columns and parses each row independently. Empty meter IDs, invalid timestamps, non-numeric or negative readings, and duplicate meter/timestamp pairs are rejected with the source row number. Valid readings remain available for the descriptive summaries.

Daily indicators are calculated per meter and calendar date. Since the input represents 15-minute energy intervals, interval kWh is multiplied by four to express interval-average kW. The load factor is the daily average load divided by the maximum interval-average load.

The anomaly review signal uses a median for the same meter and quarter-hour of day. A reading must exceed both a relative and a small absolute floor. The rule is easy to inspect but is not seasonally adjusted, does not estimate uncertainty, and may be misleading when meter behavior changes. Fewer than four baseline observations are not enough to create a signal.

The demo dataset is deterministic and synthetic. It exists to make the end-to-end workflow reproducible without sharing operational or personal data.
