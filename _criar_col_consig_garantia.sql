-- ---------------------------------------------------------------------------
-- tab_mov: campo da GARANTIA do empréstimo consignado na rescisão
--
-- A importação do empréstimo da rescisão pode rodar ANTES do cálculo. Quando
-- roda, ela ainda não tem como saber o valor do desconto: ele é uma fatia das
-- verbas rescisórias, que só existem depois do cálculo. Então ela grava a
-- verba 700+ no movimento e deixa aqui os dois números que o cálculo vai
-- precisar para apurar o valor.
--
-- Campo char, empacotado, no mesmo estilo do esocial_recibo do Folha10
-- Desktop. Só dígitos, zeros à esquerda:
--
--      1 - 6   percentual da garantia x100    000766 = 7,66%
--      7 - 20  saldo devedor em centavos      00000000123456 = R$ 1.234,56
--
-- Fica NULO na importação mensal (folha_tipo 'N'): lá não existe garantia, o
-- valor da parcela já vem pronto na planilha.
-- Verba 700 com este campo nulo é a lançada com o valor já pronto (ou digitada
-- à mão) — o cálculo não mexe nela.
-- ---------------------------------------------------------------------------

ALTER TABLE tab_mov
    ADD COLUMN IF NOT EXISTS consig_garantia char(20);

COMMENT ON COLUMN tab_mov.consig_garantia IS
    'Consignado da rescisao: 1-6 percentual da garantia x100, 7-20 saldo devedor em centavos. Nulo fora da rescisao.';
