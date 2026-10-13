-- =====================================================================
-- tab_dissidio — Diferenca de Dissidio (Eventuais > Salarios)  13/10/2026
-- Rodar no Supabase -> SQL Editor.
--
-- Guarda o DETALHE do calculo, que o tab_mov nao tem: o tab_mov recebe so'
-- uma linha por funcionario (a verba destino com o total); aqui fica cada
-- mes base x verba, com o indice usado. Dai saem a reimpressao da listagem,
-- o demonstrativo individual e o quadro opcional no contracheque.
--
-- Valores em CENTAVOS, como no tab_mov. valor_dif e' negativo nas verbas de
-- desconto que reduzem a diferenca (0132 faltas, 0139 DSR, 0141 suspensao).
-- =====================================================================

CREATE TABLE IF NOT EXISTS public.tab_dissidio (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente        integer      NOT NULL,
    id_empresa        integer      NOT NULL,
    folha             integer      NOT NULL,          -- folha que paga (YYYYMM)
    folha_tipo        varchar(1)   NOT NULL DEFAULT 'N',
    matricula         integer      NOT NULL,
    folha_base        integer      NOT NULL,          -- mes da diferenca (YYYYMM)
    folha_base_tipo   varchar(1)   NOT NULL DEFAULT 'N',  -- N normal, 1 = 13o salario
    sal_atual         bigint,
    sal_base          bigint,
    indice            numeric(14,8),                  -- 0.05 = 5%
    cod_verba         integer      NOT NULL,          -- verba da folha base
    valor_base        bigint       NOT NULL,
    valor_dif         bigint       NOT NULL,
    cod_verba_destino integer      NOT NULL,
    cpf_usuario       varchar(11),
    criado_em         timestamp    DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_tab_dissidio_folha
    ON public.tab_dissidio (id_empresa, folha, folha_tipo, matricula);

NOTIFY pgrst, 'reload schema';
