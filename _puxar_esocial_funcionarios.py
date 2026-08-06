"""
TESTE — SO LEITURA. Puxa os funcionarios do eSocial (webservices de consulta
de identificadores + download cirurgico) e joga numa planilha .xlsx.

NAO envia nada ao eSocial e NAO grava nada na nossa base:
  - eSocial: so ConsultarIdentificadoresEventos* e SolicitarDownloadEventos*
  - Supabase: so GET (tab_empresa para pegar o certificado, tab_cad para a
    lista de CPFs semente)

Uso:  python _puxar_esocial_funcionarios.py [CNPJ] [tpAmb]
      CNPJ  default 08777252000133 (FOLHA10 - COMSIST)
      tpAmb 1=Producao (default) / 2=Producao Restrita
"""
import os, re, sys, base64, hashlib, datetime, tempfile
import requests, urllib3
from dotenv import load_dotenv
from lxml import etree

urllib3.disable_warnings()
load_dotenv(r"C:\folha10-simples\.env")

CNPJ_EMP = re.sub(r"\D", "", sys.argv[1] if len(sys.argv) > 1 else "08777252000133")
TP_AMB   = sys.argv[2] if len(sys.argv) > 2 else "1"

SUPA_URL = os.getenv("SUPABASE_URL").rstrip("/")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
H_SUPA   = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}

OUT_DIR = r"C:\folha10-simples\__teste_esocial"
XML_DIR = os.path.join(OUT_DIR, "xml_brutos")

# ── endpoints (copiados do app.py) ────────────────────────────────────────
BASE_DWN   = "https://webservices.download.esocial.gov.br"
BASE_HOMOL = "https://webservices.producaorestrita.esocial.gov.br"
P_CONS_IDE = "/servicos/empregador/dwlcirurgico/WsConsultarIdentificadoresEventos.svc"
P_DOWNLOAD = "/servicos/empregador/dwlcirurgico/WsSolicitarDownloadEventos.svc"

NS_SOAP     = "http://schemas.xmlsoap.org/soap/envelope/"
NS_CIE_TRAB = "http://www.esocial.gov.br/servicos/empregador/consulta/identificadores-eventos/trabalhador/v1_0_0"
NS_CIE_EMP  = "http://www.esocial.gov.br/servicos/empregador/consulta/identificadores-eventos/empregador/v1_0_0"
NS_CIE_TAB  = "http://www.esocial.gov.br/servicos/empregador/consulta/identificadores-eventos/v1_0_0"
NS_DWN      = "http://www.esocial.gov.br/servicos/empregador/download/solicitacao/v1_0_0"

SA_CIE_TRAB = NS_CIE_TRAB + "/ServicoConsultarIdentificadoresEventos/ConsultarIdentificadoresEventosTrabalhador"
SA_CIE_EMP  = NS_CIE_EMP  + "/ServicoConsultarIdentificadoresEventos/ConsultarIdentificadoresEventosEmpregador"
SA_CIE_TAB  = NS_CIE_TAB  + "/ServicoConsultarIdentificadoresEventos/ConsultarIdentificadoresEventosTabela"
SA_DWN      = NS_DWN      + "/ServicoSolicitarDownloadEventos/SolicitarDownloadEventosPorId"


