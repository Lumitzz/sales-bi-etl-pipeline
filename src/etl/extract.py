"""Extract layer: reads raw CSV datasets and profiles initial data quality."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from src.config import RAW_DIR

logger = logging.getLogger(__name__)

EXPECTED_SCHEMAS: dict[str, list[str]] = {
    "clientes": ["cliente_id", "nome", "email", "cidade", "estado", "segmento", "data_cadastro"],
    "produtos": ["produto_id", "nome_produto", "categoria", "marca", "preco_unitario", "custo_unitario"],
    "lojas": ["loja_id", "nome_loja", "cidade", "estado", "canal"],
    "vendas": [
        "venda_id",
        "data_venda",
        "cliente_id",
        "produto_id",
        "loja_id",
        "quantidade",
        "preco_unitario",
        "desconto_pct",
        "forma_pagamento",
        "canal_venda",
    ],
}

FILE_MAP: dict[str, str] = {
    "clientes": "clientes_raw.csv",
    "produtos": "produtos_raw.csv",
    "lojas": "lojas_raw.csv",
    "vendas": "vendas_raw.csv",
}


def _read_csv_file(path: Path, expected_cols: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo raw não encontrado: {path}")

    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"Arquivo CSV vazio ou sem cabeçalho: {path}")
        missing = [col for col in expected_cols if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"Colunas obrigatórias ausentes em {path.name}: {missing}")
        return list(reader)


def _profile_table(rows: list[dict[str, str]], pk_col: str) -> dict[str, Any]:
    total_rows = len(rows)
    null_counts: dict[str, int] = {}
    if rows:
        for col in rows[0].keys():
            null_counts[col] = sum(1 for r in rows if (r.get(col) or "").strip() == "")
    seen_pks = [(r.get(pk_col) or "").strip() for r in rows if (r.get(pk_col) or "").strip()]
    duplicate_pks = len(seen_pks) - len(set(seen_pks))
    return {
        "total_rows": total_rows,
        "distinct_keys": len(set(seen_pks)),
        "duplicate_keys": duplicate_pks,
        "null_counts": null_counts,
    }


def extract_raw_data(raw_dir: Path = RAW_DIR) -> tuple[dict[str, list[dict[str, str]]], dict[str, Any]]:
    """Read all raw CSVs and return `(datasets, extract_profile)`."""
    datasets: dict[str, list[dict[str, str]]] = {}
    pk_map = {
        "clientes": "cliente_id",
        "produtos": "produto_id",
        "lojas": "loja_id",
        "vendas": "venda_id",
    }
    profile: dict[str, Any] = {}

    for key, filename in FILE_MAP.items():
        path = raw_dir / filename
        rows = _read_csv_file(path, EXPECTED_SCHEMAS[key])
        datasets[key] = rows
        table_profile = _profile_table(rows, pk_map[key])
        profile[key] = table_profile
        logger.info(
            "Extracted %-8s | rows=%d | distinct_keys=%d | duplicate_keys=%d",
            key,
            table_profile["total_rows"],
            table_profile["distinct_keys"],
            table_profile["duplicate_keys"],
        )

    return datasets, profile
