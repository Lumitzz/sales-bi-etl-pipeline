"""Transform layer: cleans, deduplicates, standardizes, validates, and enriches data.

Produces clean Star Schema tables:
- dim_clientes
- dim_produtos
- dim_lojas
- dim_tempo
- fato_vendas

And writes a comprehensive `data_quality_report.json`.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.config import (
    CATEGORY_STANDARDIZATION,
    CHANNEL_STANDARDIZATION,
    MONTH_NAMES_PT,
    PAYMENT_STANDARDIZATION,
    QUALITY_REPORT_PATH,
    RAW_DATE_FORMATS,
    STATE_STANDARDIZATION,
    WEEKDAY_NAMES_PT,
)

logger = logging.getLogger(__name__)


def _strip_accents_upper(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    nfkd = unicodedata.normalize("NFKD", cleaned)
    ascii_str = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return ascii_str.upper()


def clean_text(value: str | None, title_case: bool = False) -> str:
    """Trim whitespace, collapse internal spaces, and optionally apply smart title case."""
    if not value:
        return ""
    cleaned = " ".join(value.strip().split())
    if not title_case:
        return cleaned
    lowercase_particles = {"de", "da", "do", "das", "dos", "e"}
    words = cleaned.lower().split(" ")
    formatted = [
        w if (i > 0 and w in lowercase_particles) else w.capitalize()
        for i, w in enumerate(words)
    ]
    return " ".join(formatted)


def parse_date(raw_value: str | None) -> date | None:
    """Parse multiple messy date formats into a Python `date` object."""
    if not raw_value:
        return None
    cleaned = raw_value.strip()
    if not cleaned:
        return None
    for fmt in RAW_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def parse_currency(raw_value: str | None) -> float | None:
    """Parse messy numeric/currency strings such as 'R$ 1.299,90', '450,00', '1299.90'."""
    if raw_value is None:
        return None
    cleaned = raw_value.strip()
    if not cleaned:
        return None
    cleaned = re.sub(r"[R$\s]", "", cleaned, flags=re.IGNORECASE)
    if "," in cleaned and "." in cleaned:
        # Assume Brazilian format: 1.299,90 -> 1299.90
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def standardize_state(raw_state: str | None) -> tuple[str, str, str]:
    """Return `(uf, nome_estado, regiao)` from any raw state representation."""
    if not raw_state:
        return ("ND", "Não Informado", "Não Informada")
    key = _strip_accents_upper(raw_state)
    if key in STATE_STANDARDIZATION:
        return STATE_STANDARDIZATION[key]
    raw_upper = " ".join(raw_state.strip().split()).upper()
    if raw_upper in STATE_STANDARDIZATION:
        return STATE_STANDARDIZATION[raw_upper]
    return ("ND", "Não Informado", "Não Informada")


def standardize_category(raw_category: str | None) -> str:
    """Map messy category labels into canonical retail categories."""
    if not raw_category:
        return "Outros"
    key = _strip_accents_upper(raw_category)
    return CATEGORY_STANDARDIZATION.get(key, clean_text(raw_category, title_case=True))


def standardize_payment(raw_payment: str | None) -> str:
    if not raw_payment:
        return "Não Informado"
    key = _strip_accents_upper(raw_payment)
    return PAYMENT_STANDARDIZATION.get(key, clean_text(raw_payment, title_case=True))


def standardize_channel(raw_channel: str | None) -> str:
    if not raw_channel:
        return "Não Informado"
    key = _strip_accents_upper(raw_channel)
    return CHANNEL_STANDARDIZATION.get(key, clean_text(raw_channel, title_case=True))


def _build_dim_tempo(dates: set[date]) -> list[dict[str, Any]]:
    dim_tempo: list[dict[str, Any]] = []
    for dt in sorted(dates):
        quarter = (dt.month - 1) // 3 + 1
        dim_tempo.append(
            {
                "tempo_id": int(dt.strftime("%Y%m%d")),
                "data": dt.isoformat(),
                "ano": dt.year,
                "trimestre": f"T{quarter}",
                "mes": dt.month,
                "nome_mes": MONTH_NAMES_PT[dt.month],
                "ano_mes": dt.strftime("%Y-%m"),
                "dia": dt.day,
                "dia_semana": WEEKDAY_NAMES_PT[dt.weekday()],
                "fim_de_semana": 1 if dt.weekday() >= 5 else 0,
            }
        )
    return dim_tempo


def transform_data(
    raw_datasets: dict[str, list[dict[str, str]]],
    extract_profile: dict[str, Any] | None = None,
    report_path: Path | None = QUALITY_REPORT_PATH,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Run full cleaning, deduplication, standardization, validation, and KPI enrichment.

    Returns `(star_schema_tables, quality_report)`.
    """
    issues_fixed: dict[str, int] = {
        "duplicatas_removidas": 0,
        "datas_padronizadas": 0,
        "datas_invalidas_rejeitadas": 0,
        "valores_monetarios_padronizados": 0,
        "estados_padronizados": 0,
        "categorias_padronizadas": 0,
        "espacos_e_caixa_corrigidos": 0,
        "emails_ausentes_preenchidos": 0,
        "descontos_ausentes_zerados": 0,
        "quantidades_invalidas_rejeitadas": 0,
        "precos_invalidos_rejeitados": 0,
        "chaves_estrangeiras_invalidas_rejeitadas": 0,
    }

    # --- 1. Transform dim_clientes ---
    dim_clientes: list[dict[str, Any]] = []
    seen_clients: set[str] = set()
    for row in raw_datasets["clientes"]:
        cid = clean_text(row.get("cliente_id"))
        if not cid or cid in seen_clients:
            if cid in seen_clients:
                issues_fixed["duplicatas_removidas"] += 1
            continue
        seen_clients.add(cid)

        raw_name = row.get("nome", "")
        clean_name = clean_text(raw_name, title_case=True)
        if clean_name != raw_name:
            issues_fixed["espacos_e_caixa_corrigidos"] += 1

        raw_city = row.get("cidade", "")
        clean_city = clean_text(raw_city, title_case=True)
        if clean_city != raw_city:
            issues_fixed["espacos_e_caixa_corrigidos"] += 1

        raw_state = row.get("estado", "")
        uf, state_name, region = standardize_state(raw_state)
        if raw_state.strip() != uf:
            issues_fixed["estados_padronizados"] += 1

        email = clean_text(row.get("email")).lower()
        if not email:
            email = "nao_informado@retailpulse.local"
            issues_fixed["emails_ausentes_preenchidos"] += 1

        raw_reg = row.get("data_cadastro", "")
        parsed_reg = parse_date(raw_reg)
        if parsed_reg and raw_reg.strip() != parsed_reg.isoformat():
            issues_fixed["datas_padronizadas"] += 1

        dim_clientes.append(
            {
                "cliente_id": cid,
                "nome": clean_name,
                "email": email,
                "cidade": clean_city,
                "estado": uf,
                "nome_estado": state_name,
                "regiao": region,
                "segmento": clean_text(row.get("segmento"), title_case=False) or "Varejo",
                "data_cadastro": parsed_reg.isoformat() if parsed_reg else "2023-01-01",
            }
        )

    # --- 2. Transform dim_produtos ---
    dim_produtos: list[dict[str, Any]] = []
    seen_products: dict[str, dict[str, Any]] = {}
    for row in raw_datasets["produtos"]:
        pid = clean_text(row.get("produto_id"))
        if not pid or pid in seen_products:
            if pid in seen_products:
                issues_fixed["duplicatas_removidas"] += 1
            continue

        raw_pname = row.get("nome_produto", "")
        clean_pname = clean_text(raw_pname)
        if clean_pname != raw_pname:
            issues_fixed["espacos_e_caixa_corrigidos"] += 1

        raw_cat = row.get("categoria", "")
        clean_cat = standardize_category(raw_cat)
        if raw_cat.strip() != clean_cat:
            issues_fixed["categorias_padronizadas"] += 1

        raw_price = row.get("preco_unitario", "")
        raw_cost = row.get("custo_unitario", "")
        unit_price = parse_currency(raw_price)
        unit_cost = parse_currency(raw_cost)
        if unit_price is None or unit_price <= 0 or unit_cost is None or unit_cost <= 0:
            issues_fixed["precos_invalidos_rejeitados"] += 1
            continue
        if "R$" in raw_price or "," in raw_price or raw_price != raw_price.strip():
            issues_fixed["valores_monetarios_padronizados"] += 1
        if "R$" in raw_cost or "," in raw_cost or raw_cost != raw_cost.strip():
            issues_fixed["valores_monetarios_padronizados"] += 1

        record = {
            "produto_id": pid,
            "nome_produto": clean_pname,
            "categoria": clean_cat,
            "marca": clean_text(row.get("marca")),
            "preco_lista": unit_price,
            "custo_unitario": unit_cost,
        }
        seen_products[pid] = record
        dim_produtos.append(record)

    # --- 3. Transform dim_lojas ---
    dim_lojas: list[dict[str, Any]] = []
    seen_stores: set[str] = set()
    for row in raw_datasets["lojas"]:
        lid = clean_text(row.get("loja_id"))
        if not lid or lid in seen_stores:
            if lid in seen_stores:
                issues_fixed["duplicatas_removidas"] += 1
            continue
        seen_stores.add(lid)

        raw_state = row.get("estado", "")
        uf, state_name, region = standardize_state(raw_state)
        if raw_state.strip() != uf:
            issues_fixed["estados_padronizados"] += 1

        dim_lojas.append(
            {
                "loja_id": lid,
                "nome_loja": clean_text(row.get("nome_loja")),
                "cidade": clean_text(row.get("cidade"), title_case=True),
                "estado": uf,
                "nome_estado": state_name,
                "regiao": region,
                "canal_padrao": standardize_channel(row.get("canal")),
            }
        )

    # --- 4. Transform fato_vendas ---
    fato_vendas: list[dict[str, Any]] = []
    seen_sales: set[str] = set()
    valid_dates: set[date] = set()
    rejected_sales = 0

    for row in raw_datasets["vendas"]:
        vid = clean_text(row.get("venda_id"))
        if not vid:
            rejected_sales += 1
            continue
        if vid in seen_sales:
            issues_fixed["duplicatas_removidas"] += 1
            rejected_sales += 1
            continue

        # Validate foreign keys
        cid = clean_text(row.get("cliente_id"))
        pid = clean_text(row.get("produto_id"))
        lid = clean_text(row.get("loja_id"))
        if cid not in seen_clients or pid not in seen_products or lid not in seen_stores:
            issues_fixed["chaves_estrangeiras_invalidas_rejeitadas"] += 1
            rejected_sales += 1
            continue

        # Validate date
        raw_dt = row.get("data_venda", "")
        parsed_dt = parse_date(raw_dt)
        if parsed_dt is None:
            issues_fixed["datas_invalidas_rejeitadas"] += 1
            rejected_sales += 1
            continue
        if raw_dt.strip() != parsed_dt.isoformat() or raw_dt != raw_dt.strip():
            issues_fixed["datas_padronizadas"] += 1

        # Validate quantity
        try:
            qty = int(clean_text(row.get("quantidade")))
        except ValueError:
            issues_fixed["quantidades_invalidas_rejeitadas"] += 1
            rejected_sales += 1
            continue
        if qty <= 0:
            issues_fixed["quantidades_invalidas_rejeitadas"] += 1
            rejected_sales += 1
            continue

        # Validate unit price
        raw_price = row.get("preco_unitario", "")
        unit_price = parse_currency(raw_price)
        if unit_price is None or unit_price <= 0:
            issues_fixed["precos_invalidos_rejeitados"] += 1
            rejected_sales += 1
            continue
        if "R$" in raw_price or "," in raw_price or raw_price != raw_price.strip():
            issues_fixed["valores_monetarios_padronizados"] += 1

        # Discount handling
        raw_disc = clean_text(row.get("desconto_pct"))
        if not raw_disc:
            discount_pct = 0.0
            issues_fixed["descontos_ausentes_zerados"] += 1
        else:
            parsed_disc = parse_currency(raw_disc)
            discount_pct = parsed_disc if (parsed_disc is not None and 0.0 <= parsed_disc <= 0.8) else 0.0

        seen_sales.add(vid)
        valid_dates.add(parsed_dt)

        unit_cost = seen_products[pid]["custo_unitario"]
        gross_amount = round(qty * unit_price, 2)
        discount_amount = round(gross_amount * discount_pct, 2)
        net_revenue = round(gross_amount - discount_amount, 2)
        total_cost = round(qty * unit_cost, 2)
        gross_profit = round(net_revenue - total_cost, 2)
        gross_margin_pct = round((gross_profit / net_revenue) * 100, 2) if net_revenue > 0 else 0.0

        fato_vendas.append(
            {
                "venda_id": vid,
                "tempo_id": int(parsed_dt.strftime("%Y%m%d")),
                "data_venda": parsed_dt.isoformat(),
                "cliente_id": cid,
                "produto_id": pid,
                "loja_id": lid,
                "quantidade": qty,
                "preco_unitario": unit_price,
                "desconto_pct": round(discount_pct, 4),
                "valor_bruto": gross_amount,
                "valor_desconto": discount_amount,
                "receita_liquida": net_revenue,
                "custo_total": total_cost,
                "lucro_bruto": gross_profit,
                "margem_bruta_pct": gross_margin_pct,
                "forma_pagamento": standardize_payment(row.get("forma_pagamento")),
                "canal_venda": standardize_channel(row.get("canal_venda")),
            }
        )

    # --- 5. Build dim_tempo ---
    dim_tempo = _build_dim_tempo(valid_dates)

    star_tables = {
        "dim_clientes": dim_clientes,
        "dim_produtos": dim_produtos,
        "dim_lojas": dim_lojas,
        "dim_tempo": dim_tempo,
        "fato_vendas": fato_vendas,
    }

    raw_sales_total = len(raw_datasets["vendas"])
    valid_sales_total = len(fato_vendas)
    acceptance_rate = round((valid_sales_total / raw_sales_total) * 100, 2) if raw_sales_total else 0.0

    quality_report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "raw_sales_rows": raw_sales_total,
            "valid_sales_rows": valid_sales_total,
            "rejected_sales_rows": rejected_sales,
            "sales_acceptance_rate_pct": acceptance_rate,
            "total_issues_resolved": sum(issues_fixed.values()),
        },
        "table_counts": {
            "clientes": {"raw": len(raw_datasets["clientes"]), "clean": len(dim_clientes)},
            "produtos": {"raw": len(raw_datasets["produtos"]), "clean": len(dim_produtos)},
            "lojas": {"raw": len(raw_datasets["lojas"]), "clean": len(dim_lojas)},
            "tempo": {"raw": 0, "clean": len(dim_tempo)},
            "vendas": {"raw": raw_sales_total, "clean": valid_sales_total},
        },
        "issues_resolved_breakdown": issues_fixed,
        "extract_profile": extract_profile or {},
    }

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as fh:
            json.dump(quality_report, fh, indent=2, ensure_ascii=False)
        logger.info("Saved data quality report to %s", report_path)

    logger.info(
        "Transformed Star Schema | fato_vendas=%d/%d (%.2f%%) | issues_resolved=%d",
        valid_sales_total,
        raw_sales_total,
        acceptance_rate,
        quality_report["summary"]["total_issues_resolved"],
    )
    return star_tables, quality_report