def soap_ide_trab(raiz, cpf, dt_ini, dt_fim, tp_evt=""):
    tp = f"<tpEvt>{tp_evt}</tpEvt>" if tp_evt else ""
    body = (f'<eSocial xmlns="http://www.esocial.gov.br/schema/consulta/identificadores-eventos/trabalhador/v1_0_0">'
            f"<consultaIdentificadoresEvts>"
            f"<ideEmpregador><tpInsc>1</tpInsc><nrInsc>{raiz}</nrInsc></ideEmpregador>"
            f"<consultaEvtsTrabalhador><cpfTrab>{cpf}</cpfTrab>"
            f"<dtIni>{dt_ini}</dtIni><dtFim>{dt_fim}</dtFim>{tp}"
            f"</consultaEvtsTrabalhador></consultaIdentificadoresEvts></eSocial>")
    body = assinar(body, PFX, SENHA)
    return (f'<soapenv:Envelope xmlns:soapenv="{NS_SOAP}" xmlns:ser="{NS_CIE_TRAB}">'
            f"<soapenv:Header/><soapenv:Body>"
            f"<ser:ConsultarIdentificadoresEventosTrabalhador><ser:consulta>{body}"
            f"</ser:consulta></ser:ConsultarIdentificadoresEventosTrabalhador>"
            f"</soapenv:Body></soapenv:Envelope>")


def soap_ide_emp(raiz, tp_evt, per_apur):
    body = (f'<eSocial xmlns="http://www.esocial.gov.br/schema/consulta/identificadores-eventos/empregador/v1_0_0">'
            f"<consultaIdentificadoresEvts>"
            f"<ideEmpregador><tpInsc>1</tpInsc><nrInsc>{raiz}</nrInsc></ideEmpregador>"
            f"<consultaEvtsEmpregador><tpEvt>{tp_evt}</tpEvt><perApur>{per_apur}</perApur>"
            f"</consultaEvtsEmpregador></consultaIdentificadoresEvts></eSocial>")
    body = assinar(body, PFX, SENHA)
    return (f'<soapenv:Envelope xmlns:soapenv="{NS_SOAP}" xmlns:ser="{NS_CIE_EMP}">'
            f"<soapenv:Header/><soapenv:Body>"
            f"<ser:ConsultarIdentificadoresEventosEmpregador><ser:consulta>{body}"
            f"</ser:consulta></ser:ConsultarIdentificadoresEventosEmpregador>"
            f"</soapenv:Body></soapenv:Envelope>")


def soap_ide_tab(raiz, tp_evt):
    body = (f'<eSocial xmlns="http://www.esocial.gov.br/schema/consulta/identificadores-eventos/tabela/v1_0_0">'
            f"<consultaIdentificadoresEvts>"
            f"<ideEmpregador><tpInsc>1</tpInsc><nrInsc>{raiz}</nrInsc></ideEmpregador>"
            f"<consultaEvtsTabela><tpEvt>{tp_evt}</tpEvt></consultaEvtsTabela>"
            f"</consultaIdentificadoresEvts></eSocial>")
    body = assinar(body, PFX, SENHA)
    return (f'<soapenv:Envelope xmlns:soapenv="{NS_SOAP}" xmlns:v1="{NS_CIE_TAB}">'
            f"<soapenv:Header/><soapenv:Body>"
            f"<v1:ConsultarIdentificadoresEventosTabela><v1:consultaEventosTabela>{body}"
            f"</v1:consultaEventosTabela></v1:ConsultarIdentificadoresEventosTabela>"
            f"</soapenv:Body></soapenv:Envelope>")


def soap_download(raiz, ids):
    ids_xml = "".join(f"<id>{i}</id>" for i in ids[:40])
    body = (f'<eSocial xmlns="http://www.esocial.gov.br/schema/download/solicitacao/v1_0_0">'
            f"<download><ideEmpregador><tpInsc>1</tpInsc><nrInsc>{raiz}</nrInsc></ideEmpregador>"
            f"<solicDownloadEvtsPorId>{ids_xml}</solicDownloadEvtsPorId></download></eSocial>")
    body = assinar(body, PFX, SENHA)
    return (f'<soapenv:Envelope xmlns:soapenv="{NS_SOAP}" xmlns:ser="{NS_DWN}">'
            f"<soapenv:Header/><soapenv:Body>"
            f"<ser:SolicitarDownloadEventosPorId><ser:solicitacao>{body}"
            f"</ser:solicitacao></ser:SolicitarDownloadEventosPorId>"
            f"</soapenv:Body></soapenv:Envelope>")


