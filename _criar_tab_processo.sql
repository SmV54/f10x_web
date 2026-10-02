-- =====================================================================
-- Processo Trabalhista — eSocial S-2500 e S-2501 (leiaute S-1.3)
-- Rodar no Supabase → SQL Editor.
--
-- Três tabelas:
--   tab_processo          S-2500: uma linha por processo × trabalhador × contrato
--   tab_processo_periodo  S-2500: as bases mês a mês (idePeriodo)
--   tab_processo_pagto    S-2501: uma linha por processo × mês do pagamento × trabalhador
--
-- Convenções (as mesmas de tab_cad / tab_pensao):
--   datas         char(8)  AAAAMMDD          (ex.: '20260315')
--   competências  integer  AAAAMM            (ex.: 202603)
--   valores       bigint   em CENTAVOS       (150000 = R$ 1.500,00)
--   percentuais   integer  2 decimais        (3000 = 30,00%)
--   CPF/CNPJ      só dígitos
--   jsonb         grupos do leiaute que se repetem e são raros; valores em
--                 centavos e datas AAAAMMDD também dentro do jsonb.
--
-- Remessas: ficam na tab_esocial, como os demais eventos —
--   layout '2500' com codigo2 = tab_processo.id
--   layout '2501' com codigo2 = tab_processo_pagto.id
--   layout '3500' (exclusão) aponta para o recibo do evento excluído.
--
-- Os nomes de coluna seguem o nome do campo no leiaute, em minúsculas.
-- Prefixos agrupam os subgrupos: resp_ (ideResp), dur_ (duracao),
-- suc_ (sucessaoVinc), lt_ (localTrabalho), estab_ (ideEstab).
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1) tab_processo — S-2500
--    Mais de um contrato no mesmo processo (ex.: unicidade contratual) =
--    mais de uma linha com o mesmo processo e CPF; contrato_seq as distingue
--    e o gerador junta tudo num evento só (infoContr 1-99).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.tab_processo (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente          integer      NOT NULL,
    id_empresa          integer      NOT NULL,
    situacao            varchar(1)   NOT NULL DEFAULT 'A',   -- A=ativo, D=desativado
    criado_em           timestamptz  DEFAULT now(),
    alterado_em         timestamptz,
    matricula           integer,          -- funcionário no cadastro (NULL = trabalhador fora do cadastro,
                                          -- ex.: reconhecimento de vínculo)

    -- infoProcesso
    origem              smallint     NOT NULL,   -- 1=Judicial trabalhista 2=CCP ou NINTER 3=Justiça Comum
    nrproctrab          varchar(20)  NOT NULL,   -- 20 dígitos (origem 1 e 3) ou 15 (origem 2)
    obsproctrab         varchar(999),

    -- dadosCompl/infoProcJud (origem = 1 ou 3)
    dtsent              char(8),                 -- data da sentença / homologação do acordo
    ufvara              char(2),
    codmunic            varchar(7),
    idvara              integer,                 -- até 4 dígitos
    infopatprec         bigint,                  -- cota patronal p/ requisição autônoma — obrigatório e exclusivo da origem 3

    -- dadosCompl/infoCCP (origem = 2)
    dtccp               char(8),
    tpccp               smallint,                -- 1=CCP empresa 2=CCP sindicato 3=NINTER
    cnpjccp             varchar(14),

    -- ideEmpregador/ideResp (responsabilidade indireta — raro)
    resp_tpinsc         smallint,                -- 1=CNPJ 2=CPF
    resp_nrinsc         varchar(14),
    resp_dtadmrespdir   char(8),
    resp_matrespdir     varchar(30),

    -- ideTrab
    cpftrab             varchar(11)  NOT NULL,
    nmtrab              varchar(70),
    dtnascto            char(8),
    nmsoc               varchar(70),
    ideseqtrab          smallint,                -- só quando o mesmo processo vai em mais de um S-2500 do trabalhador
    contrato_seq        smallint     NOT NULL DEFAULT 1,

    -- infoContr
    tpcontr             smallint     NOT NULL,   -- 1 a 9 (ver tabela do leiaute)
    indcontr            char(1)      NOT NULL,   -- S/N: contrato já tem S-2190/S-2200/S-2300
    dtadmorig           char(8),
    indreint            char(1),                 -- S/N
    indcateg            char(1)      NOT NULL,   -- S/N
    indnatativ          char(1)      NOT NULL,   -- S/N
    indmotdeslig        char(1)      NOT NULL,   -- S/N
    matricula_es        varchar(30),             -- matrícula do eSocial (campo "matricula" do leiaute)
    codcateg            varchar(3),
    dtinicio            char(8),                 -- início de TSVE

    -- infoContr/infoCompl
    nmcargo             varchar(100),
    codcbo              varchar(6),
    nmfuncao            varchar(100),
    cbofuncao           varchar(6),
    natatividade        smallint,                -- 1=urbano 2=rural

    -- infoCompl/infoVinc
    tpregtrab           smallint,
    tpregprev           smallint,
    dtadm               char(8),
    tmpparc             smallint,
    dur_tpcontr         smallint,                -- duracao/tpContr: 1=indeterminado 2=determinado (dias) 3=determinado (fato)
    dur_dtterm          char(8),
    dur_clauassec       char(1),
    dur_objdet          varchar(255),
    suc_tpinsc          smallint,                -- sucessaoVinc
    suc_nrinsc          varchar(14),
    suc_matricant       varchar(30),
    suc_dttransf        char(8),
    dtdeslig            char(8),                 -- infoDeslig
    mtvdeslig           varchar(2),
    dtprojfimapi        char(8),
    pensalim            smallint,
    percaliment         integer,
    vralim              bigint,

    -- infoCompl/infoTerm (TSVE)
    dtterm              char(8),
    mtvdesligtsv        varchar(2),

    -- infoCompl/localTrabalho
    lt_tpinsc           smallint,
    lt_nrinsc           varchar(14),
    lt_desccomp         varchar(80),
    lt_endereco         jsonb,                   -- localTempDom: {tpLograd,dscLograd,nrLograd,complemento,bairro,cep,codMunic,uf}

    -- ideEstab + infoVlr
    estab_tpinsc        smallint     NOT NULL DEFAULT 1,   -- 1=CNPJ 3=CAEPF 4=CNO
    estab_nrinsc        varchar(14)  NOT NULL,
    compini             integer      NOT NULL,   -- AAAAMM
    compfim             integer      NOT NULL,   -- AAAAMM
    indreperc           smallint     NOT NULL,   -- 1 a 5 (1 e 3 exigem S-2501)
    indensd             char(1),                 -- 'S' ou NULL
    indenabono          char(1),                 -- 'S' ou NULL
    abono_anos          jsonb,                   -- [2023, 2024] — até 9 anos-base

    -- grupos repetidos e raros
    remuneracao         jsonb,                   -- [{dtRemun,vrSalFx,undSalFixo,dscSalVar}]          0-99
    observacoes         jsonb,                   -- ["texto", ...]                                   0-99
    mudcategativ        jsonb,                   -- [{codCateg,natAtividade,dtMudCategAtiv}]          0-99
    unicontr            jsonb,                   -- [{matUnic,codCateg,dtInicio}]                      0-99

    CONSTRAINT chk_processo_situacao   CHECK (situacao IN ('A','D')),
    CONSTRAINT chk_processo_origem     CHECK (origem BETWEEN 1 AND 3),
    CONSTRAINT chk_processo_nrproc     CHECK (nrproctrab ~ '^([0-9]{15}|[0-9]{20})$'),
    CONSTRAINT chk_processo_tpccp      CHECK (tpccp IS NULL OR tpccp BETWEEN 1 AND 3),
    CONSTRAINT chk_processo_cpf        CHECK (cpftrab ~ '^[0-9]{11}$'),
    CONSTRAINT chk_processo_tpcontr    CHECK (tpcontr BETWEEN 1 AND 9),
    CONSTRAINT chk_processo_sn         CHECK (indcontr IN ('S','N') AND indcateg IN ('S','N')
                                              AND indnatativ IN ('S','N') AND indmotdeslig IN ('S','N')
                                              AND (indreint IS NULL OR indreint IN ('S','N'))),
    CONSTRAINT chk_processo_indreperc  CHECK (indreperc BETWEEN 1 AND 5),
    CONSTRAINT chk_processo_comp       CHECK (compfim >= compini),
    CONSTRAINT chk_processo_estab      CHECK (estab_tpinsc IN (1,3,4))
);

