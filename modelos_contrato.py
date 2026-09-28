# -*- coding: utf-8 -*-
"""
MEU CONTRATO — o contrato de experiencia que o CLIENTE edita.

Decidido com o Sergio em 28/09/2026:
  - O contrato PADRAO do sistema continua no app.py (rota /contrato_experiencia_pdf)
    e fica SEMPRE disponivel na impressao, mesmo para quem tem o seu.
  - O "Meu Contrato" e' um por CLIENTE (vale para todas as empresas dele), fica na
    tab_contrato_modelo e nasce como copia do padrao (MODELO_INICIAL, abaixo).
  - A clausula do PRAZO e' do sistema: o cliente muda o titulo e a posicao, nao o
    texto. E' ela que garante os 90 dias do art. 445, paragrafo unico, da CLT — a
    frase da prorrogacao so entra quando ainda cabe prorrogar.
  - Data do contrato: hoje (padrao) ou a da admissao. Testemunhas: opcionais.
  - O texto alterado e' responsabilidade do cliente (aviso na tela de edicao).

Substitui o modelo fixo do cliente 30 (04/09/2026), que foi para a tabela como o
primeiro "Meu Contrato" (_criar_tab_contrato_modelo.sql).

FORMATO do modelo (o JSON gravado em tab_contrato_modelo.modelo):
  {"titulo": str, "cabecalho": [str, ...], "preambulo": str,
   "clausulas": [{"titulo": str, "texto": str} | {"tipo": "prazo", "titulo": str}],
   "fecho": str, "data": "hoje" | "admissao", "testemunhas": bool}

No texto do cliente: {marcador} vira o dado do funcionario/empresa, **assim** sai
em negrito e a quebra de linha e' mantida. Qualquer outro caractere sai como foi
digitado (o texto e' escapado antes de ir para o ReportLab).
"""

import html
import re

# Marcadores que o cliente pode usar no texto livre. Os da prorrogacao ficam de
# fora de proposito: so a clausula do prazo sabe quando ela cabe.
MARCADORES = [
    ("razao",           "Razão social"),
    ("cnpj",            "CNPJ"),
    ("endereco_prosa",  "Endereço da empresa"),
    ("cidade_uf",       "Cidade/UF"),
    ("nome",            "Nome do empregado"),
    ("cpf",             "CPF"),
    ("matricula_fmt",   "Matrícula"),
    ("funcao",          "Função"),
    ("cbo",             "CBO"),
    ("salario",         "Salário"),
    ("salario_extenso", "Salário por extenso"),
    ("jornada",         "Jornada (resumo)"),
    ("jornada_prosa",   "Jornada (por extenso)"),
    ("dtadm_fmt",       "Data de admissão"),
    ("dias_inicial",    "Dias do 1º período"),
    ("dtterm_inicial",  "Término do 1º período"),
]
_MARCADORES_OK = {m for m, _ in MARCADORES}

# Texto da clausula do prazo — o mesmo do contrato do cliente 30, que ja' estava
# em uso. O segundo trecho so entra com d["tem_prorrogacao"].
PRAZO_TITULO = "DO PRAZO DE EXPERIÊNCIA"
PRAZO_TEXTO = (
    "O presente contrato terá duração inicial de {dias_inicial} "
    "({dias_inicial_extenso}) dias, com início em **{dtadm_fmt}** e "
    "término em **{dtterm_inicial}**."
)
PRAZO_PRORROGACAO = (
    "Por mútuo acordo, poderá ser prorrogado uma única vez por mais "
    "{dias_prorrog} ({dias_prorrog_extenso}) dias, mediante termo de "
    "prorrogação, passando o segundo período a vigorar de "
    "**{dtprorrog_ini}** até **{dtprorrog_fim}**, totalizando "
    "{dias_total} ({dias_total_extenso}) dias de experiência."
)