def assinar(xml_str, pfx_bytes, senha):
    """XMLDSig enveloped com URI="" — o eSocial EXIGE a consulta assinada
    (sem isso responde 417 'incomplete content ... expected Signature')."""
    from signxml import XMLSigner, methods
    from copy import deepcopy
    from cryptography.hazmat.primitives import hashes as _h
    from cryptography.hazmat.primitives.asymmetric import padding as _p
    from cryptography.hazmat.primitives.serialization import (
        pkcs12, Encoding, PrivateFormat, NoEncryption)
    pk, cert, _ = pkcs12.load_key_and_certificates(
        pfx_bytes, senha.encode() if isinstance(senha, str) else senha)
    key_pem  = pk.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    cert_pem = cert.public_bytes(Encoding.PEM)
    root = etree.fromstring(xml_str.encode("utf-8"))
    filho = root[0]
    tirar_id = not filho.get("Id")
    if tirar_id:
        filho.set("Id", "ID1")
    signer = XMLSigner(method=methods.enveloped, signature_algorithm="rsa-sha256",
                       digest_algorithm="sha256",
                       c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
    signed = signer.sign(root, key=key_pem, cert=cert_pem, reference_uri=f"#{filho.get('Id')}")
    NS_DS = "http://www.w3.org/2000/09/xmldsig#"
    ref = signed.find(f".//{{{NS_DS}}}Reference")
    ref.set("URI", "")
    if tirar_id:
        for ch in signed:
            if lname(ch) != "Signature" and ch.get("Id") == "ID1":
                del ch.attrib["Id"]
    sem = deepcopy(signed)
    s = sem.find(f"{{{NS_DS}}}Signature")
    if s is not None:
        sem.remove(s)
    ref.find(f"{{{NS_DS}}}DigestValue").text = base64.b64encode(
        hashlib.sha256(etree.tostring(sem, method="c14n")).digest()).decode()
    si = signed.find(f".//{{{NS_DS}}}SignedInfo")
    signed.find(f".//{{{NS_DS}}}SignatureValue").text = base64.b64encode(
        pk.sign(etree.tostring(si, method="c14n"), _p.PKCS1v15(), _h.SHA256())).decode()
    return etree.tostring(signed, encoding="unicode", xml_declaration=False)


def http_post_cert(url, soap, pfx_bytes, senha, soap_action=""):
    from cryptography.hazmat.primitives.serialization import (
        pkcs12, Encoding, PrivateFormat, NoEncryption)
    pk, cert, _ = pkcs12.load_key_and_certificates(
        pfx_bytes, senha.encode() if isinstance(senha, str) else senha)
    kf = tempfile.NamedTemporaryFile(delete=False, suffix=".key.pem")
    cf = tempfile.NamedTemporaryFile(delete=False, suffix=".cert.pem")
    try:
        kf.write(pk.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())); kf.close()
        cf.write(cert.public_bytes(Encoding.PEM)); cf.close()
        resp = requests.post(url, data=soap.encode("utf-8"),
                             headers={"Content-Type": "text/xml;charset=UTF-8",
                                      "SOAPAction": f'"{soap_action}"'},
                             cert=(cf.name, kf.name), verify=False, timeout=90)
        if resp.status_code != 200 or not (resp.text or "").strip():
            raise Exception(f"HTTP {resp.status_code}: {(resp.text or '')[:400]}")
        return resp.text
    finally:
        os.unlink(kf.name); os.unlink(cf.name)


def lname(el):
    return el.tag.split("}")[-1] if isinstance(el.tag, str) else ""


