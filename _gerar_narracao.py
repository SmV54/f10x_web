# -*- coding: utf-8 -*-
"""Gera a narração da apresentação de 90 segundos (/apresentacao).

Por que existe: a primeira narração foi feita com a voz SAPI antiga do
Windows (Microsoft Maria Desktop), que arrasta as sílabas, e o roteiro não
foi guardado em lugar nenhum -- só sobrou o arquivo de áudio. Aqui o texto
fica versionado junto com o código, e a voz passa a ser neural (edge-tts,
o mesmo motor do "Ler em voz alta" do Edge; gratuito, mas exige internet).

Como funciona: cada slide tem um trecho de fala e um tempo de tela. O
trecho é gerado sozinho, medido, e -- se passar do tempo do slide -- é
refeito mais rápido, em degraus, até caber. No fim tudo é montado num
arquivo só, com cada fala começando exatamente no segundo em que o slide
entra. Assim a voz nunca desencontra da imagem, mesmo que um trecho sobre
ou falte tempo.

Rodar:  python _gerar_narracao.py
Saída:  static/apresentacao_narracao.mp3

O tempo de cada slide TEM que bater com o data-dur do apresentacao_90s.html.
Mudou lá, muda aqui.
"""

import io
import os
import re
import subprocess
import sys

VOZ = "pt-BR-ThalitaMultilingualNeural"
SAIDA = os.path.join("static", "apresentacao_narracao.mp3")
FOLGA = 0.25          # segundos de respiro no fim de cada trecho
DEGRAUS = ["+0%", "+8%", "+16%", "+24%", "+32%"]

# (segundos do slide, fala). A ordem é a dos <section class="slide"> do HTML.
ROTEIRO = [
    (7,  "Folha dez Simples: a folha inteira dentro do navegador, "
         "sem instalar nada."),

    (8,  "Dois problemas, todo mês: o sistema numa máquina só, "
         "e o eSocial que muda de layout e rejeita evento."),

    (9,  "Dez módulos num menu só: cadastros, competência, eventuais, "
         "movimento, cálculo, relatórios, conexões e eSocial."),

    (8,  "O caminho é sempre o mesmo: cadastrar, lançar, calcular, "
         "conferir e enviar. O eSocial sai da mesma folha."),

    (8,  "Filtre por situação, função, admissão ou férias. "
         "Marque vários de uma vez e lance em lote."),

    (8,  "A folha em uma tela: proventos, descontos, líquido "
         "e o INSS da empresa. Um clique, e vira PDF."),

    (8,  "Faltou um relatório? Monte o seu: escolha o período e as seções, "
         "salve o modelo e rode todo mês."),

    (10, "O eSocial é nativo: admitiu, calculou ou demitiu, a remessa entra "
         "na fila sozinha. E a verificação mostra a diferença "
         "antes de virar multa."),

    (7,  "Não é só a folha mensal: férias, rescisão, décimo terceiro, "
         "pensão, consignados e afastamentos."),

    (7,  "Dez módulos, cento e cinquenta e oito telas, "
         "treze eventos do eSocial. Em produção, hoje."),

    (10, "Processe o primeiro mês sem custo, sem compromisso e com suporte. "
         "Acesse folha dez simples ponto com ponto bê erre."),
]


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duracao(caminho):
    """Segundos de um arquivo de áudio, lidos da saída do próprio ffmpeg."""
    p = subprocess.run([ffmpeg(), "-i", caminho], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr or "")
    if not m:
        raise RuntimeError("não consegui medir " + caminho)
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def falar(texto, rate, destino):
    subprocess.run([sys.executable, "-m", "edge_tts", "--voice", VOZ,
                    "--rate", rate, "--text", texto,
                    "--write-media", destino],
                   check=True, capture_output=True)


def conferir_html():
    """Avisa se os tempos daqui saíram de sincronia com os do HTML."""
    try:
        h = io.open("apresentacao_90s.html", encoding="utf-8").read()
    except OSError:
        return
    durs = [float(d) for d in re.findall(r'class="slide[^"]*"[^>]*data-dur="([\d.]+)"', h)]
    meus = [float(d) for d, _ in ROTEIRO]
    if durs and durs != meus:
        print("ATENÇÃO: os tempos do HTML mudaram.")
        print("  HTML:", durs)
        print("  aqui:", meus)


def main():
    conferir_html()
    tmp = os.path.join("static", "_narr_tmp")
    os.makedirs(tmp, exist_ok=True)

    partes, inicio, t = [], [], 0.0
    for i, (dur, texto) in enumerate(ROTEIRO):
        alvo = dur - FOLGA
        arq = os.path.join(tmp, "seg%02d.mp3" % i)
        for rate in DEGRAUS:
            falar(texto, rate, arq)
            d = duracao(arq)
            if d <= alvo:
                break
        marca = "ok " if d <= alvo else "ESTOURA"
        print("slide %2d  %4.1fs de %ds  rate %-5s  %s" % (i + 1, d, dur, rate, marca))
        partes.append(arq)
        inicio.append(t)
        t += dur

    # Monta tudo num arquivo só: cada trecho é atrasado até o segundo em que
    # o slide entra e os onze são somados. Como não se sobrepõem, somar não
    # mistura nada -- é só colar cada fala no seu lugar da linha do tempo.
    entradas = []
    for p in partes:
        entradas += ["-i", p]
    filtro = "".join("[%d:a]adelay=%d|%d[a%d];" % (i, int(s * 1000), int(s * 1000), i)
                     for i, s in enumerate(inicio))
    filtro += "".join("[a%d]" % i for i in range(len(partes)))
    filtro += "amix=inputs=%d:normalize=0,alimiter=limit=0.95[out]" % len(partes)

    subprocess.run([ffmpeg(), "-y"] + entradas +
                   ["-filter_complex", filtro, "-map", "[out]",
                    "-t", str(int(t)), "-ac", "1", "-ar", "24000",
                    "-b:a", "64k", SAIDA],
                   check=True, capture_output=True)

    for p in partes:
        os.remove(p)
    os.rmdir(tmp)
    print("\n%s  %.1fs  %.0f KB" % (SAIDA, duracao(SAIDA), os.path.getsize(SAIDA) / 1024))


if __name__ == "__main__":
    main()
