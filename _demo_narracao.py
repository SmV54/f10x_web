# -*- coding: utf-8 -*-
"""Gera a narração da demonstração longa (demo_comercial.html).

Mesma técnica da apresentação de 90 s ([[_gerar_narracao.py]]): voz neural
Thalita pelo edge-tts, cada trecho gravado sozinho, medido, e todos colados
num arquivo só, cada um no segundo em que a cena entra.

A DIFERENÇA para a de 90 s, e é o ponto deste script: lá o tempo do slide
era fixo e a voz era acelerada até caber. Aqui é o contrário -- quem manda é
a fala. Motivo prático: os módulos são desiguais. Eventuais tem 36 telas e
Movimento Fixo tem 3; dar 42 segundos aos dois deixava meio minuto de
silêncio em cima de três telas. Agora cada fase dura o que a frase dela
durou, mais um respiro, e o _demo_montar.py escreve esses tempos no HTML.

Cada módulo tem TRÊS falas, uma por fase do bloco:
    gaveta   -- o menu aberto, com todos os submenus
    mosaico  -- as telas do módulo em miniatura
    tela     -- uma tela em tamanho cheio, com digitação simulada

Rodar:  python _demo_narracao.py         (precisa de internet)
Saída:  static/demo_narracao.mp3
        _demo_tempos.json    -> depois:  python _demo_montar.py

Os dois passos são um só assunto: mexer no roteiro sem regerar o HTML deixa
a voz correndo por cima da cena errada.
"""

import asyncio
import io
import json
import os
import re
import subprocess
import sys

import edge_tts

import _demo_montar as montar

VOZ = "pt-BR-ThalitaMultilingualNeural"
RATE = "+0%"
SAIDA = os.path.join("static", "demo_narracao.mp3")
TEMPOS = "_demo_tempos.json"
RESPIRO = 0.7          # segundos de silêncio no fim de cada fase
RESPIRO_SLIDE = 1.0    # respiro maior na virada de slide

# A fala de cada cena. As chaves dos módulos são as do menu -- se um módulo
# entrar ou sair do inventário, o script para e diz qual, em vez de narrar
# um sistema que não é mais este.
#
# Sem sigla escrita: "S-1200" a voz lê como "esse menos mil e duzentos". Os
# eventos são citados pelo nome ("a remuneração", "o desligamento"), que é
# como o cliente entende de qualquer forma.
ABERTURA = (
    "Folha dez Simples: a folha de pagamento inteira dentro do navegador. "
    "Nada para instalar, nada para atualizar. Do cadastro do funcionário ao "
    "recibo do eSocial, num sistema só. E sempre à vista, no alto de toda "
    "tela: a empresa, o mês que está aberto e a validade do certificado."
)

FECHO = (
    "As conexões bancárias, com remessa em CNAB e PIX, estão chegando. "
    "Todo o resto que você viu está em produção, hoje. "
    "Processe o primeiro mês sem custo, sem compromisso e com suporte. "
    "Folha dez simples ponto com ponto bê erre."
)

