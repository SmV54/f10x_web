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

Nos slides 3 e 4 a voz enumera itens (os dez módulos, os cinco passos) e o
item citado cresce na tela. O instante de cada palavra não é chutado: a voz
devolve, junto com o áudio, o segundo exato em que disse cada palavra. Daí
sai o atraso de cada destaque, escrito direto no HTML. Por isso áudio e
destaques nascem na mesma passada -- gerar um sem o outro os desencontra.

Rodar:  python _gerar_narracao.py
Saída:  static/apresentacao_narracao.mp3
        + o bloco DESTAQUES do apresentacao_90s.html, reescrito

O tempo de cada slide TEM que bater com o data-dur do apresentacao_90s.html.
Mudou lá, muda aqui -- o script avisa se saírem de sincronia.
"""

import asyncio
import io
import os
import re
import subprocess
import sys
import unicodedata

import edge_tts

VOZ = "pt-BR-ThalitaMultilingualNeural"
SAIDA = os.path.join("static", "apresentacao_narracao.mp3")
FOLGA = 0.25          # segundos de respiro no fim de cada trecho
DEGRAUS = ["+0%", "+8%", "+16%", "+24%", "+32%"]

HTML = "apresentacao_90s.html"

# Onde cada destaque pega: o slide e como achar o item pelo número de ordem.
# Fora daqui nenhum item é animado -- outros slides também têm .tela-lista e
# acenderiam sozinhos, no tempo errado.
ALVOS = {
    3: ".slide:nth-of-type(3).on .chip:nth-child(%d)",
    4: ".slide:nth-of-type(4).on .tela-lista>div:nth-child(%d)",
}
CRESCE = ".85s"       # quanto dura o pulso de cada item

# (segundos do slide, fala) ou (segundos, fala, destaques).
# Em destaques, cada par é (palavra dita, item que cresce). A palavra é
# procurada na ordem em que aparece na fala, então "movimento" duas vezes
# acende primeiro o Movimento Mês e depois o Movimento Fixo, sem ambiguidade.
# A ordem é a dos <section class="slide"> do HTML.
ROTEIRO = [
    (7,  "Folha dez Simples: a folha inteira dentro do navegador, "
         "sem instalar nada."),

    (8,  "Dois problemas, todo mês: o sistema numa máquina só, "
         "e o eSocial que muda de layout e rejeita evento."),

    # Antes a fala citava oito dos dez cartões, e "movimento" servia para os
    # dois. Com o destaque isso viraria buraco: dois cartões nunca acenderiam.
    # Agora nomeia os dez, na ordem em que estão na tela, e o slide ganhou os
    # segundos a mais de que a lista precisa.
    (14, "Dez módulos num menu só: cadastros, mês e ano, eventuais, "
         "movimento do mês, movimento fixo, cálculo, relatórios, "
         "conexões, eSocial e diversos.",
     [("cadastros", 1), ("mês", 2), ("eventuais", 3), ("movimento", 4),
      ("movimento", 5), ("cálculo", 6), ("relatórios", 7), ("conexões", 8),
      ("eSocial", 9), ("diversos", 10)]),

    (9,  "O caminho é sempre o mesmo: cadastrar, lançar, calcular, "
         "conferir e enviar. O eSocial sai da mesma folha.",
     [("cadastrar", 1), ("lançar", 2), ("calcular", 3),
      ("conferir", 4), ("enviar", 5)]),

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
    """Grava o mp3 do trecho e devolve [(segundo, palavra), ...] do que disse.

    Vai pela API e não pela linha de comando por um motivo só: o
    boundary="WordBoundary". Sem ele -- e é o padrão -- a voz devolve a
    frase inteira num evento só, e não daria para saber quando ela chega em
    "relatórios". Pelo CLI não há como pedir isso.

    Os tempos são do trecho, contados do zero; quem soma o segundo em que o
    slide entra é o main.
    """
    async def rodar():
        c = edge_tts.Communicate(texto, VOZ, rate=rate,
                                 boundary="WordBoundary")
        palavras = []
        with open(destino, "wb") as f:
            async for ch in c.stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "WordBoundary":
                    # offset vem em unidades de 100 nanossegundos
                    palavras.append((ch["offset"] / 1e7, ch["text"]))
        return palavras

    return asyncio.run(rodar())


def simples(s):
    """Sem acento e em minúscula, para casar "cálculo" com o que a voz disse."""
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if not unicodedata.combining(c))


def casar(palavras, marcas):
    """Liga cada destaque do roteiro ao segundo em que a palavra foi dita.

    Procura sempre para a frente, nunca do começo: é o que permite repetir a
    mesma palavra ("movimento") apontando para itens diferentes.
    """
    saida, k = [], 0
    for palavra, alvo in marcas:
        p = simples(palavra)
        while k < len(palavras) and simples(palavras[k][1]) != p:
            k += 1
        if k >= len(palavras):
            raise SystemExit(
                "ERRO: a voz nunca disse %r -- confira a grafia no roteiro.\n"
                "      Ela disse: %s"
                % (palavra, " ".join(w for _, w in palavras)))
        saida.append((palavras[k][0], alvo))
        k += 1
    return saida


def partes_do_roteiro(linha):
    """Aceita (dur, fala) e (dur, fala, destaques) na mesma lista."""
    return (linha[0], linha[1], linha[2] if len(linha) > 2 else [])


def conferir_html():
    """Avisa se os tempos daqui saíram de sincronia com os do HTML."""
    try:
        h = io.open(HTML, encoding="utf-8").read()
    except OSError:
        return
    durs = [float(d) for d in re.findall(r'class="slide[^"]*"[^>]*data-dur="([\d.]+)"', h)]
    meus = [float(partes_do_roteiro(l)[0]) for l in ROTEIRO]
    if durs and durs != meus:
        print("ATENÇÃO: os tempos do HTML mudaram.")
        print("  HTML:", durs)
        print("  aqui:", meus)


def escrever_html(destaques, total):
    """Reescreve no HTML o bloco que depende dos tempos da narração.

    Vão dois assuntos no mesmo bloco, porque os dois saem das durações:

    - o atraso de cada destaque, medido na fala de verdade;
    - a duração do modo sem JavaScript, em que os slides passam por animação
      de CSS. Esses tempos são porcentagens de um total fixo. Ficavam escritos
      à mão e, no dia em que um slide mudasse de duração, passariam a mostrar
      o slide errado sem avisar ninguém.
    """
    h = io.open(HTML, encoding="utf-8").read()
    ini, fim = "/* DESTAQUES-INICIO", "/* DESTAQUES-FIM */"
    a, b = h.find(ini), h.find(fim)
    if a < 0 or b < 0:
        raise SystemExit("ERRO: não achei as marcas DESTAQUES no %s." % HTML)

    linhas = [ini + " — bloco gerado por _gerar_narracao.py, não editar à mão */",
              "/* pulso de cada item, no segundo em que a voz o cita */"]
    for seletor, atraso in destaques:
        linhas.append("%s{animation:destacar %s both %.2fs}"
                      % (seletor, CRESCE, atraso))

    linhas.append("/* modo sem JavaScript: os mesmos %ds, em porcentagem */"
                  % total)
    linhas.append("html:not(.js) .slide{animation-duration:%ds}" % total)
    t = 0.0
    for i, linha in enumerate(ROTEIRO, 1):
        dur = partes_do_roteiro(linha)[0]
        entra, sai = t / total * 100, (t + dur) / total * 100
        if i == 1:
            quadros = "0%%{opacity:1}%.3f%%{opacity:0}100%%{opacity:0}" % sai
        elif i == len(ROTEIRO):
            quadros = "0%%{opacity:0}%.3f%%{opacity:1}100%%{opacity:1}" % entra
        else:
            quadros = ("0%%{opacity:0}%.3f%%{opacity:1}%.3f%%{opacity:0}"
                       "100%%{opacity:0}" % (entra, sai))
        linhas.append("@keyframes cena%d{%s}" % (i, quadros))
        t += dur
    linhas.append(fim)

    io.open(HTML, "w", encoding="utf-8", newline="").write(
        h[:a] + "\n".join(linhas) + h[b + len(fim):])
    print("%s: %d destaques e os tempos do modo sem JavaScript"
          % (HTML, len(destaques)))


def main():
    conferir_html()
    tmp = os.path.join("static", "_narr_tmp")
    os.makedirs(tmp, exist_ok=True)

    partes, inicio, destaques, t = [], [], [], 0.0
    for i, linha in enumerate(ROTEIRO):
        dur, texto, marcas = partes_do_roteiro(linha)
        alvo = dur - FOLGA
        arq = os.path.join(tmp, "seg%02d.mp3" % i)
        for rate in DEGRAUS:
            palavras = falar(texto, rate, arq)
            d = duracao(arq)
            if d <= alvo:
                break
        marca = "ok " if d <= alvo else "ESTOURA"
        print("slide %2d  %4.1fs de %ds  rate %-5s  %s" % (i + 1, d, dur, rate, marca))

        # Os tempos têm que sair da tomada ACEITA: se a fala foi refeita mais
        # rápida para caber, as palavras da primeira tentativa cairiam tarde.
        if marcas:
            seletor = ALVOS[i + 1]
            # O atraso é contado da ENTRADA DO SLIDE, não do início da
            # apresentação: a animação do CSS só começa quando o slide passa
            # a ser exibido. E é aí também que a fala dele começa, então os
            # dois relógios batem -- inclusive se o usuário voltar um slide.
            for segundo, item in casar(palavras, marcas):
                destaques.append((seletor % item, segundo))
            print("          %d destaques, de %.1fs a %.1fs dentro do slide"
                  % (len(marcas), destaques[-len(marcas)][1],
                     destaques[-1][1]))

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

    escrever_html(destaques, int(t))
    print("\nFalta regerar a versão com voz embutida:"
          "\n  python _gerar_apresentacao_offline.py")


if __name__ == "__main__":
    main()
