"""Tests for Star Schema SQLite loading, referential integrity, and Power BI CSV export."""

from __future__ import annotations

from contextlib import closing
import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.etl.extract import extract_raw_data
from src.etl.load import TABLE_LOAD_ORDER, load_star_schema
from src.etl.transform import transform_data
from src.generate_raw_data import generate_raw_data


class TestStarSchemaLoad(unittest.TestCase):
    def test_star_schema_integrity_and_powerbi_exports(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            raw_dir = tmp / "raw"
            db_path = tmp / "warehouse" / "retail_dw.db"
            pbi_dir = tmp / "powerbi"
            report_path = tmp / "warehouse" / "data_quality_report.json"

            generate_raw_data(output_dir=raw_dir, num_customers=40, num_sales=300, seed=123)
            raw_datasets, profile = extract_raw_data(raw_dir)
            star_tables, _report = transform_data(raw_datasets, profile, report_path=report_path)
            load_summary = load_star_schema(star_tables, db_path=db_path, powerbi_dir=pbi_dir)

            self.assertTrue(db_path.exists())
            with closing(sqlite3.connect(db_path)) as conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                # Foreign key check must return zero violations
                fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
                self.assertEqual(fk_errors, [])

                for table in TABLE_LOAD_ORDER:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    self.assertGreater(count, 0)
                    self.assertEqual(count, load_summary["sqlite_counts"][table])

                # Ensure no negative quantities or revenues exist in fact table
                bad_rows = conn.execute(
                    "SELECT COUNT(*) FROM fato_vendas WHERE quantidade <= 0 OR receita_liquida <= 0"
                ).fetchone()[0]
                self.assertEqual(bad_rows, 0)

            # Verify all 5 Power BI CSVs exist and match SQLite row counts
            for table in TABLE_LOAD_ORDER:
                csv_path = pbi_dir / f"{table}.csv"
                self.assertTrue(csv_path.exists())
                with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
                    rows = list(csv.DictReader(fh))
                self.assertEqual(len(rows), load_summary["sqlite_counts"][table])


if __name__ == "__main__":
    unittest.main()
