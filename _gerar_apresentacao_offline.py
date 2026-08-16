# -*- coding: utf-8 -*-
"""Gera a apresentação de 90 segundos num arquivo HTML só, com a voz dentro.

Por que existe: o apresentacao_90s.html busca a narração em
/static/apresentacao_narracao.mp3. Isso funciona pelo link (/apresentacao),
onde quem serve o arquivo é o Flask, mas não funciona com duplo clique nem
num pendrive: em file:// o navegador não acha /static, e a apresentação
passa muda. Aqui o mp3 entra embutido no próprio HTML, em base64, e o
arquivo vira autossuficiente -- roda offline, em qualquer máquina, sem
servidor e sem instalar nada.

A música NÃO precisa de arquivo: é sintetizada por WebAudio no próprio
JavaScript. Por isso o mp3 da voz é a única coisa que falta embutir.

Rodar:  python _gerar_apresentacao_offline.py
Saída:  Comercial/Folha10-Simples - Apresentacao 90s (com voz).html

O arquivo de saída é DERIVADO: mudou o HTML ou a narração, é só rodar de
novo. Não edite a saída à mão, porque a próxima rodada apaga a alteração.
"""

import base64
import io
import os
import re
import sys

ORIGEM = "apresentacao_90s.html"
AUDIO = os.path.join("static", "apresentacao_narracao.mp3")
SAIDA = os.path.join("Comercial",
                     "Folha10-Simples - Apresentacao 90s (com voz).html")

# O que trocar pelo áudio embutido. Se o HTML mudar o caminho do mp3, esta
# busca falha e o script para -- melhor parar do que entregar uma
# apresentação muda achando que deu certo.
ALVO = 'src="/static/apresentacao_narracao.mp3"'


def kb(n):
    return "%.1f MB" % (n / 1048576.0) if n >= 1048576 else "%.0f KB" % (n / 1024.0)


def main():
    for arq in (ORIGEM, AUDIO):
        if not os.path.exists(arq):
            print("ERRO: não achei %s (rode a partir da pasta do projeto)." % arq)
            return 1

    html = io.open(ORIGEM, encoding="utf-8").read()
    if ALVO not in html:
        print("ERRO: não achei no HTML a marca do áudio:")
        print("  %s" % ALVO)
        print("O caminho do mp3 mudou? Ajuste o ALVO deste script.")
        return 1

    mp3 = open(AUDIO, "rb").read()
    b64 = base64.b64encode(mp3).decode("ascii")
    html = html.replace(ALVO, 'src="data:audio/mpeg;base64,%s"' % b64)

    # Confere se sobrou alguma outra coisa vinda de fora. Se sobrar, o
    # arquivo ainda depende do servidor e o duplo clique quebra em algum
    # ponto -- avisa em vez de deixar a surpresa para o comercial.
    fora = [r for r in re.findall(r'(?:src|href)="([^"]+)"', html)
            if not r.startswith("data:")]
    if fora:
        print("ATENÇÃO: ainda há referência(s) externa(s):")
        for r in sorted(set(fora)):
            print("  %s" % r)

    pasta = os.path.dirname(SAIDA)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    io.open(SAIDA, "w", encoding="utf-8", newline="").write(html)

    print("slides   %s  (%s)" % (kb(os.path.getsize(ORIGEM)), ORIGEM))
    print("voz      %s  (%s)" % (kb(len(mp3)), AUDIO))
    print("saída    %s  (%s)" % (kb(os.path.getsize(SAIDA)), SAIDA))
    print()
    print("Pronto. Este arquivo roda com duplo clique, sem servidor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
