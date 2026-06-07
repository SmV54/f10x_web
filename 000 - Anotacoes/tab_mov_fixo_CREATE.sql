-- =====================================================================
-- tab_mov_fixo — Movimentos fixos recorrentes
-- Exemplos: empréstimo em parcelas, desconto fixo mensal, plano de saúde
-- =====================================================================

CREATE TABLE tab_mov_fixo (

    -- ------------------------------------------------------------------
    -- Controle interno
    -- ------------------------------------------------------------------
    id              BIGSERIAL       PRIMARY KEY,
    id_cliente      INTEGER         NOT NULL,
    id_empresa      INTEGER         NOT NULL,
    situacao        CHAR(1)         NOT NULL DEFAULT 'A'
                        CHECK (situacao IN ('A','D')),

    -- ------------------------------------------------------------------
    -- Funcionário — NULL = aplica filtro de grupo abaixo
    -- ------------------------------------------------------------------
    matricula       INTEGER                             -- 1 a 999999; NULL = grupo
                        CHECK (matricula BETWEEN 1 AND 999999),

    -- ------------------------------------------------------------------
    -- Filtros de grupo (opcionais; todos NULL = todos os funcionários)
    -- ------------------------------------------------------------------
    id_sindicato    INTEGER,                            -- FK tab_aux_sindicatos
    id_funcao       INTEGER,                            -- FK tab_aux_funcao_cli
    id_centrocusto  VARCHAR(8),                         -- uso futuro
    id_filial       VARCHAR(6),                         -- uso futuro
    categoria       VARCHAR(3),                         -- filtra tab_cad.categoria; código Tab.01 eSocial (ex: "101")

    -- ------------------------------------------------------------------
    -- Filtros por data de nascimento  (YYYYMMDD)
    -- ------------------------------------------------------------------
    datanascimento1 CHAR(8),                            -- limite inferior
    datanascimento2 CHAR(8),                            -- limite superior

    -- ------------------------------------------------------------------
    -- Filtros por data de admissão  (YYYYMMDD)
    -- ------------------------------------------------------------------
    dataadmissao1   CHAR(8),                            -- limite inferior
    dataadmissao2   CHAR(8),                            -- limite superior

    -- ------------------------------------------------------------------
    -- Filtros por salário base  (em centavos)
    -- ------------------------------------------------------------------
    salariobase1    BIGINT                              -- limite inferior
                        CHECK (salariobase1 >= 0),
    salariobase2    BIGINT                              -- limite superior
                        CHECK (salariobase2 >= 0),

    -- ------------------------------------------------------------------
    -- Filtros por idade  (anos)
    -- ------------------------------------------------------------------
    idade1          SMALLINT                            -- limite inferior
                        CHECK (idade1 BETWEEN 0 AND 120),
    idade2          SMALLINT                            -- limite superior
                        CHECK (idade2 BETWEEN 0 AND 120),

    -- ------------------------------------------------------------------
    -- Filtros por tempo de serviço  (meses)
    -- ------------------------------------------------------------------
    tempo_servico1  SMALLINT                            -- limite inferior
                        CHECK (tempo_servico1 >= 0),
    tempo_servico2  SMALLINT                            -- limite superior
                        CHECK (tempo_servico2 >= 0),

    -- ------------------------------------------------------------------
    -- Período de vigência  (YYYYMM)
    -- Mutuamente exclusivo com qtd_parcelas / qtd_parcelas_before
    -- ------------------------------------------------------------------
    folha_inicial   INTEGER                             -- mês de início
                        CHECK (folha_inicial BETWEEN 190001 AND 209912),
    folha_final     INTEGER                             -- mês de término
                        CHECK (folha_final   BETWEEN 190001 AND 209912),

    -- ------------------------------------------------------------------
    -- Rubrica (verba)
    -- ------------------------------------------------------------------
    cod_verba       SMALLINT        NOT NULL
                        CHECK (cod_verba BETWEEN 1 AND 9999),

    -- ------------------------------------------------------------------
    -- Controle de parcelas (alternativo a folha_inicial/folha_final)
    -- ------------------------------------------------------------------
    qtd_parcelas        SMALLINT                        -- total de parcelas (01-99)
                            CHECK (qtd_parcelas BETWEEN 1 AND 99),
    qtd_parcelas_before SMALLINT    DEFAULT 0           -- já descontadas (0-99)
                            CHECK (qtd_parcelas_before BETWEEN 0 AND 99),

    -- ------------------------------------------------------------------
    -- Valor  (em centavos; ex: R$ 1.000,00 → 100000)
    -- ------------------------------------------------------------------
    valor           BIGINT          NOT NULL
                        CHECK (valor BETWEEN 1 AND 9999999999),

    -- ------------------------------------------------------------------
    -- Regras de processamento
    -- ------------------------------------------------------------------
    nas_ferias      CHAR(1)         NOT NULL DEFAULT '0'
                        CHECK (nas_ferias IN ('0','1','2','3','4')),
                        -- 0 = Não processar mesmo que seja 1 dia de férias
                        -- 1 = Processar integral sem proporcionalidade
                        -- 2 = Processar tudo nas férias (no mês do início)
                        -- 3 = Proporcional aos dias trabalhados e dias gozados
                        -- 4 = Proporcional aos dias trabalhados; zero nas férias

    se_afastado     CHAR(1)         NOT NULL DEFAULT '1'
                        CHECK (se_afastado IN ('1','2','3')),
                        -- 1 = Continuar normalmente mesmo afastado
                        -- 2 = Interromper se afastado no cálculo
                        -- 3 = Pagar proporcional aos dias trabalhados

    mes_admissao    CHAR(1)         NOT NULL DEFAULT 'T'
                        CHECK (mes_admissao IN ('T','P')),
                        -- T = Total no mês de admissão
                        -- P = Proporcional aos dias trabalhados

    mes_rescisao    CHAR(1)         NOT NULL DEFAULT 'T'
                        CHECK (mes_rescisao IN ('T','P')),
                        -- T = Total no mês de rescisão
                        -- P = Proporcional aos dias trabalhados

    -- ------------------------------------------------------------------
    -- Controle interno de auditoria
    -- ------------------------------------------------------------------
    data_cad        CHAR(8),                            -- YYYYMMDD — criação
    hora_cad        CHAR(4),                            -- HHMM
    dt_gravacao     VARCHAR(13),                        -- "YYYYMMDD HHMM"

    -- ------------------------------------------------------------------
    -- Restrição: parcelas e período de folha são mutuamente exclusivos
    -- ------------------------------------------------------------------
    CONSTRAINT chk_parcelas_ou_periodo CHECK (
        NOT (
            qtd_parcelas IS NOT NULL
            AND (folha_inicial IS NOT NULL OR folha_final IS NOT NULL)
        )
    )
);

