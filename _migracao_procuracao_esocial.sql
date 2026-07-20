-- =====================================================================
-- Procuração eletrônica no eSocial — certificado de TERCEIROS
-- Rodar no Supabase (SQL Editor) quando for ativar a funcionalidade.
-- Enquanto NÃO rodar, o sistema continua 100% no modo "certificado próprio"
-- (a plumbing no app.py já tem fallback compatível).
-- =====================================================================

-- 1) Tabela do procurador (escritório/contador). Um certificado A1 pode ser
--    reutilizado por vários clientes/empresas do mesmo escritório.
CREATE TABLE IF NOT EXISTS tab_procurador (
    id_procurador   BIGSERIAL PRIMARY KEY,
    id_cliente      BIGINT,                 -- dono/escritório (multi-tenant)
    nome            TEXT,                   -- nome do procurador/escritório
    tpinsc          TEXT DEFAULT '1',       -- 1=CNPJ (14) | 2=CPF (11)
    nrinsc          TEXT,                   -- só dígitos (CNPJ/CPF do procurador)
    cert_pfx_b64    TEXT,                   -- .pfx (A1) em base64
    cert_senha_enc  TEXT,                   -- senha do .pfx criptografada (_cert_encrypt)
    cert_titular    TEXT,
    cert_validade   TEXT,                   -- yyyymmdd
    ativo           BOOLEAN DEFAULT TRUE,
    data_grava      TEXT,
    hora_grava      TEXT
);

CREATE INDEX IF NOT EXISTS idx_tab_procurador_cliente ON tab_procurador (id_cliente);

-- 2) tab_empresa: como a empresa transmite ao eSocial.
--    cert_modo = 'proprio'    -> usa o próprio certificado (padrão / atual)
--    cert_modo = 'procuracao' -> usa o certificado do procurador (id_procurador)
ALTER TABLE tab_empresa ADD COLUMN IF NOT EXISTS cert_modo     TEXT DEFAULT 'proprio';
ALTER TABLE tab_empresa ADD COLUMN IF NOT EXISTS id_procurador BIGINT;

-- Garante que empresas já existentes fiquem explicitamente no modo próprio.
UPDATE tab_empresa SET cert_modo = 'proprio' WHERE cert_modo IS NULL;
