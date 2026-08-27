-- tab_mov_fixo — "Parar" um movimento em modo parcelas batia na trava antiga.
--
-- A trava original proibia qtd_parcelas junto com folha_inicial OU folha_final.
-- So que folha_final nao e' vigencia: e' o marcador de encerramento gravado pelo
-- botao "Parar", e vale para os dois modos. O que continua sendo exclusivo e' o
-- inicio da vigencia (folha_inicial) contra o modo parcelas.
ALTER TABLE tab_mov_fixo DROP CONSTRAINT IF EXISTS chk_parcelas_ou_periodo;

ALTER TABLE tab_mov_fixo ADD CONSTRAINT chk_parcelas_ou_periodo CHECK (
    NOT (qtd_parcelas IS NOT NULL AND folha_inicial IS NOT NULL)
);

COMMENT ON CONSTRAINT chk_parcelas_ou_periodo ON tab_mov_fixo IS
    'Modo parcelas (qtd_parcelas) e modo periodo (folha_inicial) sao exclusivos. '
    'folha_final e permitida nos dois: e o encerramento gravado pelo botao Parar.';
