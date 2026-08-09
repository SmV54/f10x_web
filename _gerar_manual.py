# -*- coding: utf-8 -*-
"""Gera o Manual de Regras do Folha10 Simples em Word.

Uma ETAPA por card do menu principal, na mesma ordem em que os cards aparecem
na tela (const ordem, em templates/F10_Menu.html):
    cadastros, novafolha, eventuais, movimento, movimentofixo, calculo,
    relatorios, conexoes, esocial, diversos, interno_f10

Conteudo: REGRAS_DO_SISTEMA.txt reorganizado por modulo + regras confirmadas
no codigo. Nada aqui e suposicao: o que nao esta documentado aparece como
lacuna declarada, nao inventado.
"""
import os
from _manual_base import *   # noqa: F401,F403

DESTINO = "C:/folha10-simples/manual"
ARQUIVO = os.path.join(DESTINO, "Manual_de_Regras_Folha10_Simples.docx")
VERSAO_SISTEMA = open("C:/folha10-simples/versaoxxx.txt", encoding="utf-8").read().strip()

iniciar("Folha10 Simples — Manual de Regras do Sistema", f"versão {VERSAO_SISTEMA}")


# ================================================================== CAPA
capa("FOLHA10 SIMPLES",
     "Manual de Regras do Sistema",
     "Organizado etapa por etapa, na ordem dos botões do menu principal")

p("Este manual reúne as regras que já estão definidas e valendo no sistema — "
  "não é um projeto do que se pretende fazer. Cada etapa corresponde a um card "
  "do menu principal, na mesma ordem em que eles aparecem na tela, e dentro da "
  "etapa as regras seguem os grupos e itens daquele card.")

p("Onde uma regra ainda não está fechada, ela aparece marcada como lacuna em "
  "aberto. Preferimos declarar o que falta a preencher com suposição.")

p()
tabela(
    ["", ""],
    [["Versão do sistema", VERSAO_SISTEMA],
     ["Emitido em", "09/08/2026"],
     ["Base", "REGRAS_DO_SISTEMA.txt + comportamento verificado no código e no banco"],
     ["Alcance", "11 etapas — os 10 cards do menu mais o card Administrador"]],
    larguras=[4.5, 11.5],
)

p()
h2("As etapas deste manual")
for n, nome in enumerate([
    "Conceitos que valem para o sistema inteiro (antes de qualquer etapa)",
    "Cadastros", "Nova Folha", "Eventuais", "Movimento Mês", "Movimento Fixo",
    "Cálculo", "Relatórios", "Conexões", "eSocial", "Diversos", "Administrador",
]):
    rot = "Etapa 0" if n == 0 else f"Etapa {n}"
    par = documento().add_paragraph()
    par.paragraph_format.space_after = Pt(2)
    par.add_run(f"{rot}  ").bold = True
    par.add_run(nome)

par = documento().add_paragraph()
par.paragraph_format.space_before = Pt(10)
par.add_run("Anexos  ").bold = True
par.add_run("A) Armadilhas de banco e de dados   B) Padrões de tela   "
            "C) Regras específicas de cliente")


# ============================================================== ETAPA 0
h1("Etapa 0 — Conceitos que valem para o sistema inteiro")
p("Estas regras não pertencem a um card do menu: elas atravessam todos. "
  "Quase todo comportamento estranho relatado no dia a dia cai em uma delas.")

h2("Valores são sempre em centavos")
regra("Formato", "R$ 1.500,00 é gravado como 150000, em número inteiro. Vale para "
      "salário (vrsalfx), verbas, totais e tabelas legais.")
regra("Percentuais", "guardados em centésimos: 750 significa 7,50%.")
atencao("Na migração vinda do Access o valor JÁ chega em centavos. Multiplicar por 100 "
        "nessa importação multiplica o salário por cem.")

h2("Folha ativa (competência)")
regra("O que é", "o mês/ano ativo da sessão. Quase toda tela depende dele: é a competência "
      "em que o lançamento vai cair.")
regra("Só anda para a frente", "não é possível abrir competência anterior à mais recente "
      "da empresa.")
regra("Primeira folha", "ao cadastrar a empresa, a primeira folha já é aberta "
      "automaticamente, junto com o centro de custo 001.")
regra("Até o dia 5", "a competência sugerida é o MÊS ANTERIOR — quem se cadastra no começo "
      "do mês normalmente vem processar o mês que passou.")

h2("Situação e tipo da folha")
tabela(["Situação", "Significado", "Efeito"],
       [["A ou X", "Aberta", "Permite incluir e alterar"],
        ["C", "Calculada", "Bloqueia inclusão e alteração na maioria das telas"],
        ["F", "Fechada", "Bloqueia inclusão e alteração na maioria das telas"]],
       larguras=[2.6, 4.0, 9.4])
tabela(["Tipo", "Folha"],
       [["N", "Normal"], ["F", "Férias"], ["R", "Rescisão"],
        ["A", "Adiantamento do 13º"], ["1", "13º final"]],
       larguras=[2.6, 13.4])

h2("Regra de nomes no banco")
regra("Tudo minúsculo", "o Postgres rebaixa nomes não aspeados. CamelCase no código Python "
      "vira erro 42703 (coluna não existe) — e como quase sempre está dentro de "
      "except: pass, a falha é calada. Exemplos: tab_CAD é tab_cad; codCateg é codcateg.")


# ============================================================== ETAPA 1
h1("Etapa 1 — Cadastros")
caminho("Menu principal › Cadastros")
p("O card reúne cinco grupos: Funcionário, Tabelas Auxiliares, Pensão Alimentícia e Empresa. "
  "Com a folha calculada ou fechada, os cadastros ficam bloqueados — só Nova Empresa "
  "continua liberado.")

h2("Grupo Funcionário")
caminho("Incluir Funcionário · Alterar Funcionário · Dependentes · Ficha de Registro · Limpar Funcionário")

