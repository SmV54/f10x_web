"""
Portal do eSocial — solicitacao dos ZIP de eventos, mes a mes. SEMIAUTOMATICO.

POR QUE SEMI: o login do gov.br termina em hcaptcha.execute() — nenhum login
envia o formulario antes do captcha resolver, inclusive o do certificado digital
(provado em 10/08/2026). Entao o navegador abre VISIVEL, voce faz o login, e o
script assume dali. Nao existe versao 100% automatica, nem aqui nem no Render.

FASE 1 (este arquivo, comando "recon"): abre o navegador, espera voce logar e
despeja a estrutura da pagina (HTML, print e todos os campos) em __portal_recon/.
NAO ENVIA NADA. Serve para escrever a fase 2 em cima da tela real. Captura
QUANTAS telas voce quiser na mesma sessao — o login e que custa (captcha
manual), a captura nao. A fase 2 precisa de duas: a de PEDIR a solicitacao e a
de CONSULTAR/baixar o ZIP.

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


def cert_do_banco(cnpj, id_empresa=None):
    """Le o .pfx e a senha do tab_empresa. So funciona no ambiente onde o
    certificado foi gravado (a senha e cifrada com a FLASK_SECRET_KEY).

    O MESMO CNPJ pode estar cadastrado em varios clientes (a base e multi-cliente,
    e a mesma empresa aparece de novo numa base de teste). O certificado costuma
    estar em uma so dessas linhas, entao a busca filtra por quem TEM certificado
    e fica com a validade mais longa. --id-empresa resolve na mao se precisar.
    """
    supa = os.getenv("SUPABASE_URL", "").rstrip("/")
    key  = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    sel  = "id_empresa,id_cliente,razaosocial,cert_validade,cert_pfx_b64,cert_senha_enc"
    hdr  = {"apikey": key, "Authorization": f"Bearer {key}"}
    par  = {"select": sel, "cnpj": f"eq.{re.sub(r'[^0-9]', '', cnpj)}"}
    if id_empresa:
        par["id_empresa"] = f"eq.{int(id_empresa)}"
    r = requests.get(f"{supa}/rest/v1/tab_empresa", params=par, headers=hdr,
                     verify=False, timeout=30)
    todas = r.json() or []
    comcert = [l for l in todas if l.get("cert_pfx_b64") and l.get("cert_senha_enc")]
    comcert.sort(key=lambda l: str(l.get("cert_validade") or ""), reverse=True)

    if not comcert:
        print(f"!! nenhuma das {len(todas)} empresa(s) com CNPJ {cnpj} tem certificado:")
        for l in todas:
            print(f"   id_empresa={l.get('id_empresa')} id_cliente={l.get('id_cliente')} "
                  f"{(l.get('razaosocial') or '')[:40]}")
        raise SystemExit("   suba o certificado na tela do eSocial ou use --pfx/--senha")

    linha = comcert[0]
    if len(todas) > 1:
        print(f"{len(todas)} empresas com o CNPJ {cnpj}; usando a que tem certificado: "
              f"id_empresa={linha['id_empresa']} (cliente {linha['id_cliente']}, "
              f"vence {linha.get('cert_validade')})")
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
        pfx, senha = cert_do_banco(args.cnpj, getattr(args, "id_empresa", None))
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
        print("O navegador abriu. Faca o login (certificado + captcha).")
        print("Depois navegue por UMA tela de cada vez e volte aqui para capturar.")
        print("")
        print("A fase 2 precisa de DUAS telas, entao capture as duas na mesma")
        print("sessao de login (o captcha so pede uma vez):")
        print("  1) DOWNLOAD -> no ponto de PEDIR uma solicitacao nova")
        print("     (com o Tipo de Solicitacao 'Todos os eventos ... de um")
        print("      determinado periodo' ja escolhido, para os campos de data")
        print("      e a opcao 'Todos' aparecerem)")
        print("  2) CONSULTAR -> a lista das solicitacoes, onde aparece")
        print("     'Solicitado' e o link/botao que baixa o ZIP")
        print("")
        print("Nao precisa enviar nada — so deixe cada tela aberta e tecle ENTER.")
        print("=" * 70)

        # Varias capturas por sessao: o login e o gargalo (captcha manual), entao
        # nao faz sentido gastar um login por tela.
        n = 0
        while True:
            rotulo = input("\n>>> nome desta tela (ex.: solicitar, consultar) "
                           "— ENTER vazio encerra: ").strip()
            if not rotulo:
                break
            rotulo = re.sub(r"[^A-Za-z0-9_-]", "_", rotulo)[:30] or f"tela{n}"
            n += 1
            pref = f"{rotulo}_{stamp}"

            linhas = [f"# recon do portal do eSocial — {stamp} — tela '{rotulo}'",
                      f"# url:    {pg.url}",
                      f"# titulo: {pg.title()}", ""]
            print(f"Capturando '{rotulo}': {pg.url}")

            pg.screenshot(path=os.path.join(OUT_DIR, f"{pref}.png"), full_page=True)
            with open(os.path.join(OUT_DIR, f"{pref}.html"), "w", encoding="utf-8") as f:
                f.write(pg.content())

            # A tela pode estar dentro de iframe — percorre todos os frames.
            for i, fr in enumerate(pg.frames):
                linhas.append(f"\n--- FRAME {i}: {fr.url[:120]}")
                descrever(fr, f"[f{i}]", linhas)
                if fr != pg.main_frame:
                    try:
                        with open(os.path.join(OUT_DIR, f"{pref}_frame{i}.html"),
                                  "w", encoding="utf-8") as f:
                            f.write(fr.content())
                    except Exception:
                        pass

            with open(os.path.join(OUT_DIR, f"{pref}_campos.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(linhas))
            print(f"  -> {pref}.png / .html / _campos.txt  ({len(pg.frames)} frame(s))")

        print(f"\n{n} tela(s) capturada(s) em {OUT_DIR}")
        input(">>> ENTER para fechar o navegador: ")
        br.close()


def main():
    ap = argparse.ArgumentParser(description="Portal do eSocial (semiautomatico)")
    ap.add_argument("comando", choices=["recon", "solicitar"])
    ap.add_argument("--pfx",   help="caminho do .pfx do certificado A1")
    ap.add_argument("--senha", help="senha do .pfx")
    ap.add_argument("--cnpj",  help="pega o certificado do tab_empresa por CNPJ")
    ap.add_argument("--id-empresa", dest="id_empresa", type=int,
                    help="desempata quando o mesmo CNPJ esta em mais de um cliente")
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
