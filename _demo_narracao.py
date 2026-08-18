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

import unicodedata

import edge_tts

import _demo_montar as montar

VOZ = "pt-BR-ThalitaMultilingualNeural"
RATE = "+0%"
SAIDA = os.path.join("static", "demo_narracao.mp3")
TEMPOS = "_demo_tempos.json"
# Os respiros são o ritmo da demonstração. Ficaram curtos na primeira versão
# (0,7 e 1,0) e ela saiu apressada: uma frase emendava na outra e a troca de
# módulo passava sem o espectador perceber que mudou de assunto.
RESPIRO = 1.1          # segundos de silêncio no fim de cada fase
RESPIRO_SLIDE = 2.0    # respiro maior na virada de slide
ATRASO_INICIAL = 1.5   # silêncio antes da primeira palavra, para a capa entrar

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

LOGIN = (
    "Entrar é o CPF e uma senha de seis dígitos. Cada pessoa do escritório "
    "tem o seu acesso, com o que pode ver e o que pode mudar, e tudo o que "
    "ela faz fica registrado no log."
)

# O passeio pelo menu: a voz apresenta os dez módulos na ordem em que estão
# na tela, e cada cartão acende quando é citado. A palavra-gatilho de cada um
# está em MARCAS_MENU, e o instante sai da própria fala -- por isso mexer
# neste texto obriga a regerar o áudio, senão os cartões acendem fora de hora.
MENU = (
    "O sistema inteiro cabe num menu. "
    "Cadastros guarda o funcionário, a função e a empresa. "
    "Nova Folha abre e fecha o mês. "
    "Eventuais cuida de férias, rescisão e afastamento. "
    "Movimento é o que muda a cada mês: hora extra, falta, comissão. "
    "Fixo é o que se repete sozinho. "
    "Cálculo roda a folha. "
    "Relatórios põem tudo em PDF. "
    "Conexões levam o pagamento ao banco. "
    "O eSocial monta e transmite a remessa. "
    "E Diversos guarda o log."
)

# (palavra dita, posição do cartão no menu). "Movimento" e "Fixo" são cartões
# diferentes, e a busca anda sempre para a frente -- por isso funciona.
MARCAS_MENU = [
    ("Cadastros", 1), ("Nova", 2), ("Eventuais", 3), ("Movimento", 4),
    ("Fixo", 5), ("Cálculo", 6), ("Relatórios", 7), ("Conexões", 8),
    ("eSocial", 9), ("Diversos", 10),
]

FECHO = (
    "As conexões bancárias, com remessa em CNAB e PIX, estão chegando. "
    "Todo o resto que você viu está em produção, hoje. "
    "Processe o primeiro mês sem custo, sem compromisso e com suporte. "
    "Folha dez simples ponto com ponto bê erre."
)

# O que a voz destaca na GAVETA de cada módulo: (palavra dita, rótulo do
# botão). O botão é apontado pelo nome, nunca pelo número -- ver
# indice_do_botao(). E só entra aqui o que está VISÍVEL na foto: a gaveta
# mostra as seções todas, mas só os itens da seção aberta. Narrar um item de
# outra seção faria o realce cair em cima de nada.
MARCAS_GAVETA = {
    "cadastros": [
        ("Funcionário", "Funcionário"), ("inclui", "Incluir Funcionário"),
        ("altera", "Alterar Funcionário"), ("dependentes", "Dependentes"),
        ("ficha", "Ficha de Registro"), ("Tabelas", "Tabelas Auxiliares"),
        ("Pensão", "Pensão Alimentícia"), ("Empresa", "Empresa"),
    ],
    "novafolha": [
        ("Novo", "Novo Mês/Ano"), ("Outro", "Outro Mês/Ano"),
    ],
    "eventuais": [
        ("Férias", "Férias"), ("lança", "Lançar Férias"),
        ("calcula", "Calcular Férias"), ("recibo", "Recibo de Férias"),
        ("cancelar", "Cancelar Férias"), ("Salários", "Salários"),
        ("Rescisão", "Rescisão"), ("Contrato", "Contrato Temporário"),
        ("Afastamentos", "Afastamentos"), ("Faltas", "Faltas"),
        ("Exame", "Exame Médico"), ("Insalubridade", "Insalubridade"),
        ("FAP", "FAP"),
    ],
    "movimento": [
        ("Lançar", "Lançar Eventos"), ("Consignados", "Importar Consignados"),
        ("Ponto", "Importar Ponto"), ("Horas", "Horas Extras"),
        ("Faltas", "Faltas e Atrasos"), ("Listagens", "Listagens"),
        ("Adiantamento", "Adiantamento Quinzenal"),
    ],
    "movimentofixo": [
        ("Movimentos", "Movimentos Fixos"), ("Excluir", "Excluir / Parar"),
        ("Listagens", "Listagens"),
    ],
    "calculo": [
        ("Calcular", "Calcular Folha"), ("Visualizar", "Visualizar Cálculo"),
        ("Memória", "Memória de Cálculo"), ("Individual", "Cálculo Individual"),
        ("Verificar", "Verificar Inconsistências"),
        ("Adiantamento", "Adiantamento Quinzenal"),
    ],
    "relatorios": [
        ("Cadastros", "Cadastros"), ("Eventos", "Eventos"),
        ("Eventuais", "Eventuais"), ("Folha", "Folha de Pagamento"),
        ("Gerador", "Gerador de Relatório"), ("Sistema", "Sistema"),
        ("Lista", "Lista de Funcionários"), ("Funções", "Funções"),
        ("Rubricas", "Rubricas"), ("Dependentes", "Dependentes"),
        ("Ficha", "Ficha de Registro"),
    ],
    "esocial": [
        ("Tabelas", "Tabelas"), ("Periódicos", "Eventos Não Periódicos"),
        ("Periódicos", "Eventos Periódicos"), ("Exclusão", "Exclusão de Eventos"),
        ("Certificado", "Certificado Digital"), ("Remessas", "Remessas"),
        ("Consultas", "Consultas"), ("Admissão", "Admissão"),
        ("Desligamento", "Desligamento"),
    ],
}