-- =====================================================================
-- Índices
-- =====================================================================
CREATE INDEX idx_mov_fixo_empresa
    ON tab_mov_fixo (id_cliente, id_empresa);

CREATE INDEX idx_mov_fixo_matricula
    ON tab_mov_fixo (id_cliente, id_empresa, matricula);

CREATE INDEX idx_mov_fixo_situacao
    ON tab_mov_fixo (id_cliente, id_empresa, situacao);

CREATE INDEX idx_mov_fixo_cod_verba
    ON tab_mov_fixo (id_cliente, id_empresa, cod_verba);

-- =====================================================================
-- ALTER TABLE para corrigir tabela já criada:
-- =====================================================================
-- categoria foi criada como CHAR(1); códigos da Tab.01 eSocial têm 3 dígitos
ALTER TABLE tab_mov_fixo ALTER COLUMN categoria TYPE VARCHAR(3);
-- =====================================================================

-- =====================================================================
-- Observações de negócio
-- =====================================================================
-- 1. MODO PARCELAS vs. MODO PERÍODO:
--    - Parcelas: preencher qtd_parcelas; folha_inicial e folha_final ficam NULL.
--      qtd_parcelas_before indica quantas já foram descontadas (controle de progresso).
--    - Período: preencher folha_inicial e/ou folha_final; qtd_parcelas fica NULL.
--
-- 2. FILTROS DE GRUPO:
--    Se matricula for NULL, o movimento se aplica ao grupo definido pelos
--    filtros (id_sindicato, id_funcao, categoria, faixas de data/salário/idade).
--    Todos os filtros NULL = aplica a todos os funcionários ativos.
--
-- 3. VALOR em centavos: R$ 1.000,00 é armazenado como 100000.
--
-- 4. nas_ferias controla o comportamento quando o mês tem folha de férias
--    em paralelo à folha normal.
--
-- 5. se_afastado controla o comportamento quando o funcionário está
--    afastado no período de cálculo (INSS, acidente, etc.).
-- =====================================================================
