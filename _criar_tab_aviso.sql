-- =====================================================================
-- tab_aviso / tab_aviso_lido — Quadro de Avisos do Menu Principal
-- Rodar no Supabase -> SQL Editor (as duas tabelas de uma vez).
--
-- tab_aviso      = o aviso publicado pelo administrador
-- tab_aviso_lido = 1 linha por cliente que clicou em "Entendi"
--
-- Datas/horas em timestamp SEM fuso, ja no horario de Brasilia
-- (o sistema grava com _agora_brasilia(); o Render roda em UTC).
-- =====================================================================

CREATE TABLE IF NOT EXISTS public.tab_aviso (
    id_aviso     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    titulo       varchar(120) NOT NULL,
    mensagem     text         NOT NULL,
    tipo         varchar(1)   DEFAULT 'I',   -- I=informativo, A=atencao, U=urgente
    dh_inicio    timestamp    NOT NULL,      -- inicio da publicacao
    dh_fim       timestamp    NOT NULL,      -- fim da publicacao
    destino      varchar(1)   DEFAULT 'T',   -- T=todos os clientes, S=selecionados
    id_clientes  text,                       -- quando destino='S': "6,12,45"
    fixado       varchar(1)   DEFAULT 'N',   -- S = nao some com o "Entendi"
    link_url     varchar(200),               -- botao opcional no aviso
    link_texto   varchar(40),
    ativo        varchar(1)   DEFAULT 'S',   -- N = encerrado sem apagar
    criado_por   varchar(11),                -- CPF do admin que publicou
    criado_em    timestamp    DEFAULT now(),
    CONSTRAINT chk_aviso_tipo    CHECK (tipo    IN ('I','A','U')),
    CONSTRAINT chk_aviso_destino CHECK (destino IN ('T','S')),
    CONSTRAINT chk_aviso_periodo CHECK (dh_fim >= dh_inicio)
);

-- Busca tipica do /menu: avisos ativos dentro da janela de publicacao.
CREATE INDEX IF NOT EXISTS ix_tab_aviso_janela
    ON public.tab_aviso (ativo, dh_inicio, dh_fim);


CREATE TABLE IF NOT EXISTS public.tab_aviso_lido (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_aviso   bigint  NOT NULL,
    id_cliente integer NOT NULL,
    cpf        varchar(11),                 -- quem clicou em "Entendi"
    datahora   timestamp DEFAULT now(),
    CONSTRAINT uq_aviso_lido UNIQUE (id_aviso, id_cliente)
);

CREATE INDEX IF NOT EXISTS ix_tab_aviso_lido_cliente
    ON public.tab_aviso_lido (id_cliente);

-- 16/11/2026: onde o aviso aparece no menu.
--   Q = quadro abaixo dos cards (com "Entendi"), F = faixa correndo no rodape
ALTER TABLE public.tab_aviso ADD COLUMN IF NOT EXISTS forma varchar(1) DEFAULT 'Q';
ALTER TABLE public.tab_aviso DROP CONSTRAINT IF EXISTS chk_aviso_forma;
ALTER TABLE public.tab_aviso ADD CONSTRAINT chk_aviso_forma CHECK (forma IN ('Q','F'));

-- (Opcional) apagar o aviso apaga as leituras junto:
-- ALTER TABLE public.tab_aviso_lido
--   ADD CONSTRAINT fk_aviso_lido_aviso
--   FOREIGN KEY (id_aviso) REFERENCES public.tab_aviso (id_aviso) ON DELETE CASCADE;
