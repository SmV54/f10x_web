-- Arredondamento do liquido por empresa (Folha e Ferias) - 19/10/2026
-- Valor do degrau em CENTAVOS: 1000 = arredonda para cima ate o proximo
-- multiplo de R$ 10,00. Zero = nao arredonda. Mesmo desenho do Desktop
-- (valor_arredondar_fol / valor_arredondar_fer).
--
-- A empresa 4 ja arredondava (fixo no codigo, R$ 10,00, so na Folha):
-- o UPDATE passa isso para o cadastro, para ela continuar igual.

alter table public.tab_empresa
    add column if not exists valor_arredondar_fol integer not null default 0,
    add column if not exists valor_arredondar_fer integer not null default 0;

update public.tab_empresa
   set valor_arredondar_fol = 1000
 where id_empresa = 4;

notify pgrst, 'reload schema';

select id_empresa, razaosocial, valor_arredondar_fol, valor_arredondar_fer
  from public.tab_empresa
 where valor_arredondar_fol > 0 or valor_arredondar_fer > 0;