h3("Data de admissão contra a folha ativa")
tabela(["Data de admissão", "O que o sistema faz"],
       [["Posterior à folha ativa", "RECUSA. Não grava."],
        ["No mês da folha ativa", "Grava normal, com S-2200 ou S-2300."],
        ["Anterior à folha ativa", "Pede confirmação na tela e NÃO gera o S-2200."]],
       larguras=[5.0, 11.0])
p("A admissão retroativa é quase sempre implantação: o evento já foi transmitido pelo "
  "sistema anterior, e um S-2200 duplicado dá trabalho para desfazer no eSocial. Se o "
  "evento realmente precisar ir, o caminho é o Gerador de Remessa.")
atencao("As duas travas valem NO SERVIDOR, não apenas na tela.")

h3("Matrícula")
regra("Formato", "6 dígitos.")
item("Estagiário (categoria 901) recebe prefixo 8.")
item("Pró-labore (categorias 721, 722 e 723) recebe prefixo 9.")

h3("Matrícula eSocial (tab_cad.matricula_es)")
p("É a matrícula pela qual o eSocial já conhece o trabalhador — usada quando ele veio de "
  "outro sistema. Nas inclusões normais vem igual à matrícula.")
item("PODE ficar em branco nas categorias 721, 722 e 723: esses contribuintes costumam ter "
     "sido cadastrados no eSocial sem matrícula nenhuma. Nessas categorias o sistema não "
     "copia mais a matrícula automaticamente.")
item("Em branco, a tag <matricula> não sai no S-1200 nem no S-2300.")
item("Alterar a matrícula eSocial NÃO gera S-2205 nem S-2206. Depois de aceito, só se "
     "corrige retificando o próprio S-2200.")

h3("Categoria — o que ela muda no cálculo")
tabela(["Categoria", "Verba do salário", "INSS", "FGTS"],
       [["101 e demais empregados", "1", "verba 101", "Normal"],
        ["721 — Diretor com FGTS", "6", "verba 102", "SIM — única da faixa 700 que tem"],
        ["722", "16", "verba 102", "Não"],
        ["723", "86", "verba 102", "Não"],
        ["Demais 700 a 799", "16", "verba 102", "Não"],
        ["901 — Estagiário", "7 (bolsa)", "Não tem", "Não"]],
       larguras=[4.6, 3.6, 3.0, 4.8])
p("O estagiário (901) sofre apenas IRRF: sem INSS e sem FGTS.")
regra("Evento gerado", "categoria 700 ou maior gera S-2300 (TSVE) em vez de S-2200.")

h3("Nome do cargo (nmcargo)")
p("Em branco, vale o nome da função pelo CBO. Preenchido, tem precedência. Serve para o "
  "caso de duas funções diferentes compartilharem o mesmo CBO. É lido pelo TRCT e pelos "
  "eventos S-2200, S-2300 e S-2206.")

h3("Sindicato")
p("O vínculo é por CNPJ (tab_cad.cnpjsindcategprof), não por id. "
  "NÃO SINDICALIZADO corresponde ao CNPJ 37115367003500.")

h2("Grupo Tabelas Auxiliares")
caminho("Funções/Cargos · Horários · Sindicatos · Vale Transporte · Rubricas · Feriados · "
        "Centros de Custo · Filiais · Usuários da Conta")

h3("Rubricas (verbas) — faixas de código")
tabela(["Faixa", "Dono", "Regra"],
       [["1 a 999", "Sistema (id_cliente = 0)", "Iguais para todos os clientes. Só a equipe F10 altera."],
        ["1000 a 9899", "Cliente", "O sistema sugere o próximo código livre."],
        ["9900 a 9999", "Informativas", "Aparecem no holerite e vão ao eSocial, mas NÃO entram no total de proventos, descontos nem no líquido."]],
       larguras=[2.8, 4.0, 9.2])

h3("Tipo e unidade da rubrica")
tabela(["Tipo", "Descrição"],
       [["1", "Provento"], ["2", "Desconto"], ["3", "Informativa"],
        ["4", "Informativa dedutora"]], larguras=[2.0, 14.0])
tabela(["Unidade", "Como o cálculo trata"],
       [["V", "Valor em reais."],
        ["H", "Hora — multiplica a quantidade pelo salário-hora no momento do cálculo."],
        ["D", "Diária — multiplica a quantidade pelo salário-dia no momento do cálculo."]],
       larguras=[2.4, 13.6])
p("Como a conversão acontece no cálculo, e não na digitação, o valor acompanha o reajuste "
  "sozinho. O “% de acréscimo” soma sobre isso: 50 é hora extra de 50% (×1,5) e 100 é o dobro.")

h3("Incidências não são S/N")
p("Os campos tpn_ / tpr_ / tpf_ / tp1_ combinados com _inc_cp, _inc_fgts, _inc_irrf e "
  "_inc_pis guardam o CÓDIGO DE INCIDÊNCIA DO eSOCIAL — por exemplo, 11 significa incide "
  "integralmente. Os prefixos indicam o evento:")
tabela(["Prefixo", "Evento"],
       [["tpn_", "Folha normal"], ["tpr_", "Rescisão"],
        ["tpf_", "Férias"], ["tp1_", "13º salário"]], larguras=[2.4, 13.6])
atencao("É esse código que vai no S-1010. Errar aqui vira rejeição no envio ao eSocial.")

h3("Incidência por evento — como a verba vira média")
tabela(["Código", "Significado"],
       [["NI", "Não incide"],
        ["M12", "Média dos últimos 12 meses"],
        ["MAP", "Média do período aquisitivo (férias)"],
        ["MAN", "Média desde o início do ano (13º)"],
        ["UL", "Repete o último lançamento"],
        ["CN", "Cálculo normal, sem média"]], larguras=[2.4, 13.6])
p("É o que faz a hora extra habitual refletir em férias e rescisão. Esquecer disso é a "
  "causa mais comum do relato “a média não bateu”.")

