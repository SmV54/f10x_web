-- Cadastro de funcionario: celular, e-mail e chave Pix (07/10/2026)
-- celular e email alimentam o grupo <contato> do S-2205 (fonePrinc/emailPrinc).
-- pix guarda so' a chave; se e' o CPF, o celular ou outra, a tela deduz.
ALTER TABLE tab_cad ADD COLUMN IF NOT EXISTS celular varchar(11);
ALTER TABLE tab_cad ADD COLUMN IF NOT EXISTS pix     varchar(30);
ALTER TABLE tab_cad ADD COLUMN IF NOT EXISTS email   varchar(50);

NOTIFY pgrst, 'reload schema';
