"""RetailPulse — End-to-End ETL, Star Schema & BI Analytics CLI Entrypoint.

Usage:
    python main.py
    python main.py --sales 3000 --seed 42
    python main.py --skip-generate
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.config import DASHBOARD_DIR, DB_PATH, POWERBI_DIR, QUALITY_REPORT_PATH, RAW_DIR
from src.etl.extract import extract_raw_data
from src.etl.load import load_star_schema
from src.etl.transform import transform_data
from src.generate_raw_data import generate_raw_data
from src.run_analytics import execute_analytics


def run_pipeline(
    num_sales: int = 2400,
    num_customers: int = 200,
    seed: int = 42,
    skip_generate: bool = False,
) -> dict:
    """Execute the full RetailPulse pipeline end-to-end."""
    logger = logging.getLogger("retailpulse")

    if not skip_generate:
        logger.info("[1/5] Generating realistic raw retail CSV datasets...")
        raw_summary = generate_raw_data(
            output_dir=RAW_DIR,
            num_customers=num_customers,
            num_sales=num_sales,
            seed=seed,
        )
        logger.info("      Raw files written: %s", raw_summary)
    else:
        logger.info("[1/5] Skipping raw generation (using existing files in %s)", RAW_DIR)

    logger.info("[2/5] Extracting raw CSV datasets & profiling data quality...")
    raw_datasets, extract_profile = extract_raw_data(RAW_DIR)

    logger.info("[3/5] Transforming, cleaning, deduplicating & validating Star Schema...")
    star_tables, quality_report = transform_data(
        raw_datasets=raw_datasets,
        extract_profile=extract_profile,
        report_path=QUALITY_REPORT_PATH,
    )

    logger.info("[4/5] Loading Star Schema into SQLite DW & Power BI CSVs...")
    load_summary = load_star_schema(
        star_tables=star_tables,
        db_path=DB_PATH,
        powerbi_dir=POWERBI_DIR,
    )

    logger.info("[5/5] Running analytical SQL queries & updating dashboard dataset...")
    analytics_payload = execute_analytics(
        db_path=DB_PATH,
        quality_report_path=QUALITY_REPORT_PATH,
    )

    return {
        "quality_report": quality_report,
        "load_summary": load_summary,
        "analytics": analytics_payload,
    }


def _format_brl(value: float) -> str:
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RetailPulse — Pipeline ETL, Star Schema & Dashboard Analítico"
    )
    parser.add_argument("--sales", type=int, default=2400, help="Número base de vendas raw (padrão: 2400)")
    parser.add_argument("--customers", type=int, default=200, help="Número base de clientes raw (padrão: 200)")
    parser.add_argument("--seed", type=int, default=42, help="Seed aleatória para reprodutibilidade (padrão: 42)")
    parser.add_argument("--skip-generate", action="store_true", help="Usa arquivos já existentes em data/raw/")
    parser.add_argument("--quiet", action="store_true", help="Reduz verbosidade dos logs")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    result = run_pipeline(
        num_sales=args.sales,
        num_customers=args.customers,
        seed=args.seed,
        skip_generate=args.skip_generate,
    )

    kpi = result["analytics"]["kpi_overview"]
    qr = result["quality_report"]["summary"]

    print("\n" + "=" * 68)
    print("  RETAILPULSE — PIPELINE ETL & BI CONCLUÍDO COM SUCESSO")
    print("=" * 68)
    print(f"  Receita Líquida Total : {_format_brl(kpi['receita_total'])}")
    print(f"  Lucro Bruto Total     : {_format_brl(kpi['lucro_bruto'])} (Margem: {kpi['margem_bruta_pct']:.2f}%)")
    print(f"  Ticket Médio          : {_format_brl(kpi['ticket_medio'])}")
    print(f"  Pedidos Válidos       : {kpi['total_pedidos']:,} / {qr['raw_sales_rows']:,} ({qr['sales_acceptance_rate_pct']:.2f}% aproveitamento)")
    print(f"  Anomalias Tratadas    : {qr['total_issues_resolved']:,}")
    print("-" * 68)
    print(f"  SQLite Warehouse      : {DB_PATH}")
    print(f"  Power BI CSVs         : {POWERBI_DIR}")
    print(f"  Relatório Qualidade   : {QUALITY_REPORT_PATH}")
    print(f"  Dashboard Interativo  : {Path(DASHBOARD_DIR) / 'index.html'}")
    print("=" * 68 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