ROTEIRO = {
    "cadastros": [
        "A gaveta de Cadastros abre em quatro partes. Em Funcionário você "
        "inclui, altera, lança dependentes e imprime a ficha de registro. "
        "Tabelas Auxiliares guarda a função, o horário, o sindicato e a "
        "verba. Ainda tem Pensão Alimentícia, e os dados da Empresa.",

        "Cada uma abre no mesmo padrão: o filtro em cima, a lista no meio, "
        "e o botão que vira PDF ao lado. Quem aprendeu uma tela aprendeu "
        "todas — é o mesmo desenho do começo ao fim do sistema.",

        "Na inclusão do funcionário, o cadastro já segue o leiaute do "
        "eSocial: é o mesmo que vai virar a admissão. Cargo, código da "
        "ocupação, horário e sindicato saem das tabelas que você cadastrou "
        "antes. Nada é digitado duas vezes.",
    ],
    "novafolha": [
        "A folha de cada mês nasce aqui. Novo Mês abre a competência; "
        "Outro Mês troca para uma que já existe.",

        "O mês aberto aparece no cabeçalho de todas as telas, com a situação "
        "ao lado: aberta, calculada ou fechada. Não tem como lançar no mês "
        "errado sem perceber, porque o mês está sempre à vista.",

        "Ao abrir o mês, os cadastros, os movimentos fixos e os afastamentos "
        "vêm juntos. Folha fechada trava o cálculo e libera o eSocial; "
        "reabrir é um clique, e fica registrado no log de operações.",
    ],
    "eventuais": [
        "Eventuais abre em nove partes. Em Férias você lança, calcula, tira "
        "o recibo e ainda pode cancelar. Ao lado: Salários, Rescisão, "
        "Contrato Temporário, Afastamentos, Faltas, Exame Médico, "
        "Insalubridade e o FAP.",

        "Cada assunto tem o ciclo inteiro: lançar, calcular, imprimir o "
        "recibo, listar e cancelar. Porque errar acontece, e desfazer "
        "precisa ser tão simples quanto fazer.",

        "Nas férias, informe o início e os dias. O sistema acha o período "
        "aquisitivo, calcula o um terço, o abono e as médias, e emite o "
        "recibo. A rescisão segue o mesmo caminho e termina na guia oficial, "
        "no modelo da portaria.",
    ],
    "movimento": [
        "No movimento do mês: Lançar Eventos, para a verba avulsa. "
        "Importar Consignados, da planilha do banco. Importar Ponto, "
        "Horas Extras, Faltas e Atrasos. Do lado, as Listagens e o "
        "Adiantamento Quinzenal.",

        "Lance para um funcionário, ou para vários de uma vez. A listagem "
        "mostra tudo o que entrou antes de calcular — conferir na hora sai "
        "bem mais barato do que corrigir depois.",

        "Digite o código da verba, ou procure pelo nome. Quantidade ou "
        "valor: o sistema sabe qual dos dois aquela verba pede. E o descanso "
        "semanal sobre a hora extra sai sozinho, na verba certa.",
    ],
    "movimentofixo": [
        "O que se repete todo mês entra uma vez só. Movimentos Fixos "
        "cadastra o vale transporte, o plano de saúde, o empréstimo. "
        "Excluir ou Parar encerra quando aquele desconto acabar. E as "
        "Listagens mostram o que está valendo.",

        "Cadastrar, listar, e parar quando acabar. Sempre com data de fim, "
        "sem apagar o histórico: o que já foi descontado continua lá, do "
        "jeito que saiu na folha daquele mês.",

        "O fixo entra em toda folha até a data de término, e aparece no "
        "contracheque como qualquer outra verba.",
    ],
    "calculo": [
        "Calcular Folha roda o mês inteiro. Visualizar mostra o resultado. "
        "A Memória abre a conta linha por linha. O Individual refaz um "
        "funcionário só, e Verificar Inconsistências avisa antes. Ao lado, "
        "o Adiantamento Quinzenal.",

        "Instituto, imposto de renda, fundo de garantia e salário família "
        "saem das tabelas legais embutidas. O mês da folha escolhe a tabela "
        "que valia naquele mês, então recalcular uma competência antiga não "
        "usa a tabela de hoje.",

        "E quando o valor não bate, a memória de cálculo mostra a conta, "
        "linha por linha: a base, a alíquota, a dedução e o resultado. É o "
        "que responde à pergunta do cliente sem você abrir uma planilha.",
    ],
    "relatorios": [
        "Relatórios abre por assunto: Cadastros, Eventos, Eventuais, "
        "Folha de Pagamento, o Gerador e o Sistema. Só nos cadastros já "
        "saem a Lista de Funcionários, as Funções, as Rubricas, os "
        "Dependentes e a Ficha de Registro.",

        "Todos saem em PDF, com o mesmo cabeçalho, filtrados por período, "
        "filial ou centro de custo. E o filtro que você montou hoje fica "
        "salvo para o mês que vem.",

        "Faltou algum? O gerador monta o seu: escolha as verbas, as colunas "
        "e a ordem, salve o modelo e rode todo mês. E o resumo fecha a folha "
        "com proventos, descontos, líquido e o custo da empresa.",
    ],
    "esocial": [
        "O eSocial é nativo, não é exportação. Abre em sete partes: as "
        "Tabelas, os eventos Não Periódicos, os Periódicos, a Exclusão, o "
        "Certificado Digital, as Remessas e as Consultas. Nos não "
        "periódicos ficam a Admissão e o Desligamento.",

        "Admitiu, calculou ou demitiu, a remessa entra na fila sozinha. "
        "Mas transmitir é sempre uma ação sua: nada sai daqui sem você "
        "mandar. Nem por engano, nem por automatismo.",

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
    """Grava o mp3 do trecho e devolve [(segundo, palavra), ...] do que disse.

    Vai pela API e não pela linha de comando por causa do
    boundary="WordBoundary". Sem ele -- e é o padrão -- a voz devolve a frase
    inteira num evento só, e não daria para saber quando ela chega em
    "Relatórios". É disso que sai o instante em que cada cartão do menu
    acende: medido na fala de verdade, não cronometrado no olho.
    """
    async def rodar():
        c = edge_tts.Communicate(texto, VOZ, rate=RATE,
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
    """Liga cada destaque ao segundo em que a palavra foi dita.

    Procura sempre para a frente, nunca do começo: é o que permite repetir a
    mesma palavra apontando para cartões diferentes.
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
        saida.append((round(palavras[k][0], 2), alvo))
        k += 1
    return saida


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

    lista = [("abertura", "Abertura", [ABERTURA]),
             ("login", "Login", [LOGIN]),
             ("menu", "Menu", [MENU])]
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
        fases, luz, alvos = [], [], []
        for i, fala in enumerate(falas):
            arq = os.path.join(tmp, "%s_%d.mp3" % (chave, i))
            palavras = falar(fala, arq)
            d = duracao(arq)
            # O respiro é maior na última fase da cena: é ali que o slide
            # inteiro troca, e emendar a fala de um módulo no outro sem
            # pausa faz a demonstração soar apressada.
            folga = RESPIRO_SLIDE if i == len(falas) - 1 else RESPIRO
            # Antes da primeira palavra vai um silêncio: sem ele a voz começa
            # junto com a capa, ainda em transição, e atropela a abertura.
            antes = ATRASO_INICIAL if not partes else 0.0
            # Os cartões do menu acendem contados da ENTRADA DA CENA, que é
            # também onde o áudio dela começa -- os dois relógios batem.
            if chave == "menu" and i == 0:
                luz = [seg + antes for seg, _ in casar(palavras, MARCAS_MENU)]
            # Fase 0 de um módulo é a gaveta: os botões citados crescem nela.
            elif i == 0 and chave in MARCAS_GAVETA:
                marcas = [(p, montar.indice_do_botao(chave, r))
                          for p, r in MARCAS_GAVETA[chave]]
                casadas = casar(palavras, marcas)
                luz = [seg for seg, _ in casadas]
                alvos = [i_botao for _, i_botao in casadas]
            partes.append(arq)
            inicio.append(t + antes)
            fases.append(round(antes + d + folga, 2))
            t += antes + d + folga
            nome = ["gaveta", "mosaico", "tela"][i] if len(falas) == 3 else "-"
            print("%-20.20s %-9s %5.1fs   %5.1fs"
                  % (titulo if i == 0 else "", nome, d, fases[-1]))
        cena = {"chave": chave, "titulo": titulo,
                "fases": fases, "dur": round(sum(fases), 2)}
        if luz:
            cena["luz"] = luz
            if alvos:
                cena["alvos"] = alvos
            print("%-20.20s %d destaques, de %.1fs a %.1fs dentro da cena"
                  % ("", len(luz), luz[0], luz[-1]))
        slides.append(cena)

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
