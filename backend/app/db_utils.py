"""
Database dialect helpers for SQLite vs PostgreSQL compatibility.
Use these instead of raw strftime/date_trunc so the same code works with both backends.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func


def day_range_utc(day_str: str):
    """
    Return (day_start_utc, day_end_utc) for filtering logs by date string 'YYYY-MM-DD'.
    Use: timestamp >= day_start, timestamp < day_end (works for SQLite and PostgreSQL).
    """
    day_start = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    return day_start, day_end


def _is_sqlite(session: Session) -> bool:
    """True if the session is bound to a SQLite engine."""
    return session.get_bind().dialect.name == "sqlite"


def minute_bucket(session: Session, column):
    """
    Expression for truncating timestamp to minute (for COUNT DISTINCT unique minutes).
    SQLite: strftime('%Y-%m-%d %H:%M', col)
    PostgreSQL: date_trunc('minute', col)
    """
    if _is_sqlite(session):
        return func.strftime("%Y-%m-%d %H:%M", column)
    return func.date_trunc("minute", column)


def date_expr(session: Session, column):
    """
    Expression for date part (YYYY-MM-DD) for grouping/label.
    SQLite: strftime('%Y-%m-%d', col)
    PostgreSQL: to_char(col, 'YYYY-MM-DD')
    """
    if _is_sqlite(session):
        return func.strftime("%Y-%m-%d", column)
    return func.to_char(column, "YYYY-MM-DD")


def hour_expr(session: Session, column):
    """
    Expression for hour part (0-23) for grouping/label.
    SQLite: strftime('%H', col)  -> string
    PostgreSQL: extract(hour from col) -> numeric, int() in Python works
    """
    if _is_sqlite(session):
        return func.strftime("%H", column)
    return func.extract("hour", column)