h3("Flags de Outras Informações que o cálculo usa")
tabela(["Flag", "Efeito"],
       [["01", "Não permite digitar no movimento — some das telas de lançamento."],
        ["04", "Comissão — gera DSR na verba 0027."],
        ["11", "Adicional noturno — gera DSR na verba 0026."],
        ["19", "Hora extra — gera DSR na verba 0025."],
        ["06 e 07", "Insalubridade e periculosidade — impedem pagamento em dobro (cadastro mais movimento fixo)."]],
       larguras=[2.0, 14.0])

h3("Verbas que compõem a base")
p("Para verba que é percentual de outras: escolhendo as verbas da base, o cálculo soma "
  "esses valores antes de aplicar o percentual, em vez de usar só o salário.")

h2("Grupo Pensão Alimentícia")
caminho("Cadastro da Pensionista · Fórmulas · Recibo da Pensão")
regra("Onde grava", "tab_pensao — um responsável e até 9 beneficiários por registro.")
regra("Valor", "em centavos; percentual multiplicado por 100. A vigência começa na folha ativa "
      "(anomes_inicial).")
regra("Fórmulas", "ficam em tab_tabela_cli com num_tabela = 7.")
p("A tela trabalha com duas listas — responsável e beneficiários — e não tem edição: "
  "correção é refazer o registro.")

h2("Grupo Empresa")
caminho("Nova Empresa · Alterar Esta Empresa")
regra("Liberado com folha bloqueada", "Nova Empresa é o único item de Cadastros que continua "
      "acessível com a folha calculada ou fechada.")
regra("Primeiros passos do cliente novo", "a ordem é empresa, funções, centro de custo e "
      "funcionários. O centro de custo 001 e a folha do mês são criados automaticamente, e o "
      "painel de primeiros passos desaparece assim que existe o primeiro funcionário.")
atencao("O centro de custo é o codLotacao do eSocial. Funcionário sem centro de custo faz o "
        "S-1200 e o S-2299 saírem sem <codLotacao>, e o eSocial recusa.")


# ============================================================== ETAPA 2
h1("Etapa 2 — Nova Folha")
caminho("Menu principal › Nova Folha")
p("O card abre a competência de trabalho e controla a passagem entre aberta, calculada e "
  "fechada.")

h2("Abrir a competência")
caminho("Novo Mês/Ano · Outro Mês/Ano")
regra("Sugestão do próximo mês", "sai sempre da última folha NORMAL. As folhas de 13º "
      "(tipo A de adiantamento e tipo 1 de final) são ignoradas na sequência, porque são "
      "abertas em novembro e dezembro e não fazem parte do calendário mensal.")
regra("Sentido único", "a folha só anda para a frente. Competência anterior à mais recente "
      "da empresa não abre.")

h2("Reabrir e fechar")
caminho("Reabrir esta Folha Calculada · Fechar esta Folha Calculada · Reabrir esta Folha Fechada")
p("Fechar consolida a competência; reabrir devolve a folha ao estado editável. O status da "
  "folha comanda o que o eSocial aceita receber — ver a Etapa 9.")
atencao("Fechar a folha no Folha10 é diferente de fechar o período no eSocial (S-1299). "
        "São dois fechamentos independentes.")


# ============================================================== ETAPA 3
h1("Etapa 3 — Eventuais")
caminho("Menu principal › Eventuais")
p("O card maior do sistema: Férias, Salários, Rescisão, Contrato Temporário, Afastamentos, "
  "Faltas, Exame Médico, Insalubridade/Periculosidade e FAP.")

h2("Grupo Férias")
caminho("Lançar Férias · Movimento Férias · Calcular · Memória · Recibo · Cancelar · "
        "Funcionários em Férias · Programação · Férias Vencidas")

h3("Direito (CLT)")
p("Período aquisitivo de 12 meses. Os dias de direito dependem das faltas:")
tabela(["Faltas no período", "Dias de férias"],
       [["0 a 5", "30 dias"], ["6 a 14", "24 dias"], ["15 a 23", "18 dias"],
        ["24 a 32", "12 dias"], ["mais de 32", "nenhum"]], larguras=[5.0, 11.0])
item("Período concessivo: 12 meses após o aquisitivo. Fora do prazo, as férias são pagas em dobro.")
item("Fracionamento em até 3 períodos: um de no mínimo 14 dias e os demais de no mínimo 5.")
item("Abono pecuniário: venda de até 1/3 dos dias.")

h3("Sequência do cálculo")
tabela(["Passo", "O que faz"],
       [["1", "Salário de férias = salário ÷ 30 × dias"],
        ["2", "1/3 constitucional = salário de férias ÷ 3"],
        ["3", "Médias das verbas variáveis do período aquisitivo"],
        ["4", "Base de INSS, IRRF e FGTS = férias + 1/3 + médias"],
        ["5", "O abono e o 1/3 sobre o abono são ISENTOS de INSS e IRRF"]],
       larguras=[1.8, 14.2])
atencao("Evento op1 = 3 com data1i = 99999999 é período aquisitivo SEM gozo marcado. "
        "Não é férias e tem que ficar fora das listagens.")

h2("Grupo Salários")
caminho("Alteração de Salário · Cancelar Alteração · Relatório de Salários")
p("A alteração salarial fica registrada em tab_eventos e alimenta o relatório de salários "
  "e a alteração contratual no eSocial (S-2206).")

h2("Grupo Rescisão")
caminho("Aviso Prévio · Registrar Rescisão · Movimento do Mês · Calcular · TRCT · "
        "Memória · Listagem dos Demitidos · Cancelar Aviso · Cancelar Rescisão")

h3("O que o cálculo pressupõe")
p("A rescisão já precisa estar REGISTRADA (situação D, com data e motivo). O cálculo lê "
  "esse registro e não mexe no cadastro do funcionário.")

h3("As verbas da rescisão")
tabela(["Verba", "Descrição", "Verba", "Descrição"],
       [["10", "Saldo de salário", "44", "Férias do aviso prévio"],
        ["12", "13º proporcional", "49", "Férias proporcionais"],
        ["13", "13º indenizado", "61", "Aviso prévio indenizado"],
        ["41", "Férias", "101", "INSS"],
        ["42", "1/3 de férias — verba própria, sobre 43 + 44 + 49", "104", "INSS do 13º"],
        ["43", "Férias vencidas", "120", "IRRF"],
        ["", "", "122", "IRRF do 13º"]],
       larguras=[1.6, 6.6, 1.6, 6.2])