def parse_ide(xml_resp):
    out = {"ok": False, "cd": "", "desc": "", "ids": [], "erro": ""}
    try:
        root = etree.fromstring(xml_resp.encode("utf-8", errors="replace"))
    except Exception as e:
        out["erro"] = f"XML invalido: {e}"; return out
    for el in root.iter():
        if lname(el) == "faultstring":
            out["erro"] = f"SOAP Fault: {(el.text or '').strip()}"; return out
    for el in root.iter():
        t, txt = lname(el), (el.text or "").strip()
        if t == "cdResposta":   out["cd"] = txt
        elif t == "descResposta": out["desc"] = txt
    for el in root.iter():
        if lname(el) != "ideEvento":
            continue
        item = {"id": "", "tpEvt": "", "nrRecEvt": "", "perApur": ""}
        for c in el:
            t, txt = lname(c), (c.text or "").strip()
            if t in item: item[t] = txt
        if item["id"]:
            out["ids"].append(item)
    out["ok"] = out["cd"].startswith("2") if out["cd"] else bool(out["ids"])
    return out


def parse_dwn(xml_resp):
    out = {"ok": False, "cd": "", "desc": "", "eventos": [], "erro": ""}
    try:
        root = etree.fromstring(xml_resp.encode("utf-8", errors="replace"))
    except Exception as e:
        out["erro"] = f"XML invalido: {e}"; return out
    for el in root.iter():
        if lname(el) == "faultstring":
            out["erro"] = f"SOAP Fault: {(el.text or '').strip()}"; return out
    for el in root.iter():
        t, txt = lname(el), (el.text or "").strip()
        if t == "cdResposta":   out["cd"] = txt
        elif t == "descResposta": out["desc"] = txt
    for el in root.iter():
        if lname(el) != "evento":
            continue
        evt_id, inner = el.get("Id") or el.get("id") or "", ""
        for c in el:
            if isinstance(c.tag, str):
                inner = etree.tostring(c, encoding="unicode"); break
        if inner:
            out["eventos"].append({"id": evt_id, "xml": inner})
    out["ok"] = out["cd"].startswith("2") if out["cd"] else bool(out["eventos"])
    return out


# ── 1. Empresa + certificado (leitura no Supabase) ────────────────────────
print("=" * 72)
print(f"TESTE eSocial — CNPJ {CNPJ_EMP} — ambiente {'Producao' if TP_AMB=='1' else 'Producao Restrita'}")
print("=" * 72)

r = requests.get(f"{SUPA_URL}/rest/v1/tab_empresa",
                 params={"select": "*", "cnpj": f"eq.{CNPJ_EMP}"},
                 headers=H_SUPA, verify=False, timeout=30)
emp = (r.json() or [None])[0]
if not emp:
    print("!! Empresa nao encontrada em tab_empresa"); sys.exit(1)
print(f"Empresa: {emp.get('razaosocial') or emp.get('nome_fantasia')} (id_empresa={emp.get('id_empresa')})")

def cert_decrypt(token):
    from cryptography.fernet import Fernet
    raw = (os.getenv("FLASK_SECRET_KEY", "F10default") + "_cert_v1").encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw).digest())).decrypt(token.encode()).decode()

try:
    PFX   = base64.b64decode(emp["cert_pfx_b64"])
    SENHA = cert_decrypt(emp["cert_senha_enc"])
except Exception as e:
    print(f"!! Nao consegui abrir o certificado: {e}")
    print("   (a senha so descriptografa no ambiente onde o .pfx foi gravado)")
    sys.exit(1)

from cryptography.hazmat.primitives.serialization import pkcs12
_pk, _c, _ = pkcs12.load_key_and_certificates(PFX, SENHA.encode())
print(f"Certificado OK — titular: {_c.subject.rfc4514_string()[:70]}")
print(f"                 validade ate: {_c.not_valid_after_utc.strftime('%d/%m/%Y')}")

RAIZ = CNPJ_EMP[:8]
BASE = BASE_DWN if TP_AMB == "1" else BASE_HOMOL
URL_IDE, URL_DWN = BASE + P_CONS_IDE, BASE + P_DOWNLOAD
os.makedirs(XML_DIR, exist_ok=True)

