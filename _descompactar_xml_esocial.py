# -*- coding: utf-8 -*-
"""
Etapa 1 da importacao do eSocial: descompacta os ZIPs baixados a mao do portal
(C:\\XMLeSocial\\XMLzip) para a pasta de trabalho (C:\\XMLeSocial\\XML),
podendo trazer SO os layouts que interessam agora.

O filtro nao precisa abrir o XML: o portal nomeia cada arquivo terminando com o
layout, no formato  ID<numero>.S-2200.xml.

Uso:
    python _descompactar_xml_esocial.py --listar
    python _descompactar_xml_esocial.py --preset cadastro
    python _descompactar_xml_esocial.py --layouts S-2200,S-2206,S-2299
    python _descompactar_xml_esocial.py --layouts 2200,2206 --de 202601 --ate 202612
    python _descompactar_xml_esocial.py                      # tudo

--listar so conta o que existe nos ZIPs, sem gravar nada. Sempre bom rodar
antes para saber com o que se esta lidando.

O nucleo e o processar(), usado tambem pela tela Admin > Migracao > Descompactar
XML do eSocial (rotas /admin_descompactar_xml). Mexer aqui muda os dois.
"""
import os, re, sys, zipfile, argparse, tempfile
from collections import Counter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ORIGEM  = r"C:\XMLeSocial\XMLzip"
DESTINO = r"C:\XMLeSocial\XML"
# As planilhas geradas a partir dos XMLs. Entra aqui porque a Etapa 1 so pode
# comecar com as duas pastas de trabalho VAZIAS: sobra de uma rodada anterior se
# mistura com a nova e ninguem percebe.
PLANILHAS = r"C:\XMLeSocial\Planilhas"

# Nome do arquivo dentro do ZIP: ID<...>.S-2200.xml
RE_LAYOUT = re.compile(r"\.(S-\d{4})\.xml$", re.I)
# Nome do ZIP do portal: "202105 - 22821433.zip" -> competencia 202105
RE_COMPET = re.compile(r"(20\d{4})")

# Todo XML baixado traz o recibo DELE proprio no bloco <recibo> do download; o
# S-3000 aponta o recibo do evento que ele EXCLUIU. Casando um no outro sabemos
# quais arquivos da pasta estao mortos. Regex em vez de parser de XML porque sao
# milhares de arquivos e a tag e sempre plana.
RE_RECIBO = re.compile(rb"<nrRecibo>([^<]+)</nrRecibo>")
RE_RECEVT = re.compile(rb"<nrRecEvt>([^<]+)</nrRecEvt>")


# Quem é o empregador dos ZIPs. PEGA: o S-1000 do eSocial NAO tem razao social —
# so o CNPJ raiz em ideEmpregador/nrInsc (o governo ja sabe o nome pelo CNPJ).
# O nome tem que vir de fora: do cadastro do Folha10 (quem chama cruza) ou, como
# pista, do certificado que assinou. Regex pelo mesmo motivo do recibo.
RE_NRINSC = re.compile(rb"<nrInsc>([^<]+)</nrInsc>")
RE_X509   = re.compile(rb"<X509Certificate>([^<]+)</X509Certificate>")


def tag_do_xml(dados, nome):
    """Texto de uma tag plana do XML. Sem parser: sao milhares de arquivos."""
    m = re.search(("<%s>([^<]*)</%s>" % (nome, nome)).encode("ascii"), dados or b"")
    return m.group(1).decode("utf-8", "replace").strip() if m else ""


# O que o S-1000 tem que serve para ABRIR a empresa no Folha10. Nao tem razao
# social — ela entra provisoria e o usuario corrige no cadastro.
S1000_CAMPOS = ("classTrib", "natJurid", "indCoop", "indConstr", "indDesFolha",
                "indPorte", "nmCtt", "cpfCtt", "email", "foneFixo", "foneCel",
                "iniValid")


def dados_s1000(dados):
    return {k: tag_do_xml(dados, k) for k in S1000_CAMPOS}


def assinante_do_xml(dados):
    """Nome do certificado que assinou o evento.

    CUIDADO: e quem TRANSMITIU, que muitas vezes e o contador/procurador e nao a
    empresa — nos ZIPs de teste o empregador e 04866946 e quem assina e outro
    CNPJ. Serve so como pista para reconhecer de quem e a pasta.
    """
    m = RE_X509.search(dados or b"")
    if not m:
        return {}
    try:
        import base64
        from cryptography import x509
        cert = x509.load_der_x509_certificate(base64.b64decode(m.group(1)))
        cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    except Exception:
        return {}
    nome, _, doc = str(cn).partition(":")
    return {"nome": nome.strip(), "cnpj": re.sub(r"\D", "", doc)[:14]}


