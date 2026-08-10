"""
Portal do eSocial — solicitacao dos ZIP de eventos, mes a mes. SEMIAUTOMATICO.

POR QUE SEMI: o login do gov.br termina em hcaptcha.execute() — nenhum login
envia o formulario antes do captcha resolver, inclusive o do certificado digital
(provado em 10/08/2026). Entao o navegador abre VISIVEL, voce faz o login, e o
script assume dali. Nao existe versao 100% automatica, nem aqui nem no Render.

FASE 1 (este arquivo, comando "recon"): abre o navegador, espera voce logar e
chegar na tela de Download, e despeja a estrutura da pagina (HTML, print e todos
os campos) em __portal_recon/. NAO ENVIA NADA. Serve para escrever a fase 2 em
cima da tela real.

FASE 2 ("solicitar"): dispara uma solicitacao "Todos os eventos de um
determinado periodo" por mes, do mes atual retroagindo. Ainda nao implementada —
depende do que o recon mostrar.

Uso:
    python _portal_esocial.py recon
    python _portal_esocial.py recon --pfx C:\\caminho\\cert.pfx --senha SENHA
    python _portal_esocial.py recon --cnpj 08777252000133      (pega do banco)

Requer: pip install playwright  +  python -m playwright install chromium
"""
import os, re, sys, base64, hashlib, argparse, datetime
import requests, urllib3
from dotenv import load_dotenv

urllib3.disable_warnings()
load_dotenv(r"C:\folha10-simples\.env")

OUT_DIR = r"C:\folha10-simples\__portal_recon"
URL_LOGIN = "https://login.esocial.gov.br/login.aspx"

# Origens que podem pedir o certificado do cliente durante o login.
ORIGENS = ["https://login.esocial.gov.br", "https://certificado.sso.acesso.gov.br",
           "https://sso.acesso.gov.br", "https://www.gov.br",
           "https://servicos.acesso.gov.br"]

# O Chromium inicializa audio/video ao subir e as paginas chamam
# enumerateDevices() para fingerprint — o antivirus acusa acesso a webcam/mic.
# Com estes flags ele nunca toca no hardware real.
FLAGS_SEM_MIDIA = ["--use-fake-device-for-media-stream",
                   "--use-fake-ui-for-media-stream",
                   "--mute-audio", "--disable-audio-input"]


def cert_do_banco(cnpj):
    """Le o .pfx e a senha do tab_empresa. So funciona no ambiente onde o
    certificado foi gravado (a senha e cifrada com a FLASK_SECRET_KEY)."""
    supa = os.getenv("SUPABASE_URL", "").rstrip("/")
    key  = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    r = requests.get(f"{supa}/rest/v1/tab_empresa",
                     params={"select": "razaosocial,cert_pfx_b64,cert_senha_enc",
                             "cnpj": f"eq.{re.sub(r'[^0-9]', '', cnpj)}"},
                     headers={"apikey": key, "Authorization": f"Bearer {key}"},
                     verify=False, timeout=30)
    linha = (r.json() or [None])[0]
    if not linha or not linha.get("cert_pfx_b64"):
        raise SystemExit(f"!! empresa {cnpj} sem certificado em tab_empresa")
    from cryptography.fernet import Fernet
    raw = (os.getenv("FLASK_SECRET_KEY", "F10default") + "_cert_v1").encode()
    senha = Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
                   ).decrypt(linha["cert_senha_enc"].encode()).decode()
    return base64.b64decode(linha["cert_pfx_b64"]), senha


def cert_para_pem(pfx_bytes, senha):
    """O .pfx do A1 brasileiro usa cifra antiga (RC2/3DES/SHA1) e o OpenSSL 3 do
    Node recusa com 'Unsupported TLS certificate'. Converte para PEM em memoria."""
    from cryptography.hazmat.primitives.serialization import (
        pkcs12, Encoding, PrivateFormat, NoEncryption)
    pk, cert, extras = pkcs12.load_key_and_certificates(pfx_bytes, senha.encode())
    key_pem = pk.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    cert_pem = cert.public_bytes(Encoding.PEM) + b"".join(
        c.public_bytes(Encoding.PEM) for c in (extras or []))
    return cert_pem, key_pem, cert


