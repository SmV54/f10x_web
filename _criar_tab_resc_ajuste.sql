-- =====================================================================
-- tab_resc_ajuste — Ajuste de verba CALCULADA da rescisao   13/10/2026
-- Rodar no Supabase -> SQL Editor.
--
-- O calculo da rescisao apaga e regrava as verbas calculadas (tab_mov,
-- origem 'C') a cada rodada, entao um valor corrigido direto no tab_mov
-- sumiria no recalculo. O ajuste fica aqui, fora do tab_mov, e o calculo
-- usa este valor no lugar do apurado: as bases de INSS/IRRF/FGTS e o
-- liquido saem dele. valor = 0 exclui a verba da rescisao.
--
-- Uma linha por verba de cada rescisao (folha + matricula + verba).
-- Valores em CENTAVOS, como no tab_mov.
-- =====================================================================

CREATE TABLE IF NOT EXISTS public.tab_resc_ajuste (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente        integer      NOT NULL,
    id_empresa        integer      NOT NULL,
    folha             integer      NOT NULL,          -- folha da rescisao (YYYYMM)
    matricula         integer      NOT NULL,
    cod_verba         integer      NOT NULL,
    valor             bigint       NOT NULL DEFAULT 0, -- valor que vale (0 = excluida)
    valor_calculado   bigint       NOT NULL DEFAULT 0, -- o que o calculo dava ao ajustar
    motivo            text         NOT NULL DEFAULT '',
    cpf_usuario       varchar(11),
    criado_em         timestamp    DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tab_resc_ajuste
    ON public.tab_resc_ajuste (id_empresa, folha, matricula, cod_verba);

NOTIFY pgrst, 'reload schema';
