import pyodbc, os, sys, requests, json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Conexão Supabase via requests (sem verificação SSL) ───────────────────────
SUPABASE_URL = "https://yxberbwwchmikvzgbtqh.supabase.co"
SUPABASE_KEY = "sb_publishable_GnMdKsPugq7Ij6tGamjscg_1d6J_Nft"
HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": "Bearer " + SUPABASE_KEY,
    "Content-Type":  "application/json",
    "Prefer":        "return=minimal",
}

def sb_select(tabela, select="*", filtros=None):
    url = f"{SUPABASE_URL}/rest/v1/{tabela}?select={select}"
    if filtros:
        for k, v in filtros.items():
            url += f"&{k}=eq.{v}"
    r = requests.get(url, headers=HEADERS, verify=False)
    r.raise_for_status()
    return r.json()

def sb_insert(tabela, dados):
    url = f"{SUPABASE_URL}/rest/v1/{tabela}"
    r = requests.post(url, headers=HEADERS, json=dados, verify=False)
    if r.status_code not in (200, 201):
        raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
    return True

# ── Conexão Access ────────────────────────────────────────────────────────────
DB  = r'C:\Folha10\ARQUIVOS\BASES\FolhaFIX_000690.ACCDB'
conn = pyodbc.connect(r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + DB)
cur  = conn.cursor()
cur.execute('SELECT * FROM tabverba ORDER BY codigo')
cols = [d[0] for d in cur.description]
rows = [dict(zip(cols, r)) for r in cur.fetchall()]
conn.close()

def s(v):
    return '' if v is None else str(v).strip()

def conv_flag(val):
    v = s(val).upper()
    if v.startswith('NAO') or v.startswith('N\xc3\x83O') or v == '':
        return 'N'
    return 'S'

INI_VALID = 202001

# Filtro: apenas ativas, empresa=0
importar = [r for r in rows if s(r['situacao']) == 'A' and (r['empresa'] or 0) == 0]
print(f"Verbas a importar: {len(importar)}")

# ── Busca verbas já existentes no Supabase (id_cliente=0) ────────────────────
existentes_resp = sb_select("tab_rubrica", "cod_rubr,ini_valid", {"id_cliente": 0})
existentes = set(
    (e["cod_rubr"], e["ini_valid"])
    for e in existentes_resp
)
print(f"Já existentes em tab_rubrica (id_cliente=0): {len(existentes)}")

# ── Importação ────────────────────────────────────────────────────────────────
ok = 0
skip = 0
erro = 0
erros_lista = []

for r in importar:
    cod  = int(s(r['codigo']))
    nom  = s(r['nomec'])[:40]
    res  = s(r['nomer'])[:20]
    sin  = s(r['sinal'])
    uni  = s(r['unidade']) if s(r['unidade']) in ('V','H','D') else 'V'
    inc  = s(r['incidencia'])
    resc = s(r['rescisao'])
    fer  = s(r['ferias'])
    t13  = s(r['13sal'])
    t13a = s(r['13sala'])
    esoc = r['esocial_tab03']  # int ou None

    d_tp  = '1' if sin == '+' else '2'
    d_cp  = inc[0] if len(inc) > 0 else 'N'
    d_fg  = inc[1] if len(inc) > 1 else 'N'
    d_ir  = inc[2] if len(inc) > 2 else 'N'
    d_pi  = inc[3] if len(inc) > 3 else 'N'
    d_rsc = conv_flag(resc)
    d_fer = conv_flag(fer)
    d_13  = conv_flag(t13)
    d_13a = conv_flag(t13a)

    # cod_rubr < 1000 → id_cliente = 0
    id_cli = 0 if cod < 1000 else None  # não há >= 1000 neste conjunto

    # Pula duplicata
    if (cod, INI_VALID) in existentes:
        print(f"  SKIP {cod:04d} {nom} (já existe)")
        skip += 1
        continue

    registro = {
        "id_cliente":         id_cli,
        "situacao":           "A",
        "cod_rubr":           cod,
        "ini_valid":          INI_VALID,
        "dsc_rubr":           nom,
        "dsc_rubr_resumido":  res,
        "tp_rubr":            d_tp,
        "unid_verba":         uni,
        "es03_nat_rubr":      esoc,
        "tpn_inc_cp":         d_cp,
        "tpn_inc_fgts":       d_fg,
        "tpn_inc_irrf":       d_ir,
        "tpn_inc_pis":        d_pi,
        "tpr_inc_cp":         d_cp,
        "tpr_inc_fgts":       d_fg,
        "tpr_inc_irrf":       d_ir,
        "tpr_inc_pis":        d_pi,
        "tpf_inc_cp":         d_cp,
        "tpf_inc_fgts":       d_fg,
        "tpf_inc_irrf":       d_ir,
        "tpf_inc_pis":        d_pi,
        "tp1_inc_cp":         d_cp,
        "tp1_inc_fgts":       d_fg,
        "tp1_inc_irrf":       d_ir,
        "tp1_inc_pis":        d_pi,
        "inc_rescisao":       d_rsc,
        "inc_ferias":         d_fer,
        "inc_13sal":          d_13,
        "inc_adto13":         d_13a,
    }

    try:
        sb_insert("tab_rubrica", registro)
        print(f"  OK   {cod:04d} {nom}")
        ok += 1
    except Exception as e:
        msg = str(e)[:120]
        print(f"  ERRO {cod:04d} {nom} → {msg}")
        erros_lista.append((cod, nom, msg))
        erro += 1

print()
print("=" * 60)
print(f"RESULTADO FINAL:")
print(f"  Gravados : {ok}")
print(f"  Pulados  : {skip}  (já existiam)")
print(f"  Erros    : {erro}")
if erros_lista:
    print()
    print("ERROS DETALHADOS:")
    for cod, nom, msg in erros_lista:
        print(f"  {cod:04d} {nom}: {msg}")
print("=" * 60)