atencao("A verba 17 é ADIANTAMENTO DO 13º SALÁRIO. Não é verba de férias.")

h3("Médias — cada uma tem a sua janela")
tabela(["Sobre o quê", "Janela da média"],
       [["Férias vencidas", "O próprio período aquisitivo"],
        ["Férias proporcionais", "12 meses até o mês da rescisão"],
        ["13º salário", "De janeiro do ano até o mês da rescisão"]],
       larguras=[5.0, 11.0])
p("As médias são REFLEXO: entram no 13º e nas férias e não viram linha própria no recibo.")

h3("Cancelar rescisão")
p("Reverte o cadastro, apaga o S-2299 pendente e cancela também o aviso prévio que a "
  "originou. Só é permitido quando as três condições valem ao mesmo tempo:")
item("a folha atual está aberta;")
item("o mês da rescisão é o mês da folha ativa;")
item("o S-1299 do período não está ativo — ou nunca foi enviado, ou foi excluído por S-3000.")

h3("TRCT")
p("Réplica do formulário oficial (Portaria 1057/2012). Lê o que foi PERSISTIDO no cálculo, "
  "então é obrigatório calcular a rescisão antes de emitir.")

h2("Grupo Contrato Temporário")
caminho("Contrato / Prorrogação · Relação dos Contratos · Imprimir Contrato de Experiência")
regra("Contrato de experiência", "o PDF é oferecido logo depois de concluir o cadastro do "
      "funcionário e também fica no card do menu. O modelo não traz os itens Local de "
      "Trabalho e Dano.")

h2("Grupo Afastamentos")
caminho("Lançar Afastamento · CAT (informar, alterar, ficha) · Funcionários Afastados · "
        "Licença Maternidade/Paternidade")

h3("As datas")
tabela(["Data", "Comportamento"],
       [["Início posterior à folha ativa", "ERRO. Não grava."],
        ["Início anterior à folha ativa", "Grava com confirmação."],
        ["Fim em branco", "Afastamento EM ABERTO — é o caso mais comum ao registrar."],
        ["Fim posterior a hoje", "Permitido com confirmação, mas não recomendado: se o afastamento se prolongar, vira correção no eSocial."]],
       larguras=[5.4, 10.6])

h3("Duas remessas, cada uma na sua competência")
p("Informando início e fim, saem dois S-2230: a SAÍDA na competência do mês de início e o "
  "RETORNO na competência do mês do fim. Um afastamento de 20/07 a 05/08 gera saída em "
  "07/2026 e retorno em 08/2026.")
atencao("A Fila do eSocial mostra uma competência por vez. Remessa de mês anterior não "
        "aparece na fila da folha ativa — é preciso trocar o período. A mensagem de "
        "confirmação diz qual é a competência de cada uma.")

h3("Data retroativa: enviar ou não")
p("Aparecem duas caixas “Não enviar o S-2230”, uma para a saída e outra para o retorno, "
  "JÁ MARCADAS. O padrão é não gerar: afastamento antigo normalmente já foi transmitido, ou "
  "está sendo registrado só para a folha enxergar os dias parados. As duas escolhas são "
  "independentes uma da outra.")

h3("Motivos (Tabela 18 do eSocial)")
item("01 e 03 (acidente ou doença) pedem “mesmo motivo” e acidente de trânsito, e oferecem "
     "registrar a CAT (S-2210) depois de gravar.")
item("21 (licença não remunerada) exige observação.")
p("“Mesmo motivo” importa para o INSS: afastamentos pela mesma causa em menos de 60 dias se "
  "somam, e isso muda de quem é a responsabilidade pelo pagamento.")

h2("Grupos Faltas, Exame Médico, Insalubridade e FAP")
caminho("Incluir/Excluir/Listar Faltas · Exame Médico · Insalubridade/Periculosidade · FAP")
regra("Insalubridade", "percentual sobre o SALÁRIO MÍNIMO. Fonte: tab_eventos op1 = 31.")
regra("Periculosidade", "percentual sobre o SALÁRIO BASE. Fonte: tab_eventos op1 = 41.")
atencao("Lacuna em aberto: as verbas 30, 31 e 32 estão com inc_* = CN, valor que o código "
        "não trata. Por isso o adicional não entra em férias, 13º nem rescisão. "
        "Pendente de decisão.")


# ============================================================== ETAPA 4
h1("Etapa 4 — Movimento Mês")
caminho("Menu principal › Movimento Mês")
p("Lançamentos da competência: o que varia de um mês para o outro.")

h2("Grupo Lançamentos")
caminho("Lançar Eventos · Importar Consignados · Importar Ponto · Horas Extras · Faltas e Atrasos")
regra("Origem do lançamento", "o que você digita entra no tab_mov com origem M e NUNCA é "
      "sobrescrito pelo recálculo. O que o cálculo gera a partir do movimento fixo entra "
      "com origem F.")
regra("Verba com flag 01", "não aparece nas telas de lançamento — é calculada, não digitada.")

h3("Importar Consignados")
p("As verbas 700 a 749 (empréstimo consignado) não se cadastram como movimento fixo: cada "
  "contrato tem banco, número e prazo próprios, que só chegam pela planilha mensal. A "
  "importação apaga e regrava a faixa inteira a cada rodada.")

h2("Grupo Adiantamento Quinzenal")
caminho("Calcular · Informar · Listagem · Alterar ou Excluir · Recibo")

h3("Três estados, não dois")
tabela(["No cadastro", "Resultado"],
       [["Campo vazio", "Herda o percentual do cadastro da empresa."],
        ["Caixa “Não adianta” marcada", "NÃO adianta nada, e nem herda o percentual da empresa."],
        ["Valor ou percentual preenchido", "Usa o que está preenchido."]],
       larguras=[5.4, 10.6])
