"""Tests for analytical SQL queries (MoM/YoY, ABC curve, RFM, KPIs) and dashboard export."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.etl.extract import extract_raw_data
from src.etl.load import load_star_schema
from src.etl.transform import transform_data
from src.generate_raw_data import generate_raw_data
from src.run_analytics import execute_analytics


class TestSQLAnalytics(unittest.TestCase):
    def test_analytical_queries_and_dashboard_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            raw_dir = tmp / "raw"
            db_path = tmp / "warehouse" / "retail_dw.db"
            pbi_dir = tmp / "powerbi"
            report_path = tmp / "warehouse" / "data_quality_report.json"
            out_json = tmp / "dashboard" / "data.json"
            out_js = tmp / "dashboard" / "dashboard_data.js"

            generate_raw_data(output_dir=raw_dir, num_customers=60, num_sales=600, seed=99)
            raw_datasets, profile = extract_raw_data(raw_dir)
            star_tables, _ = transform_data(raw_datasets, profile, report_path=report_path)
            load_star_schema(star_tables, db_path=db_path, powerbi_dir=pbi_dir)

            payload = execute_analytics(
                db_path=db_path,
                quality_report_path=report_path,
                output_json_path=out_json,
                output_js_path=out_js,
            )

            # 1. KPI overview sanity checks
            kpi = payload["kpi_overview"]
            self.assertGreater(kpi["receita_total"], 0)
            self.assertGreater(kpi["lucro_bruto"], 0)
            self.assertGreater(kpi["margem_bruta_pct"], 0)
            self.assertLess(kpi["margem_bruta_pct"], 100)
            self.assertAlmostEqual(
                kpi["ticket_medio"],
                round(kpi["receita_total"] / kpi["total_pedidos"], 2),
                delta=0.05,
            )

            # 2. Monthly series has MoM growth computed after first month
            monthly = payload["monthly_revenue_growth"]
            self.assertGreaterEqual(len(monthly), 12)
            self.assertIsNone(monthly[0]["crescimento_mom_pct"])
            self.assertIsNotNone(monthly[1]["crescimento_mom_pct"])

            # 3. Category & regional shares sum to ~100%
            cat_share_sum = sum(r["participacao_pct"] for r in payload["category_performance"])
            self.assertAlmostEqual(cat_share_sum, 100.0, delta=0.5)
            reg_share_sum = sum(r["participacao_pct"] for r in payload["regional_performance"])
            self.assertAlmostEqual(reg_share_sum, 100.0, delta=0.5)

            # 4. ABC curve cumulative % is monotonically non-decreasing and ends at ~100%
            abc = payload["abc_curve_products"]
            self.assertGreater(len(abc), 0)
            cumulatives = [r["acumulado_pct"] for r in abc]
            self.assertEqual(cumulatives, sorted(cumulatives))
            self.assertAlmostEqual(cumulatives[-1], 100.0, delta=0.5)
            self.assertTrue(all(r["classe_abc"] in {"A", "B", "C"} for r in abc))

            # 5. RFM segmentation covers active customers
            rfm = payload["rfm_segmentation"]
            self.assertGreater(len(rfm), 0)
            self.assertEqual(sum(r["total_clientes"] for r in rfm), kpi["clientes_ativos"])

            # 6. Top customers capped at 10
            self.assertLessEqual(len(payload["top_customers"]), 10)

            # 7. Dashboard files exist and JS embeds valid JSON payload
            self.assertTrue(out_json.exists())
            self.assertTrue(out_js.exists())
            loaded_json = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(loaded_json["kpi_overview"]["total_pedidos"], kpi["total_pedidos"])
            js_content = out_js.read_text(encoding="utf-8")
            self.assertIn("window.RETAILPULSE_DATA =", js_content)


if __name__ == "__main__":
    unittest.main()
