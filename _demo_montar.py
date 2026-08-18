# -*- coding: utf-8 -*-
"""Monta o HTML da demonstração comercial a partir do inventário + prints.

Por que é gerado e não escrito à mão: são 109 telas. Um HTML manual ficaria
desatualizado no dia em que uma tela entrasse no menu, e ninguém perceberia
— a demo continuaria vendendo o sistema de ontem. Aqui a fonte é sempre o
_demo_telas.json, que por sua vez sai do menu de verdade.

Roda sem os prints: as telas que faltam viram moldura vazia com o nome. Isso
permite ver a estrutura e o ritmo antes de capturar nada.

Entra:  _demo_telas.json           (python _demo_inventario.py)
        static/demo/*.jpg          (python _demo_capturar.py)
        _demo_tempos.json          (python _demo_narracao.py)
Sai:    demo_comercial.html

Rodar:  python _demo_montar.py
"""

import base64
import io
import json
import os
import re
import unicodedata
from datetime import datetime

INVENTARIO = "_demo_telas.json"
TEMPOS = "_demo_tempos.json"
PASTA_PRINTS = os.path.join("static", "demo")
NARRACAO = os.path.join("static", "demo_narracao.mp3")
PRINT_LOGIN = os.path.join(PASTA_PRINTS, "_login.jpg")
PRINT_MENU = os.path.join(PASTA_PRINTS, "_menu.jpg")
CARTOES_MENU = "_demo_menu_cards.json"
BOTOES_MENU = "_demo_menu_botoes.json"
SAIDA = "demo_comercial.html"

# Onde os campos ficam na FOTO da tela de login, em porcentagem da imagem.
# Porcentagem e nao pixel porque a foto e redimensionada para caber no palco:
# em pixel, o texto digitado descolaria do campo em qualquer tela diferente
# daquela em que o print foi tirado.
LOGIN_CAMPOS = [
    ("cpf",   "123.456.789-09", 37.9),
    ("senha", "••••••",         45.9),
]
LOGIN_BOTAO = 57.4

# Conexões não tem nenhuma tela pronta e Diversos tem 1 de 5. Módulo vazio num
# vídeo de venda joga contra, então os dois saem do corpo e viram uma frase de
# promessa no fecho. Para mostrá-los assim mesmo, basta esvaziar este conjunto.
MODULOS_NO_FECHO = {"conexoes", "diversos"}

# Tela que aparece em tamanho cheio, com digitação simulada, em cada módulo.
# É a mais representativa — a que o cliente reconhece como "o sistema".
DESTAQUE = {
    "cadastros":     "/cad_funcionario",
    "novafolha":     "/cad_anomes",
    "eventuais":     "/calc_ferias",
    "movimento":     "/cad_mov",
    "movimentofixo": "/mov_fixo",
    "calculo":       "/calcular_folha",
    "relatorios":    "/resumo_folha",
    "esocial":       "/esocial_fila",
}

# O que é digitado na tela de destaque: (rótulo do campo, texto). O cartão é
# desenhado por cima do print — não tenta acertar a posição do campo real,
# que mudaria a cada captura.
DIGITACAO = {
    "cadastros":     [("CPF", "123.456.789-09"), ("Nome", "MARIA SOUZA LIMA")],
    "novafolha":     [("Mês/Ano", "08/2026")],
    "eventuais":     [("Início das férias", "01/09/2026"), ("Dias", "30")],
    "movimento":     [("Verba", "0011 Horas Extras"), ("Quantidade", "12,50")],
    "movimentofixo": [("Verba", "0033 Vale Transporte"), ("Valor", "180,00")],
    "calculo":       [("Competência", "07/2026")],
    "relatorios":    [("Período", "07/2026")],
    "esocial":       [("Evento", "S-1200 Remuneração")],
}

# Segundos de cada parte do bloco de um módulo. Só valem enquanto não houver
# narração: quando o _demo_tempos.json existe, quem manda é a fala -- cada
# fase dura o que a frase dela durou. Antes disso os tempos eram fixos e
# Movimento Fixo, com 3 telas, ficava tanto no ar quanto Eventuais, com 36.
T_GAVETA, T_MOSAICO, T_TELA = 12, 10, 20
T_ABERTURA, T_FECHO = 24, 22


def audio_embutido():
    """A narração como data: URI, dentro do próprio HTML.

    Custa uns 3 MB no arquivo e vale cada um deles. Com o mp3 do lado de
    fora, bastava a página ser aberta de outra pasta, movida, copiada ou
    enviada para alguém, e ela rodava MUDA -- sem erro, sem aviso, sem
    nada. Foi exatamente o que aconteceu aqui: o áudio estava certo, tocava
    quando testado, e mesmo assim não saía som. Embutido não há caminho para
    dar errado, e é também o que permite mandar um arquivo só para o cliente.
    """
    if not os.path.exists(NARRACAO):
        return ""
    b64 = base64.b64encode(io.open(NARRACAO, "rb").read()).decode("ascii")
    return "data:audio/mpeg;base64," + b64


def tempos_da_voz():
    """Os tempos medidos na narração, por chave de cena. {} se não houver."""
    if not os.path.exists(TEMPOS):
        return {}
    d = json.load(io.open(TEMPOS, encoding="utf-8"))
    return {s["chave"]: s for s in d["slides"]}


def slug(texto):
    t = unicodedata.normalize("NFD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", t.lower())).strip("_")


def arquivo_do(tela):
    return os.path.join(PASTA_PRINTS, "%s_%s.jpg"
                        % (tela["modulo"], slug(tela["href"])))


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def img_ou_moldura(tela, classe="tiro"):
    """<img> quando o print existe; moldura com o nome quando não.

    O caminho é RELATIVO, e é preciso que seja. Com a barra na frente
    ("/static/demo/x.jpg") o navegador procura na raiz do disco quando a
    página é aberta como arquivo -- que é como ela é vista. O print existia,
    o <img> apontava para ele, e mesmo assim a tela saía vazia: todos os
    prints capturados sumiam de uma vez, sem nada no lugar além da moldura
    tracejada de "ainda não capturei". Foi o que fez a demonstração parecer
    piscar entre quadros vazios.
    """
    caminho = arquivo_do(tela)
    if os.path.exists(caminho):
        # Sem loading="lazy", de proposito. Com ele o navegador so buscava a
        # imagem quando o slide aparecia -- e como o slide aparece e some em
        # segundos, cada troca mostrava o quadro vazio antes de preencher.
        # Era metade do "piscar" entre uma tela e outra.
        return ('<div class="%s"><img src="%s" alt="%s"></div>'
                % (classe, caminho.replace("\\", "/"), esc(tela["nome"])))
    return ('<div class="%s falta"><span>%s</span></div>'
            % (classe, esc(tela["nome"])))


