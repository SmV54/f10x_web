-- Novo campo: percentual do adiantamento do 13º salário por empresa.
-- Inteiro entre 10 e 90. Empresas já existentes recebem 50 automaticamente.
-- Rodar no SQL Editor do Supabase.
-- OBS: o nome é mixed-case ("perAdianta13"), então SEMPRE use aspas duplas ao referenciá-lo em SQL.

ALTER TABLE tab_empresa
  ADD COLUMN IF NOT EXISTS "perAdianta13" smallint NOT NULL DEFAULT 50;

-- Garante a faixa 10..90 no banco (defesa em profundidade)
ALTER TABLE tab_empresa
  DROP CONSTRAINT IF EXISTS chk_peradianta13;
ALTER TABLE tab_empresa
  ADD CONSTRAINT chk_peradianta13 CHECK ("perAdianta13" BETWEEN 10 AND 90);

-- Confirmação: todas as empresas devem ficar com 50
-- SELECT id_empresa, "perAdianta13" FROM tab_empresa ORDER BY id_empresa;
