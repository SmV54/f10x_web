-- tab_usuario — quem entra no sistema.
--
-- Divisao: tab_cliente e o CONTRATO (licenca, limites, data_limite);
-- tab_usuario e a PESSOA que faz login. Um contrato pode ter mais de um
-- usuario (limite atual: 2, ver LIMITE_USUARIOS_CLIENTE no app.py).
--
-- titular = 'S' e o usuario mestre: nasce junto com o cadastro do cliente,
-- e o unico que pode cadastrar/desativar os demais e nunca pode ser desativado.
--
-- ATENCAO: o SQL Editor do Supabase so aceitou o CREATE em UMA LINHA.
-- Rode um comando de cada vez, sem quebrar as linhas.

CREATE TABLE public.tab_usuario (id_usuario bigserial PRIMARY KEY, id_cliente bigint NOT NULL, cpf varchar(11) NOT NULL UNIQUE, nome varchar(80) NOT NULL, senha varchar(6), situacao char(1) NOT NULL DEFAULT 'A', titular char(1) NOT NULL DEFAULT 'N', celular varchar(11), email varchar(120), tentativas_login integer NOT NULL DEFAULT 0, bloqueado_ate timestamptz, datahora_cadastro timestamptz NOT NULL DEFAULT now(), datahora_ultimo_login timestamptz, datahora_ultima_atividade timestamptz);

CREATE INDEX idx_tab_usuario_cliente ON public.tab_usuario (id_cliente);