def botoes_da_gaveta(chave):
    """Os botões medidos na foto da gaveta daquele módulo. [] se não houver."""
    if not os.path.exists(BOTOES_MENU):
        return []
    return json.load(io.open(BOTOES_MENU, encoding="utf-8")).get(chave, [])


def _limpo(s):
    """Sem emoji, sem acento, minúsculo -- para casar rótulo com roteiro."""
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/ ]+", " ", s)).strip()


def indice_do_botao(chave, rotulo):
    """Posição do botão cujo rótulo bate com `rotulo`, na gaveta do módulo.

    O roteiro aponta para o botão pelo NOME, não pelo número: número mudaria
    silenciosamente no dia em que um item entrasse no menu, e o destaque
    passaria a acender o botão errado sem ninguém perceber.
    """
    alvo = _limpo(rotulo)
    for i, b in enumerate(botoes_da_gaveta(chave)):
        if alvo in _limpo(b["texto"]):
            return i
    raise SystemExit(
        "ERRO: na gaveta de %r não existe botão com %r.\n"
        "      O que existe: %s\n"
        "      (se o menu mudou, rode antes: python _demo_menu_print.py)"
        % (chave, rotulo,
           ", ".join(b["texto"] for b in botoes_da_gaveta(chave)) or "nada"))


def bloco_gaveta(mod, telas):
    """A gaveta do módulo aberta.

    Usa a FOTO da gaveta de verdade quando ela existe (a que o
    _demo_menu_print.py tira abrindo o menu pelo próprio código dele). A
    versão desenhada abaixo continua como reserva: ela lista item por item,
    o que é útil enquanto os prints não existem, mas nunca vai ser igual ao
    menu -- e num vídeo de venda a diferença aparece.
    """
    foto = os.path.join(PASTA_PRINTS, "_menu_%s.jpg" % mod["chave"])
    if os.path.exists(foto):
        # Cada realce carrega, como fundo, o PEDAÇO da foto onde o botão
        # está. É o que faz o botão crescer de verdade quando é citado: uma
        # moldura só aumentaria a borda, e o botão continuaria do mesmo
        # tamanho lá embaixo. As contas são a fórmula padrão de recorte por
        # porcentagem: o fundo é ampliado na razão inversa do tamanho da
        # janelinha, e deslocado na proporção do espaço que sobra.
        src = foto.replace("\\", "/")
        realces = "".join(
            '<span class="brealce %s" style="left:%.2f%%;top:%.2f%%;'
            'width:%.2f%%;height:%.2f%%;background-image:url(%s);'
            'background-size:%.2f%% %.2f%%;background-position:%.2f%% %.2f%%">'
            '</span>'
            % (b["tipo"], b["left"], b["top"], b["width"], b["height"], src,
               10000.0 / b["width"], 10000.0 / b["height"],
               b["left"] / max(0.01, 100 - b["width"]) * 100,
               b["top"] / max(0.01, 100 - b["height"]) * 100)
            for b in botoes_da_gaveta(mod["chave"]))
        return ('<div class="cheia"><div class="tiro grande quadro-gaveta">'
                '<img src="%s" alt="Menu — %s">%s</div></div>'
                % (foto.replace("\\", "/"), esc(mod["titulo"]), realces))

    secoes, ordem = {}, []
    for t in telas:
        if t["secao"] not in secoes:
            secoes[t["secao"]] = []
            ordem.append(t["secao"])
        secoes[t["secao"]].append(t)
    partes = []
    for nome in ordem:
        itens = "".join(
            '<li%s>%s %s</li>' % (" class=\"nao\"" if not t["ok"] else "",
                                  esc(t["icone"]), esc(t["nome"]))
            for t in secoes[nome])
        partes.append('<div class="secao"><h4>%s</h4><ul>%s</ul></div>'
                      % (esc(nome or "Geral"), itens))
    return ('<div class="gaveta"><div class="gaveta-cab">%s %s</div>'
            '<div class="gaveta-corpo">%s</div></div>'
            % (esc(mod["icone"]), esc(mod["titulo"]), "".join(partes)))


# Quantas telas o módulo mostra nesta fase -- UMA DE CADA VEZ, em tamanho
# cheio. Já foram seis lado a lado, e antes disso as trinta e seis: em grade,
# cada tela ficava com 160 a 440px e não dava para ler nada. Uma parede de
# retângulos borrados não prova volume nenhum, só cansa. Três, grandes e em
# sequência, mostram como o sistema é; o contador no fim diz o tamanho do
# módulo sem precisar exibir as outras trinta e uma.
MOSAICO_PASSOS = 3


# Para que serve cada módulo, na linha do cartão do menu. Curto de propósito:
# quem lê é o espectador, de longe, enquanto a voz explica o mesmo.
PARA_QUE_SERVE = {
    "cadastros":     "funcionário, função, empresa",
    "novafolha":     "abre e fecha o mês",
    "eventuais":     "férias, rescisão, afastamento",
    "movimento":     "o que muda a cada mês",
    "movimentofixo": "o que se repete sozinho",
    "calculo":       "roda a folha",
    "relatorios":    "tudo em PDF",
    "conexoes":      "pagamento no banco",
    "esocial":       "monta e transmite",
    "diversos":      "log de auditoria",
}


