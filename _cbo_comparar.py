# -*- coding: utf-8 -*-
"""Compara o CBO do PDF com tab_aux_funcao_total. SOMENTE LEITURA - gera relatorio."""
import os, json, io, unicodedata
from dotenv import load_dotenv
load_dotenv()
import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SUPABASE_URL = os.getenv("SUPABASE_URL").rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

# ---------- PDF ----------
with open(r"C:\folha10-simples\_cbo_pdf.json", encoding="utf-8") as f:
    pdfj = json.load(f)
pdf_ocup = pdfj["ocupacoes"]           # cod6 -> nome
print("PDF: ocupacoes =", len(pdf_ocup))

# ---------- BANCO ----------
banco = []
offset = 0
while True:
    url = (f"{SUPABASE_URL}/rest/v1/tab_aux_funcao_total"
           f"?select=id,cbo_codigo,cbo_nome&order=id&limit=1000&offset={offset}")
    r = requests.get(url, headers=H, verify=False, timeout=60)
    ch = r.json()
    banco.extend(ch)
    if len(ch) < 1000:
        break
    offset += 1000
print("BANCO: linhas =", len(banco))

def norm_cod(c):
    return str(c or "").strip().replace("-", "").replace(".", "").zfill(6)

def norm_nome(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("  ", " ")
    return " ".join(s.split())

banco_por_cod = {}
dup = []
for row in banco:
    c = norm_cod(row["cbo_codigo"])
    if c in banco_por_cod:
        dup.append((c, row))
    else:
        banco_por_cod[c] = row

print("BANCO: codigos distintos =", len(banco_por_cod), "| duplicados =", len(dup))
for c, r in dup[:10]:
    print("   dup:", c, r["cbo_nome"])

# tamanho dos codigos gravados
tam = {}
for row in banco:
    tam[len(str(row["cbo_codigo"]).strip())] = tam.get(len(str(row["cbo_codigo"]).strip()), 0) + 1
print("tamanhos de cbo_codigo no banco:", tam)

# ---------- Classificacao militar / publico ----------
def grupo(c):        # grande grupo
    return c[0]
def familia(c):
    return c[:4]

FAM_PUBLICO = {"1111", "1112", "1113", "1114", "1115"}

def eh_militar(c):
    return c.startswith("0")
def eh_publico(c):
    return familia(c) in FAM_PUBLICO

# ---------- Comparacao ----------
faltando, divergentes, iguais = [], [], []
for cod, nome in pdf_ocup.items():
    b = banco_por_cod.get(cod)
    if b is None:
        faltando.append((cod, nome))
    elif norm_nome(b["cbo_nome"]) != norm_nome(nome):
        divergentes.append((cod, b["cbo_nome"], nome, b["id"]))
    else:
        iguais.append(cod)

sobrando = [(c, r["cbo_nome"], r["id"]) for c, r in banco_por_cod.items() if c not in pdf_ocup]

print()
print("=== RESULTADO ===")
print("iguais           :", len(iguais))
print("nome divergente  :", len(divergentes))
print("faltando no banco:", len(faltando))
print("   dos quais militares (grupo 0):", sum(1 for c, n in faltando if eh_militar(c)))
print("   dos quais poder publico (111x):", sum(1 for c, n in faltando if eh_publico(c)))
print("   restantes (para incluir)      :",
      sum(1 for c, n in faltando if not eh_militar(c) and not eh_publico(c)))
print("no banco e NAO no PDF:", len(sobrando))

no_banco_militar = [(c, r["cbo_nome"], r["id"]) for c, r in banco_por_cod.items() if eh_militar(c)]
no_banco_publico = [(c, r["cbo_nome"], r["id"]) for c, r in banco_por_cod.items() if eh_publico(c)]
print("no banco - militares (grupo 0):", len(no_banco_militar))
print("no banco - poder publico (111x):", len(no_banco_publico))

# ---------- Relatorio ----------
out = io.StringIO()
def w(s=""):
    out.write(s + "\n")

w("################ MILITARES NO BANCO (grupo 0) ################")
for c, n, i in sorted(no_banco_militar):
    w(f"{c}  {n}   (id {i})")
w()
w("################ PODER PUBLICO NO BANCO (familias 111x) ################")
for c, n, i in sorted(no_banco_publico):
    w(f"{c}  {n}   (id {i})")
w()
w("################ NOMES DIVERGENTES (banco  ->  PDF) ################")
for c, nb, np_, i in sorted(divergentes):
    w(f"{c}  BANCO: {nb}")
    w(f"        PDF : {np_}   (id {i})")
w()
w("################ FALTANDO NO BANCO (excluindo militar/publico) ################")
for c, n in sorted(faltando):
    if not eh_militar(c) and not eh_publico(c):
        w(f"{c}  {n}")
w()
w("################ FALTANDO - militares/publico (NAO incluir) ################")
for c, n in sorted(faltando):
    if eh_militar(c) or eh_publico(c):
        w(f"{c}  {n}")
w()
w("################ NO BANCO E NAO NO PDF ################")
for c, n, i in sorted(sobrando):
    w(f"{c}  {n}   (id {i})")

with open(r"C:\folha10-simples\_cbo_relatorio.txt", "w", encoding="utf-8") as f:
    f.write(out.getvalue())
print("\ngravado _cbo_relatorio.txt")

json.dump({"faltando": faltando, "divergentes": divergentes, "sobrando": sobrando,
           "militar_banco": no_banco_militar, "publico_banco": no_banco_publico},
          open(r"C:\folha10-simples\_cbo_diff.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