ROTEIRO = {
    "cadastros": [
        "Tudo começa no cadastro. Dezoito telas num menu só: funcionário, "
        "dependentes, funções, horários, sindicatos, vale transporte, "
        "rubricas, centros de custo, filiais e a própria empresa.",

        "Cada uma abre no mesmo padrão: o filtro em cima, a lista no meio, "
        "e o botão que vira PDF ao lado.",

        "Na inclusão do funcionário, o cadastro já segue o leiaute do "
        "eSocial: é o mesmo que vai virar a admissão. Cargo, código da "
        "ocupação, horário e sindicato saem das tabelas que você cadastrou "
        "antes. Nada é digitado duas vezes.",
    ],
    "novafolha": [
        "A folha de cada mês nasce aqui: abrir a competência, trocar de mês, "
        "fechar, reabrir.",

        "O mês aberto aparece no cabeçalho de todas as telas, com a situação "
        "ao lado: aberta, calculada ou fechada.",

        "Ao abrir o mês, os cadastros, os movimentos fixos e os afastamentos "
        "vêm juntos. Folha fechada trava o cálculo e libera o eSocial; "
        "reabrir é um clique, e fica registrado no log de operações.",
    ],
    "eventuais": [
        "Eventuais é o módulo mais largo, trinta e seis telas: férias, "
        "alteração de salário, aviso prévio, rescisão, contrato de "
        "experiência, afastamentos, acidente de trabalho, faltas, exames "
        "médicos e insalubridade.",

        "Cada assunto tem o ciclo inteiro: lançar, calcular, imprimir o "
        "recibo, listar e cancelar. Porque errar acontece.",

        "Nas férias, informe o início e os dias. O sistema acha o período "
        "aquisitivo, calcula o um terço, o abono e as médias, e emite o "
        "recibo. A rescisão segue o mesmo caminho e termina na guia oficial, "
        "no modelo da portaria.",
    ],
    "movimento": [
        "No movimento do mês entram as verbas que variam: horas extras, "
        "faltas, adicionais, comissões, e os consignados importados da "
        "planilha do banco.",

        "Lance para um funcionário, ou para vários de uma vez. A listagem "
        "mostra tudo o que entrou, antes de calcular.",

        "Digite o código da verba, ou procure pelo nome. Quantidade ou "
        "valor: o sistema sabe qual dos dois aquela verba pede. E o descanso "
        "semanal sobre a hora extra sai sozinho, na verba certa.",
    ],
    "movimentofixo": [
        "O que se repete todo mês entra uma vez só: vale transporte, plano "
        "de saúde, empréstimo, pensão.",

        "Três telas: cadastrar, listar, e parar quando acabar. Com data de "
        "fim, sem apagar o histórico.",

        "O fixo entra em toda folha até a data de término, e aparece no "
        "contracheque como qualquer outra verba.",
    ],
    "calculo": [
        "Calcular é um botão. A folha inteira, ou um funcionário só, e o "
        "adiantamento quinzenal com recibo próprio.",

        "Instituto, imposto de renda, fundo de garantia e salário família "
        "saem das tabelas legais embutidas. O mês da folha escolhe a tabela "
        "que valia naquele mês.",

        "E quando o valor não bate, a memória de cálculo mostra a conta, "
        "linha por linha: a base, a alíquota, a dedução e o resultado. É o "
        "que responde à pergunta do cliente sem você abrir uma planilha.",
    ],
    "relatorios": [
        "Dezenove relatórios prontos: folha de pagamento, contracheque, "
        "resumo, relação dos líquidos, ficha financeira, recibo de pensão e "
        "o log de operações.",

        "Todos saem em PDF, com o mesmo cabeçalho, filtrados por período, "
        "filial ou centro de custo.",

        "Faltou algum? O gerador monta o seu: escolha as verbas, as colunas "
        "e a ordem, salve o modelo e rode todo mês. E o resumo fecha a folha "
        "com proventos, descontos, líquido e o custo da empresa.",
    ],
    "esocial": [
        "O eSocial é nativo, não é exportação. Vinte e três telas: as "
        "tabelas do empregador, as rubricas, as lotações, a admissão, o "
        "desligamento, a remuneração, os pagamentos e o fechamento do mês.",

        "Admitiu, calculou ou demitiu, a remessa entra na fila sozinha. "
        "Transmitir é sempre uma ação sua: nada sai daqui sem você mandar.",

        "Na fila você vê o arquivo, envia, e o recibo do governo volta "
        "gravado ao lado do evento. E a verificação compara o que o eSocial "
        "recebeu com o que a folha calculou. A diferença aparece na tela, "
        "antes de virar multa.",
    ],
}


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


def falar(texto, destino):
    """Grava o mp3 do trecho. Devolve nada -- aqui não há destaque a casar."""
    async def rodar():
        c = edge_tts.Communicate(texto, VOZ, rate=RATE)
        with open(destino, "wb") as f:
            async for ch in c.stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
    asyncio.run(rodar())


