"""
Atribui aleatoriamente às CBOs dos funcionários de teste (id_empresa=3)
apenas CBOs que existem em tab_funcao_cli para o cliente (id_cliente=4).
"""
import requests
import random

URL = 'https://yxberbwwchmikvzgbtqh.supabase.co'
KEY = 'sb_publishable_GnMdKsPugq7Ij6tGamjscg_1d6J_Nft'
HEADERS = {
    'apikey':         KEY,
    'Authorization':  'Bearer ' + KEY,
    'Content-Type':   'application/json',
    'Prefer':         'return=minimal',
}

ID_CLIENTE_CPF = '15313921487'   # CPF do cliente (tab_funcao_cli.idcliente)
ID_CLIENTE_INT = 4               # id_cliente numérico (tab_cad.id_cliente)
ID_EMPRESA     = 3


def get(table, params):
    r = requests.get(f'{URL}/rest/v1/{table}', headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()


def patch(table, params, data):
    r = requests.patch(f'{URL}/rest/v1/{table}', headers=HEADERS, params=params, json=data)
    r.raise_for_status()


# ── 1. Busca CBOs válidas em tab_funcao_cli ──────────────────────────────────
rows_cli = get('tab_funcao_cli', {
    'idcliente': f'eq.{ID_CLIENTE_CPF}',
    'situacao':  'eq.A',
    'select':    'cbo_codigo,idfuncao_total',
})

cbos = [r['cbo_codigo'] for r in rows_cli if r.get('cbo_codigo')]

# Fallback: se cbo_codigo ainda não foi preenchido, busca via tab_aux_funcao_total
if not cbos:
    print('cbo_codigo vazio em tab_funcao_cli — buscando via tab_aux_funcao_total...')
    ids = [r['idfuncao_total'] for r in rows_cli if r.get('idfuncao_total')]
    if ids:
        ids_str = ','.join(str(i) for i in ids)
        rows_total = get('tab_aux_funcao_total', {
            'id':     f'in.({ids_str})',
            'select': 'cbo_codigo',
        })
        cbos = [r['cbo_codigo'] for r in rows_total if r.get('cbo_codigo')]

if not cbos:
    print('ERRO: nenhuma CBO encontrada para o cliente CPF', ID_CLIENTE_CPF)
    raise SystemExit(1)

print(f'CBOs disponíveis ({len(cbos)}): {sorted(cbos)}')

# ── 2. Busca funcionários de teste ───────────────────────────────────────────
funcs = get('tab_cad', {
    'id_cliente': f'eq.{ID_CLIENTE_INT}',
    'id_empresa': f'eq.{ID_EMPRESA}',
    'select':     'id,matricula,cbofuncao',
    'order':      'matricula',
})
print(f'Funcionários encontrados: {len(funcs)}\n')

# ── 3. Distribui ciclicamente (embaralhado) e atualiza ───────────────────────
cbos_sorted = sorted(cbos)
random.seed(42)
random.shuffle(cbos_sorted)

for i, f in enumerate(funcs):
    cbo_novo  = cbos_sorted[i % len(cbos_sorted)]
    cbo_velho = f.get('cbofuncao') or '—'
    patch('tab_cad', {'id': f'eq.{f["id"]}'}, {'cbofuncao': cbo_novo})
    print(f'  mat {str(f["matricula"]).zfill(6)}  {cbo_velho:>10} → {cbo_novo}')

print('\nConcluído!')
