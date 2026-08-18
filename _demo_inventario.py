# -*- coding: utf-8 -*-
"""Extrai do menu real a lista de telas que a demonstração vai mostrar.

Por que existe: a demo tem que percorrer o sistema INTEIRO, e a única fonte
confiável do que existe é o objeto `modulos` do templates/F10_Menu.html --
o mesmo que desenha o menu para o usuário. Manter uma lista à parte
garantiria que, no dia em que uma tela nova entrasse no menu, a demo
continuaria mostrando o sistema de ontem sem ninguém perceber.

Saída: _demo_telas.json  (módulo, seção, nome, href, ok)

Rodar:  python _demo_inventario.py
"""

import io
import json
import re

MENU = "templates/F10_Menu.html"
SAIDA = "_demo_telas.json"

# O módulo do Administrador não entra: a demo é de venda, para quem ainda
# não é cliente, e essas telas são da equipe F10.
FORA = {"interno_f10"}


def bloco_modulos(texto):
    """Recorta o objeto `modulos` contando chaves, do `{` ao `}` que fecha."""
    i = texto.index("const modulos = {")
    i = texto.index("{", i)
    nivel, j = 0, i
    while j < len(texto):
        if texto[j] == "{":
            nivel += 1
        elif texto[j] == "}":
            nivel -= 1
            if nivel == 0:
                return texto[i:j + 1]
        j += 1
    raise SystemExit("ERRO: não achei o fim do objeto modulos.")


def campo(trecho, nome):
    """Lê `nome: 'valor'` de um item, aceitando aspas simples com acento."""
    m = re.search(r"\b%s:\s*'((?:[^'\\]|\\.)*)'" % nome, trecho)
    return m.group(1).replace("\\'", "'") if m else ""


def main():
    texto = io.open(MENU, encoding="utf-8").read()
    corpo = bloco_modulos(texto)

    # Cada módulo começa numa linha `  chave: {` com 4 espaços de recuo.
    inicios = [(m.start(), m.group(1))
               for m in re.finditer(r"\n    ([a-z_0-9]+):\s*\{", corpo)]
    telas, modulos = [], []

    for k, (pos, chave) in enumerate(inicios):
        fim = inicios[k + 1][0] if k + 1 < len(inicios) else len(corpo)
        bloco = corpo[pos:fim]
        titulo = campo(bloco, "titulo")
        icone = campo(bloco, "icone")
        if chave in FORA:
            continue
        modulos.append({"chave": chave, "titulo": titulo, "icone": icone})

        # As seções aparecem como `{ nome: 'X', ... itens: [`; tudo o que vem
        # depois, até a próxima seção, pertence a ela.
        secoes = [(m.start(), m.group(1))
                  for m in re.finditer(r"\{\s*nome:\s*'((?:[^'\\]|\\.)*)'"
                                       r"[^\n]*?itens:\s*\[", bloco)]

        # Nova Folha monta as seções por função, não por lista literal: o
        # nome da seção só existe no `return`, depois dos itens. Sem este
        # desvio o módulo sairia vazio -- e vazio em silêncio, que é pior.
        if not secoes:
            m = re.search(r"return\s*\[\{\s*nome:\s*'((?:[^'\\]|\\.)*)'", bloco)
            secoes = [(0, m.group(1) if m else "")]
        for s, (spos, snome) in enumerate(secoes):
            sfim = secoes[s + 1][0] if s + 1 < len(secoes) else len(bloco)
            for m in re.finditer(r"\{\s*icone:[^\n]*\}", bloco[spos:sfim]):
                item = m.group(0)
                href = campo(item, "href")
                telas.append({
                    "modulo": chave,
                    "modulo_titulo": titulo,
                    "secao": snome,
                    "icone": campo(item, "icone"),
                    "nome": campo(item, "nome"),
                    "href": href,
                    "ok": bool(re.search(r"\bok:\s*true", item)) and href != "#",
                })

    # A mesma tela aparece em mais de um módulo (a Ficha de Registro está em
    # Cadastros e em Relatórios, por exemplo). Para a captura isso é trabalho
    # repetido: o arquivo do print é o mesmo, então basta capturar uma vez.
    vistos, unicas = set(), 0
    for t in telas:
        t["repetida"] = t["href"] in vistos
        if t["ok"] and not t["repetida"]:
            unicas += 1
        vistos.add(t["href"])

    io.open(SAIDA, "w", encoding="utf-8").write(
        json.dumps({"modulos": modulos, "telas": telas},
                   ensure_ascii=False, indent=1))

    print("%d módulos, %d itens de menu" % (len(modulos), len(telas)))
    print("%d com tela pronta (%d prints a capturar, sem repetir)"
          % (sum(1 for t in telas if t["ok"]), unicas))
    print("%d ainda sem rota (não entram na demo)"
          % sum(1 for t in telas if not t["ok"]))
    print()
    for mo in modulos:
        do_mod = [t for t in telas if t["modulo"] == mo["chave"]]
        print("  %-16s %2d itens, %2d prontos, %d seções"
              % (mo["titulo"], len(do_mod),
                 sum(1 for t in do_mod if t["ok"]),
                 len({t["secao"] for t in do_mod})))
    print("\n%s gravado." % SAIDA)


if __name__ == "__main__":
    main()