def bloco_menu(modulos, luz):
    """O menu com os dez módulos, cada um acendendo quando a voz o cita.

    Em cima da FOTO do menu de verdade, quando ela existe. O realce não é
    posicionado no olho: o _demo_menu_print.py pergunta ao navegador onde
    cada cartão ficou, no mesmo instante em que tira o print, e grava em
    porcentagem. Mudou o menu de lugar, o realce vai junto.

    Sem a foto, cai na grade desenhada mais abaixo -- que serve, mas nunca
    vai ser igual ao menu de verdade.
    """
    titulos = {m["chave"]: m["titulo"] for m in modulos}
    if os.path.exists(PRINT_MENU) and os.path.exists(CARTOES_MENU):
        pos = json.load(io.open(CARTOES_MENU, encoding="utf-8"))
        realces = "".join(
            '<span class="mrealce" data-nome="%s" data-pq="%s" style="left:%.2f%%;'
            'top:%.2f%%;width:%.2f%%;height:%.2f%%"></span>'
            % (esc(titulos.get(c["chave"], c["chave"])),
               esc(PARA_QUE_SERVE.get(c["chave"], "")),
               c["left"], c["top"], c["width"], c["height"])
            for c in pos)
        return ('<div class="menu-foto" data-luz="%s">'
                '<div class="tiro grande quadro-menu">'
                '<img src="%s" alt="Menu do sistema">%s</div>'
                '<div class="mlegenda"><b></b><span></span></div></div>'
                % (",".join("%.2f" % s for s in luz),
                   PRINT_MENU.replace("\\", "/"), realces))

    cards = "".join(
        '<div class="mcard"><span class="mic">%s</span>'
        '<b>%s</b><span class="mpq">%s</span></div>'
        % (esc(m.get("icone", "")), esc(m["titulo"]),
           esc(PARA_QUE_SERVE.get(m["chave"], "")))
        for m in modulos)
    return ('<div class="menu-cena"><h3>Um menu, dez módulos</h3>'
            '<div class="menu-grade" data-luz="%s">%s</div></div>'
            % (",".join("%.2f" % s for s in luz), cards))


def bloco_login():
    """A tela de login com CPF e senha sendo digitados, e o Entrar acendendo.

    O texto vai POR CIMA dos campos da propria foto, posicionado em
    porcentagem -- nao e um cartao flutuante como nos outros modulos. Aqui
    vale o esforco a mais: e a primeira coisa que o cliente ve, e digitar num
    campo que nao e o campo da tela entregaria a encenacao na hora.
    """
    if not os.path.exists(PRINT_LOGIN):
        return ('<div class="cheia"><div class="tiro falta"><span>Tela de login'
                ' — falta o print (static/demo/_login.jpg)</span></div></div>')
    campos = "".join(
        '<span class="campo %s" data-txt="%s" style="top:%.1f%%">'
        '<span class="valor"><span></span><i></i></span></span>'
        % (classe, esc(txt), topo)
        for classe, txt, topo in LOGIN_CAMPOS)
    return ('<div class="cheia"><div class="tiro grande quadro-login">'
            '<img src="%s" alt="Tela de login">%s'
            '<span class="botao-sobre" style="top:%.1f%%"></span>'
            '</div></div>'
            % (PRINT_LOGIN.replace("\\", "/"), campos, LOGIN_BOTAO))


def bloco_mosaico(telas, dur):
    """Um desfile das telas do módulo: uma de cada vez, em tamanho cheio.

    Prefere as que já têm print -- uma moldura vazia entre três é quase a
    fase inteira em branco.

    O tempo de cada passo sai daqui, e não do CSS, porque a fase dura o que a
    frase dela durou: dividir por igual no navegador exigiria o navegador
    saber a duração, que é justamente o que ele não sabe.
    """
    prontas = [t for t in telas if t["ok"]]
    com_print = [t for t in prontas if os.path.exists(arquivo_do(t))]
    amostra = (com_print or prontas)[:MOSAICO_PASSOS]
    resto = len(prontas) - len(amostra)

    passos = ['<div class="passo">%s<figcaption>%s</figcaption></div>'
              % (img_ou_moldura(t, "tiro grande"), esc(t["nome"]))
              for t in amostra]
    if resto > 0:
        passos.append('<div class="passo contador"><b>+%d</b>'
                      '<span>telas neste módulo</span></div>' % resto)
    return ('<div class="desfile" data-passo="%.2f">%s</div>'
            % (dur / max(1, len(passos)), "".join(passos)))


def bloco_tela(mod_chave, telas):
    """A tela representativa, em tamanho cheio, com o cartão de digitação."""
    href = DESTAQUE.get(mod_chave)
    tela = next((t for t in telas if t["href"] == href), None)
    if tela is None:
        tela = next((t for t in telas if t["ok"]), None)
    if tela is None:
        return ""
    campos = "".join(
        '<div class="campo" data-txt="%s"><label>%s</label>'
        '<div class="valor"><span></span><i></i></div></div>'
        % (esc(txt), esc(rot))
        for rot, txt in DIGITACAO.get(mod_chave, []))
    return ('<div class="cheia">%s<div class="cartao">%s</div></div>'
            % (img_ou_moldura(tela, "tiro grande"), campos))