def formatar_cnpj(v):
    """'12345678' -> '12.345.678'; 14 digitos -> '12.345.678/0001-99'."""
    s = re.sub(r"\D", "", str(v or ""))
    if len(s) >= 14:
        return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:14]}"
    if len(s) == 8:
        return f"{s[:2]}.{s[2:5]}.{s[5:8]}"
    return s


def identificar_empresa(origem, de="", ate=""):
    """De quem sao os ZIPs — antes de descompactar qualquer coisa.

    Sem isso da para passar a tarde conferindo a planilha da empresa errada.
    Le os S-1000 e S-1005 (poucos arquivos): o S-1000 da o CNPJ raiz do
    empregador e o S-1005 os CNPJs completos dos estabelecimentos. Sem eles, cai
    para uma amostra de qualquer evento — todo evento traz ideEmpregador.
    """
    zips = listar_zips(origem, de, ate)
    if not zips:
        return {"ok": False, "msg": f"Nenhum .zip em {origem}"
                                    + (" no período informado." if (de or ate) else ".")}

    raizes, estabs, assinante = {}, {}, {}
    s1000, s1000_arq = {}, ""

    def anotar(dados):
        nonlocal assinante
        achou = False
        for bruto in RE_NRINSC.findall(dados or b""):
            d = re.sub(r"\D", "", bruto.decode("ascii", "ignore"))
            if len(d) == 14:
                estabs[d] = estabs.get(d, 0) + 1
                d = d[:8]
            elif len(d) != 8:
                continue
            if not achou:                     # 1 evento conta 1 vez para a raiz
                raizes[d] = raizes.get(d, 0) + 1
                achou = True
        if not assinante:
            assinante = assinante_do_xml(dados) or {}

    so_tabelas = lambda n: bool(re.search(r"\.S-100[05]\.xml$", n, re.I))
    for nz in zips:
        for nome, dados in iter_xmls(os.path.join(origem, nz), filtro_nome=so_tabelas):
            if not (nome and dados):
                continue
            anotar(dados)
            # O nome do arquivo do portal e ID<cnpj><AAAAMMDDHHMMSS><seq>, entao a
            # ordem alfabetica maior e o S-1000 mais recente — o que vale hoje.
            if re.search(r"\.S-1000\.xml$", nome, re.I) and nome > s1000_arq:
                s1000_arq, s1000 = nome, dados_s1000(dados)

    fonte = "S-1000 / S-1005"
    if not raizes:                            # sem tabelas: amostra de qualquer evento
        fonte = "amostra de eventos"
        vistos = 0
        for nz in zips:
            for nome, dados in iter_xmls(os.path.join(origem, nz)):
                if nome and dados:
                    anotar(dados)
                    vistos += 1
                if vistos >= 20:
                    break
            if vistos >= 20:
                break

    if assinante.get("cnpj"):
        assinante["cnpj_fmt"] = formatar_cnpj(assinante["cnpj"])
    return {
        "ok": True, "fonte": fonte, "zips": len(zips),
        "empresas": [{"cnpj": c, "cnpj_fmt": formatar_cnpj(c), "eventos": n}
                     for c, n in sorted(raizes.items(), key=lambda x: -x[1])],
        "estabelecimentos": [formatar_cnpj(c) for c in sorted(estabs)],
        "estabelecimentos_num": sorted(estabs),
        "s1000": s1000, "s1000_arquivo": s1000_arq,
        "assinante": assinante,
    }


def recibo_proprio(dados):
    """Recibo DESTE evento — o do bloco <recibo> do download, sempre no fim.

    PEGA: evento de RETIFICACAO traz outro <nrRecibo> la em cima, no ideEvento,
    que e o do evento retificado. Pegando o primeiro do arquivo se compara com
    recibo alheio: na base de teste 1 dos 126 S-2206 estava anulado por um
    S-3000 e passava batido.
    """
    corte = dados.rfind(b"<recibo>")
    m = RE_RECIBO.search(dados, corte if corte >= 0 else 0)
    return m.group(1).decode("ascii", "ignore").strip() if m else ""