diag = []   # linhas da aba Diagnostico

# ── 2. TESTE A — conectividade (evento de tabela S-1000, nao precisa CPF) ──
print("\n[A] Consulta de identificadores — S-1000 (tabela)")
BLOQUEADO = False
try:
    p = parse_ide(http_post_cert(URL_IDE, soap_ide_tab(RAIZ, "S-1000"), PFX, SENHA, SA_CIE_TAB))
    print(f"    cd={p['cd']} {p['desc'][:110]} | eventos: {len(p['ids'])} | erro: {p['erro'][:120]}")
    diag.append(["A", "S-1000 (tabela)", "-", p["cd"], p["desc"], len(p["ids"]), p["erro"]])
    if p["cd"] == "403" or "entre os dias 1 e 7" in (p["desc"] or ""):
        BLOQUEADO = True
except Exception as e:
    print(f"    !! {str(e)[:300]}")
    diag.append(["A", "S-1000 (tabela)", "-", "", "", 0, str(e)[:300]])
    if "HTTP 500" in str(e):
        # Producao devolve 500 com corpo vazio no lugar da mensagem amigavel.
        # A Producao Restrita, com a MESMA requisicao, responde cd=403
        # "Nao e possivel enviar solicitacao de download entre os dias 1 e 7 do mes".
        BLOQUEADO = True
        diag.append(["A", "diagnostico", "-", "500",
                     "Producao devolveu 500 vazio; restrita responde cd=403 (janela dia 1-7)",
                     0, ""])

if BLOQUEADO:
    print("\n    >>> O eSocial bloqueia solicitacoes de download entre os dias 1 e 7 do mes.")
    print("    >>> Nada a puxar hoje; rode de novo a partir do dia 8.")