def main():
    if not os.path.exists(INVENTARIO):
        raise SystemExit("ERRO: falta o %s. Rode antes:\n"
                         "  python _demo_inventario.py" % INVENTARIO)
    dados = json.load(io.open(INVENTARIO, encoding="utf-8"))
    modulos = [m for m in dados["modulos"]
               if m["chave"] not in MODULOS_NO_FECHO]
    telas = dados["telas"]

    voz = tempos_da_voz()
    slides, roteiro = [], []

    t_abertura = voz["abertura"]["dur"] if "abertura" in voz else T_ABERTURA
    slides.append((t_abertura, """
      <section class="slide on capa" data-dur="%s">
        <h1>Folha10-Simples</h1>
        <p class="lede">A folha inteira dentro do navegador — do cadastro do
        funcionário ao recibo do eSocial.</p>
        <div class="cab-demo">
          <div class="cab-col"><b>Empresa</b><span>Sua empresa aqui</span></div>
          <div class="cab-col"><b>Folha 07/2026</b><span class="badge">Aberta</span></div>
          <div class="cab-col"><b>Versão</b><span>no rodapé, sempre à vista</span></div>
        </div>
        <div class="avisos">
          <div class="aviso cert">🔑 Certificado digital A1 — válido até 12/2026</div>
          <div class="aviso lic">🔐 Licença Folha10-Simples ativa</div>
        </div>
      </section>""" % t_abertura))

    # O login vem logo depois da capa: a demonstracao entra no sistema na
    # frente de quem assiste, em vez de aparecer ja logada do nada.
    t_login = voz["login"]["dur"] if "login" in voz else 14
    slides.append((t_login, """
      <section class="slide" data-dur="%s" data-fases="%s">
        <div class="fase fase-login">%s</div>
      </section>""" % (t_login, t_login, bloco_login())))

    # O passeio pelo menu, antes de entrar em módulo nenhum: é aqui que o
    # cliente entende o mapa. Mostra os dez, inclusive os dois que ainda não
    # têm tela pronta -- no menu eles existem, e escondê-los seria mentir.
    t_menu = voz["menu"]["dur"] if "menu" in voz else 36
    slides.append((t_menu, """
      <section class="slide" data-dur="%s" data-fases="%s">
        <div class="fase fase-menu">%s</div>
      </section>""" % (t_menu, t_menu,
                       bloco_menu(dados["modulos"],
                                  voz.get("menu", {}).get("luz", [])))))

    for mod in modulos:
        do_mod = [t for t in telas if t["modulo"] == mod["chave"]]
        prontas = [t for t in do_mod if t["ok"]]
        if not prontas:
            continue
        fases = (voz[mod["chave"]]["fases"] if mod["chave"] in voz
                 else [T_GAVETA, T_MOSAICO, T_TELA])
        dur = round(sum(fases), 2)
        v = voz.get(mod["chave"], {})
        marca = ' data-luz="%s" data-alvos="%s"' % (
            ",".join("%.2f" % s for s in v.get("luz", [])),
            ",".join(str(a) for a in v.get("alvos", [])))
        slides.append((dur, """
      <section class="slide modulo" data-dur="%s" data-fases="%s" data-mod="%s">
        <div class="fase fase-gaveta"%s>%s</div>
        <div class="fase fase-mosaico"><h3>%s — %d telas</h3>%s</div>
        <div class="fase fase-tela">%s</div>
      </section>""" % (dur, ",".join(str(f) for f in fases),
                       esc(mod["chave"]), marca, bloco_gaveta(mod, do_mod),
                       esc(mod["titulo"]), len(prontas),
                       bloco_mosaico(do_mod, fases[1]),
                       bloco_tela(mod["chave"], do_mod))))
        roteiro.append((mod["titulo"], len(prontas), dur))

    fora = [m for m in dados["modulos"] if m["chave"] in MODULOS_NO_FECHO]
    promessa = " · ".join(m["titulo"] for m in fora)
    t_fecho = voz["fecho"]["dur"] if "fecho" in voz else T_FECHO
    slides.append((t_fecho, """
      <section class="slide fecho" data-dur="%s">
        <h2>Processe o primeiro mês sem custo</h2>
        <p class="lede">Sem compromisso e com suporte.%s</p>
        <p class="url">folha10-simples.com.br</p>
      </section>""" % (t_fecho,
                       (" Chegando: " + promessa + ".") if promessa else "")))

    total = round(sum(d for d, _ in slides), 2)
    audio = audio_embutido()
    carimbo = datetime.now().strftime("gerado %d/%m %H:%M")
    html = MOLDE.replace("{{SLIDES}}", "".join(s for _, s in slides)) \
                .replace("{{TOTAL}}", str(total)) \
                .replace("{{CARIMBO}}", carimbo) \
                .replace("{{AUDIO}}", audio)
    io.open(SAIDA, "w", encoding="utf-8", newline="").write(html)

    faltam = sum(1 for t in telas
                 if t["ok"] and not t["repetida"] and not os.path.exists(arquivo_do(t)))
    print("%s gerado — %d slides, %.0f s (%d min %02d s), %.1f MB%s"
          % (SAIDA, len(slides), total, int(total) // 60, int(total) % 60,
             os.path.getsize(SAIDA) / 1048576,
             "" if voz else "   [tempos fixos, sem narração]"))
    print("   %s   narração %s"
          % (carimbo, "embutida no HTML" if audio else "AUSENTE"))
    for titulo, n, dur in roteiro:
        print("   %-16s %2d telas  %.0fs" % (titulo, n, dur))
    if fora:
        print("   (no fecho, sem tela pronta: %s)" % promessa)
    if not voz:
        print("\nATENÇÃO: sem narração — os tempos acima são chutes fixos e o"
              "\nHTML vai rodar mudo. Rode:  python _demo_narracao.py")
    if faltam:
        print("\nATENÇÃO: %d print(s) ainda não capturado(s) — essas telas saem"
              "\ncomo moldura vazia. Rode:  python _demo_capturar.py" % faltam)
    else:
        print("\nTodos os prints no lugar.")


MOLDE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Folha10-Simples — Demonstração</title>
<style>
:root{
  --paper:#EFF3F8; --stage:#FFFFFF; --panel:#F5F8FC;
  --ink:#0C1726; --ink-2:#4A5D75; --ink-3:#7C8EA5;
  --rule:#D3DDE9; --brand:#1F6FD0; --brand-soft:#E2EDFB;
  --ok:#06773F; --ok-soft:#DDF2E6; --amber:#9A5B06; --amber-soft:#FBEEDA;
  --sans:"Segoe UI",system-ui,-apple-system,Arial,sans-serif;
  --mono:"Cascadia Mono",Consolas,ui-monospace,monospace;
  --shadow:0 1px 0 rgba(12,23,38,.04), 0 18px 40px -24px rgba(12,23,38,.35);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#080F19; --stage:#101D2D; --panel:#16273A;
    --ink:#E9F1F9; --ink-2:#9FB4CB; --ink-3:#71879F;
    --rule:#23374E; --brand:#63A5F6; --brand-soft:#173049;
    --ok:#3CCB85; --ok-soft:#10331F; --amber:#E9A84A; --amber-soft:#33260F;
    --shadow:0 1px 0 rgba(0,0,0,.4), 0 22px 50px -28px rgba(0,0,0,.9);
  }
}
:root[data-theme="dark"]{
  --paper:#080F19; --stage:#101D2D; --panel:#16273A;
  --ink:#E9F1F9; --ink-2:#9FB4CB; --ink-3:#71879F;
  --rule:#23374E; --brand:#63A5F6; --brand-soft:#173049;
  --ok:#3CCB85; --ok-soft:#10331F; --amber:#E9A84A; --amber-soft:#33260F;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
     -webkit-font-smoothing:antialiased}
.deck{min-height:100vh;min-height:100dvh;display:flex;flex-direction:column;
      gap:14px;padding:16px clamp(12px,3vw,32px) 14px}
