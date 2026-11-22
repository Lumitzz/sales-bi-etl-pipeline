-- ============================================================================
-- RetailPulse — Consultas SQL Analíticas (SQLite 3.25+ / MySQL 8.0+ compatível)
-- Utiliza CTEs, Window Functions (LAG, SUM OVER, RANK, NTILE), Curva ABC e RFM
-- ============================================================================

-- @name: kpi_overview
SELECT
    ROUND(SUM(f.receita_liquida), 2)                                    AS receita_total,
    ROUND(SUM(f.lucro_bruto), 2)                                        AS lucro_bruto,
    ROUND(SUM(f.lucro_bruto) * 100.0 / NULLIF(SUM(f.receita_liquida), 0), 2) AS margem_bruta_pct,
    ROUND(AVG(f.receita_liquida), 2)                                    AS ticket_medio,
    COUNT(f.venda_id)                                                   AS total_pedidos,
    SUM(f.quantidade)                                                   AS itens_vendidos,
    COUNT(DISTINCT f.cliente_id)                                        AS clientes_ativos,
    ROUND(AVG(f.desconto_pct) * 100.0, 2)                               AS desconto_medio_pct
FROM fato_vendas f;

-- @name: monthly_revenue_growth
WITH mensal AS (
    SELECT
        t.ano,
        t.mes,
        t.ano_mes,
        t.nome_mes,
        ROUND(SUM(f.receita_liquida), 2) AS receita,
        ROUND(SUM(f.lucro_bruto), 2)     AS lucro,
        COUNT(f.venda_id)                AS pedidos,
        ROUND(AVG(f.receita_liquida), 2) AS ticket_medio
    FROM fato_vendas f
    JOIN dim_tempo t ON f.tempo_id = t.tempo_id
    GROUP BY t.ano, t.mes, t.ano_mes, t.nome_mes
),
com_variacao AS (
    SELECT
        ano,
        mes,
        ano_mes,
        nome_mes,
        receita,
        lucro,
        pedidos,
        ticket_medio,
        LAG(receita, 1)  OVER (ORDER BY ano_mes) AS receita_mes_anterior,
        LAG(receita, 12) OVER (ORDER BY ano_mes) AS receita_ano_anterior
    FROM mensal
)
SELECT
    ano,
    mes,
    ano_mes,
    nome_mes,
    receita,
    lucro,
    pedidos,
    ticket_medio,
    ROUND((receita - receita_mes_anterior) * 100.0 / NULLIF(receita_mes_anterior, 0), 2) AS crescimento_mom_pct,
    ROUND((receita - receita_ano_anterior) * 100.0 / NULLIF(receita_ano_anterior, 0), 2) AS crescimento_yoy_pct
FROM com_variacao
ORDER BY ano_mes;

-- @name: category_performance
WITH cat_agg AS (
    SELECT
        p.categoria,
        ROUND(SUM(f.receita_liquida), 2) AS receita,
        ROUND(SUM(f.lucro_bruto), 2)     AS lucro,
        COUNT(f.venda_id)                AS pedidos,
        SUM(f.quantidade)                AS unidades
    FROM fato_vendas f
    JOIN dim_produtos p ON f.produto_id = p.produto_id
    GROUP BY p.categoria
)
SELECT
    RANK() OVER (ORDER BY receita DESC)                                 AS ranking,
    categoria,
    receita,
    lucro,
    ROUND(lucro * 100.0 / NULLIF(receita, 0), 2)                        AS margem_pct,
    ROUND(receita * 100.0 / NULLIF(SUM(receita) OVER (), 0), 2)         AS participacao_pct,
    pedidos,
    unidades,
    ROUND(receita / NULLIF(pedidos, 0), 2)                              AS ticket_medio
FROM cat_agg
ORDER BY receita DESC;

-- @name: regional_performance
WITH reg_agg AS (
    SELECT
        c.regiao,
        ROUND(SUM(f.receita_liquida), 2) AS receita,
        ROUND(SUM(f.lucro_bruto), 2)     AS lucro,
        COUNT(f.venda_id)                AS pedidos,
        COUNT(DISTINCT f.cliente_id)     AS clientes_unicos
    FROM fato_vendas f
    JOIN dim_clientes c ON f.cliente_id = c.cliente_id
    GROUP BY c.regiao
)
SELECT
    regiao,
    receita,
    lucro,
    ROUND(lucro * 100.0 / NULLIF(receita, 0), 2)                        AS margem_pct,
    ROUND(receita * 100.0 / NULLIF(SUM(receita) OVER (), 0), 2)         AS participacao_pct,
    pedidos,
    clientes_unicos,
    ROUND(receita / NULLIF(pedidos, 0), 2)                              AS ticket_medio
FROM reg_agg
ORDER BY receita DESC;

