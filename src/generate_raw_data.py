"""Realistic raw retail sales data generator with intentional data quality issues.

Generates messy CSV files in `data/raw/` simulating real-world ERP/e-commerce exports:
- Duplicate rows
- Inconsistent date formats (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, YYYY/MM/DD)
- Missing / null values
- Whitespace and casing inconsistencies
- Invalid negative or zero quantities and prices
- Unstandardized Brazilian state names and product categories
- Mixed currency string formats ("R$ 1.299,90", "1299.90", "450,00")
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.config import RAW_DIR

FIRST_NAMES = [
    "Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique",
    "Isabela", "João", "Kamila", "Lucas", "Mariana", "Nathan", "Olívia", "Pedro",
    "Rafaela", "Samuel", "Tatiana", "Vinícius", "Beatriz", "Caio", "Daniela", "Enzo",
    "Fernanda", "Gustavo", "Helena", "Igor", "Juliana", "Leonardo", "Larissa", "Matheus",
]

LAST_NAMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira",
    "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho", "Almeida", "Lopes",
    "Soares", "Fernandes", "Vieira", "Barbosa", "Rocha", "Dias", "Nascimento", "Mendes",
]

CUSTOMER_SEGMENTS = ["Varejo", "Corporativo", "VIP", "PME"]

CITY_STATE_POOL = [
    ("São Paulo", ["SP", "sp", "São Paulo", "sao paulo", "  SP "]),
    ("Campinas", ["SP", "sp", "São Paulo"]),
    ("Rio de Janeiro", ["RJ", "rj", "Rio de Janeiro", "  rj "]),
    ("Belo Horizonte", ["MG", "mg", "Minas Gerais", "minas gerais"]),
    ("Vitória", ["ES", "es", "Espírito Santo"]),
    ("Curitiba", ["PR", "pr", "Paraná", "parana"]),
    ("Florianópolis", ["SC", "sc", "Santa Catarina"]),
    ("Porto Alegre", ["RS", "rs", "Rio Grande do Sul"]),
    ("Salvador", ["BA", "ba", "Bahia", "  bahia "]),
    ("Recife", ["PE", "pe", "Pernambuco"]),
    ("Fortaleza", ["CE", "ce", "Ceará", "ceara"]),
    ("Brasília", ["DF", "df", "Distrito Federal"]),
    ("Goiânia", ["GO", "go", "Goiás", "goias"]),
    ("Manaus", ["AM", "am", "Amazonas"]),
    ("Belém", ["PA", "pa", "Pará", "para"]),
]

PRODUCTS_CATALOG = [
    # (sku, name, canonical_category, messy_categories, brand, unit_price, unit_cost)
    ("PRD-001", "Smartphone Galaxy A55 256GB", "Eletrônicos", ["Eletrônicos", "eletronicos", "ELETRO", "  Eletrônicos "], "Samsung", 2199.90, 1480.00),
    ("PRD-002", "Smart TV 55\" 4K UHD", "Eletrônicos", ["Eletrônicos", "ELETRONICOS", "eletro"], "LG", 2799.00, 1920.00),
    ("PRD-003", "Fone Bluetooth ANC Pro", "Eletrônicos", ["Eletrônicos", "eletronico", "ELETRO"], "Sony", 649.90, 390.00),
    ("PRD-004", "Caixa de Som Portátil 40W", "Eletrônicos", ["Eletrônicos", "eletronicos"], "JBL", 499.90, 295.00),
    ("PRD-005", "Smartwatch Fit GPS", "Eletrônicos", ["Eletrônicos", "ELETRO", "eletronicos"], "Garmin", 1299.00, 820.00),
    ("PRD-006", "Kindle Paperwhite 16GB", "Eletrônicos", ["Eletrônicos", "eletronicos"], "Amazon", 799.00, 510.00),
    ("PRD-007", "Notebook Core i7 16GB 512GB", "Informática", ["Informática", "informatica", "TECH", "TI"], "Dell", 4499.00, 3250.00),
    ("PRD-008", "Monitor Ultrawide 29\" IPS", "Informática", ["Informática", "INFORMATICA", "tech"], "LG", 1399.00, 910.00),
    ("PRD-009", "Teclado Mecânico RGB Switch Brown", "Informática", ["Informática", "TI", "informatica"], "Logitech", 429.90, 240.00),
    ("PRD-010", "Mouse Ergonomico Wireless", "Informática", ["Informática", "TECH", "  informatica "], "Logitech", 349.90, 195.00),
    ("PRD-011", "SSD NVMe 1TB Gen4", "Informática", ["Informática", "INFORMATICA", "TI"], "Kingston", 479.00, 290.00),
    ("PRD-012", "Webcam Full HD 1080p", "Informática", ["Informática", "informatica"], "Logitech", 289.90, 165.00),
    ("PRD-013", "Cafeteira Espresso Automática", "Casa & Decoração", ["Casa & Decoração", "Casa e Decoracao", "CASA", "casa & decoracao"], "Nespresso", 899.90, 540.00),
    ("PRD-014", "Aspirador Robô Smart Wi-Fi", "Casa & Decoração", ["Casa & Decoração", "CASA", "Casa e Decoração"], "WAP", 1199.00, 740.00),
    ("PRD-015", "Air Fryer Digital 5.5L", "Casa & Decoração", ["Casa & Decoração", "casa e decoracao", "CASA"], "Philips Walita", 589.90, 355.00),
    ("PRD-016", "Jogo de Panelas Antiaderente 7pç", "Casa & Decoração", ["Casa & Decoração", "Casa e Decoracao"], "Tramontina", 449.00, 260.00),
    ("PRD-017", "Luminária de Mesa LED Minimalista", "Casa & Decoração", ["Casa & Decoração", "CASA", "  casa "], "Philips", 189.90, 95.00),
    ("PRD-018", "Conjunto Lençol 400 Fios Queen", "Casa & Decoração", ["Casa & Decoração", "Casa e Decoracao"], "Buddemeyer", 379.90, 210.00),
    ("PRD-019", "Tênis Running Amortecimento Pro", "Moda & Acessórios", ["Moda & Acessórios", "MODA", "Moda e Acessorios", "vestuario"], "Nike", 599.90, 310.00),
    ("PRD-020", "Jaqueta Corta-Vento Impermeável", "Moda & Acessórios", ["Moda & Acessórios", "moda", "VESTUARIO"], "Adidas", 349.90, 175.00),
    ("PRD-021", "Mochila Executiva Anti-Furto", "Moda & Acessórios", ["Moda & Acessórios", "Moda e Acessorios", "MODA"], "Samsonite", 419.90, 220.00),
    ("PRD-022", "Óculos de Sol Polarizado Classic", "Moda & Acessórios", ["Moda & Acessórios", "moda", "  MODA "], "Ray-Ban", 689.00, 350.00),
    ("PRD-023", "Relógio Analógico Couro Minimal", "Moda & Acessórios", ["Moda & Acessórios", "Moda e Acessorios"], "Fossil", 549.00, 285.00),
    ("PRD-024", "Bicicleta Mountain Bike Aro 29", "Esportes & Lazer", ["Esportes & Lazer", "ESPORTES", "Esporte", "esportes e lazer"], "Caloi", 1899.00, 1260.00),
    ("PRD-025", "Kit Halteres Ajustáveis 20kg", "Esportes & Lazer", ["Esportes & Lazer", "esportes", "ESPORTE"], "Polimet", 329.90, 185.00),
    ("PRD-026", "Tapete de Yoga Antiderrapante 8mm", "Esportes & Lazer", ["Esportes & Lazer", "Esportes e Lazer", "esporte"], "Acte", 139.90, 68.00),
    ("PRD-027", "Barraca Camping 4 Pessoas Impermeável", "Esportes & Lazer", ["Esportes & Lazer", "ESPORTES"], "Nautika", 489.90, 275.00),
    ("PRD-028", "Garrafa Térmica Inox 1L", "Esportes & Lazer", ["Esportes & Lazer", "esportes", "  esporte "], "Stanley", 249.90, 130.00),
    ("PRD-029", "Perfume Eau de Parfum 100ml", "Beleza & Saúde", ["Beleza & Saúde", "BELEZA", "Beleza e Saude", "saude"], "Natura", 299.90, 145.00),
    ("PRD-030", "Secador de Cabelo Profissional 2200W", "Beleza & Saúde", ["Beleza & Saúde", "beleza", "SAUDE"], "Taiff", 359.90, 195.00),
    ("PRD-031", "Kit Skincare Vitamina C + Ácido Hialurônico", "Beleza & Saúde", ["Beleza & Saúde", "Beleza e Saude", "BELEZA"], "La Roche-Posay", 279.90, 142.00),
    ("PRD-032", "Escova Dental Elétrica Sônica", "Beleza & Saúde", ["Beleza & Saúde", "saude", "  BELEZA "], "Oral-B", 229.90, 118.00),
]

STORES_CATALOG = [
    ("LJ-01", "RetailPulse Paulista", "São Paulo", ["SP", "São Paulo", "sp"], "Loja Física"),
    ("LJ-02", "RetailPulse Barra", "Rio de Janeiro", ["RJ", "Rio de Janeiro", "rj"], "Loja Física"),
    ("LJ-03", "RetailPulse Savassi", "Belo Horizonte", ["MG", "Minas Gerais", "mg"], "Loja Física"),
    ("LJ-04", "RetailPulse Batel", "Curitiba", ["PR", "Paraná", "pr"], "Loja Física"),
    ("LJ-05", "RetailPulse Moinhos", "Porto Alegre", ["RS", "Rio Grande do Sul"], "Loja Física"),
    ("LJ-06", "RetailPulse Salvador Shopping", "Salvador", ["BA", "Bahia", "ba"], "Loja Física"),
    ("LJ-07", "RetailPulse Boa Viagem", "Recife", ["PE", "Pernambuco"], "Loja Física"),
    ("LJ-08", "RetailPulse ParkShopping", "Brasília", ["DF", "Distrito Federal"], "Loja Física"),
    ("LJ-09", "RetailPulse Manauara", "Manaus", ["AM", "Amazonas"], "Loja Física"),
    ("LJ-10", "RetailPulse E-commerce Nacional", "São Paulo", ["SP", "sao paulo"], "E-commerce"),
    ("LJ-11", "RetailPulse App Mobile", "São Paulo", ["SP", "sp"], "App Mobile"),
    ("LJ-12", "RetailPulse Marketplace Hub", "Campinas", ["SP", "São Paulo"], "Marketplace"),
]

MESSY_CHANNELS = {
    "Loja Física": ["Loja Física", "loja fisica", "FISICA", "  Loja Física "],
    "E-commerce": ["E-commerce", "ecommerce", "ONLINE", "site"],
    "App Mobile": ["App Mobile", "APP", "mobile", "  app mobile "],
    "Marketplace": ["Marketplace", "marketplace", "MARKETPLACE"],
}

MESSY_PAYMENTS = [
    "PIX", "pix", "  PIX ",
    "Cartão de Crédito", "cartao credito", "CREDITO", "Cartao de Credito",
    "Cartão de Débito", "cartao debito", "DEBITO",
    "Boleto Bancário", "boleto", "BOLETO BANCARIO",
]


def _format_messy_date(dt: date, rng: random.Random) -> str:
    fmt = rng.choices(
        ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", " %d/%m/%Y "],
        weights=[0.45, 0.25, 0.12, 0.10, 0.08],
        k=1,
    )[0]
    return dt.strftime(fmt)


def _format_messy_currency(value: float, rng: random.Random) -> str:
    style = rng.choices(["plain", "brl", "comma", "spaces"], weights=[0.55, 0.20, 0.15, 0.10], k=1)[0]
    if style == "plain":
        return f"{value:.2f}"
    if style == "brl":
        formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    if style == "comma":
        return f"{value:.2f}".replace(".", ",")
    return f"  {value:.2f}  "


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_raw_data(
    output_dir: Path = RAW_DIR,
    num_customers: int = 200,
    num_sales: int = 2400,
    seed: int = 42,
) -> dict[str, int]:
    """Generate messy raw CSV files for customers, products, stores, and sales.

    Returns a summary dict with the number of raw rows written per file.
    """
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate raw customers
    customers: list[dict[str, Any]] = []
    start_reg = date(2022, 1, 1)
    for idx in range(1, num_customers + 1):
        cid = f"CLI-{idx:04d}"
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        # Introduce whitespace/casing noise
        noise_roll = rng.random()
        if noise_roll < 0.12:
            full_name = f"  {full_name.upper()}  "
        elif noise_roll < 0.22:
            full_name = full_name.lower()

        city, state_variants = rng.choice(CITY_STATE_POOL)
        state = rng.choice(state_variants)
        if rng.random() < 0.1:
            city = f" {city.upper()} "

        email = f"{first.lower()}.{last.lower()}{idx}@email.com"
        if rng.random() < 0.08:
            email = ""  # missing email

        segment = rng.choices(CUSTOMER_SEGMENTS, weights=[0.55, 0.18, 0.12, 0.15], k=1)[0]
        reg_date = start_reg + timedelta(days=rng.randint(0, 720))

        customers.append(
            {
                "cliente_id": cid,
                "nome": full_name,
                "email": email,
                "cidade": city,
                "estado": state,
                "segmento": segment,
                "data_cadastro": _format_messy_date(reg_date, rng),
            }
        )

    # Inject duplicate customer rows (~4%)
    dup_customers = rng.sample(customers, k=max(1, int(num_customers * 0.04)))
    customers.extend(dict(row) for row in dup_customers)
    rng.shuffle(customers)

    _write_csv(
        output_dir / "clientes_raw.csv",
        ["cliente_id", "nome", "email", "cidade", "estado", "segmento", "data_cadastro"],
        customers,
    )

    # 2. Generate raw products
    products: list[dict[str, Any]] = []
    for sku, name, _canon_cat, messy_cats, brand, price, cost in PRODUCTS_CATALOG:
        noisy_name = f"  {name} " if rng.random() < 0.15 else name
        products.append(
            {
                "produto_id": sku,
                "nome_produto": noisy_name,
                "categoria": rng.choice(messy_cats),
                "marca": brand,
                "preco_unitario": _format_messy_currency(price, rng),
                "custo_unitario": _format_messy_currency(cost, rng),
            }
        )
    # Inject 2 duplicate product rows
    products.append(dict(products[0]))
    products.append(dict(products[5]))

    _write_csv(
        output_dir / "produtos_raw.csv",
        ["produto_id", "nome_produto", "categoria", "marca", "preco_unitario", "custo_unitario"],
        products,
    )

    # 3. Generate raw stores
    stores: list[dict[str, Any]] = []
    for lid, name, city, state_variants, channel in STORES_CATALOG:
        stores.append(
            {
                "loja_id": lid,
                "nome_loja": name,
                "cidade": city,
                "estado": rng.choice(state_variants),
                "canal": rng.choice(MESSY_CHANNELS[channel]),
            }
        )

    _write_csv(
        output_dir / "lojas_raw.csv",
        ["loja_id", "nome_loja", "cidade", "estado", "canal"],
        stores,
    )

    # 4. Generate raw sales (24 months: Jan 2024 - Dec 2025 with realistic seasonality & growth)
    # Give some products Pareto popularity weights (so ABC curve looks realistic)
    product_weights = [
        10 if i < 6 else (4 if i < 16 else 1.2) for i in range(len(PRODUCTS_CATALOG))
    ]
    # Give some customers higher repeat frequency (for realistic RFM segmentation)
    customer_ids = [f"CLI-{idx:04d}" for idx in range(1, num_customers + 1)]
    customer_weights = [
        6.0 if i < 25 else (2.5 if i < 80 else 0.8) for i in range(num_customers)
    ]
    store_weights = [8, 6, 5, 4, 4, 4, 3, 3, 2, 16, 12, 9]

    start_date = date(2024, 1, 1)
    total_days = (date(2025, 12, 31) - start_date).days

    sales: list[dict[str, Any]] = []
    for seq in range(1, num_sales + 1):
        vid = f"VND-{seq:06d}"

        # Slight upward trend in 2025 + Q4 seasonality
        day_offset = int((rng.random() ** 0.86) * total_days)
        sale_dt = start_date + timedelta(days=day_offset)
        # Boost November (Black Friday) and December (Christmas)
        if rng.random() < 0.14:
            year = rng.choice([2024, 2025])
            month = rng.choice([11, 12])
            day = rng.randint(1, 28)
            sale_dt = date(year, month, day)

        cid = rng.choices(customer_ids, weights=customer_weights, k=1)[0]
        prod = rng.choices(PRODUCTS_CATALOG, weights=product_weights, k=1)[0]
        store = rng.choices(STORES_CATALOG, weights=store_weights, k=1)[0]

        sku, _pname, _ccat, _mcats, _brand, base_price, _base_cost = prod
        lid, _sname, _scity, _svars, canon_channel = store

        qty = rng.choices([1, 2, 3, 4, 5], weights=[0.52, 0.26, 0.12, 0.06, 0.04], k=1)[0]
        # Slight price variation (+/- 5%)
        unit_price = round(base_price * rng.uniform(0.95, 1.05), 2)
        discount_pct = rng.choices([0.0, 0.05, 0.10, 0.15, 0.20], weights=[0.48, 0.22, 0.16, 0.09, 0.05], k=1)[0]
        payment = rng.choice(MESSY_PAYMENTS)
        channel = rng.choice(MESSY_CHANNELS[canon_channel])

        row = {
            "venda_id": vid,
            "data_venda": _format_messy_date(sale_dt, rng),
            "cliente_id": cid,
            "produto_id": sku,
            "loja_id": lid,
            "quantidade": str(qty),
            "preco_unitario": _format_messy_currency(unit_price, rng),
            "desconto_pct": "" if rng.random() < 0.06 else f"{discount_pct:.2f}",
            "forma_pagamento": payment,
            "canal_venda": channel,
        }

        # Inject intentional data quality defects in ~6% of records
        defect = rng.random()
        if defect < 0.015:
            row["quantidade"] = str(-rng.randint(1, 3))  # invalid negative quantity
        elif defect < 0.025:
            row["quantidade"] = "0"  # zero quantity
        elif defect < 0.035:
            row["preco_unitario"] = f"-{unit_price:.2f}"  # negative price
        elif defect < 0.045:
            row["data_venda"] = "data-invalida"  # unparseable date
        elif defect < 0.055:
            row["cliente_id"] = ""  # missing foreign key
        elif defect < 0.062:
            row["produto_id"] = "PRD-999"  # orphan product FK

        sales.append(row)

    # Inject exact & near-duplicate sales rows (~3.5%)
    dup_count = max(1, int(num_sales * 0.035))
    dup_sales = rng.sample(sales, k=dup_count)
    sales.extend(dict(r) for r in dup_sales)
    rng.shuffle(sales)

    _write_csv(
        output_dir / "vendas_raw.csv",
        [
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
        sales,
    )

    return {
        "clientes_raw.csv": len(customers),
        "produtos_raw.csv": len(products),
        "lojas_raw.csv": len(stores),
        "vendas_raw.csv": len(sales),
    }


if __name__ == "__main__":
    summary = generate_raw_data()
    for fname, count in summary.items():
        print(f"Generated {fname}: {count} rows")
