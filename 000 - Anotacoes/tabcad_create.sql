-- ============================================================
--  tab_CAD  -  Cadastro de Funcionários
--  Baseado no layout eSocial S-2200
-- ============================================================

CREATE TABLE tab_CAD (
    id                  BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- ---------------------------------------------------------
    -- Identificação
    -- ---------------------------------------------------------
    id_Cliente          BIGINT       NOT NULL REFERENCES tab_Cliente(id_cliente),
    id_Empresa          BIGINT       NOT NULL REFERENCES tab_Empresa(id_empresa),
    situacao            CHAR(1)      NOT NULL DEFAULT 'A'  CHECK (situacao        IN ('A','D')),
    matricula           INTEGER      NOT NULL               CHECK (matricula       BETWEEN 1 AND 999999),
    matricula_eS        VARCHAR(30),
    filial              VARCHAR(6),
    cpf                 VARCHAR(11)  NOT NULL,
    nome                VARCHAR(70)  NOT NULL,
    nomeR               VARCHAR(30),
    codCateg            VARCHAR(3)   NOT NULL,
    nomeMae             VARCHAR(70),
    vrSalFx             INTEGER      NOT NULL DEFAULT 0,
    UndSalFixo          CHAR(1)      NOT NULL               CHECK (UndSalFixo     IN ('M','H','D')),

    -- ---------------------------------------------------------
    -- Contrato de Trabalho
    -- ---------------------------------------------------------
    tpContr             CHAR(1)      NOT NULL               CHECK (tpContr        IN ('1','2','3')),
    dtTerm              CHAR(8),
    ClauAssec           CHAR(1)                             CHECK (ClauAssec      IN ('S','N')),
    objDet              VARCHAR(120),

    -- ---------------------------------------------------------
    -- Local de Trabalho
    -- ---------------------------------------------------------
    centrocusto         VARCHAR(8),
    lt_tpInsc           CHAR(1)                             CHECK (lt_tpInsc      IN ('1','3','4')),
    lt_nrInsc           VARCHAR(14),

    -- ---------------------------------------------------------
    -- Jornada de Trabalho
    -- ---------------------------------------------------------
    qtdHrsSem           VARCHAR(2),
    qtdHrsMes           VARCHAR(3),
    tpJornada           CHAR(1)                             CHECK (tpJornada      IN ('2','3','4','5','6','7','9')),
    tmpParc             CHAR(1)      NOT NULL DEFAULT '0'   CHECK (tmpParc        IN ('0','1','2','3')),
    horNoturno          CHAR(1)                             CHECK (horNoturno     IN ('S','N')),
    id_tab_Horario      BIGINT       REFERENCES tab_aux_horarios(id_horario),

    -- ---------------------------------------------------------
    -- Dados Pessoais
    -- ---------------------------------------------------------
    sexo                CHAR(1)      NOT NULL               CHECK (sexo           IN ('M','F')),
    racaCor             CHAR(1)      NOT NULL               CHECK (racaCor        IN ('1','2','3','4','5','6')),
    estCiv              CHAR(1)                             CHECK (estCiv         IN ('1','2','3','4','5')),
    grauInstr           CHAR(2)                             CHECK (grauInstr      IN ('01','02','03','04','05','06','07','08','09','10','11','12')),
    dtNascto            CHAR(8)      NOT NULL,
    paisNascto          CHAR(3)      NOT NULL,
    paisNac             CHAR(3)      NOT NULL,

    -- ---------------------------------------------------------
    -- Admissão
    -- ---------------------------------------------------------
    dtAdm               CHAR(8)      NOT NULL,
    tpAdmissao          CHAR(1)      NOT NULL               CHECK (tpAdmissao     IN ('1','2','3','4','6','7')),
    dtTransf            CHAR(8),
    cnpjTransf          VARCHAR(14),
    matriculaTransf     INTEGER                             CHECK (matriculaTransf BETWEEN 1 AND 999999),
    indAdmissao         CHAR(1)      NOT NULL DEFAULT '1'   CHECK (indAdmissao    IN ('1','2','3')),
    nrProcTrab          VARCHAR(20),
    tpRegJor            CHAR(1)      NOT NULL               CHECK (tpRegJor       IN ('1','2','3','4')),
    natAtividade        CHAR(1)      NOT NULL DEFAULT '1'   CHECK (natAtividade   IN ('1','2')),
    cnpjSindCategProf   VARCHAR(14),
    tomador_tpInsc      CHAR(1)                             CHECK (tomador_tpInsc IN ('1','3','4')),
    tomador_nrInsc      VARCHAR(14),
    CBOFuncao           VARCHAR(6)   NOT NULL,

    -- ---------------------------------------------------------
    -- Dados Bancários
    -- ---------------------------------------------------------
    banco_Numero        VARCHAR(3),
    banco_Agencia       VARCHAR(4),
    banco_AgenciaDV     VARCHAR(1),
    banco_Conta         VARCHAR(12),
    banco_ContaDV       VARCHAR(1),

    -- ---------------------------------------------------------
    -- Uso Futuro
    -- ---------------------------------------------------------
    Flags               VARCHAR(20),

    -- ---------------------------------------------------------
    -- Endereço
    -- ---------------------------------------------------------
    ender_dscLograd     VARCHAR(100),
    ender_nrLograd      VARCHAR(10),
    ender_complemento   VARCHAR(30),
    ender_bairro        VARCHAR(90),
    ender_cep           VARCHAR(8),
    ender_codMunic      VARCHAR(7),
    ender_uf            VARCHAR(2),

    -- ---------------------------------------------------------
    -- Imigrante
    -- ---------------------------------------------------------
    ind_Imigrante       CHAR(1)      NOT NULL DEFAULT 'N'   CHECK (ind_Imigrante  IN ('S','N')),
    imigrante_tmpResid  CHAR(1)                             CHECK (imigrante_tmpResid IN ('1','2')),
    condIng             CHAR(1)                             CHECK (condIng        IN ('1','2','3','4','5','6','7')),

    -- ---------------------------------------------------------
    -- Deficiência
    -- ---------------------------------------------------------
    defFisica           CHAR(1)      NOT NULL DEFAULT 'N'   CHECK (defFisica      IN ('S','N')),
    defVisual           CHAR(1)      NOT NULL DEFAULT 'N'   CHECK (defVisual      IN ('S','N')),
    defAuditiva         CHAR(1)      NOT NULL DEFAULT 'N'   CHECK (defAuditiva    IN ('S','N')),
    defMental           CHAR(1)      NOT NULL DEFAULT 'N'   CHECK (defMental      IN ('S','N')),
    defIntelectual      CHAR(1)      NOT NULL DEFAULT 'N'   CHECK (defIntelectual IN ('S','N')),
    reabReadap          CHAR(1)      NOT NULL DEFAULT 'N'   CHECK (reabReadap     IN ('S','N')),
    infoCota            CHAR(1)                             CHECK (infoCota       IN ('S','N')),

    -- ---------------------------------------------------------
    -- Menor Aprendiz
    -- ---------------------------------------------------------
    indAprend           CHAR(1)      NOT NULL DEFAULT '0'   CHECK (indAprend      IN ('0','1','2')),
    cnpjEntQual         VARCHAR(14),
    Aprend_tpInsc       CHAR(1)                             CHECK (Aprend_tpInsc  IN ('1','2')),
    Aprend_cnpjPrat     VARCHAR(14),

    -- ---------------------------------------------------------
    -- Auditoria
    -- ---------------------------------------------------------
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Índices
CREATE UNIQUE INDEX idx_tabcad_cpf_empresa    ON tab_CAD (id_Empresa, cpf);
CREATE UNIQUE INDEX idx_tabcad_matricula      ON tab_CAD (id_Empresa, matricula);
CREATE        INDEX idx_tabcad_situacao       ON tab_CAD (id_Empresa, situacao);
CREATE        INDEX idx_tabcad_nome           ON tab_CAD (id_Empresa, nome);
