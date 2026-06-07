import requests
import json

URL = 'https://yxberbwwchmikvzgbtqh.supabase.co'
KEY = 'sb_publishable_GnMdKsPugq7Ij6tGamjscg_1d6J_Nft'
HEADERS = {
    'apikey': KEY,
    'Authorization': 'Bearer ' + KEY,
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}


def gerar_cpf(seed):
    import random
    random.seed(seed * 7919 + 13)
    while True:
        d = [random.randint(0, 9) for _ in range(9)]
        if len(set(d)) == 1:
            continue
        soma = sum(x * (10 - i) for i, x in enumerate(d))
        r = soma % 11
        d1 = 0 if r < 2 else 11 - r
        d.append(d1)
        soma = sum(x * (11 - i) for i, x in enumerate(d))
        r = soma % 11
        d2 = 0 if r < 2 else 11 - r
        d.append(d2)
        return int(''.join(map(str, d)))


# Colunas:
# nome, nomer, sexo, racacor, estciv, grauinstr, dtnascto, dtadm, vrsalfx, cbofuncao, nomemae,
# banco_numero, banco_agencia, banco_agenciadv, banco_conta, banco_contadv,
# ender_dsclograd, ender_complemento, ender_bairro, ender_cep, ender_codmunic, ender_uf
FUNCIONARIOS = [
    ('ANA PAULA SOUZA LIMA', 'ANA PAULA SOUZA LIMA', 'F', 3, '1', '07', 19900315, 20260102, 180000, '411005', 'MARIA SOUZA LIMA',
     '001', '3721', 'X', '12340', '1', 'Rua da Paz', 'Ap 12', 'Boa Vista', 50060030, 2611606, 'PE'),
    ('CARLOS EDUARDO FERREIRA', 'CARLOS EDUARDO FERREIRA', 'M', 1, '2', '09', 19850620, 20260102, 250000, '252210', 'HELENA FERREIRA',
     '033', '1234', '5', '56789', '2', 'Av Brasil', 'Casa', 'Derby', 52011050, 2611606, 'PE'),
    ('MARIA JOSE SANTOS SILVA', 'MARIA JOSE SANTOS SILVA', 'F', 4, '3', '05', 19751210, 20260203, 141200, '513325', 'JOANA SANTOS SILVA',
     '104', '0852', '3', '98765', '0', 'Rua Nova', '', 'Afogados', 50820110, 2611606, 'PE'),
    ('JOAO PEDRO RODRIGUES COSTA', 'JOAO PEDRO RODRIGUES COSTA', 'M', 1, '2', '09', 19921105, 20260203, 300000, '211205', 'LUCIA RODRIGUES COSTA',
     '237', '4521', '7', '34512', '8', 'Av Caxanga', 'Bl A Ap 201', 'Caxanga', 52050000, 2611606, 'PE'),
    ('FERNANDA CRISTINA ALVES PEREIRA', 'FERNANDA CRISTINA PEREIRA', 'F', 3, '1', '09', 19950820, 20260302, 200000, '421125', 'ROSA ALVES PEREIRA',
     '341', '9876', '4', '11223', '5', 'Rua do Sol', '', 'Agua Fria', 52380330, 2611606, 'PE'),
    ('LUCAS HENRIQUE OLIVEIRA SANTOS', 'LUCAS HENRIQUE OLIVEIRA SANTOS', 'M', 1, '1', '09', 19980714, 20260302, 160000, '422205', 'VERA OLIVEIRA SANTOS',
     '001', '6543', '2', '44556', '9', 'Rua Padre Cassiano', '', 'Varzea', 50741430, 2611606, 'PE'),
    ('PATRICIA GOMES BARBOSA', 'PATRICIA GOMES BARBOSA', 'F', 4, '4', '07', 19801225, 20260401, 175000, '514210', 'MARLENE GOMES BARBOSA',
     '033', '2233', '1', '77889', '3', 'Av Norte', '', 'Encruzilhada', 52031010, 2611606, 'PE'),
    ('RAFAEL AUGUSTO MARTINS LIMA', 'RAFAEL AUGUSTO MARTINS LIMA', 'M', 3, '2', '09', 19940330, 20260402, 350000, '421125', 'CARMEM MARTINS LIMA',
     '104', '3344', '6', '22334', '7', 'Rua Real da Torre', '', 'Madalena', 50610480, 2611606, 'PE'),
    ('SIMONE APARECIDA RIBEIRO', 'SIMONE APARECIDA RIBEIRO', 'F', 4, '2', '07', 19881005, 20260407, 155000, '513415', 'IRENE RIBEIRO SANTOS',
     '237', '5566', '8', '55667', '4', 'Rua das Flores', '', 'Iputinga', 50660670, 2611606, 'PE'),
    ('ANDRE LUIS CARVALHO SILVA', 'ANDRE LUIS CARVALHO SILVA', 'M', 1, '1', '11', 19830225, 20260501, 500000, '211205', 'SONIA CARVALHO SILVA',
     '341', '7788', '3', '88900', '6', 'Av Agamenon Magalhaes', 'Sala 10', 'Espinheiro', 52021170, 2611606, 'PE'),
    ('JULIANA MARIA CAMPOS MELO', 'JULIANA MARIA CAMPOS MELO', 'F', 3, '2', '09', 19970415, 20260502, 220000, '422305', 'TEREZA CAMPOS MELO',
     '001', '9900', '5', '11011', '2', 'Rua Henrique Dias', '', 'Santo Antonio', 50020040, 2611606, 'PE'),
    ('MARCOS ANTONIO ARAUJO COSTA', 'MARCOS ANTONIO ARAUJO COSTA', 'M', 4, '3', '07', 19720830, 20260601, 141200, '514210', 'FRANCISCA ARAUJO COSTA',
     '033', '1122', '7', '33445', '8', 'Rua Sete de Setembro', '', 'Sao Jose', 50070170, 2611606, 'PE'),
    ('ROSANA LIMA FERREIRA', 'ROSANA LIMA FERREIRA', 'F', 1, '2', '09', 19901118, 20260601, 190000, '411005', 'NAIR LIMA FERREIRA',
     '104', '2244', '9', '66778', '1', 'Av Conde da Boa Vista', '', 'Boa Vista', 50060002, 2611606, 'PE'),
    ('THIAGO HENRIQUE NASCIMENTO', 'THIAGO HENRIQUE NASCIMENTO', 'M', 1, '1', '09', 19991230, 20260701, 160000, '412110', 'IVETE NASCIMENTO SILVA',
     '237', '3355', '2', '99001', '5', 'Rua Imperial', '', 'Sao Jose', 50050100, 2611606, 'PE'),
    ('CRISTINA SOUZA PEREIRA ALVES', 'CRISTINA SOUZA PEREIRA ALVES', 'F', 3, '4', '09', 19860506, 20260702, 280000, '421125', 'AURORA SOUZA PEREIRA',
     '341', '4466', '4', '22112', '3', 'Rua do Hospicio', 'Ap 5', 'Boa Vista', 50050060, 2611606, 'PE'),
    ('FABRICIO JOSE MOURA SANTOS', 'FABRICIO JOSE MOURA SANTOS', 'M', 4, '2', '07', 19780915, 20260801, 145000, '721105', 'CONCEICAO MOURA SANTOS',
     '001', '5577', '6', '44332', '9', 'Rua Santa Cruz', '', 'Jardim Sao Paulo', 52050480, 2611606, 'PE'),
    ('KARINA APARECIDA LOPES', 'KARINA APARECIDA LOPES', 'F', 3, '1', '09', 20010220, 20260901, 141200, '422205', 'DALVA APARECIDA LOPES',
     '033', '6688', '8', '66554', '7', 'Av Beberibe', '', 'Beberibe', 52060000, 2611606, 'PE'),
    ('VANDERLEI ANTONIO GOMES', 'VANDERLEI ANTONIO GOMES', 'M', 1, '2', '05', 19650705, 20261001, 170000, '514210', 'BENEDITA ANTONIO GOMES',
     '104', '7799', '1', '88776', '4', 'Rua Joao de Barros', '', 'Boa Vista', 50090090, 2611606, 'PE'),
    ('CLAUDIA FERREIRA DIAS', 'CLAUDIA FERREIRA DIAS', 'F', 4, '2', '09', 19930320, 20261103, 200000, '421125', 'EDNA FERREIRA DIAS',
     '237', '8800', '3', '11098', '2', 'Rua Gervaisio Pires', '', 'Boa Vista', 50060110, 2611606, 'PE'),
]