PRESETS = {
    # o que o importador da tela le: empresa + funcionario + exclusoes.
    # O S-1000 entra porque na base nova a empresa pode nem existir ainda — e
    # dele que saem os dados do empregador.
    "cadastro": ["S-1000", "S-1005", "S-1020",
                 "S-2200", "S-2205", "S-2206", "S-2230", "S-2299",
                 "S-2300", "S-2306", "S-2399", "S-3000"],
    # a folha em si
    "folha":    ["S-1200", "S-1210", "S-1280", "S-1298", "S-1299", "S-3000"],
    # tabelas do empregador
    "tabelas":  ["S-1000", "S-1005", "S-1010", "S-1020", "S-1030", "S-1050"],
    # totalizadores devolvidos pelo eSocial
    "totais":   ["S-5001", "S-5002", "S-5003", "S-5011", "S-5012", "S-5013"],
}

# O que a Etapa 1 da tela traz marcado. Menos que o preset "cadastro" de
# proposito: e so o que a importacao usa hoje. S-1000 entra porque na base nova
# a empresa pode nem existir; S-3000 porque e ele que diz o que esta morto.
ETAPA1 = ["S-1000", "S-2200", "S-2205", "S-2206", "S-2230", "S-2299", "S-3000"]

# Rotulo de cada layout, para a tela nao mostrar so o codigo seco.
NOMES = {
    "S-1000": "Informações do empregador",
    "S-1005": "Estabelecimentos",
    "S-1010": "Rubricas",
    "S-1020": "Lotações tributárias",
    "S-1030": "Cargos",
    "S-1050": "Horários de trabalho",
    "S-1200": "Remuneração (folha)",
    "S-1210": "Pagamentos",
    "S-1280": "Informações complementares",
    "S-1298": "Reabertura do movimento",
    "S-1299": "Fechamento do movimento",
    "S-2190": "Admissão preliminar",
    "S-2200": "Admissão / cadastro inicial",
    "S-2205": "Alteração de dados cadastrais",
    "S-2206": "Alteração de contrato",
    "S-2210": "CAT (acidente)",
    "S-2220": "Monitoramento da saúde",
    "S-2230": "Afastamento temporário",
    "S-2240": "Condições ambientais",
    "S-2298": "Reintegração",
    "S-2299": "Desligamento",
    "S-2300": "TSVE — início",
    "S-2306": "TSVE — alteração",
    "S-2399": "TSVE — término",
    "S-3000": "EXCLUSÃO de evento enviado",
    "S-5001": "Totais de INSS por trabalhador",
    "S-5002": "Totais de IRRF por trabalhador",
    "S-5003": "Totais de FGTS por trabalhador",
    "S-5011": "Totais de INSS por empresa",
    "S-5012": "Totais de IRRF por empresa",
    "S-5013": "Totais de FGTS por empresa",
}


def arquivos_da_pasta(pasta):
    """Todos os arquivos de dentro da pasta, descendo as subpastas."""
    if not os.path.isdir(pasta):
        return []
    fora = []
    for raiz, _dirs, arqs in os.walk(pasta):
        fora.extend(os.path.join(raiz, a) for a in arqs)
    return fora


def pastas_de_trabalho(destino=DESTINO, planilhas=PLANILHAS):
    """O que ja existe nas pastas que a Etapa 1 vai gravar."""
    return [{"pasta": p, "qtd": len(arquivos_da_pasta(p))}
            for p in (destino, planilhas)]


def limpar_pastas(destino=DESTINO, planilhas=PLANILHAS):
    """Esvazia as pastas de trabalho — apaga o CONTEUDO, nunca a pasta em si.

    So roda depois de o usuario confirmar na tela (ou responder --limpar no CLI).
    """
    apagados, erros = 0, []
    for pasta in (destino, planilhas):
        if not os.path.isdir(pasta):
            continue
        for caminho in arquivos_da_pasta(pasta):
            try:
                os.remove(caminho)
                apagados += 1
            except OSError as e:
                erros.append(f"{os.path.basename(caminho)}: {e}")
        # O modo "uma subpasta por layout" deixa varias subpastas para tras.
        for raiz, _dirs, _arqs in os.walk(pasta, topdown=False):
            if os.path.normpath(raiz) == os.path.normpath(pasta):
                continue
            try:
                os.rmdir(raiz)
            except OSError:
                pass
    return {"ok": not erros, "apagados": apagados, "erros": erros[:5]}


