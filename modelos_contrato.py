# -*- coding: utf-8 -*-
"""
Modelos de CONTRATO DE EXPERIENCIA exclusivos de determinados clientes.

O contrato padrao do sistema continua no app.py (rota /contrato_experiencia_pdf).
Aqui ficam SO os clientes que usam texto proprio — hoje um caso, o cliente 30.
Provisorio, decidido com o Sergio em 04/09/2026: atende os poucos clientes que
tem modelo proprio enquanto nao existe um modelo unico que sirva para todos.

O modelo e' DADO, nao codigo: cliente novo copia o bloco, troca o texto e pronto,
sem tocar em geracao de PDF. Se um dia forem muitos, este mesmo dicionario sobe
para o banco e o montador continua igual.

MARCADORES (o app.py monta todos em _contrato_exp_dados):
  empresa .... {razao} {cnpj} {endereco} {endereco_prosa} {cidade} {uf} {cidade_uf}
  pessoa ..... {nome} {cpf} {matricula_fmt}
  contrato ... {funcao} {cbo} {salario} {salario_extenso} {jornada_prosa}
  prazo ...... {dias_inicial} {dias_inicial_extenso} {dtadm_fmt}
               {dtterm_inicial} {data_extenso}
  prorrogacao  {tem_prorrogacao} {dias_prorrog} {dias_prorrog_extenso}
               {dtprorrog_ini} {dtprorrog_fim} {dias_total} {dias_total_extenso}

Um trecho de clausula pode vir como (chave, texto): so entra no papel quando
d[chave] for verdadeiro. E' assim que a frase da prorrogacao some do contrato
que ja nasceu com 90 dias — nao ha o que prorrogar, e prometer 90 dias a mais
seria ilegal (art. 445, paragrafo unico, da CLT).

Marcador que nao existir sai LITERAL no PDF ("{funcao_x}"), de proposito: erro
de digitacao no modelo tem que aparecer no teste, nao virar espaco em branco.
"""

import re

