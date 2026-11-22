"""Centralized configuration, paths, and standardization rules for RetailPulse."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Directory paths
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
POWERBI_DIR = DATA_DIR / "powerbi"
SQL_DIR = BASE_DIR / "sql"
DASHBOARD_DIR = BASE_DIR / "dashboard"

# Key output files
DB_PATH = WAREHOUSE_DIR / "retail_dw.db"
QUALITY_REPORT_PATH = WAREHOUSE_DIR / "data_quality_report.json"
DASHBOARD_JSON_PATH = DASHBOARD_DIR / "data.json"
DASHBOARD_JS_PATH = DASHBOARD_DIR / "dashboard_data.js"
SCHEMA_SQL_PATH = SQL_DIR / "schema.sql"
ANALYTICS_SQL_PATH = SQL_DIR / "analytical_queries.sql"

# Brazilian State standardization (code -> full info)
STATE_STANDARDIZATION = {
    "SP": ("SP", "São Paulo", "Sudeste"),
    "SAO PAULO": ("SP", "São Paulo", "Sudeste"),
    "SÃO PAULO": ("SP", "São Paulo", "Sudeste"),
    "RJ": ("RJ", "Rio de Janeiro", "Sudeste"),
    "RIO DE JANEIRO": ("RJ", "Rio de Janeiro", "Sudeste"),
    "MG": ("MG", "Minas Gerais", "Sudeste"),
    "MINAS GERAIS": ("MG", "Minas Gerais", "Sudeste"),
    "ES": ("ES", "Espírito Santo", "Sudeste"),
    "ESPIRITO SANTO": ("ES", "Espírito Santo", "Sudeste"),
    "ESPÍRITO SANTO": ("ES", "Espírito Santo", "Sudeste"),
    "PR": ("PR", "Paraná", "Sul"),
    "PARANA": ("PR", "Paraná", "Sul"),
    "PARANÁ": ("PR", "Paraná", "Sul"),
    "SC": ("SC", "Santa Catarina", "Sul"),
    "SANTA CATARINA": ("SC", "Santa Catarina", "Sul"),
    "RS": ("RS", "Rio Grande do Sul", "Sul"),
    "RIO GRANDE DO SUL": ("RS", "Rio Grande do Sul", "Sul"),
    "BA": ("BA", "Bahia", "Nordeste"),
    "BAHIA": ("BA", "Bahia", "Nordeste"),
    "PE": ("PE", "Pernambuco", "Nordeste"),
    "PERNAMBUCO": ("PE", "Pernambuco", "Nordeste"),
    "CE": ("CE", "Ceará", "Nordeste"),
    "CEARA": ("CE", "Ceará", "Nordeste"),
    "CEARÁ": ("CE", "Ceará", "Nordeste"),
    "DF": ("DF", "Distrito Federal", "Centro-Oeste"),
    "DISTRITO FEDERAL": ("DF", "Distrito Federal", "Centro-Oeste"),
    "GO": ("GO", "Goiás", "Centro-Oeste"),
    "GOIAS": ("GO", "Goiás", "Centro-Oeste"),
    "GOIÁS": ("GO", "Goiás", "Centro-Oeste"),
    "AM": ("AM", "Amazonas", "Norte"),
    "AMAZONAS": ("AM", "Amazonas", "Norte"),
    "PA": ("PA", "Pará", "Norte"),
    "PARA": ("PA", "Pará", "Norte"),
    "PARÁ": ("PA", "Pará", "Norte"),
}

# Category standardization
CATEGORY_STANDARDIZATION = {
    "ELETRONICOS": "Eletrônicos",
    "ELETRÔNICOS": "Eletrônicos",
    "ELETRO": "Eletrônicos",
    "ELETRONICO": "Eletrônicos",
    "INFORMATICA": "Informática",
    "INFORMÁTICA": "Informática",
    "TECH": "Informática",
    "TI": "Informática",
    "CASA & DECORACAO": "Casa & Decoração",
    "CASA & DECORAÇÃO": "Casa & Decoração",
    "CASA E DECORACAO": "Casa & Decoração",
    "CASA E DECORAÇÃO": "Casa & Decoração",
    "CASA": "Casa & Decoração",
    "MODA": "Moda & Acessórios",
    "MODA & ACESSORIOS": "Moda & Acessórios",
    "MODA & ACESSÓRIOS": "Moda & Acessórios",
    "MODA E ACESSORIOS": "Moda & Acessórios",
    "VESTUARIO": "Moda & Acessórios",
    "ESPORTES": "Esportes & Lazer",
    "ESPORTE": "Esportes & Lazer",
    "ESPORTES & LAZER": "Esportes & Lazer",
    "ESPORTES E LAZER": "Esportes & Lazer",
    "BELEZA": "Beleza & Saúde",
    "BELEZA & SAUDE": "Beleza & Saúde",
    "BELEZA & SAÚDE": "Beleza & Saúde",
    "BELEZA E SAUDE": "Beleza & Saúde",
    "SAUDE": "Beleza & Saúde",
}

# Payment method standardization
PAYMENT_STANDARDIZATION = {
    "PIX": "PIX",
    "CARTAO CREDITO": "Cartão de Crédito",
    "CARTÃO CRÉDITO": "Cartão de Crédito",
    "CARTAO DE CREDITO": "Cartão de Crédito",
    "CARTÃO DE CRÉDITO": "Cartão de Crédito",
    "CREDITO": "Cartão de Crédito",
    "CARTAO DEBITO": "Cartão de Débito",
    "CARTÃO DÉBITO": "Cartão de Débito",
    "CARTAO DE DEBITO": "Cartão de Débito",
    "CARTÃO DE DÉBITO": "Cartão de Débito",
    "DEBITO": "Cartão de Débito",
    "BOLETO": "Boleto Bancário",
    "BOLETO BANCARIO": "Boleto Bancário",
    "BOLETO BANCÁRIO": "Boleto Bancário",
}

# Sales channel standardization
CHANNEL_STANDARDIZATION = {
    "LOJA FISICA": "Loja Física",
    "LOJA FÍSICA": "Loja Física",
    "FISICA": "Loja Física",
    "E-COMMERCE": "E-commerce",
    "ECOMMERCE": "E-commerce",
    "ONLINE": "E-commerce",
    "SITE": "E-commerce",
    "APP": "App Mobile",
    "APP MOBILE": "App Mobile",
    "MOBILE": "App Mobile",
    "MARKETPLACE": "Marketplace",
}

# Supported raw date formats
RAW_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%m/%d/%Y",
)

MONTH_NAMES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

WEEKDAY_NAMES_PT = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}