-- @name: abc_curve_products
WITH prod_rev AS (
    SELECT
        p.produto_id,
        p.nome_produto,
        p.categoria,
        ROUND(SUM(f.receita_liquida), 2) AS receita,
        ROUND(SUM(f.lucro_bruto), 2)     AS lucro,
        SUM(f.quantidade)                AS unidades
    FROM fato_vendas f
    JOIN dim_produtos p ON f.produto_id = p.produto_id
    GROUP BY p.produto_id, p.nome_produto, p.categoria
),
pareto AS (
    SELECT
        produto_id,
        nome_produto,
        categoria,
        receita,
        lucro,
        unidades,
        ROUND(receita * 100.0 / NULLIF(SUM(receita) OVER (), 0), 2) AS participacao_pct,
        ROUND(
            SUM(receita) OVER (ORDER BY receita DESC, produto_id ASC)
            * 100.0 / NULLIF(SUM(receita) OVER (), 0),
            2
        ) AS acumulado_pct
    FROM prod_rev
)
SELECT
    produto_id,
    nome_produto,
    categoria,
    receita,
    lucro,
    unidades,
    participacao_pct,
    acumulado_pct,
    CASE
        WHEN acumulado_pct <= 80.0 THEN 'A'
        WHEN acumulado_pct <= 95.0 THEN 'B'
        ELSE 'C'
    END AS classe_abc
FROM pareto
ORDER BY receita DESC;

-- @name: rfm_segmentation
WITH ref_date AS (
    SELECT MAX(data_venda) AS max_data FROM fato_vendas
),
cliente_metricas AS (
    SELECT
        c.cliente_id,
        c.nome,
        c.regiao,
        c.segmento,
        CAST(julianday((SELECT max_data FROM ref_date)) - julianday(MAX(f.data_venda)) AS INTEGER) AS recencia_dias,
        COUNT(f.venda_id)                AS frequencia,
        ROUND(SUM(f.receita_liquida), 2) AS valor_monetario
    FROM fato_vendas f
    JOIN dim_clientes c ON f.cliente_id = c.cliente_id
    GROUP BY c.cliente_id, c.nome, c.regiao, c.segmento
),
scores AS (
    SELECT
        cliente_id,
        nome,
        regiao,
        segmento,
        recencia_dias,
        frequencia,
        valor_monetario,
        NTILE(4) OVER (ORDER BY recencia_dias DESC)   AS r_score,
        NTILE(4) OVER (ORDER BY frequencia ASC)       AS f_score,
        NTILE(4) OVER (ORDER BY valor_monetario ASC)  AS m_score
    FROM cliente_metricas
),
classificado AS (
    SELECT
        *,
        CASE
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Campeões'
            WHEN f_score >= 3 AND m_score >= 2                  THEN 'Clientes Fiéis'
            WHEN r_score >= 3 AND m_score <= 2                  THEN 'Potencial de Crescimento'
            WHEN r_score <= 2 AND (f_score >= 2 OR m_score >= 3) THEN 'Em Risco'
            ELSE 'Hibernando'
        END AS segmento_rfm
    FROM scores
)
SELECT
    segmento_rfm,
    COUNT(cliente_id)                       AS total_clientes,
    ROUND(AVG(recencia_dias), 1)            AS recencia_media_dias,
    ROUND(AVG(frequencia), 1)               AS frequencia_media,
    ROUND(SUM(valor_monetario), 2)          AS receita_total,
    ROUND(AVG(valor_monetario), 2)          AS ticket_clv_medio
FROM classificado
GROUP BY segmento_rfm
ORDER BY receita_total DESC;

-- @name: top_customers
SELECT
    RANK() OVER (ORDER BY SUM(f.receita_liquida) DESC) AS ranking,
    c.cliente_id,
    c.nome,
    c.cidade,
    c.estado,
    c.segmento,
    COUNT(f.venda_id)                                  AS total_pedidos,
    ROUND(SUM(f.receita_liquida), 2)                   AS receita_total,
    ROUND(AVG(f.receita_liquida), 2)                   AS ticket_medio
FROM fato_vendas f
JOIN dim_clientes c ON f.cliente_id = c.cliente_id
GROUP BY c.cliente_id, c.nome, c.cidade, c.estado, c.segmento
ORDER BY receita_total DESC
LIMIT 10;

-- @name: channel_performance
SELECT
    f.canal_venda,
    COUNT(f.venda_id)                                                   AS pedidos,
    ROUND(SUM(f.receita_liquida), 2)                                    AS receita,
    ROUND(SUM(f.lucro_bruto), 2)                                        AS lucro,
    ROUND(SUM(f.receita_liquida) * 100.0 / NULLIF(SUM(SUM(f.receita_liquida)) OVER (), 0), 2) AS participacao_pct
FROM fato_vendas f
GROUP BY f.canal_venda
ORDER BY receita DESC;
