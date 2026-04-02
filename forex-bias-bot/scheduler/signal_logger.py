import sqlite3
import json
from datetime import datetime
from typing import Optional
import os


class SignalLogger:
    def __init__(self, db_path: str = "signals.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence INTEGER,
                reasoning TEXT,
                sentiment_score REAL,
                rsi REAL,
                macd REAL,
                current_price REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER REFERENCES signals(id),
                price_1h_later REAL,
                price_change_pct REAL,
                outcome TEXT,
                validation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def log(self, signal_data: dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals (pair, signal, confidence, reasoning, sentiment_score, rsi, macd, current_price, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_data.get("pair"),
            signal_data.get("signal"),
            signal_data.get("confidence"),
            signal_data.get("reasoning"),
            signal_data.get("sentiment_score"),
            signal_data.get("technical", {}).get("rsi"),
            signal_data.get("technical", {}).get("macd"),
            signal_data.get("technical", {}).get("current_price"),
            datetime.now(),
        ))
        conn.commit()
        conn.close()

    def get_recent(self, pair: Optional[str] = None, limit: int = 10) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if pair:
            cursor.execute(
                "SELECT * FROM signals WHERE pair = ? ORDER BY timestamp DESC LIMIT ?",
                (pair, limit)
            )
        else:
            cursor.execute("SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?", (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_unvalidated(self, pair: Optional[str] = None, limit: int = 100) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if pair:
            cursor.execute("""
                SELECT s.* FROM signals s
                LEFT JOIN signal_validations v ON s.id = v.signal_id
                WHERE s.pair = ? AND v.id IS NULL
                ORDER BY s.timestamp DESC LIMIT ?
            """, (pair, limit))
        else:
            cursor.execute("""
                SELECT s.* FROM signals s
                LEFT JOIN signal_validations v ON s.id = v.signal_id
                WHERE v.id IS NULL
                ORDER BY s.timestamp DESC LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def log_validation(self, validation: dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signal_validations (signal_id, price_1h_later, price_change_pct, outcome)
            VALUES (?, ?, ?, ?)
        """, (
            validation.get("signal_id"),
            validation.get("price_1h_later"),
            validation.get("price_change_pct"),
            validation.get("outcome"),
        ))
        conn.commit()
        conn.close()

    def get_stats(self, pair: Optional[str] = None) -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if pair:
            cursor.execute("""
                SELECT s.pair, s.signal, s.confidence, v.outcome
                FROM signals s
                JOIN signal_validations v ON s.id = v.signal_id
                WHERE s.pair = ?
            """, (pair,))
        else:
            cursor.execute("""
                SELECT s.pair, s.signal, s.confidence, v.outcome
                FROM signals s
                JOIN signal_validations v ON s.id = v.signal_id
            """)

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


signal_logger = SignalLogger()