def normalizar_layouts(itens):
    """Aceita 'S-2200,2206', lista, 's2200'... e devolve o conjunto padronizado."""
    if isinstance(itens, str):
        itens = itens.replace(";", ",").split(",")
    fora = set()
    for p in (itens or []):
        p = str(p or "").strip().upper().replace("S-", "").replace("S", "")
        if not p:
            continue
        if not p.isdigit() or len(p) != 4:
            continue
        fora.add("S-" + p)
    return fora


def competencia_do_zip(nome):
    m = RE_COMPET.search(os.path.basename(nome))
    return m.group(1) if m else ""


def listar_zips(origem, de="", ate=""):
    """ZIPs da pasta, opcionalmente filtrados pela competencia do nome."""
    if not os.path.isdir(origem):
        return []
    zips = sorted(f for f in os.listdir(origem) if f.lower().endswith(".zip"))
    if de or ate:
        zips = [z for z in zips
                if (not de  or (competencia_do_zip(z) and competencia_do_zip(z) >= de))
                and (not ate or (competencia_do_zip(z) and competencia_do_zip(z) <= ate))]
    return zips


def iter_xmls(caminho, nivel=1, so_nomes=False, filtro_nome=None):
    """Percorre o ZIP e devolve (nome_do_xml, bytes | None), descendo ZIP dentro
    de ZIP ate 3 niveis.

    O download por periodo do portal aninha quando o periodo tem muito evento;
    sem descer, a extracao termina em zero calada. Com so_nomes=True nao
    descompacta o conteudo — e o modo do inventario, muito mais rapido.
    filtro_nome(nome) -> False descarta o arquivo antes de descompactar.
    """
    try:
        with zipfile.ZipFile(caminho) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                nome = os.path.basename(info.filename)
                if nome.lower().endswith(".zip"):
                    if nivel >= 3:
                        continue
                    # ZIP aninhado tem que sair para o disco para ser aberto.
                    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                        tmp.write(z.read(info))
                        tmp_nome = tmp.name
                    try:
                        for item in iter_xmls(tmp_nome, nivel + 1, so_nomes, filtro_nome):
                            yield item
                    finally:
                        try:
                            os.unlink(tmp_nome)
                        except OSError:
                            pass
                elif nome.lower().endswith(".xml"):
                    if filtro_nome and not filtro_nome(nome):
                        continue
                    yield nome, (None if so_nomes else z.read(info))
    except zipfile.BadZipFile:
        yield "", None          # sinaliza ZIP invalido para quem chamou


def recibos_excluidos(origem, zips, progresso=None):
    """Recibos dos eventos anulados por um S-3000.

    O S-3000 e o unico jeito de saber que um XML da pasta esta morto: ele traz
    <nrRecEvt> com o recibo do evento excluido. Le so os proprios S-3000 — sao
    poucos perto do total.
    """
    fora = set()
    so_s3000 = lambda n: bool(re.search(r"\.S-3000\.xml$", n, re.I))
    for i, nz in enumerate(zips, 1):
        for nome, dados in iter_xmls(os.path.join(origem, nz), filtro_nome=so_s3000):
            if nome and dados:
                fora.update(r.decode("ascii", "ignore").strip()
                            for r in RE_RECEVT.findall(dados))
        if progresso:
            progresso(i, len(zips))
    return fora


