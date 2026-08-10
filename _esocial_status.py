"""
Diz se os webservices de consulta/download cirurgico do eSocial estao no ar.

NAO gasta a cota de 10 solicitacoes/dia: so faz GET do ?wsdl, que nao e
solicitacao. Serve para saber se vale a pena rodar o
_puxar_esocial_funcionarios.py (esse sim gasta).

Uso:  python _esocial_status.py [CNPJ]
      CNPJ default 08777252000133 (FOLHA10 - COMSIST); e so de onde sai o
      certificado, a consulta nao e feita.

Como ler a resposta:
  * 403 sem cert e o normal - o servico exige certificado do cliente.
  * 200 com <wsdl:definitions>  -> NO AR.
  * 500 com pagina do ASP.NET   -> FORA DO AR (problema do proprio governo).
"""
import os, re, sys, base64, hashlib, tempfile
import requests, urllib3
from dotenv import load_dotenv

urllib3.disable_warnings()
load_dotenv(r"C:\folha10-simples\.env")

CNPJ = re.sub(r"\D", "", sys.argv[1] if len(sys.argv) > 1 else "08777252000133")

BASE = "https://webservices.download.esocial.gov.br/servicos/empregador/dwlcirurgico"
SERVICOS = [("consulta de identificadores", "WsConsultarIdentificadoresEventos.svc"),
            ("download de eventos",         "WsSolicitarDownloadEventos.svc")]

SUPA = os.getenv("SUPABASE_URL").rstrip("/")
KEY  = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
H    = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

emp = (requests.get(f"{SUPA}/rest/v1/tab_empresa",
                    params={"select": "cnpj,razaosocial,cert_pfx_b64,cert_senha_enc",
                            "cnpj": f"eq.{CNPJ}"},
                    headers=H, verify=False, timeout=30).json() or [None])[0]
if not emp or not emp.get("cert_pfx_b64"):
    print(f"!! Empresa {CNPJ} sem certificado em tab_empresa"); sys.exit(1)

from cryptography.fernet import Fernet
raw = (os.getenv("FLASK_SECRET_KEY", "F10default") + "_cert_v1").encode()
try:
    senha = Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
                   ).decrypt(emp["cert_senha_enc"].encode()).decode()
except Exception as e:
    # A senha so descriptografa no ambiente onde o .pfx foi gravado.
    print(f"!! Nao abriu o certificado: {e}"); sys.exit(1)

from cryptography.hazmat.primitives.serialization import (
    pkcs12, Encoding, PrivateFormat, NoEncryption)
pk, cert, _ = pkcs12.load_key_and_certificates(
    base64.b64decode(emp["cert_pfx_b64"]), senha.encode())
kf = tempfile.NamedTemporaryFile(delete=False, suffix=".key.pem")
kf.write(pk.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())); kf.close()
cf = tempfile.NamedTemporaryFile(delete=False, suffix=".cert.pem")
cf.write(cert.public_bytes(Encoding.PEM)); cf.close()

def limpar(html):
    t = re.sub(r"<style.*?</style>", "", html, flags=re.S)
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()

print(f"eSocial — dwlcirurgico — cert de {emp.get('razaosocial') or CNPJ}\n")
no_ar = True
try:
    for nome, svc in SERVICOS:
        try:
            r = requests.get(f"{BASE}/{svc}?wsdl", cert=(cf.name, kf.name),
                             verify=False, timeout=40)
            t = r.text or ""
        except Exception as e:
            print(f"  {nome:30} ERRO DE REDE: {str(e)[:120]}"); no_ar = False; continue
        if r.status_code == 200 and "wsdl:" in t:
            print(f"  {nome:30} NO AR  (HTTP 200, {len(t)} bytes de WSDL)")
        else:
            no_ar = False
            det = limpar(t)
            m = re.search(r"Parser Error Message:\s*(.+?)\s*Source (?:Error|File)", det)
            print(f"  {nome:30} FORA DO AR  (HTTP {r.status_code})")
            print(f"  {'':30} {(m.group(1) if m else det)[:150]}")
finally:
    os.unlink(kf.name); os.unlink(cf.name)

print()
if no_ar:
    print("Os dois servicos responderam. Pode rodar:")
    print("  python _puxar_esocial_funcionarios.py        (gasta a cota de 10/dia)")
else:
    print("Problema do lado do eSocial — nao e o certificado nem a cota.")
    print("Nao adianta rodar o _puxar_esocial_funcionarios.py agora.")
