import pyodbc, datetime

db   = r'C:\Folha10\ARQUIVOS\BASES\FolhaFIX_000690.ACCDB'
conn = pyodbc.connect(r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db)
cur  = conn.cursor()
cur.execute('SELECT * FROM tabverba ORDER BY codigo')
cols = [d[0] for d in cur.description]
rows = [dict(zip(cols, r)) for r in cur.fetchall()]
conn.close()

def s(v):
    return '' if v is None else str(v).strip()

def conv_flag(val):
    v = s(val).upper()
    if v.startswith('NAO') or v.startswith('N\xc3\x83O') or v == '':
        return 'N'
    if v in ('CAL', '12U', 'PAQ'):
        return 'S'
    return 'S'

def tp_rubr_label(t):
    return {'1': 'Provento', '2': 'Desconto', '3': 'Informativa', '4': 'Info.Dedutora'}.get(t, t)

def unid_label(u):
    return {'V': 'Valor (R$)', 'H': 'Hora', 'D': 'Diaria', 'E': 'Especial'}.get(u, u)

def inc_label(c):
    return 'Incide' if c == 'S' else ('Nao incide' if c == 'N' else '???')

def id_cli(cod_int):
    # Regra 1: cod_rubr < 1000 → id_cliente = 0 (verba do sistema)
    return 0 if cod_int < 1000 else '<ID_CLIENTE>'

INI_VALID = 202001   # Regra 4

SEP  = '=' * 100
SEP2 = '-' * 100

# Regras 2 e 3: apenas ativas (sit=A) e empresa=0
importar = [r for r in rows if s(r['situacao']) == 'A' and (r['empresa'] or 0) == 0]
ignorar  = [r for r in rows if s(r['situacao']) == 'D' or (r['empresa'] or 0) > 0]

out = []
out.append(SEP)
out.append('  VERBAS PARA GRAVACAO EM tab_rubrica')
out.append('  Origem : tabverba (FolhaFIX_000690.ACCDB)')
out.append('  Gerado : ' + datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))
out.append('  Regras aplicadas:')
out.append('    - id_cliente = 0 quando cod_rubr < 1000  (sistema)  |  >= 1000 usa id do cliente')
out.append('    - ini_valid  = %d' % INI_VALID)
out.append('    - Apenas verbas ATIVAS (situacao=A)')
out.append('    - Verbas com empresa > 0 EXCLUIDAS')
out.append('  Total lido: %d  |  Para importar: %d  |  Excluidas: %d' % (len(rows), len(importar), len(ignorar)))
out.append(SEP)

# ------------------------------------------------------------------ Detalhes
out.append('')
out.append(SEP)
out.append('  DETALHAMENTO VERBA A VERBA (%d registros)' % len(importar))
out.append(SEP)