-- Um contrato por processo × trabalhador × sequência.
CREATE UNIQUE INDEX IF NOT EXISTS ux_tab_processo_chave
    ON public.tab_processo (id_empresa, nrproctrab, cpftrab, COALESCE(ideseqtrab, 0), contrato_seq);

-- Busca típica: processos de um funcionário / da empresa.
CREATE INDEX IF NOT EXISTS ix_tab_processo_empresa_matricula
    ON public.tab_processo (id_empresa, matricula, situacao);


-- ---------------------------------------------------------------------
-- 2) tab_processo_periodo — S-2500 / idePeriodo (0-999 por contrato)
--    O gerador só abre baseCalculo se vrbccpmensal tiver valor, e só abre
--    infoFGTS se vrbcfgtsproctrab tiver valor.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.tab_processo_periodo (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_processo         bigint       NOT NULL REFERENCES public.tab_processo (id) ON DELETE CASCADE,
    id_cliente          integer      NOT NULL,
    id_empresa          integer      NOT NULL,
    criado_em           timestamptz  DEFAULT now(),
    perref              integer      NOT NULL,   -- AAAAMM

    -- baseCalculo
    vrbccpmensal        bigint,
    vrbccp13            bigint,
    grauexp             smallint,                -- infoAgNocivo: 1 a 4

    -- infoFGTS
    vrbcfgtsproctrab    bigint,
    vrbcfgtssefip       bigint,
    vrbcfgtsdecant      bigint,

    -- baseMudCateg
    mud_codcateg        varchar(3),
    mud_vrbcprev        bigint,

    infointerm          jsonb,                   -- [{dia,hrsTrab}] 0-31 — trabalho intermitente

    CONSTRAINT chk_processo_periodo_grauexp CHECK (grauexp IS NULL OR grauexp BETWEEN 1 AND 4)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tab_processo_periodo
    ON public.tab_processo_periodo (id_processo, perref);


-- ---------------------------------------------------------------------
-- 3) tab_processo_pagto — S-2501
--    Uma linha por processo × mês do pagamento × trabalhador. O evento
--    aceita vários trabalhadores (ideTrab 1-N): o gerador agrupa as linhas
--    de mesmo nrproctrab + perapurpgto + ideseqproc num evento só.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.tab_processo_pagto (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_processo         bigint       REFERENCES public.tab_processo (id),   -- o S-2500 de origem
    id_cliente          integer      NOT NULL,
    id_empresa          integer      NOT NULL,
    situacao            varchar(1)   NOT NULL DEFAULT 'A',
    criado_em           timestamptz  DEFAULT now(),
    alterado_em         timestamptz,
    matricula           integer,

    -- ideProc
    nrproctrab          varchar(20)  NOT NULL,
    perapurpgto         integer      NOT NULL,   -- AAAAMM: mês em que a parcela é devida
    ideseqproc          smallint,
    obs                 varchar(999),

    -- ideTrab
    cpftrab             varchar(11)  NOT NULL,

    -- calcTrib (0-999): bases e contribuições por mês de referência
    --   [{"perRef":202401,"vrBcCpMensal":350000,"vrBcCp13":0,
    --     "infoCRContrib":[{"tpCR":"113851","vrCR":38500}]}]
    calctrib            jsonb,

    -- infoCRIRRF — o código de receita principal em colunas...
    irrf_tpcr           varchar(6),              -- 593656=Justiça do Trabalho 056152=CCP/NINTER 188951=RRA
    irrf_vrcr           bigint,
    irrf_vrcr13         bigint,
    -- ...e o detalhe (infoIR, infoRRA, dedDepen, penAlim, infoProcRet) em jsonb
    irrf_detalhe        jsonb,
    irrf_outros         jsonb,                   -- outros códigos de receita do mesmo pagamento (raro), mesmo formato

    -- infoIRComplem
    dtlaudo             char(8),                 -- moléstia grave
    infodep             jsonb,                   -- [{cpfDep,dtNascto,nome,depIRRF,tpDep,descrDep}]

    CONSTRAINT chk_processo_pagto_situacao CHECK (situacao IN ('A','D')),
    CONSTRAINT chk_processo_pagto_nrproc   CHECK (nrproctrab ~ '^([0-9]{15}|[0-9]{20})$'),
    CONSTRAINT chk_processo_pagto_cpf      CHECK (cpftrab ~ '^[0-9]{11}$'),
    CONSTRAINT chk_processo_pagto_tpcr     CHECK (irrf_tpcr IS NULL OR irrf_tpcr IN ('593656','056152','188951'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tab_processo_pagto_chave
    ON public.tab_processo_pagto (id_empresa, nrproctrab, perapurpgto, COALESCE(ideseqproc, 0), cpftrab);

CREATE INDEX IF NOT EXISTS ix_tab_processo_pagto_processo
    ON public.tab_processo_pagto (id_processo);


-- O app acessa as tabelas com a chave anon (como a tab_contrato_modelo):
-- sem isto, se o projeto ligar o RLS por padrão, as telas não enxergam nada.
ALTER TABLE public.tab_processo         DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.tab_processo_periodo DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.tab_processo_pagto   DISABLE ROW LEVEL SECURITY;