print('=== FUNCIONARIOS A INSERIR ===')
registros = []
for i, f in enumerate(FUNCIONARIOS):
    mat = i + 2
    mat_es = str(mat).zfill(6)
    cpf = gerar_cpf(mat * 13 + 7)

    (nome, nomer, sexo, racacor, estciv, grauinstr, dtnascto, dtadm, vrsalfx, cbofuncao, nomemae,
     banco_numero, banco_agencia, banco_agenciadv, banco_conta, banco_contadv,
     ender_dsclograd, ender_complemento, ender_bairro, ender_cep, ender_codmunic, ender_uf) = f

    sal_fmt = f'R$ {vrsalfx/100:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    print(f'{mat_es} | {nome[:32]:32s} | CPF {cpf} | dtadm {dtadm} | {sal_fmt}')

    reg = {
        'id_cliente': 4,
        'id_empresa': 3,
        'situacao': 'A',
        'matricula': mat,
        'matricula_es': mat_es,
        'filial': '000133',
        'cpf': cpf,
        'nome': nome,
        'nomer': nomer,
        'codcateg': 101,
        'nomemae': nomemae,
        'vrsalfx': vrsalfx,
        'undsalfixo': 'M',
        'tpcontr': 1,
        'lt_tpinsc': 1,
        'lt_nrinsc': '08777252000133',
        'qtdhrssem': 44,
        'qtdhrsmes': 220,
        'tpjornada': 9,
        'tmpparc': 0,
        'hornoturno': 'N',
        'id_tab_horario': 1,
        'sexo': sexo,
        'racacor': racacor,
        'estciv': estciv,
        'grauinstr': grauinstr,
        'dtnascto': dtnascto,
        'paisnascto': 'Bra',
        'paisnac': 'Bra',
        'dtadm': dtadm,
        'tpadmissao': 1,
        'indadmissao': 1,
        'tpregjor': 1,
        'natatividade': 1,
        'cnpjsindcategprof': '08777252000133',
        'cbofuncao': cbofuncao,
        'banco_numero': banco_numero,
        'banco_agencia': banco_agencia,
        'banco_agenciadv': banco_agenciadv,
        'banco_conta': banco_conta,
        'banco_contadv': banco_contadv,
        'ender_dsclograd': ender_dsclograd,
        'ender_complemento': ender_complemento if ender_complemento else None,
        'ender_bairro': ender_bairro,
        'ender_cep': ender_cep,
        'ender_codmunic': ender_codmunic,
        'ender_uf': ender_uf,
        'ind_imigrante': 'N',
        'deffisica': 'N',
        'defvisual': 'N',
        'defauditiva': 'N',
        'defmental': 'N',
        'defintelectual': 'N',
        'reabreadap': 'N',
        'indaprend': 0,
    }
    registros.append(reg)

print(f'\nTotal preparados: {len(registros)}')
print('\nInserindo no Supabase...')

r = requests.post(
    f'{URL}/rest/v1/tab_cad',
    headers=HEADERS,
    json=registros
)

print(f'Status: {r.status_code}')
if r.status_code in (200, 201, 204):
    print('Inseridos com sucesso!')
else:
    print('Erro:', r.text)