# =========================================================
# CLIENTE 30 — modelo do BC Industria e Comercio de Carnes
# =========================================================
# Texto transcrito do contrato do THALES HENRIQUE (17/08/2026), fornecido pelo
# Sergio. Vale para TODAS as empresas do cliente 30 (decisao de 04/09/2026).
MODELO_CLIENTE_30 = {
    "nome_modelo": "BC — cliente 30",
    "titulo": "CONTRATO INDIVIDUAL DE TRABALHO A TÍTULO DE EXPERIÊNCIA",

    "cabecalho": [
        "<b>EMPREGADOR:</b> {razao}, inscrita no CNPJ nº {cnpj}, com sede à "
        "{endereco_prosa}.",
        "<b>EMPREGADO:</b> {nome}, CPF nº {cpf}, matrícula nº {matricula_fmt}.",
    ],

    "preambulo": (
        "Por este instrumento particular, as partes acima identificadas firmam o "
        "presente contrato individual de trabalho, em caráter de experiência, nos "
        "termos dos artigos 443, 445 e 451 da Consolidação das Leis do Trabalho – "
        "CLT, mediante as seguintes condições:"
    ),

    "clausulas": [
        ("DA FUNÇÃO E REMUNERAÇÃO", [
            "O EMPREGADO exercerá a função de <b>{funcao}</b> (CBO {cbo}), "
            "desempenhando também as demais atribuições que lhe forem correlatas ou "
            "que com ela guardarem afinidade. A remuneração mensal será de "
            "<b>R$ {salario}</b> ({salario_extenso}), paga mensalmente, autorizando o "
            "EMPREGADO a EMPREGADORA a efetuar os depósitos dos salários e demais "
            "vencimentos em instituição bancária de sua escolha.",
        ]),

        ("DA JORNADA DE TRABALHO", [
            "A jornada de trabalho será {jornada_prosa}. A jornada poderá ser "
            "alterada pela EMPREGADORA de acordo com as necessidades dos serviços, "
            "respeitados os limites legais.",
        ]),

        ("DO PRAZO DE EXPERIÊNCIA", [
            "O presente contrato terá duração inicial de {dias_inicial} "
            "({dias_inicial_extenso}) dias, com início em <b>{dtadm_fmt}</b> e "
            "término em <b>{dtterm_inicial}</b>.",
            # So entra quando ainda cabe prorrogacao dentro dos 90 dias da CLT.
            ("tem_prorrogacao",
             "Por mútuo acordo, poderá ser prorrogado uma única vez por mais "
             "{dias_prorrog} ({dias_prorrog_extenso}) dias, mediante termo de "
             "prorrogação, passando o segundo período a vigorar de "
             "<b>{dtprorrog_ini}</b> até <b>{dtprorrog_fim}</b>, totalizando "
             "{dias_total} ({dias_total_extenso}) dias de experiência."),
        ]),

        ("DA CONTINUIDADE DO CONTRATO", [
            "Permanecendo o EMPREGADO a serviço da EMPREGADORA após o término do "
            "período de experiência, o contrato passará a vigorar por prazo "
            "indeterminado, permanecendo válidas as demais condições aqui "
            "estabelecidas.",
        ]),

        ("DAS OBRIGAÇÕES DO EMPREGADO", [
            "O EMPREGADO compromete-se a executar suas atividades com dedicação, zelo "
            "e lealdade, cumprir o regulamento interno da EMPREGADORA, as instruções "
            "de sua administração e as ordens de seus superiores hierárquicos, bem "
            "como observar as normas de segurança e demais procedimentos aplicáveis "
            "ao trabalho.",
        ]),

        ("DA COMPENSAÇÃO E PRORROGAÇÃO DE HORAS", [
            "O EMPREGADO compromete-se a trabalhar em regime de compensação e "
            "prorrogação de horas, inclusive em período noturno, sempre que as "
            "necessidades do serviço assim exigirem, observadas as formalidades e os "
            "limites legais.",
        ]),

        ("DOS DESCONTOS", [
            "A EMPREGADORA fica autorizada a descontar da remuneração ou de outros "
            "direitos de natureza trabalhista do EMPREGADO as contribuições legais "
            "e/ou convencionadas, adiantamentos e empréstimos concedidos, valores "
            "devidamente autorizados e eventuais prejuízos ou danos causados ao "
            "patrimônio da EMPREGADORA, quando legalmente cabíveis.",
        ]),

        ("DAS TRANSFERÊNCIAS", [
            "O EMPREGADO concorda, para os fins legais, inclusive nos termos do artigo "
            "469 da CLT, em ser transferido para outro estabelecimento da EMPREGADORA, "
            "situado nesta ou em outra localidade, quando atendidos os requisitos "
            "legais.",
        ]),

        ("DAS MODIFICAÇÕES", [
            "Durante a vigência do contrato poderão ser realizadas modificações de "
            "salário, função, cargo ou horário necessárias à adaptação ao emprego, "
            "desde que não resultem em prejuízo ao EMPREGADO e sejam observadas as "
            "disposições legais.",
        ]),

        ("DAS INVENÇÕES E RESULTADOS DO TRABALHO", [
            "As invenções, criações ou resultados decorrentes diretamente das "
            "atribuições do EMPREGADO e realizados com utilização das instalações, "
            "equipamentos ou recursos da EMPREGADORA observarão a legislação aplicável "
            "e as disposições internas da empresa.",
        ]),

        ("DA RESCISÃO ANTECIPADA", [
            "Aplicam-se ao presente contrato as normas relativas aos contratos por "
            "prazo determinado, observando-se, em caso de rescisão antecipada, as "
            "disposições legais pertinentes, inclusive os artigos 482 e 483 da CLT, "
            "conforme o caso.",
        ]),

        ("DA LGPD E PROTEÇÃO DE DADOS", [
            "A EMPREGADORA compromete-se a observar a Lei Federal nº 13.709/2018 (Lei "
            "Geral de Proteção de Dados – LGPD), adotando medidas técnicas e "
            "administrativas destinadas à proteção dos dados pessoais do EMPREGADO. O "
            "EMPREGADO declara estar ciente de que seus dados poderão ser tratados, "
            "armazenados e compartilhados com terceiros quando necessário ao "
            "cumprimento das obrigações legais, trabalhistas, previdenciárias, "
            "contratuais e administrativas da relação de emprego, observadas as bases "
            "legais aplicáveis.",
        ]),

        ("DO SIGILO", [
            "A EMPREGADORA e o EMPREGADO obrigam-se a manter sigilo sobre as "
            "informações de que tenham conhecimento em razão da relação de trabalho, "
            "utilizando-as exclusivamente para as finalidades relacionadas ao contrato "
            "e às atividades profissionais.",
        ]),

        ("DAS DISPOSIÇÕES FINAIS", [
            "Aplicam-se a este contrato todas as normas trabalhistas vigentes "
            "relativas aos contratos por prazo determinado e de experiência. Vencido o "
            "período experimental e permanecendo o EMPREGADO prestando serviços à "
            "EMPREGADORA, o contrato será convertido em prazo indeterminado, mantidas "
            "as demais condições contratadas.",
        ]),
    ],

    "fecho": (
        "E, por estarem de pleno acordo, as partes assinam o presente instrumento em "
        "02 (duas) vias de igual teor e para o mesmo fim, na presença de duas "
        "testemunhas."
    ),

    # Cidade/UF da empresa e a data da ADMISSAO por extenso (decisao de 04/09/2026).
    "local_data": "{cidade_uf}, {data_extenso}.",

    # Uma lista por coluna de assinatura. O montador desenha a linha por cima de
    # cada coluna e o vao entre elas — igual ao PDF do BC, sem testemunhas.
    "assinaturas": [
        ["{nome}",  "EMPREGADO",  "CPF: {cpf}"],
        ["{razao}", "EMPREGADOR", "CNPJ: {cnpj}"],
    ],
}


