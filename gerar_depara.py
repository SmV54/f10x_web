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
    if v.startswith('NAO') or v.startswith('NÃO') or v == '':
        return 'N'
    if v in ('CAL', '12U', 'PAQ'):
        return 'S'
    return v[:3]

SEP  = '=' * 150
SEP2 = '-' * 150

out = []
out.append(SEP)
out.append('  QUADRO DE-PARA: tabverba (Access FolhaFIX) --> tab_rubrica (Folha10 Simples)')
out.append('  Gerado em: ' + datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))
out.append('  Total de verbas: ' + str(len(rows)))
out.append(SEP)
out.append('')

# ------------------------------------------------------------------ Legenda
out.append('MAPEAMENTO DE CAMPOS')
out.append(SEP2)
mapa = [
    ('codigo',        'cod_rubr',           'Direto -- codigo inteiro (4 digitos)'),
    ('nomec',         'dsc_rubr',           'Direto -- nome completo (max 40 chars)'),
    ('nomer',         'dsc_rubr_resumido',  'Direto -- nome resumido (max 20 chars)'),
    ('sinal',         'tp_rubr',            '+ --> 1 (Provento)  |  - --> 2 (Desconto)'),
    ('unidade',       'unid_verba',         'V-->V  H-->H  D-->D  E=especial (avaliar caso a caso)'),
    ('situacao',      'situacao',           'A-->A (Ativo)  D-->I (Inativo)'),
    ('esocial_tab03', 'es03_nat_rubr',      'Direto -- natureza eSocial tabela 03'),
    ('incidencia[1]', 'tpn_inc_cp',         'Posicao 1: S-->S (incide INSS normal)  N-->N'),
    ('incidencia[2]', 'tpn_inc_fgts',       'Posicao 2: S-->S (incide FGTS normal)  N-->N'),
    ('incidencia[3]', 'tpn_inc_irrf',       'Posicao 3: S-->S (incide IRRF normal)  N-->N'),
    ('incidencia[4]', 'tpn_inc_pis',        'Posicao 4: S-->S (incide PIS normal)   N-->N'),
    ('incidencia[5]', '---',                'Posicao 5 = DSR/outros (sem campo direto -- avaliar)'),
    ('rescisao',      'inc_rescisao',       'NAO-->N  |  CAL/12U-->S'),
    ('ferias',        'inc_ferias',         'NAO-->N  |  CAL/12U/PAQ-->S'),
    ('13sal',         'inc_13sal',          'NAO-->N  |  CAL/12U-->S'),
    ('13sala',        'inc_adto13',         'NAO-->N  |  12U-->S  (adiantamento 13o)'),
    ('codigoantigo',  '---',               'Referencia historica -- nao gravar'),
    ('empresa',       '---',               '0=sistema geral; 1+ = empresa especifica'),
    ('percentual',    '---',               'Percentual base -- sem campo direto'),
    ('formula',       '---',               'Formula de calculo -- sem campo direto'),
    ('receita',       '---',               'Flags de receita -- sem campo direto'),
    ('verbasbase',    '---',               'Verbas base do calculo -- sem campo direto'),
    ('familia',       '---',               'Grupo/familia de verba -- sem campo direto'),
    ('indicadort',    '---',               'Flags estendidas -- sem campo direto'),
    ('alteracao',     '---',               'Flag interna -- ignorar'),
]
for ac, tb, regra in mapa:
    out.append('  %-20s  -->  %-22s  %s' % (ac, tb, regra))

out.append('')
out.append('LEGENDA incidencia (5 posicoes): Pos1=INSS  Pos2=FGTS  Pos3=IRRF  Pos4=PIS  Pos5=DSR')
out.append('  S=Incide   N=Nao incide')
out.append('')
out.append('CAMPOS SEM EQUIVALENTE DIRETO (necessitam avaliacao):')
out.append('  formula, receita, verbasbase, familia, indicadort, percentual')
out.append('')
out.append('CAMPO OBRIGATORIO EM tab_rubrica SEM ORIGEM NO ACCESS:')
out.append('  ini_valid -- definir data padrao (ex: 202501) na importacao')
out.append('  id_cliente -- usar id do cliente importador')
out.append('')

