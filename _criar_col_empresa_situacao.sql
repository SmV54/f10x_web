-- Empresa desativada (13/10/2026)
-- O cliente desativa no Cadastro de Empresa (Alterar Esta Empresa); so' o ADMIN
-- reativa (Lista de Clientes). Desativada: nada se grava nem se calcula (so'
-- consultas e relatorios) e ela nao conta na licenca, nem os funcionarios dela.
--   situacao: 'A' = ativa (padrao), 'D' = desativada
ALTER TABLE tab_empresa ADD COLUMN IF NOT EXISTS situacao       char(1) DEFAULT 'A';
ALTER TABLE tab_empresa ADD COLUMN IF NOT EXISTS dt_desativacao timestamp;
UPDATE tab_empresa SET situacao = 'A' WHERE situacao IS NULL;

NOTIFY pgrst, 'reload schema';
