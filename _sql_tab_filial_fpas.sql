-- FPAS próprio da filial (pode ser diferente do da empresa).
-- Mesmo tipo do tab_empresa.gps_fpas.
alter table tab_filial add column if not exists gps_fpas char(3);

-- Filiais já cadastradas ficam com o FPAS da empresa delas.
update tab_filial f
   set gps_fpas = e.gps_fpas
  from tab_empresa e
 where e.id_empresa = f.id_empresa
   and f.gps_fpas is null;

select f.id, f.id_empresa, f.filial_nome, f.gps_fpas
  from tab_filial f
 order by f.id_empresa, f.filial_nome;
