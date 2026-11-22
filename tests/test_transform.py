"""Unit tests for ETL data cleaning, standardization, deduplication, and KPI math."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.etl.transform import (
    clean_text,
    parse_currency,
    parse_date,
    standardize_category,
    standardize_state,
    transform_data,
)


class TestTransformHelpers(unittest.TestCase):
    def test_parse_date_multiple_formats(self) -> None:
        self.assertEqual(parse_date("2025-03-15"), date(2025, 3, 15))
        self.assertEqual(parse_date("15/03/2025"), date(2025, 3, 15))
        self.assertEqual(parse_date("15-03-2025"), date(2025, 3, 15))
        self.assertEqual(parse_date(" 2025/03/15 "), date(2025, 3, 15))
        self.assertIsNone(parse_date("data-invalida"))
        self.assertIsNone(parse_date(""))

    def test_parse_currency_brazilian_and_iso(self) -> None:
        self.assertEqual(parse_currency("R$ 1.299,90"), 1299.90)
        self.assertEqual(parse_currency("1299.90"), 1299.90)
        self.assertEqual(parse_currency(" 450,50 "), 450.50)
        self.assertEqual(parse_currency("-100.00"), -100.00)
        self.assertIsNone(parse_currency("abc"))
        self.assertIsNone(parse_currency(""))

    def test_standardize_state(self) -> None:
        self.assertEqual(standardize_state("  sao paulo "), ("SP", "São Paulo", "Sudeste"))
        self.assertEqual(standardize_state("rj"), ("RJ", "Rio de Janeiro", "Sudeste"))
        self.assertEqual(standardize_state("Bahia"), ("BA", "Bahia", "Nordeste"))
        self.assertEqual(standardize_state("parana"), ("PR", "Paraná", "Sul"))
        self.assertEqual(standardize_state(""), ("ND", "Não Informado", "Não Informada"))

    def test_standardize_category(self) -> None:
        self.assertEqual(standardize_category("  ELETRO "), "Eletrônicos")
        self.assertEqual(standardize_category("Casa e Decoracao"), "Casa & Decoração")
        self.assertEqual(standardize_category("tech"), "Informática")
        self.assertEqual(standardize_category("vestuario"), "Moda & Acessórios")

    def test_clean_text_title_case(self) -> None:
        self.assertEqual(clean_text("  joão da silva  ", title_case=True), "João da Silva")


class TestTransformPipeline(unittest.TestCase):
    def _sample_raw_datasets(self) -> dict[str, list[dict[str, str]]]:
        return {
            "clientes": [
                {
                    "cliente_id": "CLI-0001",
                    "nome": "  ANA SILVA  ",
                    "email": "",
                    "cidade": " são paulo ",
                    "estado": "sao paulo",
                    "segmento": "VIP",
                    "data_cadastro": "10/01/2023",
                },
                # Duplicate client
                {
                    "cliente_id": "CLI-0001",
                    "nome": "ANA SILVA",
                    "email": "ana@email.com",
                    "cidade": "São Paulo",
                    "estado": "SP",
                    "segmento": "VIP",
                    "data_cadastro": "2023-01-10",
                },
            ],
            "produtos": [
                {
                    "produto_id": "PRD-001",
                    "nome_produto": "  Smartphone X ",
                    "categoria": "ELETRO",
                    "marca": "Samsung",
                    "preco_unitario": "R$ 1.000,00",
                    "custo_unitario": "600,00",
                },
                # Duplicate product
                {
                    "produto_id": "PRD-001",
                    "nome_produto": "Smartphone X",
                    "categoria": "Eletrônicos",
                    "marca": "Samsung",
                    "preco_unitario": "1000.00",
                    "custo_unitario": "600.00",
                },
            ],
            "lojas": [
                {
                    "loja_id": "LJ-01",
                    "nome_loja": "Loja Paulista",
                    "cidade": "São Paulo",
                    "estado": "sp",
                    "canal": "ONLINE",
                }
            ],
            "vendas": [
                # Valid sale with 10% discount
                {
                    "venda_id": "VND-000001",
                    "data_venda": "15/05/2025",
                    "cliente_id": "CLI-0001",
                    "produto_id": "PRD-001",
                    "loja_id": "LJ-01",
                    "quantidade": "2",
                    "preco_unitario": "R$ 1.000,00",
                    "desconto_pct": "0.10",
                    "forma_pagamento": "pix",
                    "canal_venda": "ONLINE",
                },
                # Duplicate sale
                {
                    "venda_id": "VND-000001",
                    "data_venda": "2025-05-15",
                    "cliente_id": "CLI-0001",
                    "produto_id": "PRD-001",
                    "loja_id": "LJ-01",
                    "quantidade": "2",
                    "preco_unitario": "1000.00",
                    "desconto_pct": "0.10",
                    "forma_pagamento": "PIX",
                    "canal_venda": "E-commerce",
                },
                # Invalid negative quantity
                {
                    "venda_id": "VND-000002",
                    "data_venda": "2025-05-16",
                    "cliente_id": "CLI-0001",
                    "produto_id": "PRD-001",
                    "loja_id": "LJ-01",
                    "quantidade": "-1",
                    "preco_unitario": "1000.00",
                    "desconto_pct": "0.00",
                    "forma_pagamento": "PIX",
                    "canal_venda": "E-commerce",
                },
                # Invalid negative price
                {
                    "venda_id": "VND-000003",
                    "data_venda": "2025-05-16",
                    "cliente_id": "CLI-0001",
                    "produto_id": "PRD-001",
                    "loja_id": "LJ-01",
                    "quantidade": "1",
                    "preco_unitario": "-50.00",
                    "desconto_pct": "0.00",
                    "forma_pagamento": "PIX",
                    "canal_venda": "E-commerce",
                },
                # Invalid date
                {
                    "venda_id": "VND-000004",
                    "data_venda": "data-invalida",
                    "cliente_id": "CLI-0001",
                    "produto_id": "PRD-001",
                    "loja_id": "LJ-01",
                    "quantidade": "1",
                    "preco_unitario": "1000.00",
                    "desconto_pct": "",
                    "forma_pagamento": "PIX",
                    "canal_venda": "E-commerce",
                },
                # Orphan foreign key
                {
                    "venda_id": "VND-000005",
                    "data_venda": "2025-05-17",
                    "cliente_id": "CLI-9999",
                    "produto_id": "PRD-001",
                    "loja_id": "LJ-01",
                    "quantidade": "1",
                    "preco_unitario": "1000.00",
                    "desconto_pct": "",
                    "forma_pagamento": "PIX",
                    "canal_venda": "E-commerce",
                },
            ],
        }

    def test_transform_deduplication_validation_and_kpis(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "data_quality_report.json"
            tables, report = transform_data(
                self._sample_raw_datasets(),
                report_path=report_path,
            )

            self.assertEqual(len(tables["dim_clientes"]), 1)
            self.assertEqual(len(tables["dim_produtos"]), 1)
            self.assertEqual(len(tables["dim_lojas"]), 1)
            self.assertEqual(len(tables["dim_tempo"]), 1)
            self.assertEqual(len(tables["fato_vendas"]), 1)

            # Verify cleaned values
            client = tables["dim_clientes"][0]
            self.assertEqual(client["nome"], "Ana Silva")
            self.assertEqual(client["estado"], "SP")
            self.assertEqual(client["regiao"], "Sudeste")
            self.assertEqual(client["email"], "nao_informado@retailpulse.local")

            # Verify KPI calculations: qty=2, price=1000, disc=10%, cost=600
            sale = tables["fato_vendas"][0]
            self.assertEqual(sale["tempo_id"], 20250515)
            self.assertEqual(sale["valor_bruto"], 2000.00)
            self.assertEqual(sale["valor_desconto"], 200.00)
            self.assertEqual(sale["receita_liquida"], 1800.00)
            self.assertEqual(sale["custo_total"], 1200.00)
            self.assertEqual(sale["lucro_bruto"], 600.00)
            self.assertAlmostEqual(sale["margem_bruta_pct"], 33.33, places=2)
            self.assertEqual(sale["forma_pagamento"], "PIX")
            self.assertEqual(sale["canal_venda"], "E-commerce")

            # Verify quality report JSON persisted
            self.assertTrue(report_path.exists())
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["summary"]["rejected_sales_rows"], 5)
            self.assertEqual(saved["issues_resolved_breakdown"]["quantidades_invalidas_rejeitadas"], 1)
            self.assertEqual(saved["issues_resolved_breakdown"]["precos_invalidos_rejeitados"], 1)
            self.assertEqual(saved["issues_resolved_breakdown"]["datas_invalidas_rejeitadas"], 1)
            self.assertEqual(saved["issues_resolved_breakdown"]["chaves_estrangeiras_invalidas_rejeitadas"], 1)


if __name__ == "__main__":
    unittest.main()
