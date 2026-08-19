# -*- coding: utf-8 -*-
"""Captura o print de cada tela do sistema, para a demonstração.

ANTES DE RODAR, LEIA: entre com um cliente de DEMONSTRAÇÃO, não com um
cliente de verdade. O print pega o cabeçalho inteiro -- razão social, CNPJ,
nomes e salários dos funcionários -- e a demonstração vai para o ar num link
público. O cliente teste (id 6) existe justamente para isso.

Como funciona: abre o navegador na tela de login e ESPERA você entrar. Só
depois de logado é que ele começa a percorrer as telas, uma a uma, na ordem
do menu. Não digita senha nenhuma -- quem faz o login é você.

O que ele visita sai do _demo_telas.json (gerado por _demo_inventario.py),
que por sua vez sai do menu de verdade. Nada de lista escrita à mão.

Só GET, e só nas telas do menu. As rotas de ação (calcular, fechar folha,
reabrir) foram conferidas uma a uma: em GET todas apenas desenham a tela de
confirmação -- quem executa é o POST do botão, em que este script não toca.

Rodar:  python _demo_capturar.py
        python _demo_capturar.py --refazer     (ignora o que já capturou)
        python _demo_capturar.py --so cadastros (um módulo só)

Para rodar sozinho (recaptura em lote, sem ninguém na frente da tela):
        python _demo_capturar.py --refazer --auto-login --headless                --cpf 11111111111 --senha ****** --empresa 15
A senha não fica escrita neste arquivo de propósito -- vem por parâmetro.
Sem --empresa, toda tela do menu cai em /selecionar_empresa e o print sai
vazio.

Saída:  static/demo/<modulo>_<slug>.jpg  +  _demo_capturas.json (o relatório)
"""

import argparse
import io
import json
import os
import re
import sys
import unicodedata

BASE = "http://127.0.0.1:5000"
PASTA = os.path.join("static", "demo")
INVENTARIO = "_demo_telas.json"
RELATORIO = "_demo_capturas.json"

LARGURA, ALTURA = 1440, 900
QUALIDADE = 72
ESPERA_LOGIN = 900      # segundos que ele espera você logar (15 min)
ESPERA_TELA = 12000     # ms para a tela terminar de montar


def slug(texto):
    """Nome de arquivo previsível a partir da rota: /cad_mov?x=1 -> cad_mov_x_1."""
    t = unicodedata.normalize("NFD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", t.lower())).strip("_")


def carregar():
    if not os.path.exists(INVENTARIO):
        raise SystemExit("ERRO: falta o %s. Rode antes:\n"
                         "  python _demo_inventario.py" % INVENTARIO)
    return json.load(io.open(INVENTARIO, encoding="utf-8"))


