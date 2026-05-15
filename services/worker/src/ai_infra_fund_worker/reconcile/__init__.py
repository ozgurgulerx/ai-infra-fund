"""Cross-source reconciliation jobs.

Compare snapshots from independent providers (e.g. yfinance vs Stooq) and
emit audit events when they disagree beyond a configurable threshold.
"""