for r in importar:
    cod  = s(r['codigo'])
    nom  = s(r['nomec'])
    res  = s(r['nomer'])
    sin  = s(r['sinal'])
    uni  = s(r['unidade'])
    inc  = s(r['incidencia'])
    resc = s(r['rescisao'])
    fer  = s(r['ferias'])
    t13  = s(r['13sal'])
    t13a = s(r['13sala'])
    esoc = str(r['esocial_tab03']) if r['esocial_tab03'] else ''
    form = s(r['formula'])
    perc = r['percentual'] or 0

    d_cod  = int(cod)
    d_cli  = id_cli(d_cod)
    d_tp   = '1' if sin == '+' else ('2' if sin == '-' else '?')
    d_un   = uni if uni in ('V', 'H', 'D') else uni
    d_cp   = inc[0] if len(inc) > 0 else 'N'
    d_fg   = inc[1] if len(inc) > 1 else 'N'
    d_ir   = inc[2] if len(inc) > 2 else 'N'
    d_pi   = inc[3] if len(inc) > 3 else 'N'
    d_dsr  = inc[4] if len(inc) > 4 else 'N'
    d_rsc  = conv_flag(resc)
    d_fer  = conv_flag(fer)
    d_13   = conv_flag(t13)
    d_13a  = conv_flag(t13a)
    d_esoc = int(esoc) if esoc else None

    flag_unit = '  [** UNIDADE ESPECIAL -- revisar **]' if uni == 'E' else ''

    out.append('')
    out.append(SEP2)
    out.append('VERBA %04d -- %s%s' % (d_cod, nom, flag_unit))
    out.append(SEP2)

    out.append('  [ ORIGEM Access ]')
    out.append('    codigo      : %s' % cod)
    out.append('    nomec       : %s' % nom)
    out.append('    nomer       : %s' % res)
    out.append('    sinal       : %s (%s)' % (sin, 'Provento' if sin == '+' else 'Desconto'))
    out.append('    unidade     : %s (%s)' % (uni, unid_label(uni)))
    out.append('    incidencia  : %s  (pos1=CP  pos2=FGTS  pos3=IRRF  pos4=PIS  pos5=DSR)' % (inc or 'NNNNN'))
    out.append('    rescisao    : %-6s  ferias: %-6s  13sal: %-6s  13sala: %s' % (resc, fer, t13, t13a))
    out.append('    esocial_t03 : %s' % esoc)
    if form and form != '*':
        out.append('    formula     : %s' % form)
    if perc:
        out.append('    percentual  : %s%%' % perc)

    out.append('')
    out.append('  [ DESTINO tab_rubrica ]')
    out.append('    id_cliente        : %s' % d_cli)
    out.append('    cod_rubr          : %d' % d_cod)
    out.append('    ini_valid         : %d' % INI_VALID)
    out.append('    dsc_rubr          : %s' % nom[:40])
    out.append('    dsc_rubr_resumido : %s' % res[:20])
    out.append('    tp_rubr           : %s  (%s)' % (d_tp, tp_rubr_label(d_tp)))
    out.append('    unid_verba        : %s  (%s)' % (d_un, unid_label(d_un)))
    out.append('    situacao          : A')
    out.append('    es03_nat_rubr     : %s' % (d_esoc if d_esoc else '---'))

    out.append('')
    out.append('    -- Incidencias folha NORMAL --')
    out.append('    tpn_inc_cp        : %s  (%s)' % (d_cp, inc_label(d_cp)))
    out.append('    tpn_inc_fgts      : %s  (%s)' % (d_fg, inc_label(d_fg)))
    out.append('    tpn_inc_irrf      : %s  (%s)' % (d_ir, inc_label(d_ir)))
    out.append('    tpn_inc_pis       : %s  (%s)' % (d_pi, inc_label(d_pi)))
    out.append('    DSR (pos5)        : %s  (%s)  ** sem campo em tab_rubrica **' % (d_dsr, inc_label(d_dsr)))

    out.append('')
    out.append('    -- Incidencias RESCISAO / FERIAS / 13SAL --')
    out.append('    inc_rescisao      : %s  (Access: %s)' % (d_rsc, resc))
    out.append('    inc_ferias        : %s  (Access: %s)' % (d_fer, fer))
    out.append('    inc_13sal         : %s  (Access: %s)' % (d_13,  t13))
    out.append('    inc_adto13        : %s  (Access: %s)' % (d_13a, t13a))

    out.append('')
    out.append('    -- Incidencias por PERIODO (replicado da folha normal) --')
    out.append('    tpr_inc_cp/fgts/irrf/pis : %s/%s/%s/%s  (rescisao)' % (d_cp, d_fg, d_ir, d_pi))
    out.append('    tpf_inc_cp/fgts/irrf/pis : %s/%s/%s/%s  (ferias)'   % (d_cp, d_fg, d_ir, d_pi))
    out.append('    tp1_inc_cp/fgts/irrf/pis : %s/%s/%s/%s  (13 sal)'   % (d_cp, d_fg, d_ir, d_pi))

# ------------------------------------------------------------------ SQL INSERT
out.append('')
out.append(SEP)
out.append('  BLOCO SQL -- INSERT INTO tab_rubrica')
out.append('  %d registros  |  cod_rubr < 1000 gravam id_cliente=0' % len(importar))
out.append(SEP)
out.append('')

