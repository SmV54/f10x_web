# tab_total — Mapeamento de Campos

**Referência:** app.py, função `_salvar_memorias_etapa1()`, ~linha 13007  
**Operação de limpeza (DELETE):** ~linha 12119 — antes de recalcular, apaga todos os registros da folha

---

## Campos e origens

| # | Campo | Tipo | De onde vem |
|---|-------|------|-------------|
| 1 | `id_cliente` | int | Sessão do usuário |
| 2 | `id_empresa` | int | Sessão do usuário |
| 3 | `situacao` | char(1) | Fixo: `"A"` |
| 4 | `matricula` | int | Variável `matr` — matrícula do funcionário |
| 5 | `folha` | int | Variável `anomes` convertida para int (YYYYMM) |
| 6 | `folha_tipo` | char(1) | Variável `anomes_tipo` (ex.: `"N"` = Normal) |
| 7 | `valor_base_inss_semLimite` | bigint | `base_inss` — soma das rubricas onde `inc_cp == "11"` |
| 8 | `valor_base_inss_comLimite` | bigint | `base_inss_com` — min(base_inss, teto_inss); se sem teto = base_inss |
| 9 | `valor_inss_retido` | bigint | `inss_val` — resultado de `_calc_inss_progressivo()` |
| 10 | `valor_base_fgts` | bigint | `base_fgts_func` — soma das rubricas onde `inc_fgts == "11"` |
| 11 | `valor_fgts` | bigint | `fgts_func` = `(base_fgts_func * 8) // 100` |
| 12 | `valor_irrf_basetotal` | bigint | `base_irrf_bruta` — soma das rubricas onde `inc_irrf == "11"` |
| 13 | `valor_irrf_basetabela` | bigint | `base_irrf` — base após deduções (método simples ou completo) |
| 14 | `valor_irrf_dependentes` | bigint | `dep_irrf_total` = `qtd_dep * irrf_dep_dedu` |
| 15 | `qtd_irrf_dependentes` | int | `num_dep_irrf` — qtd de dependentes do funcionário |
| 16 | `valor_salario` | bigint | `l.get("sal_base") or 0` — salário base do funcionário |
| 17 | `valor_total_proventos` | bigint | `total_prov` — soma de rubricas com `tp == "1"` |
| 18 | `valor_total_descontos` | bigint | `total_desc` — soma de rubricas com `tp != "1"` |
| 19 | `valor_liquido` | bigint | `total_prov - total_desc` |
| 20 | `os` | int | Fixo: `0` |
| 21 | `controle` | int | Fixo: `0` |

---

## Fluxo resumido

```
tab_mov (rubricas do funcionário)
    → _salvar_memorias_etapa1()
        → agrupa por inc_cp / inc_fgts / inc_irrf / tp
        → calcula INSS progressivo, FGTS, IRRF
        → monta rec_total (21 campos)
        → INSERT INTO tab_total
```

---

## Observações / Perguntas para revisão

- [ ] O campo `situacao` ("A") existe de fato na tabela do Supabase?  
      *(código tem fallback: se der erro, tenta gravar sem esse campo)*
- [ ] O campo `valor_salario` usa `l.get("sal_base")` — confirmar que `l` é o registro do funcionário carregado corretamente antes do INSERT
- [ ] O DELETE antes do recálculo filtra por `id_empresa + folha + folha_tipo` — **não filtra por `id_cliente`**. Isso está correto?
- [ ] Valores estão todos em **centavos** (bigint)? Confirmar antes de depurar divergências de valor
- [ ] `valor_base_inss_comLimite` — qual variável exatamente recebe o min()? Verificar se está sendo gravada com int() 

---

## Trecho do INSERT (app.py ~linha 13007)

```python
rec_total = {
    "id_cliente":                id_cliente,
    "id_empresa":                id_empresa,
    "situacao":                  "A",
    "matricula":                 matr,
    "folha":                     int(anomes),
    "folha_tipo":                anomes_tipo,
    "valor_base_inss_semLimite": int(base_inss),
    "valor_base_inss_comLimite": base_inss_com,
    "valor_inss_retido":         inss_val,
    "valor_base_fgts":           int(base_fgts_func),
    "valor_fgts":                fgts_func,
    "valor_irrf_basetotal":      int(base_irrf_bruta),
    "valor_irrf_basetabela":     int(base_irrf),
    "valor_irrf_dependentes":    dep_irrf_total,
    "qtd_irrf_dependentes":      num_dep_irrf,
    "valor_salario":             int(l.get("sal_base") or 0),
    "valor_total_proventos":     int(total_prov),
    "valor_total_descontos":     int(total_desc),
    "valor_liquido":             int(total_prov - total_desc),
    "os":                        0,
    "controle":                  0,
}
supabase.table("tab_total").insert(rec_total).execute()
```
