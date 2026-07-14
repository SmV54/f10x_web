-- =====================================================================
-- tab_pensao — Pensão Alimentícia (tabela própria)
-- Rodar no Supabase → SQL Editor.
-- Valores monetários e percentual são INTEIROS com as 2 decimais
-- incorporadas (centavos / centésimos de %):
--   valor_fixo = 150000  -> R$ 1.500,00
--   percentual =   3000  -> 30,00%   (máximo 10000 = 100,00%)
-- anomes_inicial / anomes_final no formato yyyymm (ex.: 202607).
-- formula = id (PK) da linha em tab_tabela_cli onde a fórmula está cadastrada.
-- dep_responsavel / dep_benef1..9 = id (PK) do dependente em tab_dependentes.
--   Responsável = 1 id; Beneficiários = até 9 ids (colunas fixas).
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.tab_pensao (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente      integer,
    id_empresa      integer,
    situacao        varchar(1)  DEFAULT 'A',     -- string de 1 posição (A=ativa, D=inativa)
    matricula       integer,                     -- funcionário (devedor da pensão)
    dep_responsavel bigint,                      -- id do dependente responsável (tab_dependentes.id)
    anomes_inicial  integer,                     -- yyyymm — início da vigência
    anomes_final    integer,                     -- yyyymm — fim da vigência (NULL = sem término)
    formula         bigint,                      -- id da fórmula em tab_tabela_cli
    valor_fixo      integer,                     -- centavos (fórmula de valor fixo)
    percentual      integer,                     -- 2 decimais incorporadas; máx 10000 (=100,00%)
    criado_em       timestamptz DEFAULT now(),
    dep_benef1      bigint,                       -- ids dos dependentes beneficiários
    dep_benef2      bigint,                       -- (tab_dependentes.id) — até 9 beneficiários
    dep_benef3      bigint,
    dep_benef4      bigint,
    dep_benef5      bigint,
    dep_benef6      bigint,
    dep_benef7      bigint,
    dep_benef8      bigint,
    dep_benef9      bigint,
    CONSTRAINT chk_pensao_percentual
        CHECK (percentual IS NULL OR percentual BETWEEN 0 AND 10000)
);

-- Busca típica: pensões ativas de um funcionário numa empresa.
CREATE INDEX IF NOT EXISTS ix_tab_pensao_empresa_matricula
    ON public.tab_pensao (id_empresa, matricula, situacao);

-- (Opcional) integridade referencial:
-- ALTER TABLE public.tab_pensao
--   ADD CONSTRAINT fk_tab_pensao_formula
--   FOREIGN KEY (formula) REFERENCES public.tab_tabela_cli (id);