for r in importar:
    cod  = s(r['codigo'])
    nom  = s(r['nomec'])[:40].replace("'", "''")
    res  = s(r['nomer'])[:20].replace("'", "''")
    sin  = s(r['sinal'])
    uni  = s(r['unidade']) if s(r['unidade']) in ('V', 'H', 'D') else 'V'
    inc  = s(r['incidencia'])
    resc = s(r['rescisao'])
    fer  = s(r['ferias'])
    t13  = s(r['13sal'])
    t13a = s(r['13sala'])
    esoc = str(r['esocial_tab03']) if r['esocial_tab03'] else 'NULL'

    d_cod  = int(cod)
    d_cli  = str(id_cli(d_cod))
    d_tp   = '1' if sin == '+' else '2'
    d_cp   = inc[0] if len(inc) > 0 else 'N'
    d_fg   = inc[1] if len(inc) > 1 else 'N'
    d_ir   = inc[2] if len(inc) > 2 else 'N'
    d_pi   = inc[3] if len(inc) > 3 else 'N'
    d_rsc  = conv_flag(resc)
    d_fer  = conv_flag(fer)
    d_13   = conv_flag(t13)
    d_13a  = conv_flag(t13a)

    sql = ("INSERT INTO tab_rubrica "
           "(id_cliente,situacao,cod_rubr,ini_valid,dsc_rubr,dsc_rubr_resumido,"
           "tp_rubr,unid_verba,es03_nat_rubr,"
           "tpn_inc_cp,tpn_inc_fgts,tpn_inc_irrf,tpn_inc_pis,"
           "tpr_inc_cp,tpr_inc_fgts,tpr_inc_irrf,tpr_inc_pis,"
           "tpf_inc_cp,tpf_inc_fgts,tpf_inc_irrf,tpf_inc_pis,"
           "tp1_inc_cp,tp1_inc_fgts,tp1_inc_irrf,tp1_inc_pis,"
           "inc_rescisao,inc_ferias,inc_13sal,inc_adto13) VALUES "
           "(%s,'A',%d,%d,'%s','%s',"
           "'%s','%s',%s,"
           "'%s','%s','%s','%s',"
           "'%s','%s','%s','%s',"
           "'%s','%s','%s','%s',"
           "'%s','%s','%s','%s',"
           "'%s','%s','%s','%s');"
           % (d_cli, d_cod, INI_VALID, nom, res,
              d_tp, uni, esoc,
              d_cp, d_fg, d_ir, d_pi,
              d_cp, d_fg, d_ir, d_pi,
              d_cp, d_fg, d_ir, d_pi,
              d_cp, d_fg, d_ir, d_pi,
              d_rsc, d_fer, d_13, d_13a))
    out.append(sql)

# ------------------------------------------------------------------ Excluidas
out.append('')
out.append(SEP)
out.append('  VERBAS EXCLUIDAS (nao serao importadas)')
out.append(SEP)
inativas_list = [r for r in rows if s(r['situacao']) == 'D' and (r['empresa'] or 0) == 0]
empresa_list  = [r for r in rows if (r['empresa'] or 0) > 0]
out.append('')
out.append('  Inativas (situacao=D): %d' % len(inativas_list))
for r in inativas_list:
    out.append('    %4s  %-40s  sinal=%s  unid=%s  esoc=%s' % (
        s(r['codigo']), s(r['nomec']), s(r['sinal']), s(r['unidade']), r['esocial_tab03']))
out.append('')
out.append('  Empresa especifica (empresa>0): %d' % len(empresa_list))
for r in empresa_list:
    out.append('    %4s  %-40s  empresa=%s  sit=%s' % (
        s(r['codigo']), s(r['nomec']), r['empresa'], s(r['situacao'])))

# ------------------------------------------------------------------ Resumo
out.append('')
out.append(SEP)
out.append('RESUMO FINAL:')
out.append('  Total lido no Access   : %d' % len(rows))
out.append('  Importar (ativas emp=0): %d' % len(importar))
out.append('    com id_cliente = 0   : %d  (cod_rubr < 1000)' % sum(1 for r in importar if int(s(r['codigo'])) < 1000))
out.append('    com id_cliente = cli : %d  (cod_rubr >= 1000)' % sum(1 for r in importar if int(s(r['codigo'])) >= 1000))
out.append('    Proventos (+)        : %d' % sum(1 for r in importar if s(r['sinal'])=='+'))
out.append('    Descontos (-)        : %d' % sum(1 for r in importar if s(r['sinal'])=='-'))
out.append('  Excluidas inativas     : %d' % len(inativas_list))
out.append('  Excluidas empresa>0    : %d' % len(empresa_list))
out.append('  ini_valid aplicado     : %d' % INI_VALID)
out.append(SEP)

texto = '\n'.join(out)
path  = r'C:\folha10-simples\000 - Anotacoes\verbas_para_tab_rubrica.txt'
with open(path, 'w', encoding='utf-8') as f:
    f.write(texto)
print('Salvo em:', path)
print('Linhas  :', len(out))