# ------------------------------------------------------------------ Tabela
out.append(SEP)
out.append('LISTA DETALHADA DE VERBAS (ACCESS --> tab_rubrica)')
out.append(SEP)
out.append('')

# Cabecalho da tabela
cab1 = '%-4s  %-40s  %-20s  %-2s  %-2s  %-3s  %-5s  %-4s  %-4s  %-4s  %-3s  %-3s  %-3s  %-3s  %-3s  %-8s  |  %-4s  %-6s  %-4s  %-3s  %-3s  %-4s  %-4s  %-4s  %-3s  %-3s  %-3s  %-8s'
cab2 = ('COD', 'NOME COMPLETO (nomec)', 'RESUMIDO (nomer)', 'SI', 'UN', 'SIT',
        'INC', 'RSC', 'FER', '13S', '13A', 'DSR', 'RSC', 'FER', '13S',
        'eSocial',
        'COD', 'tp_rubr', 'unid', 'sit',
        'cp', 'fgts', 'irrf', 'pis',
        'iRs', 'iFe', 'i13', 'es03')
out.append('  [ ORIGEM -- ACCESS tabverba ]' + ' ' * 80 + '[ DESTINO -- tab_rubrica ]')
out.append(cab1 % cab2)
out.append(SEP2)

for r in rows:
    cod  = s(r['codigo'])
    nom  = s(r['nomec'])[:40]
    res  = s(r['nomer'])[:20]
    sin  = s(r['sinal'])
    uni  = s(r['unidade'])
    sit  = s(r['situacao'])
    inc  = s(r['incidencia'])
    resc = s(r['rescisao'])
    fer  = s(r['ferias'])
    t13  = s(r['13sal'])
    t13a = s(r['13sala'])
    esoc = str(r['esocial_tab03']) if r['esocial_tab03'] else ''
    emp  = str(r['empresa'] or '0')

    # destinos
    d_cod = cod.zfill(4)
    d_tp  = '1' if sin == '+' else ('2' if sin == '-' else '?')
    d_un  = uni if uni in ('V', 'H', 'D') else (uni + '?')
    d_sit = 'A' if sit == 'A' else 'I'
    d_cp  = inc[0] if len(inc) > 0 else '?'
    d_fg  = inc[1] if len(inc) > 1 else '?'
    d_ir  = inc[2] if len(inc) > 2 else '?'
    d_pi  = inc[3] if len(inc) > 3 else '?'
    d_dsr = inc[4] if len(inc) > 4 else '?'
    d_rsc = conv_flag(resc)
    d_fer = conv_flag(fer)
    d_13  = conv_flag(t13)
    d_13a = conv_flag(t13a)

    # flag empresa
    flag_emp = (' [emp=%s]' % emp) if emp != '0' else ''

    linha = ('%-4s  %-40s  %-20s  %-2s  %-2s  %-3s  %-5s  %-3s  %-3s  %-3s  %-3s  %-3s  %-3s  %-3s  %-3s  %-8s%s  |  %-4s  %-6s  %-4s  %-3s  %-3s  %-4s  %-4s  %-4s  %-3s  %-3s  %-3s  %-8s'
             % (cod, nom, res, sin, uni, sit,
                inc[:5], resc[:3], fer[:3], t13[:3], t13a[:3], d_dsr, d_rsc, d_fer, d_13,
                esoc, flag_emp,
                d_cod, d_tp, d_un, d_sit,
                d_cp, d_fg, d_ir, d_pi,
                d_rsc, d_fer, d_13,
                esoc))
    out.append(linha)

out.append('')

# ------------------------------------------------------------------ Alertas
out.append(SEP)
out.append('ALERTAS E PONTOS A REVISAR ANTES DA IMPORTACAO')
out.append(SEP)