# Ponto de partida do "Meu Contrato": o texto do contrato padrao do app.py, no
# formato de clausulas.
MODELO_INICIAL = {
    "titulo": "CONTRATO DE EXPERIÊNCIA",
    "cabecalho": [
        "**EMPREGADOR:** {razao}, inscrita no CNPJ nº {cnpj}, com sede à "
        "{endereco_prosa}.",
        "**EMPREGADO:** {nome}, CPF nº {cpf}, matrícula nº {matricula_fmt}.",
    ],
    "preambulo": "",
    "clausulas": [
        {"titulo": "DA MODALIDADE",
         "texto": "Contrato de trabalho por prazo determinado, na modalidade de "
                  "experiência, nos termos dos artigos 443, 445 e 451 da CLT."},
        {"titulo": "DA FUNÇÃO",
         "texto": "O EMPREGADO exercerá as funções de **{funcao}** (CBO {cbo})."},
        {"titulo": "DA REMUNERAÇÃO",
         "texto": "A remuneração mensal será de **R$ {salario}** ({salario_extenso})."},
        {"titulo": "DA JORNADA DE TRABALHO",
         "texto": "A jornada de trabalho será de **{jornada}**, podendo o "
                  "EMPREGADOR alterá-la de acordo com as necessidades, respeitados "
                  "os limites legais."},
        {"tipo": "prazo", "titulo": PRAZO_TITULO},
        {"titulo": "DA CONTINUIDADE DO CONTRATO",
         "texto": "Permanecendo o EMPREGADO a serviço do EMPREGADOR após o término "
                  "deste contrato, este passará automaticamente a vigorar por prazo "
                  "indeterminado."},
    ],
    "fecho": "E por estarem de pleno acordo, as partes assinam o presente Contrato "
             "de Experiência em duas vias, ficando a primeira para o EMPREGADOR e a "
             "segunda para o EMPREGADO.",
    "data": "hoje",
    "testemunhas": True,
}

# Limites da tela — so para ninguem gravar um livro no JSON.
_MAX_CLAUSULAS = 40
_MAX_TEXTO     = 4000
_MAX_CURTO     = 300


# =========================================================
# VALIDACAO — o que a tela manda, antes de gravar ou visualizar
# =========================================================

def validar_modelo(m):
    """Normaliza o modelo vindo da tela. Devolve (modelo, erro)."""
    if not isinstance(m, dict):
        return None, "Modelo inválido."

    def txt(v, limite):
        return str(v or "").replace("\r\n", "\n").strip()[:limite]

    out = {
        "titulo":      txt(m.get("titulo"), _MAX_CURTO),
        "cabecalho":   [txt(x, _MAX_TEXTO) for x in (m.get("cabecalho") or [])
                        if str(x or "").strip()][:5],
        "preambulo":   txt(m.get("preambulo"), _MAX_TEXTO),
        "clausulas":   [],
        "fecho":       txt(m.get("fecho"), _MAX_TEXTO),
        "data":        "admissao" if m.get("data") == "admissao" else "hoje",
        "testemunhas": bool(m.get("testemunhas")),
    }
    if not out["titulo"]:
        return None, "Informe o título do contrato."

    prazos = 0
    for c in (m.get("clausulas") or [])[:_MAX_CLAUSULAS + 1]:
        if not isinstance(c, dict):
            continue
        if c.get("tipo") == "prazo":
            prazos += 1
            out["clausulas"].append({"tipo": "prazo",
                                     "titulo": txt(c.get("titulo"), _MAX_CURTO)
                                               or PRAZO_TITULO})
            continue
        t, x = txt(c.get("titulo"), _MAX_CURTO), txt(c.get("texto"), _MAX_TEXTO)
        if not x:
            continue                       # clausula em branco: some sem reclamar
        out["clausulas"].append({"titulo": t, "texto": x})

    if prazos != 1:
        return None, "A cláusula do prazo de experiência é obrigatória e única."
    if len(out["clausulas"]) > _MAX_CLAUSULAS:
        return None, f"No máximo {_MAX_CLAUSULAS} cláusulas."

    # Marcador errado tem que aparecer aqui, nao no papel impresso.
    textos = ([out["titulo"], out["preambulo"], out["fecho"]] + out["cabecalho"]
              + [c.get("titulo", "") for c in out["clausulas"]]
              + [c.get("texto", "") for c in out["clausulas"]])
    ruins = sorted({k for t in textos for k in re.findall(r"\{(\w*)\}", t)
                    if k not in _MARCADORES_OK})
    if ruins:
        return None, ("Marcador desconhecido: "
                      + ", ".join("{" + k + "}" for k in ruins)
                      + ". Use os botões de marcador para inserir.")
    return out, None


# =========================================================
# MONTADOR
# =========================================================

def _render(txt, d):
    """Texto do modelo -> markup do ReportLab: escapa, troca {marcador},
    **negrito** e quebra de linha. Marcador sem valor sai literal."""
    s = html.escape(str(txt or ""), quote=False)
    s = re.sub(r"\{(\w+)\}",
               lambda m: html.escape(str(d[m.group(1)]), quote=False)
                         if m.group(1) in d else m.group(0),
               s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s, flags=re.S)
    return s.replace("\n", "<br/>")


