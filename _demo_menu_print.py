# -*- coding: utf-8 -*-
"""Tira o print do menu de verdade, sem precisar de login.

Por que não dá para simplesmente visitar /menu: aquela rota exige sessão, e
o capturador só entra depois que VOCÊ digita a senha -- mas o menu tem que
aparecer na demonstração antes de qualquer módulo, e ficar dependendo de uma
captura manual para uma tela só é convite a esquecer.

Como funciona: o F10_Menu.html monta a grade de módulos por JavaScript, a
partir do objeto `modulos` que está no próprio arquivo. Nada disso vem do
banco. Então o template é renderizado aqui mesmo, com valores de mentira no
cabeçalho, e fotografado. O resultado é o menu real -- os mesmos módulos, os
mesmos ícones, o mesmo desenho.

E é melhor que um print de verdade para o que a gente quer: o cabeçalho sai
com uma empresa inventada, e não com a razão social e o CNPJ de um cliente
que iriam parar num link público.

Além do menu fechado, tira também o print de CADA MÓDULO com a gaveta
aberta -- que é a primeira coisa que a demonstração mostra de cada um. Antes
essa gaveta era desenhada por mim, item por item; agora é a de verdade,
aberta pelo próprio código do menu.

Precisa do servidor no ar (python app.py). Não é para logar: a página é
servida como arquivo estático só para que /static/logo.png e as folhas de
estilo resolvam -- por file:// a logo sai quebrada.

Rodar:  python _demo_menu_print.py
Saída:  static/demo/_menu.jpg  +  static/demo/_menu_<modulo>.jpg
"""

import io
import json
import os
import sys

BASE = "http://127.0.0.1:5000"
PASTA = os.path.join("static", "demo")
SAIDA = os.path.join(PASTA, "_menu.jpg")
CARTOES = "_demo_menu_cards.json"
INVENTARIO = "_demo_telas.json"
LARGURA, ALTURA = 1440, 900

# Cabeçalho de mentira. Nome de empresa que não existe, de propósito.
CONTEXTO = {
    "versao": "260818-0900",
    "nome": "ESCRITORIO MODELO CONTABILIDADE",
    "empresa": "EMPRESA DEMONSTRACAO LTDA",
    "id_cliente_hdr": 1, "id_empresa_hdr": 1,
    "folha_ativa": "07/2026", "folha_ativa_tipo": "Mensal",
    "folha_ativa_situacao": "Aberta", "folha_ativa_sit_class": "sit-aberta",
    "folha_situacao": "A", "qtd_empresas": 1,
    "cpf_usuario": "", "cert_dias": 120, "cert_validade_fmt": "31/12/2026",
    "cert_herdado_de": "", "licenca_fmt": "31/12/2026",
    "licenca_classe": "ok", "licenca_limite": 50,
    # Vai vazio, e tem que ser uma lista de verdade: o template joga isto no
    # JavaScript com |tojson, e um valor indefinido não vira JSON.
    "esocial_pend": [],
}


def main():
    from jinja2 import Environment, FileSystemLoader, ChainableUndefined
    from playwright.sync_api import sync_playwright

    env = Environment(loader=FileSystemLoader("templates"),
                      undefined=ChainableUndefined)
    html = env.get_template("F10_Menu.html").render(**CONTEXTO)

    # Dentro de static/ de propósito: assim o Flask serve a página e os
    # caminhos absolutos do menu (/static/logo.png, as folhas de estilo)
    # resolvem. Por file:// a logo sai quebrada no meio do cabeçalho.
    tmp = os.path.join("static", "_menu_para_print.html")
    io.open(tmp, "w", encoding="utf-8", newline="").write(html)
    os.makedirs(PASTA, exist_ok=True)

    chaves = []
    if os.path.exists(INVENTARIO):
        chaves = [m["chave"] for m in
                  json.load(io.open(INVENTARIO, encoding="utf-8"))["modulos"]]

    feitos, erros = [], []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": LARGURA, "height": ALTURA})
            pg.on("pageerror", lambda e: erros.append(str(e).split("\n")[0][:90]))
            pg.goto(BASE + "/static/_menu_para_print.html",
                    wait_until="networkidle", timeout=20000)
            pg.wait_for_timeout(1200)
            cartoes = pg.evaluate("() => document.querySelectorAll('[data-modulo]').length")
            # Recorta a faixa de cima. O menu de verdade é cabeçalho, uma
            # fileira de cartões e três quartos de tela vazia -- na
            # demonstração aquilo virava um retângulo enorme de nada, com os
            # cartões pequenos demais para o realce significar alguma coisa.
            # A altura sai do último cartão, não de um número escolhido: se o
            # menu ganhar uma segunda fileira, o recorte acompanha.
            fundo = pg.evaluate("""() => Math.max(...[...document.querySelectorAll(
                '[data-modulo]')].map(e => e.getBoundingClientRect().bottom))""")
            corte = min(ALTURA, int(fundo + 30))
            pg.screenshot(path=SAIDA, type="jpeg", quality=78,
                          clip={"x": 0, "y": 0, "width": LARGURA, "height": corte})
            feitos.append(("menu (faixa de %dpx)" % corte, SAIDA))

            # Onde cada cartão está NA FOTO, em porcentagem. É o que permite
            # acender o cartão certo na demonstração sem eu medir nada no
            # olho: quem mede é o próprio navegador, no mesmo instante em que
            # tira o print, então mudou o menu, mudam as marcas junto.
            # Em porcentagem DO RECORTE, não da tela inteira: é o recorte que
            # vira a imagem, e é sobre ela que o realce é posicionado.
            rects = pg.evaluate("""(corte) => {
                const w = innerWidth;
                return [...document.querySelectorAll('[data-modulo]')].map(e => {
                    const r = e.getBoundingClientRect();
                    return {chave: e.dataset.modulo,
                            left: r.left / w * 100, top: r.top / corte * 100,
                            width: r.width / w * 100, height: r.height / corte * 100};
                });
            }""", corte)
            io.open(CARTOES, "w", encoding="utf-8").write(
                json.dumps(rects, ensure_ascii=False, indent=1))

            # Uma gaveta de cada vez. Fechar antes de abrir a próxima porque
            # clicar no módulo já aberto FECHA o painel -- e sairia um print
            # do menu vazio, igual ao anterior, sem erro nenhum para avisar.
            for chave in chaves:
                alvo = pg.query_selector('[data-modulo="%s"]' % chave)
                if not alvo:
                    erros.append("cartão %r não existe no menu" % chave)
                    continue
                pg.evaluate("() => { if (typeof fecharPanel === 'function') fecharPanel(); }")
                pg.wait_for_timeout(200)
                alvo.click()
                pg.wait_for_timeout(900)
                arq = os.path.join(PASTA, "_menu_%s.jpg" % chave)
                pg.screenshot(path=arq, type="jpeg", quality=75)
                feitos.append((chave, arq))
            b.close()
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    print("cartões de módulo no menu: %d  (posições em %s)" % (cartoes, CARTOES))
    for nome, arq in feitos:
        print("  %-16s %5.0f KB  %s" % (nome, os.path.getsize(arq) / 1024, arq))
    if erros:
        print("\navisos do JavaScript (o menu chama APIs que exigem sessão,"
              "\nentão alguns são esperados):")
        for e in erros[:6]:
            print("  -", e)


if __name__ == "__main__":
    sys.exit(main())