.rail{display:flex;align-items:center;gap:clamp(10px,2vw,20px);flex-wrap:wrap}
.mark{font-weight:700;letter-spacing:-.02em;font-size:15px;white-space:nowrap}
.mark b{color:var(--brand)}
/* A hora em que este arquivo foi gerado. Existe para responder numa olhada
   a pergunta que custou caro aqui: "e a versao nova que voce esta vendo?" */
.mark em{font-style:normal;font-weight:400;font-size:10.5px;color:var(--ink-3);
  margin-left:6px}
.track{flex:1 1 240px;height:3px;background:var(--rule);border-radius:2px;overflow:hidden}
.track i{display:block;height:100%;width:0;background:var(--brand)}
.voznota{font-size:11.5px;color:var(--ink-3);white-space:nowrap}
.voznota.ruim{color:var(--amber);font-weight:600;white-space:normal}
.ctrl{display:flex;gap:8px}
.ctrl button{font:inherit;font-size:12px;padding:6px 12px;border:1px solid var(--rule);
  border-radius:7px;background:var(--stage);color:var(--ink);cursor:pointer}
.ctrl button:hover{border-color:var(--brand);color:var(--brand)}
.palco{flex:1;position:relative;background:var(--stage);border:1px solid var(--rule);
       border-radius:12px;box-shadow:var(--shadow);overflow:hidden}
/* A troca de slide era um corte seco: o de fora sumia e o de dentro aparecia
   no mesmo quadro, e com dez trocas em cinco minutos a demonstracao parecia
   piscar. Os dois estao empilhados no mesmo lugar, entao basta a transicao
   para virar dissolucao. */
/* A troca de slide era um corte seco. Com a transicao simples os dois ficavam
   meio transparentes ao mesmo tempo, um por cima do outro, e a sobreposicao
   de dois prints claros dava um clarao -- trocou um piscar por outro. Por
   isso o que entra espera o que sai terminar: sai em .45s, entra depois. */
.slide{position:absolute;inset:0;padding:clamp(18px,3vw,40px);opacity:0;
       pointer-events:none;display:flex;flex-direction:column;gap:14px;overflow:hidden;
       transition:opacity .45s ease}
.slide.on{opacity:1;pointer-events:auto;transition:opacity .5s ease .4s}
@media (prefers-reduced-motion: reduce){.slide,.fase{transition:none}}
h1{font-size:clamp(30px,4.4vw,58px);margin:0;letter-spacing:-.03em}
h2{font-size:clamp(24px,3.4vw,44px);margin:0;letter-spacing:-.02em}
h3{font-size:clamp(15px,1.9vw,22px);margin:0 0 10px;color:var(--ink-2)}
h4{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--brand);
   margin:0 0 6px}
.lede{font-size:clamp(14px,1.5vw,19px);color:var(--ink-2);margin:0;max-width:62ch}
.url{font-family:var(--mono);font-size:clamp(17px,2.6vw,34px);color:var(--brand);
     margin:18px 0 0;padding:12px 20px;border:1px solid var(--rule);border-radius:8px;
     background:var(--panel);align-self:flex-start}
/* ---- abertura ---- */
.cab-demo{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:8px;
  border:1px solid var(--rule);border-radius:10px;padding:12px;background:var(--panel)}
.cab-col b{display:block;font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-3)}
.cab-col span{font-size:14px}
.badge{background:var(--ok-soft);color:var(--ok);padding:1px 8px;border-radius:20px;
  font-size:12px;font-weight:600}
.avisos{display:flex;gap:10px;flex-wrap:wrap;margin-top:auto}
.aviso{font-size:13px;padding:9px 14px;border-radius:9px;border:1px solid var(--rule)}
.aviso.cert{background:var(--amber-soft);color:var(--amber)}
.aviso.lic{background:var(--ok-soft);color:var(--ok)}
/* ---- fases do módulo ---- */
.fase{position:absolute;inset:clamp(18px,3vw,40px);opacity:0;transition:opacity .5s}
.fase.on{opacity:1}
.gaveta{border:1px solid var(--rule);border-radius:10px;overflow:hidden;height:100%;
  display:flex;flex-direction:column;background:var(--panel)}
.gaveta-cab{padding:11px 16px;font-weight:700;font-size:17px;background:var(--brand-soft);
  color:var(--brand);border-bottom:1px solid var(--rule)}