# ── 3. TESTE B — dá para listar trabalhador SEM CPF? ──────────────────────
hoje = datetime.date.today()
per_ini = (hoje.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
print(f"\n[B] Consulta do EMPREGADOR (sem CPF) — perApur {per_ini}")
cpfs_sem_semente = set()
for tp in (() if BLOQUEADO else ("S-5011", "S-5012", "S-5013", "S-1299")):
    try:
        resp = http_post_cert(URL_IDE, soap_ide_emp(RAIZ, tp, per_ini), PFX, SENHA, SA_CIE_EMP)
        p = parse_ide(resp)
        print(f"    {tp}: cd={p['cd']} | eventos: {len(p['ids'])} | {p['desc'][:70]}{p['erro'][:90]}")
        diag.append(["B", tp, per_ini, p["cd"], p["desc"], len(p["ids"]), p["erro"]])
        if p["ids"]:
            d = parse_dwn(http_post_cert(URL_DWN, soap_download(RAIZ, [i["id"] for i in p["ids"]]),
                                         PFX, SENHA, SA_DWN))
            for ev in d["eventos"]:
                with open(os.path.join(XML_DIR, f"{tp}_{ev['id'][:40]}.xml"), "w", encoding="utf-8") as f:
                    f.write(ev["xml"])
                for m in re.findall(r"<cpfTrab>(\d{11})</cpfTrab>", ev["xml"]):
                    cpfs_sem_semente.add(m)
            print(f"       -> baixados {len(d['eventos'])} evento(s); CPFs achados dentro: {len(cpfs_sem_semente)}")
    except Exception as e:
        print(f"    {tp}: !! {str(e)[:200]}")
        diag.append(["B", tp, per_ini, "", "", 0, str(e)[:300]])
diag.append(["B", "TOTAL CPFs sem semente", per_ini, "", "", len(cpfs_sem_semente),
             ",".join(sorted(cpfs_sem_semente))[:400]])

# ── 4. Semente de CPFs (leitura da nossa base) ────────────────────────────
r = requests.get(f"{SUPA_URL}/rest/v1/tab_cad",
                 params={"select": "cpf,nome,matricula,situacao",
                         "id_empresa": f"eq.{emp['id_empresa']}", "limit": "500"},
                 headers=H_SUPA, verify=False, timeout=30)
base_rows = r.json() if r.status_code == 200 else []
cpfs_base = {re.sub(r"\D", "", c.get("cpf") or "") for c in base_rows}
cpfs_base = {c for c in cpfs_base if len(c) == 11}
CPFS = sorted(cpfs_sem_semente | cpfs_base)
print(f"\n[C] Semente: {len(cpfs_base)} CPF(s) da nossa base + {len(cpfs_sem_semente)} do eSocial"
      f" = {len(CPFS)} a consultar")

# ── 5. Consulta + download dos eventos de cada trabalhador ────────────────
DT_INI, DT_FIM = "2019-01-01", hoje.strftime("%Y-%m-%d")
TP_TRAB = ("S-2200", "S-2205", "S-2206", "S-2230", "S-2299", "S-2300", "S-2399")

eventos_todos, xml_por_id = [], {}
for cpf in ([] if BLOQUEADO else CPFS):
    achados = []
    for tp in TP_TRAB:
        try:
            p = parse_ide(http_post_cert(URL_IDE, soap_ide_trab(RAIZ, cpf, DT_INI, DT_FIM, tp),
                                         PFX, SENHA, SA_CIE_TRAB))
            if p["erro"]:
                diag.append(["C", tp, cpf, "", "", 0, p["erro"][:200]])
                continue
            for it in p["ids"]:
                it["cpf"], it["tpEvtCons"] = cpf, tp
                achados.append(it)
        except Exception as e:
            diag.append(["C", tp, cpf, "", "", 0, str(e)[:200]])
    eventos_todos.extend(achados)
    print(f"    {cpf}: {len(achados)} evento(s)")
    ids = [a["id"] for a in achados]
    for i in range(0, len(ids), 40):
        try:
            d = parse_dwn(http_post_cert(URL_DWN, soap_download(RAIZ, ids[i:i+40]), PFX, SENHA, SA_DWN))
            if d["erro"]:
                diag.append(["D", "download", cpf, "", "", 0, d["erro"][:200]]); continue
            for ev in d["eventos"]:
                xml_por_id[ev["id"]] = ev["xml"]
                with open(os.path.join(XML_DIR, f"{cpf}_{ev['id'][:45]}.xml"), "w", encoding="utf-8") as f:
                    f.write(ev["xml"])
        except Exception as e:
            diag.append(["D", "download", cpf, "", "", 0, str(e)[:200]])

print(f"\n    Total de eventos localizados: {len(eventos_todos)} | XMLs baixados: {len(xml_por_id)}")

# ── 6. Monta a planilha ───────────────────────────────────────────────────
def txt(root, tag):
    for el in root.iter():
        if lname(el) == tag and (el.text or "").strip():
            return (el.text or "").strip()
    return ""

func = {}   # cpf -> dict
for ev_id, xml in xml_por_id.items():
    try:
        root = etree.fromstring(xml.encode("utf-8"))
    except Exception:
        continue
    tipo = ""
    for el in root.iter():
        if lname(el).startswith("evt"):
            tipo = lname(el); break
    cpf = txt(root, "cpfTrab") or txt(root, "cpfBenef")
    if not cpf:
        continue
    f = func.setdefault(cpf, {"cpf": cpf})
    if tipo in ("evtAdmissao", "evtTSVInicio", "evtCadInicial"):
        f.update({
            "nome":      txt(root, "nmTrab"),
            "nascto":    txt(root, "dtNascto"),
            "sexo":      txt(root, "sexo"),
            "matricula": txt(root, "matricula"),
            "admissao":  txt(root, "dtAdm") or txt(root, "dtInicio"),
            "categoria": txt(root, "codCateg"),
            "cargo":     txt(root, "nmCargo"),
            "cbo":       txt(root, "CBOCargo") or txt(root, "codCBO"),
            "salario":   txt(root, "vrSalFx"),
            "und_sal":   txt(root, "undSalFixo"),
            "tp_contr":  txt(root, "tpContr"),
            "hrs_sem":   txt(root, "qtdHrsSem"),
            "tp_reg_trab": txt(root, "tpRegTrab"),
            "sind_cnpj": txt(root, "cnpjSindCategProf"),
            "cep":       txt(root, "cep"),
            "municipio": txt(root, "codMunic"),
            "uf":        txt(root, "uf"),
            "evento":    tipo,
        })
    elif tipo in ("evtAltContratual", "evtAltCadastral"):
        for k, tag in (("salario_alt", "vrSalFx"), ("cargo_alt", "nmCargo"),
                       ("cbo_alt", "CBOCargo"), ("dt_alt", "dtAlteracao")):
            v = txt(root, tag)
            if v: f[k] = v
        f.setdefault("nome", txt(root, "nmTrab"))
    elif tipo in ("evtDeslig", "evtTSVTermino"):
        f["desligamento"] = txt(root, "dtDeslig") or txt(root, "dtTerm")
        f["mtv_deslig"]   = txt(root, "mtvDeslig")

COLS = [("cpf", "CPF"), ("nome", "Nome"), ("nascto", "Nascimento"), ("sexo", "Sexo"),
        ("matricula", "Matricula"), ("admissao", "Admissao"), ("categoria", "Categoria"),
        ("cargo", "Cargo"), ("cbo", "CBO"), ("salario", "Salario"), ("und_sal", "Und.Sal"),
        ("tp_contr", "Tp.Contrato"), ("hrs_sem", "Hrs/Sem"), ("tp_reg_trab", "Reg.Trab"),
        ("sind_cnpj", "CNPJ Sindicato"), ("cep", "CEP"), ("municipio", "Cod.Munic"), ("uf", "UF"),
        ("cargo_alt", "Cargo (S-2206)"), ("salario_alt", "Salario (S-2206)"), ("dt_alt", "Dt.Alteracao"),
        ("desligamento", "Desligamento"), ("mtv_deslig", "Mtv.Deslig"), ("evento", "Origem")]

import openpyxl
from openpyxl.styles import Font, PatternFill
wb = openpyxl.Workbook()

ws = wb.active; ws.title = "Funcionarios"
ws.append([c[1] for c in COLS])
for cpf in sorted(func):
    ws.append([func[cpf].get(k, "") for k, _ in COLS])

ws2 = wb.create_sheet("Eventos")
ws2.append(["CPF", "tpEvt consultado", "tpEvt retornado", "ID do evento", "Recibo", "Baixado?"])
for e in eventos_todos:
    ws2.append([e.get("cpf", ""), e.get("tpEvtCons", ""), e.get("tpEvt", ""),
                e.get("id", ""), e.get("nrRecEvt", ""), "SIM" if e.get("id") in xml_por_id else "nao"])

ws3 = wb.create_sheet("Diagnostico")
ws3.append(["Teste", "Evento", "Chave", "cdResposta", "descResposta", "Qtd", "Erro"])
for d in diag:
    ws3.append(d)

for sh in (ws, ws2, ws3):
    for c in sh[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E79")
    sh.freeze_panes = "A2"
    for col in sh.columns:
        w = max((len(str(c.value)) for c in col if c.value is not None), default=8)
        sh.column_dimensions[col[0].column_letter].width = min(max(w + 2, 10), 45)

os.makedirs(OUT_DIR, exist_ok=True)
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
out = os.path.join(OUT_DIR, f"Funcionarios_eSocial_{CNPJ_EMP}_{stamp}.xlsx")
wb.save(out)
print(f"\nPLANILHA: {out}")
print(f"XMLs brutos (so para conferencia): {XML_DIR}")
print(f"Funcionarios montados: {len(func)}")