uni_e = [r for r in rows if s(r['unidade']) == 'E']
inativas = [r for r in rows if s(r['situacao']) == 'D']
emp_esp  = [r for r in rows if (r['empresa'] or 0) > 0]

out.append('')
out.append('1. VERBAS COM UNIDADE=E (Especial) -- sem equivalente direto (%d registros):' % len(uni_e))
for r in uni_e:
    out.append('     %4s  %-40s  sit=%s  esoc=%s' % (s(r['codigo']), s(r['nomec']), s(r['situacao']), r['esocial_tab03']))

out.append('')
out.append('2. VERBAS INATIVAS (situacao=D) -- decidir se importa (%d registros):' % len(inativas))
for r in inativas:
    out.append('     %4s  %-40s  sinal=%s  unid=%s  esoc=%s' % (
        s(r['codigo']), s(r['nomec']), s(r['sinal']), s(r['unidade']), r['esocial_tab03']))

out.append('')
out.append('3. VERBAS DE EMPRESA ESPECIFICA (empresa>0) -- avaliar id_cliente (%d registros):' % len(emp_esp))
for r in emp_esp:
    out.append('     %4s  %-40s  empresa=%s' % (s(r['codigo']), s(r['nomec']), r['empresa']))

out.append('')
out.append('4. INCIDENCIA POSICAO 5 (DSR) -- sem campo direto em tab_rubrica:')
dsr_s = [r for r in rows if len(s(r['incidencia'])) >= 5 and s(r['incidencia'])[4] == 'S']
out.append('   Verbas com DSR=S (%d registros):' % len(dsr_s))
for r in dsr_s:
    out.append('     %4s  %-40s  inc=%s' % (s(r['codigo']), s(r['nomec']), s(r['incidencia'])))

out.append('')
out.append('5. VERBAS COM INCIDENCIA EM RESCISAO/FERIAS/13SAL -- checar campos tpr_*/tpf_*/tp1_*:')
out.append('   tab_rubrica tem campos separados por periodo (normal/rescisao/ferias/13sal).')
out.append('   A importacao inicial ira usar os mesmos valores de incidencia para todos os periodos.')
out.append('   Revisar verbas onde rescisao/ferias/13sal diferem da folha normal.')

out.append('')
out.append('6. CAMPOS NAO MIGRADOS (informacao de referencia):')
out.append('   formula    = logica de calculo (implementar manualmente por verba)')
out.append('   receita    = flags de receita federal')
out.append('   verbasbase = verbas que compoem a base de calculo')
out.append('   indicadort = indicadores de tributacao estendidos')
out.append('   percentual = percentual base de calculo')

out.append('')
out.append(SEP)
ativas = sum(1 for r in rows if s(r['situacao']) == 'A')
out.append('RESUMO FINAL:')
out.append('  Total de verbas lidas : %d' % len(rows))
out.append('  Ativas (sit=A)        : %d' % ativas)
out.append('  Inativas (sit=D)      : %d' % len(inativas))
out.append('  Unidade V (Valor)     : %d' % sum(1 for r in rows if s(r['unidade'])=='V'))
out.append('  Unidade H (Hora)      : %d' % sum(1 for r in rows if s(r['unidade'])=='H'))
out.append('  Unidade D (Diaria)    : %d' % sum(1 for r in rows if s(r['unidade'])=='D'))
out.append('  Unidade E (Especial)  : %d' % len(uni_e))
out.append('  Proventos (+)         : %d' % sum(1 for r in rows if s(r['sinal'])=='+'))
out.append('  Descontos (-)         : %d' % sum(1 for r in rows if s(r['sinal'])=='-'))
out.append('  Empresa especifica    : %d' % len(emp_esp))
out.append(SEP)

texto = '\n'.join(out)
path  = r'C:\folha10-simples\000 - Anotacoes\depara_tabverba.txt'
with open(path, 'w', encoding='utf-8') as f:
    f.write(texto)
print('Salvo em:', path)
print('Total de linhas:', len(out))
