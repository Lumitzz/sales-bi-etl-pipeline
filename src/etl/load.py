"""Load layer: persists Star Schema into SQLite Data Warehouse and Power BI-ready CSVs."""

from __future__ import annotations

from contextlib import closing
import csv
import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.config import DB_PATH, POWERBI_DIR, SCHEMA_SQL_PATH

logger = logging.getLogger(__name__)

TABLE_LOAD_ORDER = [
    "dim_clientes",
    "dim_produtos",
    "dim_lojas",
    "dim_tempo",
    "fato_vendas",
]

TABLE_COLUMNS: dict[str, list[str]] = {
    "dim_clientes": [
        "cliente_id", "nome", "email", "cidade", "estado",
        "nome_estado", "regiao", "segmento", "data_cadastro",
    ],
    "dim_produtos": [
        "produto_id", "nome_produto", "categoria", "marca",
        "preco_lista", "custo_unitario",
    ],
    "dim_lojas": [
        "loja_id", "nome_loja", "cidade", "estado",
        "nome_estado", "regiao", "canal_padrao",
    ],
    "dim_tempo": [
        "tempo_id", "data", "ano", "trimestre", "mes",
        "nome_mes", "ano_mes", "dia", "dia_semana", "fim_de_semana",
    ],
    "fato_vendas": [
        "venda_id", "tempo_id", "data_venda", "cliente_id", "produto_id",
        "loja_id", "quantidade", "preco_unitario", "desconto_pct",
        "valor_bruto", "valor_desconto", "receita_liquida", "custo_total",
        "lucro_bruto", "margem_bruta_pct", "forma_pagamento", "canal_venda",
    ],
}


def load_to_sqlite(
    star_tables: dict[str, list[dict[str, Any]]],
    db_path: Path = DB_PATH,
    schema_path: Path = SCHEMA_SQL_PATH,
) -> dict[str, int]:
    """Create Star Schema tables in SQLite and load all transformed records."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    ddl = schema_path.read_text(encoding="utf-8")

    inserted_counts: dict[str, int] = {}
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(ddl)

        for table_name in TABLE_LOAD_ORDER:
            rows = star_tables.get(table_name, [])
            cols = TABLE_COLUMNS[table_name]
            placeholders = ", ".join("?" for _ in cols)
            col_list = ", ".join(cols)
            sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"
            values = [tuple(row[col] for col in cols) for row in rows]
            conn.executemany(sql, values)
            inserted_counts[table_name] = len(values)
            logger.info("Loaded SQLite table %-14s | rows=%d", table_name, len(values))

        conn.commit()

    return inserted_counts


def export_powerbi_csvs(
    star_tables: dict[str, list[dict[str, Any]]],
    output_dir: Path = POWERBI_DIR,
) -> dict[str, Path]:
    """Export clean Star Schema CSVs (UTF-8 with BOM) ready for Power BI Desktop."""
    output_dir.mkdir(parents=True, exist_ok=True)
    exported: dict[str, Path] = {}

    for table_name in TABLE_LOAD_ORDER:
        cols = TABLE_COLUMNS[table_name]
        rows = star_tables.get(table_name, [])
        out_path = output_dir / f"{table_name}.csv"
        with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols)
            writer.writeheader()
            for row in rows:
                writer.writerow({col: row[col] for col in cols})
        exported[table_name] = out_path
        logger.info("Exported Power BI CSV %-18s | rows=%d", out_path.name, len(rows))

    return exported


def load_star_schema(
    star_tables: dict[str, list[dict[str, Any]]],
    db_path: Path = DB_PATH,
    powerbi_dir: Path = POWERBI_DIR,
    schema_path: Path = SCHEMA_SQL_PATH,
) -> dict[str, Any]:
    """Load data into both SQLite DW and Power BI CSVs."""
    sqlite_counts = load_to_sqlite(star_tables, db_path=db_path, schema_path=schema_path)
    pbi_files = export_powerbi_csvs(star_tables, output_dir=powerbi_dir)
    return {
        "sqlite_path": str(db_path),
        "sqlite_counts": sqlite_counts,
        "powerbi_files": {k: str(v) for k, v in pbi_files.items()},
    }
