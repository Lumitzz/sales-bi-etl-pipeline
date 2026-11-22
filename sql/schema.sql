-- RetailPulse Data Warehouse — Star Schema DDL (SQLite / ANSI SQL compatible)

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fato_vendas;
DROP TABLE IF EXISTS dim_tempo;
DROP TABLE IF EXISTS dim_lojas;
DROP TABLE IF EXISTS dim_produtos;
DROP TABLE IF EXISTS dim_clientes;

CREATE TABLE dim_clientes (
    cliente_id      TEXT PRIMARY KEY,
    nome            TEXT NOT NULL,
    email           TEXT NOT NULL,
    cidade          TEXT NOT NULL,
    estado          TEXT NOT NULL,
    nome_estado     TEXT NOT NULL,
    regiao          TEXT NOT NULL,
    segmento        TEXT NOT NULL,
    data_cadastro   TEXT NOT NULL
);

CREATE TABLE dim_produtos (
    produto_id      TEXT PRIMARY KEY,
    nome_produto    TEXT NOT NULL,
    categoria       TEXT NOT NULL,
    marca           TEXT NOT NULL,
    preco_lista     REAL NOT NULL CHECK (preco_lista > 0),
    custo_unitario  REAL NOT NULL CHECK (custo_unitario > 0)
);

CREATE TABLE dim_lojas (
    loja_id         TEXT PRIMARY KEY,
    nome_loja       TEXT NOT NULL,
    cidade          TEXT NOT NULL,
    estado          TEXT NOT NULL,
    nome_estado     TEXT NOT NULL,
    regiao          TEXT NOT NULL,
    canal_padrao    TEXT NOT NULL
);

CREATE TABLE dim_tempo (
    tempo_id        INTEGER PRIMARY KEY,
    data            TEXT NOT NULL UNIQUE,
    ano             INTEGER NOT NULL,
    trimestre       TEXT NOT NULL,
    mes             INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    nome_mes        TEXT NOT NULL,
    ano_mes         TEXT NOT NULL,
    dia             INTEGER NOT NULL CHECK (dia BETWEEN 1 AND 31),
    dia_semana      TEXT NOT NULL,
    fim_de_semana   INTEGER NOT NULL CHECK (fim_de_semana IN (0, 1))
);

CREATE TABLE fato_vendas (
    venda_id            TEXT PRIMARY KEY,
    tempo_id            INTEGER NOT NULL,
    data_venda          TEXT NOT NULL,
    cliente_id          TEXT NOT NULL,
    produto_id          TEXT NOT NULL,
    loja_id             TEXT NOT NULL,
    quantidade          INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario      REAL NOT NULL CHECK (preco_unitario > 0),
    desconto_pct        REAL NOT NULL CHECK (desconto_pct >= 0 AND desconto_pct <= 1),
    valor_bruto         REAL NOT NULL,
    valor_desconto      REAL NOT NULL,
    receita_liquida     REAL NOT NULL,
    custo_total         REAL NOT NULL,
    lucro_bruto         REAL NOT NULL,
    margem_bruta_pct    REAL NOT NULL,
    forma_pagamento     TEXT NOT NULL,
    canal_venda         TEXT NOT NULL,
    FOREIGN KEY (tempo_id)   REFERENCES dim_tempo(tempo_id),
    FOREIGN KEY (cliente_id) REFERENCES dim_clientes(cliente_id),
    FOREIGN KEY (produto_id) REFERENCES dim_produtos(produto_id),
    FOREIGN KEY (loja_id)    REFERENCES dim_lojas(loja_id)
);

-- Analytical Indexes for fast BI / OLAP aggregations
CREATE INDEX idx_fato_vendas_tempo     ON fato_vendas (tempo_id);
CREATE INDEX idx_fato_vendas_cliente   ON fato_vendas (cliente_id);
CREATE INDEX idx_fato_vendas_produto   ON fato_vendas (produto_id);
CREATE INDEX idx_fato_vendas_loja      ON fato_vendas (loja_id);
CREATE INDEX idx_dim_tempo_ano_mes     ON dim_tempo (ano_mes);
CREATE INDEX idx_dim_produtos_cat      ON dim_produtos (categoria);
CREATE INDEX idx_dim_clientes_regiao   ON dim_clientes (regiao);