p("O “não adianta” é gravado em tab_cad.sem_adiantamento (booleano). Não é possível usar 0 "
  "nem -1 nas colunas de valor: o banco tem CHECK exigindo valor_adianta > 0 e per_adianta "
  "entre 10 e 60. Digitar 0 na tela funciona como atalho para marcar a caixa.")

h3("Admitido no mês da folha")
tabela(["Dia da admissão", "Recebe?"],
       [["Do dia 1 ao 10", "Sim, PROPORCIONAL aos dias trabalhados (dia 1 = integral)."],
        ["Do dia 11 em diante", "Não recebe."]], larguras=[5.0, 11.0])
p("O divisor são os dias reais do mês (30, 31 ou 28) — a mesma regra da etapa 1030 do "
  "cálculo. Exemplo: salário 3.000,00 com 40%, admitido em 05/07 → 1.200,00 × 27/31 = 1.045,16.")
regra("Fica de fora", "quem estiver afastado ou de férias na primeira quinzena (dias 01 a 15).")

h3("As verbas do adiantamento")
tabela(["Verba", "Uso"],
       [["161 a 164", "Até 4 parcelas na mesma folha. Aparecem em bloco próprio nos relatórios e NÃO entram nos totais."],
        ["160", "Desconto único na folha mensal, somando as verbas 161 a 164."]],
       larguras=[2.6, 13.4])
regra("Recalcular", "se já existe parcela na folha, o botão vira “Recalcular esta Parcela”: "
      "apaga os lançamentos daquela verba e refaz na MESMA parcela. Lançar uma parcela "
      "adicional virou exceção, por link explícito.")


# ============================================================== ETAPA 5
h1("Etapa 5 — Movimento Fixo")
caminho("Menu principal › Movimento Fixo")

h2("O que é")
p("Lançamento cadastrado UMA VEZ que o sistema repete a cada folha. Entra no tab_mov com "
  "origem F, indicando que foi o cálculo que gerou.")

h2("Quem recebe")
tabela(["Forma", "Como funciona"],
       [["Por matrícula", "Um funcionário específico."],
        ["Por grupo", "Filtros de categoria, data de nascimento, data de admissão, salário-base, idade e tempo de serviço. É reavaliado A CADA FOLHA: quem for admitido depois, dentro do perfil, passa a receber sozinho."]],
       larguras=[3.4, 12.6])

h2("Duração")
tabela(["Forma", "Como funciona"],
       [["Por parcelas", "Informa a quantidade; para sozinho ao atingir o total."],
        ["Por período", "Folha inicial e, se quiser, folha final. Sem final, o prazo é indeterminado."]],
       larguras=[3.4, 12.6])

h2("Comportamento em férias")
tabela(["Código", "Comportamento"],
       [["0", "Não processa, mesmo que seja 1 dia de férias."],
        ["1", "Processa integral, sem proporcionalidade."],
        ["2", "Processa tudo nas férias, se as férias começarem nessa folha."],
        ["3", "Proporcional aos dias trabalhados E aos dias gozados."],
        ["4", "Proporcional aos dias trabalhados, zero nas férias."]],
       larguras=[2.0, 14.0])
p("Existem ainda as opções “Se afastado” (continuar, interromper ou proporcional) e o "
  "tratamento do mês de admissão e do mês de rescisão (total ou proporcional).")

h2("Encerrar — duas saídas diferentes")
caminho("Menu principal › Movimento Fixo › Excluir / Parar Mov. Fixo")
tabela(["Ação", "O que faz", "Quando é permitida"],
       [["PARAR", "Grava a última folha em que o movimento vale. O histórico fica intacto.", "Sempre. É o que se usa em quase todos os casos."],
        ["EXCLUIR", "Apaga de vez.", "Só quando o movimento começou NESTA folha E nunca gerou lançamento nenhum."]],
       larguras=[2.4, 6.8, 6.8])
p("A trava existe porque excluir algo que já rodou em folha paga apagaria o histórico de um "
  "valor efetivamente pago. Ela vale também no servidor.")
regra("Voltar atrás", "do PARAR dá: basta editar o movimento e limpar a última folha. "
      "Da EXCLUSÃO não há volta.")

h2("O que não entra aqui")
item("Insalubridade e periculosidade para quem já tem o adicional no cadastro — a folha já "
     "lança sozinha e o funcionário receberia em dobro. Em movimento de grupo, basta um "
     "funcionário ter o adicional para o sistema recusar o grupo inteiro.")
item("Verbas 700 a 749 (empréstimo consignado) — o caminho é Movimento Mês › Importar Consignados.")

h2("A lista")
p("Mostra por padrão só os movimentos EM VIGÊNCIA. A caixa “Mostrar também os encerrados” "
  "traz o resto. Encerrado significa que a folha final já passou da folha ativa.")


# ============================================================== ETAPA 6
h1("Etapa 6 — Cálculo")
caminho("Menu principal › Cálculo")

h2("Numeração das etapas da memória de cálculo")
p("A memória numera as etapas de 10 em 10, para caber etapa nova no meio sem renumerar tudo.")
tabela(["Faixa", "Do quê"],
       [["1xxx", "Folha mensal"], ["2xxx", "Férias"], ["3xxx", "Rescisão"],
        ["4xxx", "13º e adiantamento do 13º"],
        ["9xxx", "Rotinas auxiliares compartilhadas — o código identifica a ROTINA, não a posição."]],
       larguras=[2.0, 14.0])

h3("Etapas da folha mensal")
tabela(["Código", "Etapa", "Código", "Etapa"],
       [["1010", "Salário-hora", "1100", "Verbas do intermitente"],
        ["1020", "Admissão no mês", "1110", "DSR"],
        ["1030", "Dias trabalhados", "1120", "INSS"],
        ["1040", "Salário proporcional", "1130", "IRRF"],
        ["1050", "Faltas", "1140", "Desconto do adiant. quinzenal"],
        ["1060", "Insalubridade", "1150", "Pensão alimentícia"],
        ["1070", "Periculosidade", "1155", "Cliente sem encargos"],
        ["1080", "Movimentos fixos", "1160", "Arredondamento"],
        ["1090", "Lançamentos do mês", "1170", "Insuficiência de saldo"]],
       larguras=[1.8, 6.2, 1.8, 6.2])