def _bloco_assinaturas(colunas, st_ass, PRETO, cm, Table, TableStyle, Paragraph):
    """Colunas de assinatura lado a lado, cada uma com a linha por cima.
    A 2a linha de cada coluna (o papel da parte) sai em negrito."""
    n = len(colunas)
    vao   = 1.6                                   # cm entre uma coluna e outra
    larg  = (17.0 - vao * (n - 1)) / n
    altura = max(len(c) for c in colunas)

    larguras = []
    for i in range(n):
        larguras.append(larg * cm)
        if i < n - 1:
            larguras.append(vao * cm)

    dados = []
    for linha in range(altura):
        celulas = []
        for i, col in enumerate(colunas):
            txt = col[linha] if linha < len(col) else "&nbsp;"
            celulas.append(Paragraph(f"<b>{txt}</b>" if linha == 1 else txt, st_ass))
            if i < n - 1:
                celulas.append("")
        dados.append(celulas)

    estilo = [("ALIGN", (0, 0), (-1, -1), "CENTER"),
              ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("TOPPADDING", (0, 0), (-1, -1), 1),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
              ("TOPPADDING", (0, 0), (-1, 0), 6)]
    for i in range(n):
        estilo.append(("LINEABOVE", (i * 2, 0), (i * 2, 0), 0.8, PRETO))

    return Table(dados, colWidths=larguras, style=TableStyle(estilo))


def montar_story(modelo, d):
    """Flowables do "Meu Contrato", prontos para o SimpleDocTemplate.
    `d` e' o dicionario do _contrato_exp_dados, com "data_assinatura" ja' posta."""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle

    PRETO = colors.HexColor("#111827")
    st_tit = ParagraphStyle("mtit", fontName="Helvetica-Bold", fontSize=11,
                            alignment=1, textColor=PRETO, leading=15)
    st_cab = ParagraphStyle("mcab", fontName="Helvetica", fontSize=9,
                            alignment=4, textColor=PRETO, leading=13)
    st_cla = ParagraphStyle("mcla", fontName="Helvetica-Bold", fontSize=9,
                            textColor=PRETO, leading=13, spaceBefore=8)
    st_txt = ParagraphStyle("mtxt", fontName="Helvetica", fontSize=9,
                            alignment=4, textColor=PRETO, leading=13)
    st_ass = ParagraphStyle("mass", fontName="Helvetica", fontSize=8,
                            alignment=1, textColor=PRETO, leading=11)

    story = [Paragraph(_render(modelo.get("titulo"), d), st_tit), Spacer(1, 10)]

    for linha in modelo.get("cabecalho") or []:
        story += [Paragraph(_render(linha, d), st_cab), Spacer(1, 3)]

    if modelo.get("preambulo"):
        story += [Spacer(1, 3), Paragraph(_render(modelo["preambulo"], d), st_txt)]

    for n, c in enumerate(modelo.get("clausulas") or [], 1):
        if c.get("tipo") == "prazo":
            corpo = _render(PRAZO_TEXTO, d)
            if d.get("tem_prorrogacao"):
                corpo += " " + _render(PRAZO_PRORROGACAO, d)
        else:
            corpo = _render(c.get("texto"), d)
        titulo = _render(c.get("titulo"), d)
        story += [Paragraph(f"CLÁUSULA {n}ª" + (f" – {titulo}" if titulo else ""),
                            st_cla),
                  Paragraph(corpo, st_txt)]

    if modelo.get("fecho"):
        story += [Spacer(1, 10), Paragraph(_render(modelo["fecho"], d), st_txt)]

    story += [Spacer(1, 18),
              Paragraph(_render("{cidade_uf}, {data_assinatura}.", d), st_cab)]

    e = lambda k: html.escape(str(d.get(k, "")), quote=False)
    colunas = [[e("nome"),  "EMPREGADO",  f"CPF: {e('cpf')}"],
               [e("razao"), "EMPREGADOR", f"CNPJ: {e('cnpj')}"]]
    story += [Spacer(1, 34),
              _bloco_assinaturas(colunas, st_ass, PRETO, cm, Table, TableStyle, Paragraph)]

    if modelo.get("testemunhas"):
        testem = [["&nbsp;", "TESTEMUNHA", "Nome:", "CPF:"]] * 2
        story += [Spacer(1, 30),
                  _bloco_assinaturas(testem, st_ass, PRETO, cm, Table, TableStyle, Paragraph)]

    return story