def cenas():
    """A lista de cenas na ordem exata dos slides do demo_comercial.html.

    Sai do mesmo inventário e do mesmo filtro que o montador usa, e não de
    uma lista escrita aqui: se as duas listas fossem independentes, o dia em
    que um módulo entrasse no menu a voz continuaria narrando o de ontem,
    deslocada de um slide para sempre.

    Devolve [(chave, rótulo, [falas...]), ...].
    """
    if not os.path.exists(montar.INVENTARIO):
        raise SystemExit("ERRO: falta o %s. Rode antes:\n"
                         "  python _demo_inventario.py" % montar.INVENTARIO)
    dados = json.load(io.open(montar.INVENTARIO, encoding="utf-8"))
    telas = dados["telas"]

    lista = [("abertura", "Abertura", [ABERTURA])]
    vistos = set()
    for mod in dados["modulos"]:
        if mod["chave"] in montar.MODULOS_NO_FECHO:
            continue
        if not [t for t in telas if t["modulo"] == mod["chave"] and t["ok"]]:
            continue
        if mod["chave"] not in ROTEIRO:
            raise SystemExit(
                "ERRO: o módulo %r (%s) entrou no menu e não tem fala.\n"
                "      Escreva as três falas dele no ROTEIRO deste script:\n"
                "      gaveta, mosaico e tela cheia."
                % (mod["chave"], mod["titulo"]))
        falas = ROTEIRO[mod["chave"]]
        if len(falas) != 3:
            raise SystemExit("ERRO: %r tem %d falas; são 3 (gaveta, mosaico, "
                             "tela)." % (mod["chave"], len(falas)))
        lista.append((mod["chave"], mod["titulo"], falas))
        vistos.add(mod["chave"])
    lista.append(("fecho", "Fecho", [FECHO]))

    sobrando = set(ROTEIRO) - vistos
    if sobrando:
        raise SystemExit(
            "ERRO: o roteiro fala de módulo que o menu não tem mais: %s.\n"
            "      Tire do ROTEIRO, ou confira o _demo_telas.json."
            % ", ".join(sorted(sobrando)))
    return lista


def main():
    lista = cenas()
    tmp = os.path.join("static", "_demo_narr_tmp")
    os.makedirs(tmp, exist_ok=True)
    os.makedirs("static", exist_ok=True)

    partes, inicio, slides, t = [], [], [], 0.0
    print("cena                 fase       fala   +respiro")
    print("-" * 52)
    for chave, titulo, falas in lista:
        fases = []
        for i, fala in enumerate(falas):
            arq = os.path.join(tmp, "%s_%d.mp3" % (chave, i))
            falar(fala, arq)
            d = duracao(arq)
            # O respiro é maior na última fase da cena: é ali que o slide
            # inteiro troca, e emendar a fala de um módulo no outro sem
            # pausa faz a demonstração soar apressada.
            folga = RESPIRO_SLIDE if i == len(falas) - 1 else RESPIRO
            partes.append(arq)
            inicio.append(t)
            fases.append(round(d + folga, 2))
            t += d + folga
            nome = ["gaveta", "mosaico", "tela"][i] if len(falas) == 3 else "-"
            print("%-20.20s %-9s %5.1fs   %5.1fs"
                  % (titulo if i == 0 else "", nome, d, d + folga))
        slides.append({"chave": chave, "titulo": titulo,
                       "fases": fases, "dur": round(sum(fases), 2)})

    # Um arquivo só: cada trecho é atrasado até o segundo em que a fase entra
    # e todos são somados. Como não se sobrepõem, somar não mistura nada.
    entradas = []
    for p in partes:
        entradas += ["-i", p]
    filtro = "".join("[%d:a]adelay=%d|%d[a%d];" % (i, int(s * 1000), int(s * 1000), i)
                     for i, s in enumerate(inicio))
    filtro += "".join("[a%d]" % i for i in range(len(partes)))
    filtro += "amix=inputs=%d:normalize=0,alimiter=limit=0.95[out]" % len(partes)

    subprocess.run([ffmpeg(), "-y"] + entradas +
                   ["-filter_complex", filtro, "-map", "[out]",
                    "-t", "%.2f" % t, "-ac", "1", "-ar", "24000",
                    "-b:a", "64k", SAIDA],
                   check=True, capture_output=True)

    for p in partes:
        os.remove(p)
    os.rmdir(tmp)

    io.open(TEMPOS, "w", encoding="utf-8").write(
        json.dumps({"total": round(t, 2), "voz": VOZ, "slides": slides},
                   ensure_ascii=False, indent=1))

    print("-" * 52)
    print("%s  %.1fs (%d min %02d s)  %.0f KB"
          % (SAIDA, duracao(SAIDA), int(t) // 60, int(t) % 60,
             os.path.getsize(SAIDA) / 1024))
    print("%s gravado com %d cenas." % (TEMPOS, len(slides)))
    print("\nAgora regere o HTML para os tempos entrarem nele:"
          "\n  python _demo_montar.py")


if __name__ == "__main__":
    sys.exit(main())