def _esperar_login_na_tela(pagina, navegador):
    """Caminho manual: mostra o aviso e espera a pessoa entrar."""
    print(" >>> ABRIU UMA JANELA NOVA DO CHROMIUM, na tela de login.")
    print("     É NELA que você entra — não no seu navegador de sempre.")
    print("     Se não estiver à vista, procure na barra de tarefas.")
    print("     Depois de logar, deixe a janela quieta: fechá-la aborta.")
    print("     Esperando até %d minutos...\n" % (ESPERA_LOGIN // 60))

    # Espera o login: enquanto a tela ainda tiver campo de senha, é porque
    # não entrou. Assim funciona qualquer que seja a rota do menu.
    # O except separa duas coisas que antes se confundiam: ESPERAR demais
    # (ninguém logou) e a JANELA MORRER (browser fechado, processo em
    # segundo plano). A primeira versão dizia "ninguém logou" para os dois
    # casos, e um Chromium encerrado em 3 segundos virava um falso
    # "esperei 15 minutos" — mentira que custa tempo de quem lê.
    import time as _t
    _ini = _t.time()
    try:
        pagina.wait_for_selector("input[type=password]",
                                 state="detached",
                                 timeout=ESPERA_LOGIN * 1000)
    except Exception as e:
        gasto = _t.time() - _ini
        try:
            navegador.close()
        except Exception:
            pass
        if gasto < ESPERA_LOGIN * 0.9:
            raise SystemExit(
                "\nA janela do navegador morreu depois de %.0f segundos —\n"
                "não foi falta de login. Erro: %s\n\n"
                "Isto acontece quando o script roda em segundo plano ou\n"
                "sem sessão gráfica. Rode direto no SEU terminal, numa\n"
                "janela normal do Prompt/PowerShell:\n"
                "    python _demo_capturar.py" % (gasto, str(e).split("\n")[0][:120]))
        raise SystemExit(
            "\nNinguém logou em %d minutos, então nada foi capturado.\n"
            "Causas comuns:\n"
            "  - a janela do Chromium abriu atrás das outras e passou batido;\n"
            "  - o login foi feito no navegador de sempre, e não nela;\n"
            "  - a janela foi fechada antes de entrar.\n"
            "Rode de novo: python _demo_capturar.py"
            % (ESPERA_LOGIN // 60))
    print(" Logado. Começando.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refazer", action="store_true",
                    help="captura de novo mesmo o que já existe")
    ap.add_argument("--so", default="", metavar="MODULO",
                    help="captura só um módulo (cadastros, esocial, ...)")
    # Login automático: existe para a captura poder rodar sozinha (recaptura
    # em lote, sem ninguém na frente da tela). O caminho normal continua sendo
    # o manual -- por isso a senha NÃO fica escrita aqui, vem por parâmetro.
    ap.add_argument("--auto-login", action="store_true",
                    help="entra sozinho pela API, sem esperar o login na tela")
    ap.add_argument("--cpf", default="", help="CPF do login automático")
    ap.add_argument("--senha", default="", help="senha do login automático")
    ap.add_argument("--empresa", default="", metavar="ID",
                    help="id_empresa a selecionar depois do login automático")
    ap.add_argument("--headless", action="store_true",
                    help="sem janela; só faz sentido com --auto-login")
    args = ap.parse_args()

    if args.auto_login and not (args.cpf and args.senha):
        raise SystemExit("ERRO: --auto-login precisa de --cpf e --senha.")
    if args.headless and not args.auto_login:
        raise SystemExit("ERRO: --headless sem --auto-login não entra em lugar "
                         "nenhum -- ninguém vê a tela para digitar a senha.")

    dados = carregar()
    telas = [t for t in dados["telas"] if t["ok"] and not t["repetida"]]
    if args.so:
        telas = [t for t in telas if t["modulo"] == args.so]
        if not telas:
            raise SystemExit("ERRO: módulo %r não tem tela pronta. Os que têm: %s"
                             % (args.so, ", ".join(sorted(
                                 {t["modulo"] for t in dados["telas"] if t["ok"]}))))

    os.makedirs(PASTA, exist_ok=True)

    from playwright.sync_api import sync_playwright

    print("=" * 68)
    print(" Entre com um cliente de DEMONSTRAÇÃO (o teste, id 6).")
    print(" O print mostra razão social, CNPJ e nomes -- e vai para um link")
    print(" público. Cliente real aqui é vazamento de dados.")
    print("=" * 68)
    print("\n %d telas a capturar." % len(telas))
    print(" Abrindo o navegador. Faça o login e pode deixar a janela quieta.\n")

    feitas, pulos, erros = [], [], []

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=bool(args.headless))
        pagina = navegador.new_page(viewport={"width": LARGURA, "height": ALTURA})
        pagina.goto(BASE + "/", timeout=30000)
        try:
            pagina.bring_to_front()
        except Exception:
            pass

        # A propria tela de login e a primeira cena da demonstracao, com o
        # CPF e a senha sendo digitados. O print dela tem que sair AGORA,
        # antes do login: depois de entrar, essa tela nao existe mais.
        login_jpg = os.path.join(PASTA, "_login.jpg")
        if args.refazer or not os.path.exists(login_jpg):
            pagina.wait_for_timeout(500)
            pagina.screenshot(path=login_jpg, type="jpeg", quality=QUALIDADE)
            print(" Tela de login guardada (%s).\n" % login_jpg)

        if args.auto_login:
            # Entra pela mesma API que a tela usa, com o cookie ficando na
            # própria janela do Playwright. Depois escolhe a empresa: sem
            # isso, TODA tela do menu cai em /selecionar_empresa e o print
            # sai vazio -- que foi o que aconteceu na primeira rodada.
            r = pagina.evaluate("""async ([cpf, senha]) => {
                const r = await fetch('/fazer_login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cpf: cpf, senha: senha})});
                return await r.json();
            }""", [args.cpf, args.senha])
            if not (r or {}).get("ok"):
                navegador.close()
                raise SystemExit("\nLogin automático recusado: %s"
                                 % (r or {}).get("msg", "sem resposta"))
            print(" Login automático: ok.")
            if args.empresa:
                r2 = pagina.evaluate("""async (id) => {
                    const r = await fetch('/api/selecionar_empresa', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({id_empresa: id})});
                    return await r.json();
                }""", int(args.empresa))
                if not (r2 or {}).get("ok"):
                    navegador.close()
                    raise SystemExit("\nEmpresa %s não selecionada: %s"
                                     % (args.empresa, (r2 or {}).get("msg", "?")))
                print(" Empresa %s selecionada." % args.empresa)
            print("")
        else:
            _esperar_login_na_tela(pagina, navegador)

        for i, t in enumerate(telas, 1):
            arquivo = os.path.join(PASTA, "%s_%s.jpg"
                                   % (t["modulo"], slug(t["href"])))
            if os.path.exists(arquivo) and not args.refazer:
                pulos.append(t["nome"])
                continue
            try:
                pagina.goto(BASE + t["href"], timeout=ESPERA_TELA,
                            wait_until="networkidle")
                # O menu e várias telas montam a lista por JavaScript depois
                # do networkidle. Sem esta pausa o print sai com a moldura
                # pronta e o miolo vazio -- e vazio não dá erro nenhum.
                pagina.wait_for_timeout(700)
                pagina.screenshot(path=arquivo, type="jpeg", quality=QUALIDADE)

                # Tela bloqueada (folha calculada, permissão) devolve o menu.
                # Não é erro, mas o print não serve: precisa aparecer no fim.
                voltou = "/menu" in pagina.url or pagina.url.rstrip("/") == BASE
                marca = "  <- caiu no menu" if voltou else ""
                kb = os.path.getsize(arquivo) / 1024
                print("%3d/%d  %-42.42s %5.0f KB%s"
                      % (i, len(telas), t["nome"], kb, marca))
                feitas.append({**t, "arquivo": arquivo,
                               "url_final": pagina.url, "voltou": voltou})
            except Exception as e:
                print("%3d/%d  %-42.42s  ERRO: %s"
                      % (i, len(telas), t["nome"], str(e).split("\n")[0][:60]))
                erros.append({**t, "erro": str(e).split("\n")[0]})

        navegador.close()

    io.open(RELATORIO, "w", encoding="utf-8").write(
        json.dumps({"capturadas": feitas, "erros": erros},
                   ensure_ascii=False, indent=1))

    total_kb = sum(os.path.getsize(f["arquivo"]) for f in feitas) / 1024
    print("\n%d capturadas (%.1f MB), %d já existiam, %d com erro."
          % (len(feitas), total_kb / 1024, len(pulos), len(erros)))
    caiu = [f["nome"] for f in feitas if f["voltou"]]
    if caiu:
        print("\nCaíram no menu (tela bloqueada ou sem permissão) -- estes"
              "\nprints não servem, confira a situação da folha:")
        for n in caiu:
            print("  -", n)
    if erros:
        print("\nCom erro:")
        for e in erros:
            print("  - %s (%s): %s" % (e["nome"], e["href"], e["erro"]))
    print("\n%s gravado." % RELATORIO)


if __name__ == "__main__":
    sys.exit(main())