def processar(origem=ORIGEM, destino=DESTINO, layouts=None, de="", ate="",
              listar=False, sub_layout=False, sobrescrever=False,
              pular_excluidos=True, progresso=None):
    """Nucleo compartilhado pelo CLI e pela tela. Nao imprime nada.

    Com listar=True so conta o que existe nos ZIPs (nao grava).
    Com pular_excluidos=True (padrao) o que foi anulado por um S-3000 nao e
    extraido — senao entra no importador funcionario que o eSocial ja apagou.
    Isso obriga a ler o conteudo dos arquivos, entao deixa o inventario mais
    lento; e o preco de saber quem esta morto.
    """
    querer = normalizar_layouts(layouts) if layouts else set()
    if not os.path.isdir(origem):
        return {"ok": False, "msg": f"Pasta de origem não existe: {origem}"}

    zips = listar_zips(origem, de, ate)
    if not zips:
        return {"ok": False, "msg": f"Nenhum .zip em {origem}"
                                    + (" no período informado." if (de or ate) else ".")}

    if not listar:
        try:
            os.makedirs(destino, exist_ok=True)
        except OSError as e:
            return {"ok": False, "msg": f"Não deu para criar a pasta de destino: {e}"}

    # A tela mostra barra: a varredura dos S-3000 ocupa o primeiro terco e a
    # extracao o resto. Sem isso a barra ficaria parada durante a 1a passada.
    def _passo(ini, fim, i, n, etapa):
        if progresso:
            progresso(int(ini + (fim - ini) * i / max(1, n)), etapa)

    anulados = (recibos_excluidos(
        origem, zips,
        progresso=lambda i, n: _passo(0, 30, i, n, "procurando exclusões (S-3000)"))
        if pular_excluidos else set())

    achados = Counter()        # layout -> quantos existem nos ZIPs
    gravados = Counter()       # layout -> quantos foram gravados (ou listados)
    excluidos = Counter()      # layout -> quantos estao anulados por S-3000
    ja_tinha = pulados = sem_padrao = repetidos = 0
    invalidos = []
    vistos = set()             # o mesmo evento pode repetir em ZIPs diferentes

    # Sem a checagem de exclusao o inventario nao precisa descompactar nada.
    so_nomes = listar and not pular_excluidos

    for i_zip, nz in enumerate(zips, 1):
        _passo(30 if pular_excluidos else 0, 100, i_zip - 1, len(zips), nz)
        for nome, dados in iter_xmls(os.path.join(origem, nz), so_nomes=so_nomes):
            if not nome:
                invalidos.append(nz)
                continue
            m = RE_LAYOUT.search(nome)
            if not m:
                sem_padrao += 1
                continue
            layout = m.group(1).upper()
            achados[layout] += 1
            if querer and layout not in querer:
                pulados += 1
                continue
            if nome in vistos:
                repetidos += 1
                continue
            vistos.add(nome)
            if anulados and dados:
                meu = recibo_proprio(dados)
                if meu and meu in anulados:
                    excluidos[layout] += 1
                    continue
            if listar:
                gravados[layout] += 1
                continue
            pasta = os.path.join(destino, layout) if sub_layout else destino
            os.makedirs(pasta, exist_ok=True)
            alvo = os.path.join(pasta, nome)
            if os.path.exists(alvo) and not sobrescrever:
                ja_tinha += 1
                continue
            with open(alvo, "wb") as f:
                f.write(dados)
            gravados[layout] += 1

    linhas = [{"layout": k, "nome": NOMES.get(k, ""), "nos_zips": achados[k],
               "gravados": gravados.get(k, 0), "excluidos": excluidos.get(k, 0)}
              for k in sorted(achados)]
    return {
        "ok": True, "origem": origem, "destino": destino, "listar": listar,
        "zips": len(zips), "linhas": linhas, "checou_exclusao": bool(pular_excluidos),
        "competencias": sorted({c for c in (competencia_do_zip(z) for z in zips) if c}),
        "total_zips": sum(achados.values()), "total_gravados": sum(gravados.values()),
        "total_excluidos": sum(excluidos.values()), "anulacoes": len(anulados),
        "pulados": pulados, "repetidos": repetidos, "ja_tinha": ja_tinha,
        "sem_padrao": sem_padrao, "invalidos": sorted(set(invalidos)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origem", default=ORIGEM)
    ap.add_argument("--destino", default=DESTINO)
    ap.add_argument("--layouts", default="", help="S-2200,S-2206  (ou so 2200,2206)")
    ap.add_argument("--preset", default="", choices=sorted(PRESETS),
                    help="conjunto pronto: " + ", ".join(sorted(PRESETS)))
    ap.add_argument("--de", default="", help="competencia inicial do ZIP, AAAAMM")
    ap.add_argument("--ate", default="", help="competencia final do ZIP, AAAAMM")
    ap.add_argument("--listar", action="store_true", help="so conta, nao grava")
    ap.add_argument("--subpasta-layout", action="store_true", dest="sub_layout",
                    help="grava em uma subpasta por layout (XML\\S-2200\\...)")
    ap.add_argument("--sobrescrever", action="store_true",
                    help="regrava arquivo que ja existe no destino")
    ap.add_argument("--manter-excluidos", action="store_true", dest="manter_excluidos",
                    help="extrai tambem o que foi anulado por um S-3000 "
                         "(padrao: nao extrai)")
    ap.add_argument("--limpar", action="store_true",
                    help="esvazia as pastas de trabalho (XML e Planilhas) antes de "
                         "extrair; sem isso, pasta com arquivo aborta a extracao")
    args = ap.parse_args()

    # De quem sao os ZIPs, antes de tudo. Na tela isso e uma pergunta; aqui, ao
    # menos, sai impresso antes de gravar qualquer arquivo.
    emp = identificar_empresa(args.origem, args.de, args.ate)
    if emp.get("ok"):
        print("=" * 70, flush=True)
        for e in emp["empresas"]:
            print(f"Empregador: {e['cnpj_fmt']}  ({e['eventos']} evento(s), "
                  f"por {emp['fonte']})", flush=True)
        if len(emp["empresas"]) > 1:
            print("[ATENCAO] os ZIPs tem mais de um CNPJ.", flush=True)
        if emp.get("estabelecimentos"):
            print("Estabelecimentos: " + ", ".join(emp["estabelecimentos"]), flush=True)
        if emp.get("assinante", {}).get("nome"):
            print(f"Assinado por: {emp['assinante']['nome']} "
                  f"{emp['assinante'].get('cnpj_fmt','')} (pode ser o contador)", flush=True)

    # Pasta de trabalho com sobra da rodada anterior nao entra calada no meio da
    # nova: ou se manda apagar (--limpar), ou nao comeca.
    if not args.listar:
        cheias = [p for p in pastas_de_trabalho(destino=args.destino) if p["qtd"]]
        if cheias and not args.limpar:
            print("[ABORTADO] pasta de trabalho com arquivo:", flush=True)
            for p in cheias:
                print(f"  {p['pasta']}  ({p['qtd']} arquivo(s))", flush=True)
            print("Esvazie a mao ou rode de novo com --limpar.", flush=True)
            sys.exit(1)
        if cheias:
            r = limpar_pastas(destino=args.destino)
            print(f"Pastas de trabalho esvaziadas: {r['apagados']} arquivo(s) apagado(s).",
                  flush=True)
            for e in r["erros"]:
                print(f"[ERRO] {e}", flush=True)
            if not r["ok"]:
                sys.exit(1)

    querer = normalizar_layouts(args.layouts)
    if args.preset:
        querer |= set(PRESETS[args.preset])

    r = processar(args.origem, args.destino, querer, args.de, args.ate,
                  args.listar, args.sub_layout, args.sobrescrever,
                  pular_excluidos=not args.manter_excluidos)
    if not r["ok"]:
        print(f"[ABORTADO] {r['msg']}", flush=True)
        sys.exit(1)

    print("=" * 70, flush=True)
    print(f"Origem    : {r['origem']}  ({r['zips']} ZIPs)", flush=True)
    print(f"Destino   : {r['destino']}"
          f"{' (subpasta por layout)' if args.sub_layout else ''}", flush=True)
    if args.de or args.ate:
        print(f"Periodo   : {args.de or '...'} a {args.ate or '...'}", flush=True)
    print(f"Layouts   : {', '.join(sorted(querer)) if querer else 'TODOS'}", flush=True)
    print(f"Excluidos : {'EXTRAI TAMBEM (--manter-excluidos)' if args.manter_excluidos else 'nao extrai o que o S-3000 anulou'}", flush=True)
    print(f"Modo      : {'SO LISTAR (nao grava)' if args.listar else 'EXTRAIR'}", flush=True)
    print("=" * 70, flush=True)
    print(f"{'Layout':<10}{'nos ZIPs':>10}  "
          f"{'listaria' if args.listar else 'gravados':>10}{'anulados':>10}", flush=True)
    for L in r["linhas"]:
        print(f"{L['layout']:<10}{L['nos_zips']:>10}  {L['gravados']:>10}"
              f"{L['excluidos'] or '':>10}", flush=True)
    print("-" * 70, flush=True)
    print(f"XMLs nos ZIPs      : {r['total_zips']}", flush=True)
    if r["checou_exclusao"]:
        print(f"Anulados por S-3000: {r['total_excluidos']} "
              f"(de {r['anulacoes']} exclusoes lidas)", flush=True)
    print(f"{'Listaria' if args.listar else 'Gravados':<19}: {r['total_gravados']}", flush=True)
    if querer:
        print(f"Fora do filtro     : {r['pulados']}", flush=True)
    if r["repetidos"]:
        print(f"Repetidos entre ZIPs: {r['repetidos']} (mesmo nome, gravado uma vez)", flush=True)
    if r["ja_tinha"]:
        print(f"Ja existiam        : {r['ja_tinha']} (use --sobrescrever para regravar)", flush=True)
    if r["sem_padrao"]:
        print(f"Fora do padrao ID..S-XXXX.xml: {r['sem_padrao']}", flush=True)
    for z in r["invalidos"]:
        print(f"[ERRO] ZIP invalido: {z}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