h2("Tabelas legais")
p("INSS, IRRF e salário mínimo ficam DENTRO do sistema — o cliente não configura. A vigência "
  "é por ano_mes_inicio, e a busca usa o maior valor menor ou igual à competência da folha. "
  "Uma vez gravadas, nunca são alteradas.")

h2("INSS")
item("Progressivo por faixa, sem arredondamento intermediário.")
item("Verba 101 para o empregado; verba 102 para contribuinte individual e pró-labore (11%).")
item("Base formada pelas verbas com incidência 11: provento soma, desconto com incidência subtrai.")
item("Férias do mesmo mês entram numa base consolidada, e o INSS das férias vira adiantamento.")

h2("IRRF")
p("O sistema calcula pelos DOIS métodos — completo e simplificado — e usa o mais favorável "
  "ao funcionário.")
regra("Isenção até R$ 5.000,00", "Lei 15.270/2025, desde janeiro de 2026. Rendimento até "
      "5.000,00 fica isento; de 5.000,01 a 7.350,00 aplica o redutor. Não é faixa da tabela: "
      "é o redutor (irrf_redutor_a, _b, _ini e _fim), aplicado em folha, férias, 13º e rescisão.")

h2("FGTS")
p("Quem recolhe é definido pela CATEGORIA, não pela incidência da rubrica. As categorias 700 "
  "a 799 e a 901 não recolhem, com a única exceção da 721.")
atencao("O FGTS é calculado em 4 lugares: o cálculo que grava o tab_total e mais três que "
        "recalculam a partir do tab_mov. Mexeu na regra? Confira os quatro.")

h2("DSR — repouso remunerado")
p("Fórmula: base ÷ dias úteis × (domingos + feriados).")
tabela(["Origem (flag da verba)", "Verba gerada"],
       [["19 — Hora extra", "0025"], ["11 — Adicional noturno", "0026"],
        ["04 — Comissão", "0027"]], larguras=[6.0, 10.0])
regra("Horário de escala", "troca o divisor por 15 dias (14 em fevereiro).")

h2("Insalubridade e periculosidade no cálculo")
p("Insalubridade é percentual do salário mínimo; periculosidade é percentual do salário base. "
  "Ver a lacuna declarada na Etapa 3.")


# ============================================================== ETAPA 7
h1("Etapa 7 — Relatórios")
caminho("Menu principal › Relatórios")
p("O card agrupa relatórios de Cadastros, Eventos, Folha de Pagamento, o Gerador e os "
  "relatórios de Sistema.")

h2("Regras de leitura que valem para os relatórios")
regra("Fonte dos valores", "os relatórios de folha leem o que foi PERSISTIDO pelo cálculo "
      "(tab_mov e tab_total). Relatório em branco quase sempre significa folha não calculada, "
      "não erro do relatório.")
regra("Verbas informativas", "as da faixa 9900 a 9999 aparecem no holerite mas não entram em "
      "proventos, descontos nem no líquido.")
regra("Adiantamento quinzenal", "as verbas 161 a 164 aparecem em bloco próprio e não entram "
      "nos totais.")

h2("Relatórios com regra própria já definida")
h3("Lista de Funcionários")
item("Traz badge de Aviso Prévio para quem está nessa situação.")
item("A lista some ao mudar o filtro — é preciso clicar em “Atualizar a Lista”.")
h3("Funcionários Afastados")
item("Lê tab_eventos op1 = 6.")
item("data1f vazia significa afastamento em aberto.")
atencao("op2 = 203 é registro auxiliar da migração e duplica o afastamento verdadeiro.")
h3("Funcionários em Férias")
item("O critério é sobreposição de período com a competência.")
atencao("data1i = 99999999 é período aquisitivo sem gozo — não é férias.")
h3("Listagem dos Demitidos")
item("Filtra por data de demissão, com o mês atual como padrão. Emite PDF.")
h3("Ficha Financeira")
item("Tela pronta. Lacuna conhecida: os totais do tab_total não estão aparecendo.")

h2("Cabeçalho padrão")
p("Todo relatório usa o mesmo cabeçalho de três colunas: empresa e nome do usuário à "
  "esquerda; título e badge da folha no centro; logo, versão e botão Voltar à direita.")


# ============================================================== ETAPA 8
h1("Etapa 8 — Conexões")
caminho("Menu principal › Conexões")

h2("Pagamento bancário — CNAB 240")
caminho("CNAB 240 — Crédito em Conta · CNAB 240 — PIX")
item("Cinco bancos atendidos.")
item("Duas modalidades: crédito em conta e PIX.")
item("O arquivo tem que suportar funcionários com conta em banco diferente do banco da empresa.")



# ============================================================== ETAPA 9
h1("Etapa 9 — eSocial")
caminho("Menu principal › eSocial")
p("O card segue a ordem natural do eSocial: primeiro as tabelas, depois os eventos não "
  "periódicos, depois os periódicos.")

h2("Envio contra o status da folha")
tabela(["Grupo de eventos", "Exigência"],
       [["Não periódicos (S-1000 a S-1099 e S-2xxx)", "SEM trava de status da folha."],
        ["Periódicos (S-1200, S-1210, S-1298, S-1299)", "Exigem a folha FECHADA."]],
       larguras=[7.0, 9.0])

h2("Qual evento cada situação gera")
tabela(["Situação", "Evento"],
       [["Admissão de empregado (categoria menor que 700)", "S-2200"],
        ["Admissão de não empregado (700 ou mais)", "S-2300 (TSVE)"],
        ["Afastamento", "S-2230 — saída e retorno"],
        ["Férias", "S-2230 com flag F"],
        ["Desligamento", "S-2299"],
        ["Acidente", "S-2210 (CAT)"]], larguras=[8.0, 8.0])

