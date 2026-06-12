-- =====================================================================
-- tab_cc  —  Centro de Custos
-- =====================================================================

CREATE TABLE tab_cc (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente  BIGINT       NOT NULL REFERENCES tab_Cliente(id_cliente),
    id_empresa  BIGINT       NOT NULL REFERENCES tab_Empresa(id_empresa),
    situacao    CHAR(1)      NOT NULL DEFAULT 'A'
                    CHECK (situacao IN ('A','D')),
    codigo_cc   VARCHAR(8)   NOT NULL,
    nomecc      VARCHAR(40)  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_cc_empresa_codigo UNIQUE (id_empresa, codigo_cc)
);

-- =====================================================================
-- Índices
-- =====================================================================
CREATE INDEX idx_cc_empresa
    ON tab_cc (id_cliente, id_empresa);

CREATE INDEX idx_cc_situacao
    ON tab_cc (id_empresa, situacao);