.gaveta-corpo{padding:14px 16px;display:grid;gap:14px;overflow:auto;
  grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.gaveta ul{list-style:none;margin:0;padding:0;display:grid;gap:3px}
.gaveta li{font-size:12.5px;color:var(--ink-2);line-height:1.45}
.gaveta li.nao{opacity:.42}
/* As colunas vem escritas no proprio elemento, calculadas por modulo -- ver
   colunas_do_mosaico(). O align-content centra o que sobra: com 3 telas o
   bloco fica no meio do palco, e nao encostado no alto. */
/* O h3 e o desfile dividem a fase. Sem isto o desfile pedia 100% da altura
   INTEIRA, o titulo empurrava tudo para baixo, e o que devia estar centrado
   aparecia com um vao no alto. */
.fase-mosaico{display:flex;flex-direction:column}
/* Uma tela de cada vez, todas empilhadas no mesmo lugar. Empilhar (e nao
   esconder com display:none) e o que permite a troca ser uma dissolucao. */
.desfile{position:relative;flex:1;min-height:0}
/* Como na troca de slide: o que entra espera o que sai terminar. Com os dois
   meio transparentes ao mesmo tempo, duas telas claras somadas davam um
   clarao e liam-se as duas de uma vez. */
.passo{position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:8px;
  opacity:0;transition:opacity .3s ease}
.passo.on{opacity:1;transition:opacity .35s ease .28s}
.passo .tiro.grande{max-height:100%;max-width:100%}
.passo .tiro.grande img{max-height:calc(100vh - 250px);width:auto}
.passo figcaption{font-size:clamp(12px,1.4vw,18px);color:var(--ink-2);margin:0}
/* O "+31 telas": diz o tamanho do modulo sem precisar mostrar as trinta e uma. */
.passo.contador b{font-size:clamp(56px,10vw,150px);color:var(--brand);
  line-height:1;letter-spacing:-.04em}
.passo.contador span{font-size:clamp(14px,1.8vw,24px);color:var(--ink-2)}
.mosaico figure{margin:0;animation:sobe .7s both;animation-delay:calc(var(--i)*.09s)}
@keyframes sobe{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
figcaption{font-size:10.5px;color:var(--ink-3);margin-top:4px;line-height:1.3}
.tiro{border:1px solid var(--rule);border-radius:7px;overflow:hidden;background:#fff;
  line-height:0;box-shadow:var(--shadow)}
.tiro img{display:block;width:100%;height:auto}
.tiro.mini{aspect-ratio:16/10;display:grid;place-items:center}
.tiro.mini img{height:100%;width:100%;object-fit:cover;object-position:top center}
.tiro.falta{aspect-ratio:16/10;display:grid;place-items:center;background:var(--panel);
  border-style:dashed;line-height:1.4}
.tiro.falta span{font-size:11px;color:var(--ink-3);padding:8px;text-align:center}
/* O "+28 telas": diz o tamanho do modulo sem precisar mostrar as 28. */
.tiro.mais{aspect-ratio:16/10;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:2px;background:var(--brand-soft);
  border-color:var(--brand);box-shadow:none}
.tiro.mais b{font-size:clamp(26px,3.6vw,48px);color:var(--brand);line-height:1}
.tiro.mais span{font-size:clamp(10px,1.1vw,14px);color:var(--ink-2)}
.mosaico figcaption{text-align:center}
.cheia{position:relative;height:100%;display:grid;place-items:center}
.cheia .tiro.grande{max-height:100%;max-width:100%}
.cheia .tiro.grande img{max-height:calc(100vh - 190px);width:auto}
.cartao{position:absolute;right:4%;bottom:8%;background:var(--stage);border:1px solid var(--rule);
  border-radius:11px;box-shadow:var(--shadow);padding:14px 16px;display:grid;gap:10px;
  min-width:min(330px,80%)}
.campo label{display:block;font-size:10px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-3);margin-bottom:3px}
.campo .valor{display:flex;align-items:center;gap:1px;border:1px solid var(--rule);
  border-radius:6px;padding:7px 10px;background:var(--panel);font-family:var(--mono);
  font-size:14px;min-height:34px}
.campo .valor i{width:1.5px;height:16px;background:var(--brand);opacity:0}
.campo.digitando .valor i{animation:pisca .9s steps(1) infinite}
@keyframes pisca{0%,50%{opacity:1}51%,100%{opacity:0}}
/* ---- o menu de verdade, com o realce andando de cartao em cartao ---- */
.menu-foto{display:flex;flex-direction:column;gap:14px;height:100%;
  align-items:center;justify-content:center}
.quadro-menu{position:relative}
.mrealce{position:absolute;border:2px solid var(--brand);border-radius:10px;
  background:rgba(31,111,208,.12);opacity:0;transform:scale(.94);
  transition:opacity .3s, transform .3s;pointer-events:none}
.mrealce.aceso{opacity:1;transform:scale(1)}
/* A legenda fica FORA da foto, embaixo. Por cima taparia o proprio menu, e
   e o menu que se quer mostrar. */
.mlegenda{min-height:2.6em;text-align:center;opacity:0;transition:opacity .3s}
.mlegenda.on{opacity:1}
.mlegenda b{display:block;font-size:clamp(16px,2vw,26px);color:var(--brand)}
.mlegenda span{font-size:clamp(12px,1.3vw,17px);color:var(--ink-2)}
/* ---- reserva: os dez cartoes desenhados, quando nao ha foto do menu ---- */
.menu-cena{display:flex;flex-direction:column;height:100%}
/* As linhas seguem o conteudo, nao a altura do palco: com 1fr os cartoes
   esticavam ate o pe da tela e o texto boiava no meio de um vazio. */
.menu-grade{display:grid;gap:clamp(10px,1.6vw,22px);flex:1;min-height:0;
  grid-template-columns:repeat(5,1fr);align-content:center}
.mcard{border:1px solid var(--rule);border-radius:12px;background:var(--panel);
  padding:clamp(10px,1.4vw,18px);display:flex;flex-direction:column;gap:5px;
  justify-content:center;opacity:.5;transition:opacity .4s, transform .4s,
  border-color .4s, box-shadow .4s}
.mcard .mic{font-size:clamp(20px,2.6vw,34px);line-height:1}
.mcard b{font-size:clamp(12px,1.35vw,19px);letter-spacing:-.01em}
.mcard .mpq{font-size:clamp(10px,1.05vw,14px);color:var(--ink-2);line-height:1.35}
/* O cartao citado cresce e ganha cor; os outros continuam la, apagados. Some
   com o cartao seria pior: o cliente perde a nocao de quantos modulos sao. */
.mcard.aceso{opacity:1;transform:translateY(-4px) scale(1.04);
  border-color:var(--brand);background:var(--brand-soft);box-shadow:var(--shadow)}
/* ---- gaveta: o botao citado cresce sobre a foto do menu de verdade ---- */
.quadro-gaveta{position:relative}
.brealce{position:absolute;border-radius:8px;pointer-events:none;opacity:0;
  outline:2px solid var(--brand);outline-offset:-1px;
  background-repeat:no-repeat;background-color:var(--stage);
  transform:scale(1);transform-origin:center;
  transition:opacity .2s, transform .3s cubic-bezier(.34,1.4,.5,1), box-shadow .3s}
/* Cresce de verdade, com os proprios pixels: o olho segue o que cresce muito
   antes de ler o que mudou de cor. A sombra descola o botao da pagina, para
   parecer que ele subiu e nao que apareceu um retangulo em cima. */
.brealce.aceso{opacity:1;transform:scale(1.45);
  box-shadow:0 10px 30px -8px rgba(12,23,38,.45)}
.brealce.secao.aceso{transform:scale(1.3)}
/* ---- tela de login: o texto vai por cima dos campos da propria foto ---- */
.quadro-login{position:relative}
/* O tamanho da letra acompanha a altura da foto, que e o que o palco limita.
   Nao use container-type aqui: o inline-size aplica contencao e a caixa
   parou de acompanhar a imagem -- a tela de login saia toda branca. */
/* O fundo branco nao e enfeite: o campo da FOTO ja vem com o texto de
   ajuda escrito dentro ("Senha (6 dígitos)"), e sem cobri-lo os pontinhos
   da senha apareciam por cima da frase, um sobre o outro. */
.fase-login .campo{position:absolute;left:39.4%;width:21.2%;height:4%;
  display:flex;align-items:center;background:#fff;
  font-size:clamp(9px, calc((100vh - 190px) * .0167), 24px)}
.fase-login .campo .valor{border:0;background:none;padding:0;min-height:0;
  font-family:var(--mono);font-size:inherit;color:#1a2c44}
.fase-login .campo .valor i{height:1.15em;background:#1F6FD0}
.botao-sobre{position:absolute;left:38.7%;width:22.5%;height:4.7%;border-radius:6px;
  box-shadow:0 0 0 0 rgba(31,111,208,.55);opacity:0}
.fase-login.pronto .botao-sobre{animation:apertar 1.1s ease .2s 2;opacity:1}
@keyframes apertar{
  0%{box-shadow:0 0 0 0 rgba(31,111,208,.55)}
  70%{box-shadow:0 0 0 14px rgba(31,111,208,0)}
  100%{box-shadow:0 0 0 0 rgba(31,111,208,0)}}
.fecho{justify-content:center}
@media (max-width:820px){
  .cab-demo{grid-template-columns:1fr}
  .cartao{right:auto;left:4%;bottom:4%;min-width:auto;width:92%}
}
</style>
</head>
<body>
<div class="deck">
  <div class="rail">
    <div class="mark">Folha10<b>-Simples</b> <em id="carimbo">{{CARIMBO}}</em></div>
    <div class="track"><i id="barra"></i></div>
    <span class="voznota" id="estadoVoz"></span>
    <div class="ctrl">
      <button id="btPlay">▶ Rodar</button>
      <button id="btAnt">‹</button>
      <button id="btProx">›</button>
    </div>
  </div>
  <div class="palco" id="palco">{{SLIDES}}</div>
</div>
<audio id="voz" src="{{AUDIO}}" preload="auto"></audio>
<script>
// Motor dos slides. Cada <section> diz quanto dura em data-dur; os blocos de
// modulo tem tres fases internas (gaveta, mosaico, tela cheia) que se revezam
// dentro desse tempo. A digitacao comeca junto com a fase da tela.
//
// data-fases traz o tempo de CADA fase, medido na narracao. Sem ele as tres
// dividiam o slide em partes iguais -- e a voz, que nao e igual, entrava na
// fase errada: a frase da tela cheia comecava ainda no mosaico.
const TOTAL = {{TOTAL}};
const slides = [...document.querySelectorAll('.slide')];
const barra  = document.getElementById('barra');
const voz    = document.getElementById('voz');

const dur = s => parseFloat(s.dataset.dur || '8');

// A linha do tempo inteira, montada uma vez: o segundo em que cada slide
// entra e, dentro dele, quanto dura cada fase. Sao os mesmos numeros que
// geraram o audio, entao imagem e voz medem pela mesma regua.
const CENAS = slides.map(s => {
  const fases = [...s.querySelectorAll('.fase')];
  const medidos = (s.dataset.fases || '').split(',').filter(Boolean).map(Number);
  const passos = (fases.length && medidos.length === fases.length)
    ? medidos
    : fases.map(() => dur(s) / fases.length);
  return {dur: dur(s), passos: passos};
});
const INICIO = [];
CENAS.reduce((t, c) => { INICIO.push(t); return t + c.dur; }, 0);

let rodando = false, base = 0, t0 = 0, mostrando = -1, faseAtual = -1, laco = null;

// Um relogio so para tudo. Com o audio tocando, quem manda e ele: e o unico
// que nao acumula atraso ao longo de seis minutos -- a versao anterior
// encadeava setTimeout e, no fim da demonstracao, a voz ja falava do modulo
// seguinte. Sem audio, ou se o navegador bloquear o som, cai no cronometro.
function agora() {
  if (voz.readyState > 0 && !voz.paused) return voz.currentTime;
  return base + (rodando ? (performance.now() - t0) / 1000 : 0);
}

// `desde` = quantos segundos ja se passaram DENTRO da fase. Em reproducao
// normal e zero. Vale quando se pula para o meio de uma cena: sem isso os
// destaques eram agendados a partir do instante do pulo, e o botao que a voz
// ja tinha citado acendia varios segundos depois -- ou nunca, se a fase
// acabasse antes.
function mostrarFase(slide, i, desde) {
  desde = desde || 0;
  const fases = [...slide.querySelectorAll('.fase')];
  fases.forEach((f, k) => f.classList.toggle('on', k === i));
  const f = fases[i];
  if (f && (f.classList.contains('fase-tela') || f.classList.contains('fase-login')))
    digitar(f);
  if (f && (f.classList.contains('fase-menu') || f.classList.contains('fase-gaveta')))
    acender(f, desde);
  if (f && f.classList.contains('fase-mosaico')) desfilar(f, desde);
}

// Passa as telas do modulo uma de cada vez. O tempo de cada passo vem escrito
// no data-passo, calculado na geracao: a fase dura o que a frase dela durou,
// e so quem monta o HTML sabe disso.
let passos = [];
function desfilar(fase, desde) {
  desde = desde || 0;
  passos.forEach(clearTimeout); passos = [];
  const quadros = [...fase.querySelectorAll('.passo')];
  if (!quadros.length) return;
  const passo = parseFloat(fase.querySelector('.desfile').dataset.passo || '3');
  const por = k => quadros.forEach((q, j) => q.classList.toggle('on', j === k));
  const agora = Math.min(quadros.length - 1, Math.floor(desde / passo));
  por(agora);
  for (let k = agora + 1; k < quadros.length; k++)
    passos.push(setTimeout(() => por(k), (k * passo - desde) * 1000));
}

// Acende um cartao do menu por vez, no segundo em que a voz cita o modulo.
// Os segundos vem medidos da propria narracao (data-luz), nao cronometrados
// no olho: mexeu no texto, regere o audio e eles se reajustam sozinhos.
let luzes = [];
function acender(fase, desde) {
  desde = desde || 0;
  luzes.forEach(clearTimeout); luzes = [];
  // Dois desenhos possiveis: o realce sobre a foto do menu de verdade, ou os
  // cartoes desenhados (reserva, quando o print ainda nao existe).
  const alvos = [...fase.querySelectorAll('.mrealce, .mcard, .brealce')];
  const legenda = fase.querySelector('.mlegenda');
  // data-luz pode estar na propria fase (gaveta) ou num filho (menu).
  const fonte = fase.dataset.luz !== undefined ? fase : fase.querySelector('[data-luz]');
  alvos.forEach(c => c.classList.remove('aceso'));
  if (legenda) legenda.classList.remove('on');
  const quando = ((fonte && fonte.dataset.luz) || '')
    .split(',').filter(Boolean).map(Number);
  // Sem data-alvos, o n-esimo instante acende o n-esimo elemento. Com ele,
  // acende o que a lista mandar: na gaveta a voz pula de secao para item e
  // volta, entao a ordem da fala nao e a ordem em que os botoes estao la.
  const quais = ((fonte && fonte.dataset.alvos) || '')
    .split(',').filter(s => s !== '').map(Number);
  const por = (alvo) => {
    alvos.forEach(c => c.classList.remove('aceso'));
    alvo.classList.add('aceso');
    if (legenda) {
      legenda.querySelector('b').textContent = alvo.dataset.nome || '';
      legenda.querySelector('span').textContent = alvo.dataset.pq || '';
      legenda.classList.add('on');
    }
  };
  let jaPassou = null;
  quando.forEach((s, i) => {
    const alvo = alvos[quais.length ? quais[i] : i];
    if (!alvo) return;
    // O que ja deveria ter acendido nao entra na fila: acende de uma vez o
    // ultimo deles, que e onde a voz esta agora.
    if (s <= desde) { jaPassou = alvo; return; }
    luzes.push(setTimeout(() => por(alvo), (s - desde) * 1000));
  });
  if (jaPassou) por(jaPassou);
}

// Digita letra por letra. O texto vem do data-txt para o HTML continuar
// legivel e para o campo poder ser reiniciado quantas vezes for preciso.
function digitar(fase) {
  const campos = [...fase.querySelectorAll('.campo')];
  fase.classList.remove('pronto');
  campos.forEach(c => {
    c.querySelector('.valor span').textContent = '';
    c.classList.remove('digitando');
  });
  let atrasoCampo = 600;
  campos.forEach((c, k) => {
    setTimeout(() => {
      c.classList.add('digitando');
      const txt = c.dataset.txt || '', alvo = c.querySelector('.valor span');
      let i = 0;
      const bate = setInterval(() => {
        alvo.textContent = txt.slice(0, ++i);
        if (i >= txt.length) {
          clearInterval(bate); c.classList.remove('digitando');
          // Terminou o ultimo campo: no login e a deixa para o Entrar
          // acender, como se o usuario tivesse apertado.
          if (k === campos.length - 1) fase.classList.add('pronto');
        }
      }, 70);
    }, atrasoCampo);
    atrasoCampo += 600 + (c.dataset.txt || '').length * 70 + 500;
  });
}

// Poe na tela o que corresponde ao segundo t. Nao guarda estado proprio: e
// so o relogio traduzido em slide e fase. Por isso pular para tras, pausar
// ou arrastar o audio dao todos no mesmo lugar.
function pintar(t) {
  let n = 0;
  while (n + 1 < slides.length && t >= INICIO[n + 1]) n++;
  if (n !== mostrando) {
    slides.forEach((s, i) => s.classList.toggle('on', i === n));
    mostrando = n; faseAtual = -1;
  }
  const passos = CENAS[n].passos;
  if (passos.length) {
    let f = 0, acc = INICIO[n], inicioFase = INICIO[n];
    for (let i = 0; i < passos.length; i++) {
      if (t >= acc) { f = i; inicioFase = acc; }
      acc += passos[i];
    }
    if (f !== faseAtual) {
      faseAtual = f;
      mostrarFase(slides[n], f, Math.max(0, t - inicioFase));
    }
  }
  barra.style.width = Math.min(100, t / TOTAL * 100) + '%';
}

function irPara(t) {
  // Forca a fase a ser remontada mesmo que seja a MESMA de antes: pintar so
  // reage a troca de fase, entao pular de um ponto a outro dentro dela
  // mantinha a digitacao e o desfile no cronograma velho -- a tela continuava
  // desfilando a partir de onde estava, nao de onde a voz esta.
  faseAtual = -1;
  base = Math.max(0, Math.min(t, TOTAL)); t0 = performance.now();
  if (voz.readyState > 0) { try { voz.currentTime = base; } catch (e) {} }
  pintar(base);
}

function tique() {
  const t = agora();
  if (t >= TOTAL) { parar(); return; }
  pintar(t);
}

// A narracao falhando calada era o pior dos mundos: a demonstracao rodava
// muda, no ritmo certo mas sem motivo aparente, e quem assistia achava que
// nem havia voz. Agora o motivo aparece escrito ao lado da barra.
const nota = document.getElementById('estadoVoz');
function dizer(txt, ruim) {
  nota.textContent = txt || '';
  nota.classList.toggle('ruim', !!ruim);
}
voz.addEventListener('playing', () => dizer(''));
voz.addEventListener('error', () => dizer(
  'sem narração: não achei static/demo_narracao.mp3 — rode  python _demo_narracao.py', true));

function rodar() {
  rodando = true; t0 = performance.now();
  document.getElementById('btPlay').textContent = '❚❚ Pausar';
  // O navegador so libera som depois de um gesto seu, e recusa calado. O
  // catch transforma a recusa em recado -- outro clique costuma resolver.
  voz.play().then(() => dizer('')).catch(() => dizer(
    'som bloqueado pelo navegador — clique em Rodar mais uma vez', true));
  clearInterval(laco); laco = setInterval(tique, 100);
}

function parar() {
  base = agora();                // antes de pausar: depois o relogio some
  rodando = false; clearInterval(laco); laco = null; t0 = performance.now();
  document.getElementById('btPlay').textContent = '▶ Rodar';
  voz.pause();
}

document.getElementById('btPlay').onclick = () => rodando ? parar() : rodar();
document.getElementById('btProx').onclick = () => irPara(INICIO[Math.min(mostrando + 1, slides.length - 1)]);
document.getElementById('btAnt').onclick  = () => irPara(INICIO[Math.max(mostrando - 1, 0)]);
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight') document.getElementById('btProx').click();
  if (e.key === 'ArrowLeft')  document.getElementById('btAnt').click();
  if (e.key === ' ') { e.preventDefault(); document.getElementById('btPlay').click(); }
});
pintar(0);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