h2("Grupo Tabelas — S-1000, S-1005, S-1010 e S-1020")
regra("S-1020", "criar somente pela tela própria. O evento precisa de FPAS e código de "
      "Terceiros, que o Gerador não preenche — registro sem FPAS é rejeitado com o erro [17].")
regra("codLotacao", "é o centro de custo do funcionário (tab_cad.centrocusto).")
regra("codTercs", "é derivado do FPAS pela tab_aux_fpas. Exceção: classificação tributária "
      "01 a 04 (Simples Nacional e MEI) recolhe Terceiros pela DAS, então o codTercs TEM que "
      "ser 0000 — caso contrário vem o erro [247].")

h2("Conferência obrigatória antes do S-1200")
p("Ao mandar um S-1200 o sistema confere três coisas, nesta ordem de gravidade. As duas "
  "primeiras BARRAM o envio: são recusa certa do eSocial, e a mensagem do governo não diz "
  "qual rubrica ou lotação faltou.")
tabela(["Ordem", "Verificação", "Se faltar"],
       [["1", "Lotação da folha com S-1020 aceito e vigente",
         "Barra o envio e cria a remessa S-1020 na Fila."],
        ["2", "Verbas lançadas no tab_mov com S-1010 aceito e vigente",
         "Barra o envio e cria as remessas S-1010 na Fila."],
        ["3", "Remessas pré-requisito pendentes (S-1005, S-2200, S-2230 e outras)",
         "Apenas avisa. Dá para seguir confirmando."]],
       larguras=[1.6, 6.8, 7.6])
p("A vigência conta: rubrica declarada com início de validade em 07/2026 não cobre a folha "
  "de 06/2026. Verba informativa (código 9900 ou maior) fica de fora, porque não vai no S-1200.")
atencao("Esta conferência foi feita pensando no cliente no primeiro mês. Nele não existe "
        "NENHUM registro de tabela, e a checagem de pendências só enxerga o que já existe — "
        "por isso ela sozinha não acusava nada e o S-1200 ia direto para a rejeição.")
regra("Sem duplicar", "a criação automática pula a verba ou a lotação que já tem remessa na "
      "Fila, em qualquer situação.")

h2("Regras de XML que já custaram caro")
tabela(["Campo", "Regra"],
       [["nrSeqEvento", "00001 para lote de 1 evento. Usar a matrícula causava rejeição 609."],
        ["indApurIR", "0 sempre na folha mensal. Não existe o valor 2; usar 1 zera o IRRF."],
        ["ideDmDev", "Matrícula com 6 dígitos mais “00” (ex.: 00000100). Tem que ser único por trabalhador, senão o IRRF vem zerado no S-5012."],
        ["codRubr", "“0001-FOL”. Sufixo -FER para férias, -13S para 13º e -FOL nos demais."]],
       larguras=[2.8, 13.2])

h2("Certificado digital")
caminho("Certificado Digital · Cert. de Procurador")
p("A senha é cifrada com chave derivada do FLASK_SECRET_KEY, que é DIFERENTE entre o "
  "ambiente local e o Render. Certificado salvo localmente só abre localmente.")
atencao("Deu “Erro interno” no envio? Regrave o .pfx NO AMBIENTE de onde vai enviar — "
        "normalmente o site.")

h2("Fila de Remessas")
caminho("Gerador Manual · Fila de Remessas · Listagem · Pendências e Erros")
regra("Agrupamento", "por competência (ano_mes). Remessa de outro mês não aparece na fila da "
      "folha ativa.")
regra("Não confundir", "a “Fila de Remessas” é uma tela geral; cada layout ainda tem a sua "
      "tela própria, e elas não são a mesma coisa.")
regra("Situação da remessa", "recém-criada aparece como Pendente. Enviado é recibo "
      "preenchido; Aguardando é protocolo em consulta; Com Erro é mensagem de recusa gravada.")

h2("Verificação Folha10 × eSocial")
p("Confronta o que o Folha10 calculou com os totalizadores devolvidos pelo governo. "
  "Os S-5001 e S-5003 vêm do retorno do S-1200 e o S-5002 vem do retorno do S-1210 — "
  "nunca do S-1299.")


# ============================================================== ETAPA 10
h1("Etapa 10 — Diversos")
caminho("Menu principal › Diversos")

h2("Sistema")
caminho("Configurações · Usuários e Permissões · Log de Auditoria")
regra("Login por pessoa", "tab_cliente é o contrato e tab_usuario é quem loga. A tela de "
      "usuários é só do titular da conta.")
regra("Log", "gravado em tab_log pelo helper gravar_log(), que trunca os campos. "
      "Insert cru com código maior que o limite falha calado.")

h2("Dados")
caminho("Backup · Exportar Dados")
p("Sem regra adicional documentada até esta edição do manual.")


# ============================================================== ETAPA 11
h1("Etapa 11 — Administrador")
caminho("Menu principal › Administrador  (card visível apenas para a equipe F10)")
regra("Quem vê", "o servidor decide, pela função _pode_admin(): a conta inteira da F10 "
      "(id_cliente 4), não um CPF. Todo usuário dessa conta tem o módulo Admin, o Trocar "
      "Cliente e pode mexer nas verbas de sistema (código abaixo de 1000).")

h2("Clientes")
caminho("Lista de Clientes · Licença de Uso · Libera Folhas Anteriores")
regra("Impersonar", "o administrador entra em qualquer cliente sem senha. A sessão mostra "
      "banner vermelho e o acesso é registrado em tab_log.")

h2("Comunicação e Marketing")
caminho("Quadro de Avisos · Leads Pet-Shop")
regra("Quadro de avisos", "tab_aviso e tab_aviso_lido, publicados pela tela /admin_avisos.")

h2("Migração, Notas Fiscais e Base de Teste")
caminho("Importar do Folha 10 Antigo · Emitir NFS-e · Visualizar XML · Copiar Base p/ Teste · Backup")
regra("Copiar base para teste", "copia a base de qualquer empresa para o cliente 6. A origem "
      "NUNCA é alterada; as chaves são remapeadas no destino.")
regra("Backup do Supabase", "baixa a cópia para C:\\Folha10-Simples\\CopiaBase\\AAAAMMDD. "
      "É rotina local e só de leitura.")
