-- Grau de risco (RAT) por filial: 1 Minimo, 2 Medio, 3 Grave (0 = Simples substituido).
-- Vazio = usa o risco da empresa (tab_empresa.risco).
ALTER TABLE tab_filial ADD COLUMN IF NOT EXISTS risco smallint;
ALTER TABLE tab_filial DROP CONSTRAINT IF EXISTS tab_filial_risco_chk;
ALTER TABLE tab_filial ADD CONSTRAINT tab_filial_risco_chk CHECK (risco IS NULL OR risco BETWEEN 0 AND 3);

-- Filiais ja cadastradas comecam com o risco da empresa.
UPDATE tab_filial f
   SET risco = NULLIF(TRIM(e.risco::text), '')::smallint
  FROM tab_empresa e
 WHERE e.id_empresa = f.id_empresa
   AND f.risco IS NULL
   AND TRIM(COALESCE(e.risco::text, '')) IN ('0','1','2','3');