MODELOS_POR_CLIENTE = {
    30: MODELO_CLIENTE_30,
}


def modelo_do_cliente(id_cliente):
    """Modelo proprio do cliente, ou None para usar o contrato padrao."""
    try:
        return MODELOS_POR_CLIENTE.get(int(id_cliente or 0))
    except (TypeError, ValueError):
        return None


# =========================================================
# MONTADOR — o mesmo para todos os modelos
# =========================================================

def _subst(txt, d):
    """Troca {marcador} pelo valor. O que nao existir fica literal, de proposito."""
    return re.sub(r"\{(\w+)\}",
                  lambda m: str(d.get(m.group(1), m.group(0))),
                  str(txt or ""))


def _corpo(trechos, d):
    """Junta os trechos de uma clausula num paragrafo so, pulando os condicionais
    que nao se aplicam."""
    saida = []
    for t in trechos:
        if isinstance(t, (tuple, list)):
            chave, txt = t
            if not d.get(chave):
                continue
        else:
            txt = t
        saida.append(_subst(txt, d))
    return " ".join(saida)


def _bloco_assinaturas(colunas, d, st_ass, PRETO, cm, Table, TableStyle, Paragraph):
    """Colunas de assinatura lado a lado, cada uma com a linha por cima."""
    n = len(colunas)
    if not n:
        return None
    vao   = 1.6                                   # cm entre uma coluna e outra
    larg  = (17.0 - vao * (n - 1)) / n
    altura = max(len(c) for c in colunas)

    dados, larguras = [], []
    for i in range(n):
        larguras.append(larg * cm)
        if i < n - 1:
            larguras.append(vao * cm)

    for linha in range(altura):
        celulas = []
        for i, col in enumerate(colunas):
            txt = _subst(col[linha], d) if linha < len(col) else "&nbsp;"
            # A 2a linha e' o papel da parte (EMPREGADO / EMPREGADOR): negrito.
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
        col = i * 2                                # pula as colunas de vao
        estilo.append(("LINEABOVE", (col, 0), (col, 0), 0.8, PRETO))

    return Table(dados, colWidths=larguras, style=TableStyle(estilo))


def montar_story(modelo, d):
    """Flowables do contrato do cliente, prontos para o SimpleDocTemplate."""
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

    story = [Paragraph(_subst(modelo.get("titulo", ""), d), st_tit), Spacer(1, 10)]

    for linha in modelo.get("cabecalho", []):
        story += [Paragraph(_subst(linha, d), st_cab), Spacer(1, 3)]

    if modelo.get("preambulo"):
        story += [Spacer(1, 3), Paragraph(_subst(modelo["preambulo"], d), st_txt)]

    for n, (titulo, trechos) in enumerate(modelo.get("clausulas", []), 1):
        story += [Paragraph(f"CLÁUSULA {n}ª – {_subst(titulo, d)}", st_cla),
                  Paragraph(_corpo(trechos, d), st_txt)]

    if modelo.get("fecho"):
        story += [Spacer(1, 10), Paragraph(_subst(modelo["fecho"], d), st_txt)]

    if modelo.get("local_data"):
        story += [Spacer(1, 18), Paragraph(_subst(modelo["local_data"], d), st_cab)]

    bloco = _bloco_assinaturas(modelo.get("assinaturas", []), d, st_ass,
                               PRETO, cm, Table, TableStyle, Paragraph)
    if bloco is not None:
        story += [Spacer(1, 34), bloco]

    return story
