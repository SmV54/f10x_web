# -*- coding: utf-8 -*-
"""Atualiza tab_aux_funcao_total a partir do PDF cbo2002_lista.pdf (via _cbo_pdf.json).

  1. Backup completo da tabela em arquivo local
  2. Exclui militares (grupo 0) e cargos publicos (lista abaixo)
  3. Corrige cbo_nome divergente pelo titulo oficial da ocupacao
  4. Inclui as ocupacoes que faltam

Uso:  python _cbo_atualizar.py            -> simulacao (nao grava)
      python _cbo_atualizar.py --executar -> grava no Supabase
"""
import os, sys, json, datetime
from dotenv import load_dotenv
load_dotenv()
import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.stdout.reconfigure(encoding="utf-8")

EXECUTAR = "--executar" in sys.argv

U = os.getenv("SUPABASE_URL").rstrip("/")
K = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
H = {"apikey": K, "Authorization": f"Bearer {K}", "Content-Type": "application/json"}
TAB = "tab_aux_funcao_total"

# ---------------------------------------------------------------
# Regra de exclusao: militares + cargos publicos (proposta ampla)
# ---------------------------------------------------------------
FAM_EXCLUIDAS = {
    "1111",  # legisladores
    "1112",  # dirigentes gerais da administracao publica
    "1113",  # magistrados
    "1114",  # dirigentes do servico publico
    "1115",  # gestores publicos
    "2412",  # advogado da uniao / procuradores publicos
    "2422",  # ministerio publico
    "2423",  # delegados de policia
    "2424",  # defensores publicos
    "2544",  # fiscais de tributos estaduais e municipais
    "2545",  # fiscais de atividades urbanas
}
COD_EXCLUIDOS = {
    "517205",  # agente de policia federal
    "517210",  # policial rodoviario federal
    "517215",  # guarda-civil municipal
    "517220",  # agente de transito
    "517225",  # policial legislativo
    "517230",  # policial penal
}

def excluir(cod):
    """True = militar ou cargo publico (nao entra na tabela)."""
    return cod.startswith("0") or cod[:4] in FAM_EXCLUIDAS or cod in COD_EXCLUIDOS

def norm_cod(c):
    return str(c or "").strip().replace("-", "").replace(".", "").zfill(6)

# ---------------------------------------------------------------
# Carrega PDF e banco
# ---------------------------------------------------------------
pdf_ocup = json.load(open(r"C:\folha10-simples\_cbo_pdf.json", encoding="utf-8"))["ocupacoes"]

banco, off = [], 0
while True:
    r = requests.get(f"{U}/rest/v1/{TAB}?select=*&order=id&limit=1000&offset={off}",
                     headers=H, verify=False, timeout=60)
    r.raise_for_status()
    ch = r.json()
    banco += ch
    if len(ch) < 1000:
        break
    off += 1000

print(f"PDF: {len(pdf_ocup)} ocupacoes | BANCO: {len(banco)} linhas")

# ---------------------------------------------------------------
# 1. BACKUP
# ---------------------------------------------------------------
carimbo = datetime.datetime.now().strftime("%Y%m%d-%H%M")
bkp = rf"C:\folha10-simples\_bkp_tab_aux_funcao_total_{carimbo}.json"
with open(bkp, "w", encoding="utf-8") as f:
    json.dump(banco, f, ensure_ascii=False, indent=1)
print("backup gravado:", bkp)

# ---------------------------------------------------------------
# 2/3/4. Monta as operacoes
# ---------------------------------------------------------------
ids_excluir, updates = [], []
por_cod = {}
for row in banco:
    cod = norm_cod(row["cbo_codigo"])
    por_cod[cod] = row
    if excluir(cod):
        ids_excluir.append(row["id"])
        continue
    oficial = pdf_ocup.get(cod)
    if oficial and oficial != (row.get("cbo_nome") or ""):
        updates.append({"id": row["id"], "cbo_codigo": cod, "cbo_nome": oficial})
    elif oficial is None:
        print("  [aviso] no banco e nao no PDF:", cod, row.get("cbo_nome"))

inserts = [{"cbo_codigo": c, "cbo_nome": n}
           for c, n in sorted(pdf_ocup.items())
           if c not in por_cod and not excluir(c)]

print()
print("EXCLUIR :", len(ids_excluir))
print("ALTERAR :", len(updates))
print("INCLUIR :", len(inserts))
print("TOTAL FINAL PREVISTO:", len(banco) - len(ids_excluir) + len(inserts))

if not EXECUTAR:
    print("\n*** SIMULACAO — nada foi gravado. Rode com --executar ***")
    for u in updates[:5]:
        print("   alterar:", u["cbo_codigo"], "->", u["cbo_nome"])
    for i in inserts[:5]:
        print("   incluir:", i["cbo_codigo"], i["cbo_nome"])
    sys.exit(0)

# ---------------------------------------------------------------
# GRAVACAO
# ---------------------------------------------------------------
def lotes(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]

# --- exclusoes ---
for lote in lotes(ids_excluir, 100):
    lista = ",".join(str(i) for i in lote)
    r = requests.delete(f"{U}/rest/v1/{TAB}?id=in.({lista})", headers=H, verify=False, timeout=60)
    if r.status_code >= 300:
        print("ERRO delete:", r.status_code, r.text[:300]); sys.exit(1)
print("excluidos:", len(ids_excluir))

# --- alteracoes (upsert por id) ---
Hup = {**H, "Prefer": "resolution=merge-duplicates,return=minimal"}
feito = 0
for lote in lotes(updates, 200):
    r = requests.post(f"{U}/rest/v1/{TAB}?on_conflict=id", headers=Hup,
                      data=json.dumps(lote, ensure_ascii=False).encode("utf-8"),
                      verify=False, timeout=90)
    if r.status_code >= 300:
        print("ERRO update:", r.status_code, r.text[:300]); sys.exit(1)
    feito += len(lote)
    print(f"  alteradas {feito}/{len(updates)}")

# --- inclusoes ---
Hin = {**H, "Prefer": "return=minimal"}
feito = 0
for lote in lotes(inserts, 200):
    r = requests.post(f"{U}/rest/v1/{TAB}", headers=Hin,
                      data=json.dumps(lote, ensure_ascii=False).encode("utf-8"),
                      verify=False, timeout=90)
    if r.status_code >= 300:
        print("ERRO insert:", r.status_code, r.text[:300]); sys.exit(1)
    feito += len(lote)
    print(f"  incluidas {feito}/{len(inserts)}")

# --- conferencia final ---
r = requests.get(f"{U}/rest/v1/{TAB}?select=id",
                 headers={**H, "Prefer": "count=exact", "Range": "0-0"},
                 verify=False, timeout=30)
print("\nTOTAL NA TABELA AGORA:", r.headers.get("Content-Range"))