regra("NFS-e", "a coluna Servico_Valor está em centavos. Valor maior que zero oculta "
      "empresas e funcionários na tela.")


# ============================================================== ANEXO A
h1("Anexo A — Armadilhas de banco e de dados")
p("Regras que não pertencem a uma tela, mas derrubam qualquer uma delas.")

h2("Formatos que enganam")
regra("tab_cad.dtadm é AAAAMMDD, sem traços", "ler como AAAA-MM-DD junta o segundo dígito do "
      "mês com o primeiro do dia: 20260302 vira 202630. Isso já fez funcionários sumirem da "
      "tela de adiantamento. Usar o helper _anomes_admissao().")
regra("tab_log.menu é varchar(12)", "insert cru com código maior falha CALADO — quase todos "
      "estão dentro de except: pass. Foi o que multiplicou a licença no webhook do Asaas. "
      "O helper gravar_log() trunca; inserts crus não.")
regra("tab_tabela_cli.codigo é varchar(12)", "preferências precisam de código curto.")

h2("PostgREST corta em 1000 linhas")
p("E ignora limite maior: pedir 5000 devolve 1000. Consulta em lote para validar “já existe” "
  "pode dar falso negativo. Comportamento testado. Toda leitura que precisa ser completa "
  "tem que paginar.")

h2("tab_eventos — códigos op1")
tabela(["op1", "Evento", "op1", "Evento"],
       [["3", "Férias", "31", "Insalubridade"],
        ["6", "Afastamento", "41", "Periculosidade"],
        ["9", "Aviso prévio", "190", "matricula_es (migração)"]],
       larguras=[1.6, 6.4, 1.6, 6.4])
atencao("op2 = 203 no afastamento é registro auxiliar da migração e duplica o afastamento "
        "verdadeiro.")

h2("tab_esocial")
item("A chave primária é id_esocial, não “id”.")
item("Evento ENVIADO significa recibo não vazio.")
item("EXCLUÍDO por S-3000 é observacao_erro igual a EXCLUIDO.")
item("A coluna observacao_erro tem dois usos nos eventos de tabela: guarda os parâmetros da "
     "remessa como PARAMS:{...} e, depois de um “|”, o status do envio. Só a segunda parte é "
     "mensagem de erro — tratar a coluna inteira como erro faz remessa recém-criada aparecer "
     "como “Com Erro” sem nunca ter sido enviada.")

h2("RLS desligada no Supabase")
p("O isolamento entre clientes é feito exclusivamente pelo .eq(\"id_cliente\") no código "
  "Python. Decisão adiada — lacuna conhecida e aceita.")


# ============================================================== ANEXO B
h1("Anexo B — Padrões de tela")

h2("Cabeçalho padrão")
p("Três colunas: empresa e nome do usuário | título e badge da folha | logo, versão e botão "
  "Voltar. Fonte IBM Plex em todas as telas.")

h2("Ajuda — botão “Dúvida?”")
p("Verde, em formato de pílula, alinhado à DIREITA do cabeçalho da tela. Abre um painel "
  "próprio, não um alerta de texto puro. O texto mora num parcial _ajuda_<modulo>.html, "
  "incluído tanto na tela quanto no card do menu — editar num lugar só vale para os dois.")

h2("Cards do menu")
p("Ao selecionar um card, o grid é escondido e dá lugar a uma barra compacta com o botão "
  "Trocar, para a lista ocupar toda a área.")

h2("Tour guiado")
p("As telas com tour usam Driver.js, acionado pelo botão “?” no canto inferior direito.")

h2("Versão")
p("O arquivo versaoxxx.txt é atualizado a cada alteração rodando python _gravar_versao.py, "
  "que pega a hora de Brasília. A hora nunca é digitada à mão.")


# ============================================================== ANEXO C
h1("Anexo C — Regras específicas de cliente")

h2("Cliente 0038 — sem encargos")
p("Constantes no app.py: CLIENTES_SEM_ENCARGOS e CLIENTES_SEM_DSR.")
item("NÃO calcula INSS, IRRF nem FGTS em nenhuma verba. O cálculo roda inteiro e a memória "
     "mostra o que seria devido; só o VALOR é zerado antes de gravar. As BASES continuam "
     "gravadas no tab_total. Vale na folha mensal, no 13º, nas férias, na rescisão e no "
     "adiantamento do 13º.")
item("NÃO calcula repouso remunerado nas verbas 0025 (hora extra) e 0027 (comissões). "
     "A 0026 (adicional noturno) continua normal. O valor é apurado e mostrado na memória, "
     "mas não é lançado.")
item("Verba digitada A MÃO continua sendo mantida — a regra vale para o que o sistema CALCULA.")

h2("Cliente 000614 — nota fiscal")
p("Emite NFS-e com ISS retido pelo tomador a 5%, com endereço fixo. O DANFSe mostra "
  "alíquota, base de cálculo, ISS apurado e ISS retido.")

h2("Conta 4 — equipe F10")
p("Todo usuário do id_cliente 4 tem o módulo Admin, o Trocar Cliente e pode alterar as "
  "verbas de sistema (código abaixo de 1000).")


# ============================================================== FECHO
documento().add_page_break()
h2("Sobre este manual")
p("Reúne o que já está definido e valendo. Onde a regra ainda não está fechada, o texto diz "
  "isso — as lacunas declaradas hoje são:")
item("Verbas 30, 31 e 32 (insalubridade e periculosidade) com inc_* = CN, valor que o código "
     "não trata: o adicional não chega a férias, 13º nem rescisão.")
item("Ficha Financeira: os totais do tab_total não aparecem na tela.")
item("RLS desligada no Supabase: o isolamento entre clientes depende só do código.")
p()
p(f"Folha10 Simples — versão {VERSAO_SISTEMA}. Documento gerado em 09/08/2026.",
  italico=True, cor=CINZA)

os.makedirs(DESTINO, exist_ok=True)
salvar(ARQUIVO)
print("OK:", ARQUIVO)