def descrever(frame, prefixo, saida):
    """Lista os campos de um frame — e o que interessa para automatizar."""
    try:
        controles = frame.query_selector_all("select, input, button, a[href], textarea")
    except Exception as e:
        saida.append(f"{prefixo} (nao consegui ler: {str(e)[:80]})")
        return
    for el in controles:
        try:
            if not el.is_visible():
                continue
            tag = el.evaluate("n => n.tagName").lower()
            ident = el.get_attribute("id") or el.get_attribute("name") or ""
            texto = re.sub(r"\s+", " ", (el.inner_text() or "")).strip()[:45]
            extra = ""
            if tag == "select":
                ops = [f"{(o.get_attribute('value') or '')}={re.sub(chr(32)+'+',' ',(o.inner_text() or '')).strip()[:45]}"
                       for o in el.query_selector_all("option")]
                extra = " | OPCOES: " + " ;; ".join(ops[:15])
            elif tag == "input":
                extra = (f" type={el.get_attribute('type')}"
                         f" placeholder={el.get_attribute('placeholder')}")
            elif tag == "a":
                extra = f" href={(el.get_attribute('href') or '')[:70]}"
            saida.append(f"{prefixo} {tag:8} id/name={ident[:38]:38} txt={texto!r:47}{extra}")
        except Exception:
            continue


def recon(args):
    from playwright.sync_api import sync_playwright

    cert_pem = key_pem = None
    if args.pfx:
        with open(args.pfx, "rb") as f:
            pfx = f.read()
        cert_pem, key_pem, c = cert_para_pem(pfx, args.senha or "")
        print(f"Certificado: {c.subject.rfc4514_string()[:70]}")
    elif args.cnpj:
        pfx, senha = cert_do_banco(args.cnpj)
        cert_pem, key_pem, c = cert_para_pem(pfx, senha)
        print(f"Certificado: {c.subject.rfc4514_string()[:70]}")
    else:
        print("Sem certificado: o navegador vai abrir e voce loga como preferir.")

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    with sync_playwright() as p:
        br = p.chromium.launch(headless=False, args=FLAGS_SEM_MIDIA)
        ctx_args = {"ignore_https_errors": True, "accept_downloads": True,
                    "viewport": {"width": 1500, "height": 950}}
        if cert_pem:
            ctx_args["client_certificates"] = [
                {"origin": o, "cert": cert_pem, "key": key_pem} for o in ORIGENS]
        ctx = br.new_context(**ctx_args)
        pg = ctx.new_page()
        pg.set_default_timeout(60000)
        pg.goto(URL_LOGIN, wait_until="domcontentloaded")

        print("\n" + "=" * 70)
        print("O navegador abriu. Faca o login (certificado + captcha) e navegue")
        print("ate a tela de DOWNLOAD, no ponto de PEDIR uma solicitacao nova.")
        print("Nao precisa enviar nada — so deixe a tela aberta.")
        print("Quando estiver la, volte AQUI e tecle ENTER.")
        print("=" * 70)
        input("\n>>> ENTER quando a tela de Download estiver aberta: ")

        linhas = [f"# recon do portal do eSocial — {stamp}",
                  f"# url:    {pg.url}",
                  f"# titulo: {pg.title()}", ""]
        print(f"\nCapturando: {pg.url}")

        pg.screenshot(path=os.path.join(OUT_DIR, f"tela_{stamp}.png"), full_page=True)
        with open(os.path.join(OUT_DIR, f"pagina_{stamp}.html"), "w", encoding="utf-8") as f:
            f.write(pg.content())

        # A tela pode estar dentro de iframe — percorre todos os frames.
        for i, fr in enumerate(pg.frames):
            linhas.append(f"\n--- FRAME {i}: {fr.url[:120]}")
            descrever(fr, f"[f{i}]", linhas)
            if fr != pg.main_frame:
                try:
                    with open(os.path.join(OUT_DIR, f"frame{i}_{stamp}.html"),
                              "w", encoding="utf-8") as f:
                        f.write(fr.content())
                except Exception:
                    pass

        campos = os.path.join(OUT_DIR, f"campos_{stamp}.txt")
        with open(campos, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))

        print(f"\nGravado em {OUT_DIR}:")
        print(f"  tela_{stamp}.png      — print da tela")
        print(f"  pagina_{stamp}.html   — HTML completo")
        print(f"  campos_{stamp}.txt    — campos e opcoes de cada frame")
        print(f"\n{len(pg.frames)} frame(s). Navegador continua aberto.")
        input(">>> ENTER para fechar: ")
        br.close()


def main():
    ap = argparse.ArgumentParser(description="Portal do eSocial (semiautomatico)")
    ap.add_argument("comando", choices=["recon", "solicitar"])
    ap.add_argument("--pfx",   help="caminho do .pfx do certificado A1")
    ap.add_argument("--senha", help="senha do .pfx")
    ap.add_argument("--cnpj",  help="pega o certificado do tab_empresa por CNPJ")
    ap.add_argument("--meses", type=int, default=60,
                    help="fase 2: quantos meses retroagir a partir do mes atual")
    args = ap.parse_args()

    if args.comando == "recon":
        recon(args)
    else:
        raise SystemExit(
            "A fase 'solicitar' ainda nao existe: ela depende dos seletores da\n"
            "tela de Download, que so aparecem depois do login. Rode primeiro:\n"
            "    python _portal_esocial.py recon")


if __name__ == "__main__":
    main()
