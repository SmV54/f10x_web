# -*- coding: utf-8 -*-
"""Gera o Manual do Usuario do Folha10 Simples em Word.

Manual de OPERACAO: comeca na criacao da conta e segue ate fechar o mes, na
ordem dos cards do menu principal. Escrito para quem vai usar o sistema, nao
para quem mexe no codigo — sem nome de tabela, sem nome de coluna, sem rotina.

O irmao deste arquivo, _gerar_manual.py, faz o manual INTERNO (regras
tecnicas). Os dois compartilham o estilo, que mora em _manual_base.py.
"""
import os
from _manual_base import *   # noqa: F401,F403

DESTINO = r"C:\folha10-simples\manual"
ARQUIVO = os.path.join(DESTINO, "Manual_do_Usuario_Folha10_Simples.docx")
VERSAO = open(r"C:\folha10-simples\versaoxxx.txt", encoding="utf-8").read().strip()

iniciar("Folha10 Simples — Manual do Usuário", f"versão {VERSAO}")

# ================================================================== CAPA
capa("FOLHA10 SIMPLES",
     "Manual do Usuário",
     "Do primeiro cadastro ao fechamento do mês, etapa por etapa")

p("Este manual foi escrito para quem opera o sistema. Ele não explica como o "
  "Folha10 foi construído por dentro: explica o que fazer, em que ordem, e o "
  "que o sistema espera de você em cada tela.")
p("A ordem das etapas é a mesma dos botões do menu principal. Se você está "
  "começando agora, leia a Parte 1 inteira — são poucas páginas e evitam a "
  "maior parte das dúvidas. Depois disso, use o manual como consulta: vá "
  "direto na etapa do que você precisa fazer.")
dica("No fim há duas partes que valem mais que todo o resto no dia a dia: "
     "a Rotina do Mês, com o roteiro completo na ordem certa, e o Quando algo "
     "não sai como esperado, com as dúvidas mais comuns.")

p()
tabela(["", ""],
       [["Para quem", "Quem faz a folha de pagamento no dia a dia"],
        ["Versão do sistema", VERSAO],
        ["Endereço", "www.folha10-simples.com.br"]],
       larguras=[4.0, 12.0])

p()
h2("O que você vai encontrar")
for rot, txt in [
    ("Parte 1", "Primeiros passos — criar a conta, entender a tela e cadastrar o essencial"),
    ("Etapa 1", "Cadastros"),
    ("Etapa 2", "Nova Folha"),
    ("Etapa 3", "Eventuais — férias, rescisão, afastamento, faltas e outros"),
    ("Etapa 4", "Movimento do Mês"),
    ("Etapa 5", "Movimento Fixo"),
    ("Etapa 6", "Cálculo"),
    ("Etapa 7", "Relatórios"),
    ("Etapa 8", "Conexões — pagamento bancário e integrações"),
    ("Etapa 9", "eSocial"),
    ("Etapa 10", "Diversos"),
    ("Parte 3", "A rotina do mês, do começo ao fim"),
    ("Parte 4", "Quando algo não sai como esperado"),
]:
    par = documento().add_paragraph()
    par.paragraph_format.space_after = Pt(2)
    par.add_run(f"{rot}  ").bold = True
    par.add_run(txt)


# ============================================== PARTE 1 — PRIMEIROS PASSOS
h1("Parte 1 — Primeiros passos")
p("Esta parte é para quem está entrando no sistema pela primeira vez. Ela "
  "cobre a criação da conta, o funcionamento da tela do menu, o vocabulário "
  "que aparece o tempo todo e o cadastro mínimo para você conseguir calcular "
  "a primeira folha.")

h2("1. Criar a conta e entrar")
p("O sistema funciona pelo navegador, no endereço www.folha10-simples.com.br. "
  "Não há nada para instalar no computador.")
passo(1, "Criar Conta.", "Na tela de entrada, clique em Criar Conta e preencha "
      "seus dados. É aqui que nasce o seu acesso.")
passo(2, "Entrar.", "O login é o seu CPF e uma senha de 6 dígitos.")
passo(3, "Manter conectado.", "Marque essa caixa no computador que é só seu, "
      "para não precisar digitar a senha toda vez. Não use em máquina compartilhada.")
dica("Esqueceu a senha? Na própria tela de entrada existe a opção de recuperar. "
     "Você não precisa falar com ninguém para voltar a entrar.")

h3("Licença")
p("O sistema mostra no menu quantas empresas e quantos funcionários a sua "
  "licença cobre. Quando estiver perto do limite, ou quando a licença estiver "
  "vencendo, aparece um botão de renovação no próprio menu. Você não perde "
  "dados por causa disso — o que muda é o que o sistema deixa incluir.")

h2("2. A tela do Menu")
p("O menu é o ponto de partida de tudo. Ele tem os cards dos módulos no meio "
  "e alguns atalhos fixos em volta.")

h3("Os cards")
p("Cada card é um módulo. Clicando em um deles, a grade de cards recolhe e "
  "aparece o painel com todas as funções daquele módulo, ocupando a tela "
  "inteira. Para voltar e escolher outro, use o botão Trocar que aparece na "
  "barra do topo do painel.")

h3("O que fica em volta")
tabela(["Onde", "O que é"],
       [["Topo da tela", "O nome da empresa em que você está e a competência (mês/ano) em que o sistema está trabalhando."],
        ["Canto superior direito", "Os botões Manual e Preferências."],
        ["Cabeçalho", "O botão de trocar de empresa, quando você tem mais de uma."],
        ["Dentro das telas", "O botão verde “Dúvida?”, que abre a explicação daquela tela."],
        ["Canto inferior direito", "O botão “?”, que faz um tour guiado apontando cada parte da tela."]],
       larguras=[4.6, 11.4])
dica("O tour guiado é a forma mais rápida de aprender uma tela nova. Ele "
     "aponta os campos na ordem em que você vai usá-los, e pode ser repetido "
     "quantas vezes quiser.")

h3("Quadro de avisos")
p("Recados da equipe Folha10 aparecem no próprio menu. São coisas como "
  "mudança de legislação, prazo do eSocial e novidades do sistema.")

h2("3. Palavras que aparecem o tempo todo")
p("Vale gastar dois minutos aqui. Quase toda dúvida de quem está começando é, "
  "na verdade, uma dessas palavras que ainda não ficou clara.")

h3("Competência (ou folha ativa)")
p("É o mês e o ano em que o sistema está trabalhando. Tudo o que você lançar "
  "vai cair nessa competência — por isso ela aparece o tempo todo no alto da "
  "tela. Antes de lançar qualquer coisa, confira se a competência é a que você "
  "quer.")
atencao("A folha só anda para a frente. Não é possível voltar para um mês "
        "anterior ao mais recente já aberto na empresa.")

h3("Situação da folha")
tabela(["Situação", "O que significa", "O que você pode fazer"],
       [["Aberta", "O mês está em digitação.", "Incluir, alterar e excluir à vontade."],
        ["Calculada", "O cálculo já rodou.", "A maioria das telas fica bloqueada. Para mexer, reabra a folha."],
        ["Fechada", "O mês está encerrado.", "Bloqueado. Para mexer, reabra a folha."]],
       larguras=[2.6, 5.4, 8.0])

h3("Tipos de folha")
p("Dentro do mesmo mês pode existir mais de uma folha, cada uma com a sua "
  "finalidade:")
tabela(["Tipo", "Quando aparece"],
       [["Normal", "A folha do mês, sempre."],
        ["Férias", "Quando alguém sai de férias."],
        ["Rescisão", "Quando alguém é desligado."],
        ["Adiantamento do 13º", "Normalmente em novembro."],
        ["13º salário", "Normalmente em dezembro."]],
       larguras=[4.4, 11.6])

h3("Verba (ou rubrica)")
p("É cada linha que aparece no holerite: salário, hora extra, desconto do "
  "vale-transporte, INSS. Toda verba tem um código e um tipo:")
tabela(["Tipo", "Efeito no holerite"],
       [["Provento", "Soma — o funcionário recebe."],
        ["Desconto", "Subtrai — o funcionário paga."],
        ["Informativa", "Aparece no holerite mas não soma nem subtrai. Serve para informação, como o valor do FGTS do mês."]],
       larguras=[3.0, 13.0])

h3("Centro de custo")
p("É a forma de saber quanto custa cada parte da empresa — a loja, a filial, "
  "a obra, o departamento. Os relatórios da folha saem separados por ele. "
  "Se a sua empresa não usa essa separação, tudo bem: o sistema já cria um "
  "centro de custo padrão e preenche sozinho no cadastro de cada funcionário.")

h3("Matrícula")
p("É o número que identifica o funcionário dentro da empresa. O sistema "
  "sugere o próximo número livre — você não precisa controlar isso.")

h2("4. Os quatro primeiros passos")
p("Assim que você cadastra a empresa, o menu passa a mostrar um painel de "
  "Primeiros Passos, com quatro etapas e uma barra de progresso. Ele conduz "
  "você até a primeira folha e desaparece sozinho quando o primeiro "
  "funcionário é cadastrado.")
passo(1, "Cadastrar a empresa.", "Feito no momento em que você criou a conta. "
      "Vale conferir os dados, principalmente CNPJ e endereço, porque eles vão "
      "para o eSocial.")
passo(2, "Escolher as funções.", "Motorista, vendedor, auxiliar. Você escolhe "
      "as funções que a sua empresa tem, a partir de um catálogo pronto — não "
      "precisa digitar nada do zero.")
passo(3, "Definir o centro de custo.", "O sistema pergunta se a empresa separa "
      "os funcionários por centro de custo. Se for tudo junto, é só marcar a "
      "primeira opção e seguir: o centro de custo padrão já está criado.")
passo(4, "Cadastrar os funcionários.", "A partir daqui você já pode lançar e "
      "calcular.")
dica("A primeira folha do mês é aberta automaticamente junto com a empresa. "
     "Se você se cadastrou até o dia 5, o sistema sugere o mês ANTERIOR — "
     "porque quem chega no começo do mês normalmente vem processar o mês que "
     "acabou de passar.")


# ============================================================== ETAPA 1
h1("Etapa 1 — Cadastros")
caminho("Menu principal › Cadastros")
p("É onde ficam as informações que não mudam todo mês: os funcionários, as "
  "tabelas de apoio e os dados da empresa.")
atencao("Com a folha calculada ou fechada, os cadastros ficam bloqueados. "
        "Se precisar alterar algo, reabra a folha antes. A única exceção é "
        "Nova Empresa, que continua liberada.")

h2("Cadastrar um funcionário")
caminho("Cadastros › Funcionário › Incluir Funcionário")
p("A tela é longa, mas está dividida em blocos, na ordem em que você "
  "normalmente tem as informações em mãos:")
tabela(["Bloco", "O que vai nele"],
       [["Identificação", "Nome, CPF, matrícula e categoria do trabalhador."],
        ["Dados Pessoais", "Nascimento, documentos, estado civil, grau de instrução."],
        ["Salário / Contrato", "Salário, forma de pagamento, tipo de contrato."],
        ["Admissão", "Data de admissão e dados do vínculo."],
        ["Local de Trabalho", "Centro de custo e filial."],
        ["Jornada de Trabalho", "Horário e escala."],
        ["Endereço do Funcionário", "Endereço completo."],
        ["Contrato de Experiência", "Prazo e prorrogação, quando houver."],
        ["Dados Bancários", "Banco, agência e conta, usados no pagamento."]],
       larguras=[4.6, 11.4])
p("Alguns blocos só aparecem quando se aplicam ao caso: estágio, trabalhador "
  "estrangeiro, deficiência ou reabilitação e menor aprendiz.")

h3("A data de admissão manda em muita coisa")
tabela(["Data de admissão", "O que acontece"],
       [["Depois da competência aberta", "O sistema RECUSA. Abra a folha do mês certo antes de cadastrar."],
        ["Dentro da competência aberta", "Cadastro normal, e o sistema prepara o evento de admissão para o eSocial."],
        ["Antes da competência aberta", "O sistema pede confirmação e NÃO prepara o evento de admissão."]],
       larguras=[5.2, 10.8])
p("A última linha merece explicação. Admissão com data antiga quase sempre é "
  "implantação: o funcionário já trabalha há tempos e a admissão dele já foi "
  "enviada ao eSocial pelo sistema anterior. Mandar de novo criaria um evento "
  "duplicado, chato de desfazer. Se, no seu caso, o evento realmente precisa "
  "ir, existe o caminho manual dentro do módulo eSocial.")

h3("A categoria muda o cálculo")
p("A categoria diz que tipo de trabalhador é aquele, e é ela que determina "
  "quais encargos entram:")
tabela(["Categoria", "Na prática"],
       [["Empregado (o caso comum)", "Salário, INSS, FGTS e IRRF normalmente."],
        ["Diretor e sócio (pró-labore)", "Não tem FGTS, salvo um caso específico de diretor. O INSS é o do contribuinte individual."],
        ["Estagiário", "Recebe bolsa. Não tem INSS nem FGTS — apenas IRRF, se o valor alcançar."]],
       larguras=[5.0, 11.0])
dica("Se o holerite saiu sem FGTS ou sem INSS e você não esperava isso, "
     "confira a categoria antes de qualquer outra coisa. É a causa mais comum.")

h3("Nome do cargo")
p("Se você deixar em branco, vale o nome da função escolhida. Preencher só é "
  "necessário quando duas funções diferentes da sua empresa usam a mesma "
  "classificação oficial e você quer que cada uma apareça com o seu nome nos "
  "documentos.")

h2("Alterar, consultar e corrigir")
caminho("Cadastros › Funcionário")
tabela(["Função", "Para que serve"],
       [["Alterar Funcionário", "Mudar qualquer dado de quem já está cadastrado."],
        ["Dependentes", "Filhos e demais dependentes, que influem no imposto de renda e no salário-família."],
        ["Ficha de Registro", "A ficha completa do funcionário, para imprimir."],
        ["Limpar Funcionário", "Apagar em definitivo um cadastro feito por engano."]],
       larguras=[4.6, 11.4])
atencao("Limpar Funcionário é DEFINITIVO e não tem como desfazer: apaga o "
        "cadastro e tudo que veio junto, em todas as folhas. Só é permitido "
        "para quem foi admitido no mês da folha aberta e ainda não teve nada "
        "enviado ao eSocial. Use apenas para desfazer um cadastro errado. Para "
        "desligar alguém de verdade, o caminho é a Rescisão.")

h2("Tabelas auxiliares")
caminho("Cadastros › Tabelas Auxiliares")
p("São as tabelas de apoio que você monta uma vez e usa sempre:")
tabela(["Tabela", "Para que serve"],
       [["Funções / Cargos", "As funções da sua empresa, escolhidas a partir do catálogo oficial."],
        ["Horários de Trabalho", "As jornadas, inclusive escala."],
        ["Sindicatos", "O sindicato de cada categoria."],
        ["Vale Transporte", "As linhas e valores."],
        ["Rubricas (Verbas)", "As verbas do holerite."],
        ["Feriados", "Os feriados, que o cálculo usa no repouso remunerado."],
        ["Centros de Custo", "As divisões da empresa."],
        ["Filiais", "Os estabelecimentos."],
        ["Usuários da Conta", "Quem mais pode entrar no sistema."]],
       larguras=[4.6, 11.4])

h3("Sobre as verbas")
p("O sistema já vem com as verbas comuns prontas — salário, hora extra, "
  "faltas, INSS, IRRF. Você não precisa criar nada para começar, e essas "
  "verbas de sistema não podem ser alteradas, justamente para o cálculo não "
  "quebrar.")
p("Quando precisar de uma verba própria da sua empresa, crie uma nova: o "
  "sistema sugere o próximo código livre. Ao criar, o que você define é:")
item("se é provento, desconto ou informativa;")
item("se o valor é em reais, em horas ou em diárias — em horas e diárias o "
     "sistema faz a conta pelo salário na hora do cálculo, então o valor "
     "acompanha o reajuste sozinho;")
item("o percentual de acréscimo, quando for o caso: 50 é a hora extra de 50%, "
     "100 é a hora dobrada;")
item("sobre o que ela incide — se entra na base do INSS, do FGTS e do IRRF;")
item("se ela vira média em férias, 13º e rescisão.")
atencao("Essa última é a que mais gera dúvida depois. Se a hora extra é "
        "habitual, ela precisa estar marcada para entrar na média — senão as "
        "férias e a rescisão saem “sem a média” e ninguém entende o porquê.")
dica("A tela de verbas tem o botão “Dúvida?”, com a explicação de cada campo.")

h2("Pensão alimentícia")
caminho("Cadastros › Pensão Alimentícia")
p("Cadastre primeiro quem paga e depois os beneficiários — até nove por "
  "responsável. A fórmula do desconto é escolhida de uma lista, e a pensão "
  "começa a valer a partir da competência aberta no momento do cadastro.")
p("O recibo da pensão tem tela própria, no mesmo grupo.")

h2("Empresa")
caminho("Cadastros › Empresa")
p("Nova Empresa cadastra outra empresa dentro da mesma conta — respeitando o "
  "que a sua licença cobre. Alterar Esta Empresa mexe nos dados da empresa em "
  "que você está no momento.")
atencao("Os dados da empresa vão para o eSocial. CNPJ, endereço e a "
        "classificação tributária precisam estar corretos, ou os envios são "
        "recusados pelo governo.")


# ============================================================== ETAPA 2
h1("Etapa 2 — Nova Folha")
caminho("Menu principal › Nova Folha")
p("É aqui que você abre o mês de trabalho e controla a passagem dele entre "
  "aberto, calculado e fechado.")

h2("Abrir o mês")
tabela(["Função", "Quando usar"],
       [["Novo Mês/Ano", "O caminho normal: abre o mês seguinte ao último."],
        ["Outro Mês/Ano", "Quando você precisa ir para uma competência específica."]],
       larguras=[4.0, 12.0])
p("O sistema sugere sempre o mês seguinte ao da última folha normal. As folhas "
  "de 13º não entram nessa conta, porque são abertas em novembro e dezembro "
  "sem fazer parte da sequência dos meses.")
atencao("A folha só anda para a frente. Se você abriu o mês errado, o caminho "
        "não é voltar: é seguir no mês certo. Em caso de necessidade real de "
        "reabrir mês antigo, fale com o suporte.")

h2("Fechar e reabrir")
tabela(["Função", "O que faz"],
       [["Fechar esta Folha Calculada", "Encerra o mês depois de conferido."],
        ["Reabrir esta Folha Calculada", "Volta a folha para digitação depois de um cálculo."],
        ["Reabrir esta Folha Fechada", "Volta atrás em um mês já encerrado."]],
       larguras=[5.4, 10.6])
atencao("Fechar a folha no Folha10 não é a mesma coisa que fechar o período no "
        "eSocial. São dois fechamentos diferentes: o daqui libera o mês "
        "seguinte, o do eSocial é o envio do evento de fechamento ao governo.")


# ============================================================== ETAPA 3
h1("Etapa 3 — Eventuais")
caminho("Menu principal › Eventuais")
p("É o módulo mais cheio do sistema, porque reúne tudo o que acontece de vez "
  "em quando com um funcionário: férias, aumento, rescisão, afastamento, "
  "faltas, exame médico e adicionais.")

h2("Férias")
caminho("Eventuais › Férias")
h3("O roteiro")
passo(1, "Lançar Férias.", "Informe quem vai sair, o período aquisitivo, as "
      "datas de gozo e se há venda de dias (abono).")
passo(2, "Lançar Movimento Férias.", "Só se houver algum lançamento específico "
      "dessa folha de férias.")
passo(3, "Calcular Férias.")
passo(4, "Recibo de Férias.", "É o documento que o funcionário assina.")
passo(5, "Memória de Cálculo.", "Use quando quiser conferir de onde saiu cada valor.")
p("Se algo estiver errado, Cancelar Férias desfaz o lançamento e você refaz.")

h3("O que o sistema já sabe sozinho")
tabela(["Faltas no período aquisitivo", "Dias de férias a que tem direito"],
       [["Até 5", "30 dias"], ["6 a 14", "24 dias"], ["15 a 23", "18 dias"],
        ["24 a 32", "12 dias"], ["Mais de 32", "Nenhum"]],
       larguras=[6.4, 9.6])
item("O funcionário tem 12 meses depois do período aquisitivo para sair de "
     "férias. Passou disso, as férias são pagas em dobro.")
item("As férias podem ser divididas em até três períodos: um de no mínimo 14 "
     "dias e os outros de no mínimo 5.")
item("O abono é a venda de até um terço dos dias.")
item("O abono e o terço sobre ele não sofrem INSS nem imposto de renda.")

h3("Acompanhamento")
p("Ainda no grupo de férias existem três listagens que ajudam a não perder "
  "prazo: Funcionários em Férias, Programação de Férias e Férias Vencidas.")
dica("Férias Vencidas é a que evita pagamento em dobro. Vale olhar uma vez por mês.")

h2("Salários")
caminho("Eventuais › Salários")
p("Alteração de Salário registra o novo salário e a data. O sistema guarda o "
  "histórico e prepara a comunicação da mudança ao eSocial. Cancelar Alteração "
  "desfaz, e o Relatório de Salários mostra o que mudou no período.")

h2("Rescisão")
caminho("Eventuais › Rescisão")
h3("O roteiro")
passo(1, "Aviso Prévio.", "Quando houver aviso. Existe também a listagem de "
      "quem está em aviso.")
passo(2, "Registrar Rescisão.", "Informe a data e o motivo do desligamento.")
passo(3, "Movimento Mês Rescisão.", "Lançamentos específicos dessa rescisão, "
      "se houver.")
passo(4, "Calcular Rescisão.")
passo(5, "TRCT.", "O termo oficial de rescisão, para impressão e assinatura.")
passo(6, "Memória de Cálculo.", "Para conferir verba por verba.")

h3("O que entra na conta")
p("O cálculo monta sozinho o saldo de salário, o 13º proporcional, as férias "
  "vencidas e proporcionais com o terço, o aviso indenizado quando for o caso, "
  "e os descontos de INSS e imposto de renda. As médias das verbas variáveis "
  "entram automaticamente, cada uma com o seu período de apuração.")
atencao("O TRCT lê o que o cálculo gravou. Calcule a rescisão antes de tentar "
        "emitir o termo, senão ele sai vazio.")

h3("Cancelar rescisão")
p("Reverte o cadastro do funcionário, desfaz o evento de desligamento ainda "
  "não enviado e cancela também o aviso prévio que deu origem a ela. Só "
  "funciona quando as três condições valem ao mesmo tempo:")
item("a folha atual está aberta;")
item("a rescisão é do mês da folha aberta;")
item("o fechamento do período no eSocial ainda não está valendo.")

h2("Contrato temporário e de experiência")
caminho("Eventuais › Contrato Temporário")
p("Registre o contrato e as prorrogações, consulte a relação dos contratos em "
  "vigor e imprima o contrato de experiência.")
dica("Logo depois de cadastrar um funcionário, o sistema já pergunta se você "
     "quer emitir o contrato de experiência. É o momento mais prático de fazer isso.")

h2("Afastamentos")
caminho("Eventuais › Afastamentos")
p("Registre o afastamento com a data de início e, quando já souber, a data de "
  "fim. Deixar o fim em branco é normal e é o caso mais comum: significa "
  "afastamento em aberto, que você encerra depois.")
tabela(["Situação", "O que o sistema faz"],
       [["Início depois da competência aberta", "Recusa. Abra o mês certo antes."],
        ["Início antes da competência aberta", "Grava, pedindo confirmação."],
        ["Fim em branco", "Afastamento em aberto."],
        ["Fim depois de hoje", "Aceita com confirmação, mas evite: se o afastamento se prolongar, vira correção no eSocial."]],
       larguras=[5.6, 10.4])
p("Quando você informa início e fim, o sistema prepara duas comunicações ao "
  "eSocial: a saída, no mês do início, e o retorno, no mês do fim. Um "
  "afastamento de 20 de julho a 5 de agosto gera uma comunicação em julho e "
  "outra em agosto.")
atencao("A fila do eSocial mostra uma competência por vez. A comunicação do "
        "mês anterior não aparece na fila do mês aberto — troque o período "
        "para encontrá-la. A mensagem de confirmação diz em qual mês cada uma ficou.")
p("Em afastamento com data antiga, o sistema já vem com a opção de NÃO "
  "comunicar ao eSocial marcada, porque afastamento antigo normalmente já foi "
  "informado, ou está sendo registrado apenas para a folha enxergar os dias "
  "parados. Você decide separadamente para a saída e para o retorno.")
p("Se o motivo for acidente ou doença, a tela pede algumas informações a mais "
  "e oferece registrar a CAT logo depois de gravar. As telas da CAT ficam no "
  "mesmo grupo.")

h2("Faltas, exame médico e adicionais")
tabela(["Grupo", "O que faz"],
       [["Faltas", "Incluir, excluir e listar as faltas do período."],
        ["Exame Médico", "Registrar o exame, alterar e listar. Alimenta a comunicação de saúde ao eSocial."],
        ["Insalubridade / Periculosidade", "Registrar o adicional do funcionário."],
        ["FAP", "O fator acidentário da empresa."]],
       larguras=[5.0, 11.0])
atencao("Se o funcionário já tem insalubridade ou periculosidade registrada "
        "aqui, não lance o adicional também como movimento fixo: ele receberia "
        "duas vezes. O sistema barra essa duplicidade.")


# ============================================================== ETAPA 4
h1("Etapa 4 — Movimento do Mês")
caminho("Menu principal › Movimento Mês")
p("É onde entra o que varia de um mês para o outro: as horas extras deste mês, "
  "as faltas deste mês, um prêmio, um desconto.")

h2("Lançar eventos")
caminho("Movimento Mês › Lançamentos › Lançar Eventos")
passo(1, "Escolha o funcionário.")
passo(2, "Escolha a verba.", "Você pode buscar pelo código ou pelo nome.")
passo(3, "Informe a quantidade ou o valor.", "Depende de como a verba foi "
      "cadastrada: em horas você informa as horas, em reais você informa o valor.")
passo(4, "Inclua.", "O lançamento aparece na lista e pode ser editado ou "
      "excluído enquanto a folha estiver aberta.")
dica("O botão Fixar mantém a verba escolhida entre um lançamento e outro. "
     "Quando você vai lançar a mesma verba para várias pessoas, isso poupa "
     "muito clique.")
p("O que você digita aqui nunca é apagado pelo recálculo. O cálculo pode "
  "acrescentar linhas, mas não mexe no que veio da sua mão.")

h2("Importações")
tabela(["Função", "O que faz"],
       [["Importar Ponto", "Traz horas extras, faltas e atrasos do sistema de ponto."],
        ["Importar Consignados", "Traz os empréstimos consignados da planilha do mês."]],
       larguras=[5.0, 11.0])
p("A importação de consignados substitui a faixa inteira de verbas de "
  "empréstimo a cada rodada. Por isso ela sempre reflete exatamente a planilha "
  "que você acabou de importar — não é preciso apagar nada antes.")

h2("Adiantamento quinzenal")
caminho("Movimento Mês › Adiantamento Quinzenal")
p("Calcule, confira pela listagem e emita o recibo. O percentual pode vir do "
  "cadastro da empresa, valendo para todos, ou ser definido funcionário por "
  "funcionário.")
tabela(["No cadastro do funcionário", "Resultado"],
       [["Campo em branco", "Usa o percentual da empresa."],
        ["Marcado “não adianta”", "Não recebe adiantamento, mesmo que a empresa tenha percentual."],
        ["Valor ou percentual preenchido", "Usa o que está ali."]],
       larguras=[5.6, 10.4])
h3("Quem foi admitido no mês")
tabela(["Dia da admissão", "Recebe?"],
       [["Do dia 1 ao 10", "Sim, proporcional aos dias trabalhados."],
        ["Do dia 11 em diante", "Não recebe."]], larguras=[4.6, 11.4])
p("Também não recebe quem estiver de férias ou afastado na primeira quinzena.")
dica("Se você já calculou e precisa refazer, o botão passa a se chamar "
     "“Recalcular esta Parcela”: ele apaga e refaz a mesma parcela, sem criar "
     "uma segunda.")


# ============================================================== ETAPA 5
h1("Etapa 5 — Movimento Fixo")
caminho("Menu principal › Movimento Fixo")
p("Movimento fixo é o lançamento que você cadastra UMA VEZ e o sistema repete "
  "todo mês. É o lugar do vale-transporte, do plano de saúde, do desconto de "
  "um empréstimo em parcelas — tudo que se repete.")

h2("Como cadastrar")
passo(1, "Escolha a verba.")
passo(2, "Escolha quem recebe.", "Um funcionário específico, pela matrícula, "
      "ou um grupo, por filtros como categoria, faixa salarial, idade ou tempo "
      "de casa.")
passo(3, "Defina a duração.", "Por número de parcelas, que para sozinho ao "
      "terminar, ou por período, com folha inicial e, se quiser, final. Sem "
      "folha final, vale por prazo indeterminado.")
passo(4, "Diga o que fazer nas férias e nos afastamentos.", "É a parte que "
      "mais influi no resultado — veja a tabela abaixo.")
dica("O movimento por grupo é reavaliado a cada folha. Quem for admitido "
     "depois, dentro do perfil, passa a receber automaticamente. É a forma "
     "prática de dar um benefício a todo mundo de um setor sem ter que "
     "lembrar de incluir cada novo funcionário.")

h2("O que acontece nas férias")
tabela(["Escolha", "Comportamento"],
       [["Não processa", "Não lança nada, mesmo que seja um dia de férias."],
        ["Integral", "Lança o valor cheio, sem proporção."],
        ["Integral se as férias começarem no mês", "Lança tudo nessa folha."],
        ["Proporcional aos dias", "Divide entre dias trabalhados e dias de férias."],
        ["Proporcional, zero nas férias", "Paga só a parte trabalhada."]],
       larguras=[6.0, 10.0])
p("Existem escolhas equivalentes para quem está afastado e para os meses de "
  "admissão e de rescisão.")

h2("Encerrar um movimento fixo: parar ou excluir")
caminho("Movimento Fixo › Lançamentos › Excluir / Parar Mov. Fixo")
tabela(["Ação", "O que faz", "Quando usar"],
       [["Parar", "Marca a última folha em que o movimento vale. O histórico fica todo preservado.",
         "Praticamente sempre. É a saída normal."],
        ["Excluir", "Apaga o movimento por completo.",
         "Só para desfazer um erro de digitação recém-cadastrado."]],
       larguras=[2.2, 7.2, 6.6])
atencao("Excluir só é permitido quando o movimento foi criado nesta folha e "
        "ainda não gerou nenhum lançamento. A trava existe para proteger o "
        "histórico: apagar algo que já foi pago apagaria a prova de um "
        "pagamento feito. De um movimento parado dá para voltar atrás; de um "
        "movimento excluído não.")

h2("A lista")
p("Por padrão você vê só os movimentos em vigência. Marque “Mostrar também os "
  "encerrados” para ver o histórico completo.")


# ============================================================== ETAPA 6
h1("Etapa 6 — Cálculo")
caminho("Menu principal › Cálculo")
p("Com tudo lançado, é aqui que a folha é apurada.")

h2("Calcular a folha do mês")
passo(1, "Verificar Inconsistências.", "Rode antes. Ela aponta problemas que "
      "estragariam o cálculo — dado faltando, situação estranha.")
passo(2, "Calcular Folha.", "Apura todos os funcionários da competência.")
passo(3, "Visualizar Cálculo.", "Confira os valores na tela.")
passo(4, "Memória de Cálculo.", "Quando algum valor não bateu, é aqui que você "
      "vê passo a passo de onde ele saiu.")
p("Cálculo Individual refaz um funcionário só — útil quando você corrigiu um "
  "lançamento e não quer rodar tudo de novo.")
dica("Pode calcular quantas vezes quiser. O cálculo refaz o que ele mesmo "
     "gerou e não apaga o que você digitou.")

h2("O que o sistema calcula sozinho")
item("Salário proporcional de quem foi admitido ou desligado no mês.")
item("Desconto de faltas.")
item("Insalubridade e periculosidade de quem tem o adicional cadastrado.")
item("Repouso remunerado sobre hora extra, adicional noturno e comissão.")
item("INSS e imposto de renda, pelas tabelas oficiais já embutidas.")
item("FGTS de quem tem direito, conforme a categoria.")
item("Desconto do adiantamento quinzenal e da pensão alimentícia.")
p("As tabelas de INSS, imposto de renda e salário mínimo já vêm dentro do "
  "sistema e são atualizadas por nós. Você não precisa configurar nada, e não "
  "há risco de calcular o mês com a tabela do ano passado.")
dica("Desde janeiro de 2026 vale a isenção do imposto de renda até R$ 5.000,00, "
     "com redução gradual até R$ 7.350,00. O sistema já aplica sozinho, em "
     "folha, férias, 13º e rescisão.")

h2("Adiantamento quinzenal")
p("O mesmo grupo aparece aqui, com o cálculo, a listagem, o recibo e a opção "
  "de informar um valor manualmente.")


# ============================================================== ETAPA 7
h1("Etapa 7 — Relatórios")
caminho("Menu principal › Relatórios")
p("Todos os relatórios saem em PDF, com o mesmo cabeçalho: a empresa, o "
  "título e a competência.")

h2("Os principais")
tabela(["Relatório", "Para que serve"],
       [["Folha de Pagamento", "O relatório completo do mês."],
        ["Contracheque", "O holerite de cada funcionário."],
        ["Relação dos Líquidos", "O que cada um recebe — é o relatório que acompanha o pagamento."],
        ["Resumo da Folha", "Os totais do mês, para conferência e contabilidade."],
        ["Relação de N Verbas", "Você escolhe quais verbas quer ver."],
        ["Ficha Financeira", "O histórico do funcionário ao longo do ano."],
        ["Lista de Funcionários", "O cadastro, com filtros de situação."]],
       larguras=[4.6, 11.4])
p("Há ainda os relatórios de cadastro (funções, verbas, dependentes, ficha de "
  "registro), os de eventos (férias, faltas, salários) e o Gerador de "
  "Relatório, para montar uma listagem do seu jeito.")

h2("Duas coisas que evitam susto")
atencao("Relatório de folha em branco quase sempre significa folha ainda não "
        "calculada. Os relatórios leem o resultado do cálculo, não os "
        "lançamentos.")
p("As verbas informativas aparecem no holerite mas não entram nos totais, e o "
  "adiantamento quinzenal aparece em bloco separado, também fora dos totais. "
  "Isso é proposital: os dois já foram considerados no lugar certo.")


# ============================================================== ETAPA 8
h1("Etapa 8 — Conexões")
caminho("Menu principal › Conexões")

h2("Pagamento bancário")
p("O sistema gera o arquivo no padrão CNAB 240 para o banco pagar a folha, em "
  "duas formas: crédito em conta e PIX. Cinco bancos são atendidos, e o "
  "arquivo aceita funcionários com conta em banco diferente do banco da "
  "empresa.")
dica("Confira os dados bancários no cadastro do funcionário antes de gerar o "
     "arquivo. Conta errada é o motivo mais comum de pagamento devolvido.")


# ============================================================== ETAPA 9
h1("Etapa 9 — eSocial")
caminho("Menu principal › eSocial")
p("O eSocial é o sistema do governo que recebe as informações trabalhistas. O "
  "Folha10 monta e envia esses arquivos para você — mas a ordem importa, e é "
  "isso que esta etapa explica.")

h2("Antes de tudo: o certificado digital")
caminho("eSocial › Certificado Digital")
p("Nada é enviado sem certificado digital. Cadastre o arquivo e a senha uma "
  "vez, e o sistema usa daí em diante. Se você transmite pelo certificado do "
  "seu contador ou de um escritório, existe a opção de procurador.")
atencao("O certificado cadastrado no seu computador não vale para o sistema na "
        "internet. Cadastre o certificado direto no site, que é de onde os "
        "envios saem.")

h2("A ordem dos envios")
p("O eSocial recebe as informações em camadas. Primeiro ele precisa conhecer a "
  "empresa e as tabelas dela; depois os trabalhadores; só então os valores do "
  "mês.")
passo(1, "Tabelas.", "Dados do empregador, estabelecimentos, rubricas e "
      "lotações. É a base de tudo, e você faz uma vez.")
passo(2, "Admissões e demais eventos do trabalhador.", "Admissão, alteração de "
      "dados, alteração de contrato, afastamento, desligamento.")
passo(3, "Remuneração do mês.", "Os valores da folha e os pagamentos.")
passo(4, "Fechamento.", "O evento que encerra a competência no governo.")

h2("A conferência automática antes de enviar a folha")
p("Ao enviar a remuneração do mês, o sistema confere sozinho se o governo já "
  "conhece tudo que aquele arquivo cita. Se faltar alguma coisa, ele NÃO envia "
  "— e explica o quê:")
tabela(["O que falta", "O que o sistema faz"],
       [["A lotação (centro de custo) ainda não foi declarada",
         "Barra o envio e já deixa a remessa pronta na fila para você transmitir."],
        ["Alguma verba usada na folha ainda não foi declarada",
         "Barra o envio, diz quais verbas são e deixa as remessas prontas na fila."],
        ["Existem outros envios pendentes (admissão, afastamento)",
         "Apenas avisa. Você decide se envia assim mesmo."]],
       larguras=[6.6, 9.4])
p("As duas primeiras barram porque o governo recusaria o arquivo de qualquer "
  "forma — e a mensagem dele não diz qual verba faltou, o que transforma a "
  "correção em adivinhação. O sistema prefere descobrir antes e já preparar o "
  "que falta.")
dica("Essa conferência foi feita pensando em quem está no primeiro mês "
     "conosco, quando ainda não há nada declarado no governo. Se aparecer para "
     "você, não é erro: é o sistema te poupando de uma rejeição.")

h2("A fila de remessas")
caminho("eSocial › Remessas › Fila de Remessas")
p("A fila mostra tudo que está pronto para enviar, agrupado pela competência. "
  "Cada linha tem a sua situação:")
tabela(["Situação", "O que significa", "O que fazer"],
       [["Pendente", "Foi criada e ainda não foi enviada.", "Enviar."],
        ["Aguardando", "Foi enviada e o governo ainda está processando.", "Clicar em Consultar daqui a pouco."],
        ["Enviado", "Aceita, com recibo.", "Nada."],
        ["Com Erro", "O governo recusou.", "Ler a mensagem, corrigir a origem e enviar de novo."]],
       larguras=[2.8, 6.8, 6.4])
atencao("A fila mostra uma competência por vez. Se você não encontra uma "
        "remessa, quase sempre ela é de outro mês — troque o período no filtro.")

h2("Conferência com o governo")
caminho("eSocial › Verificação Folha10 × eSocial")
p("Depois de enviar, essa tela compara o que o Folha10 calculou com os totais "
  "que o governo devolveu. É a forma de ter certeza de que o que está lá "
  "dentro é igual ao que você fechou aqui.")

h2("Quando o status da folha importa")
tabela(["Tipo de envio", "Exigência"],
       [["Admissão, afastamento, desligamento e as tabelas", "Podem ir a qualquer momento."],
        ["Remuneração, pagamentos e fechamento", "Exigem a folha FECHADA no Folha10."]],
       larguras=[7.4, 8.6])


# ============================================================== ETAPA 10
h1("Etapa 10 — Diversos")
caminho("Menu principal › Diversos")
p("Configurações do sistema, usuários e permissões, log de auditoria, backup "
  "e exportação de dados.")
p("O log de auditoria registra quem fez o quê e quando — útil quando mais de "
  "uma pessoa opera o sistema.")
p("Se você tem uma equipe, cadastre cada pessoa como um usuário próprio, em "
  "Cadastros › Usuários da Conta. Cada um entra com o seu CPF e a sua senha, e "
  "o log passa a mostrar quem fez cada coisa.")
p()
p("Existe ainda um card de Administrador, que aparece apenas para a equipe "
  "Folha10 — ele não faz parte do seu dia a dia.", italico=True, cor=CINZA)


# ================================================ PARTE 3 — ROTINA DO MÊS
h1("Parte 3 — A rotina do mês")
p("Este é o roteiro completo, na ordem. Se você seguir esta sequência todo "
  "mês, dificilmente vai esquecer alguma coisa.")

h2("Durante o mês, conforme acontece")
passo(1, "Admissões.", "Cadastros › Funcionário › Incluir Funcionário.")
passo(2, "Férias.", "Eventuais › Férias — lançar, calcular e emitir o recibo.")
passo(3, "Afastamentos e faltas.", "Eventuais, conforme o caso.")
passo(4, "Desligamentos.", "Eventuais › Rescisão — aviso, registro, cálculo e TRCT.")
passo(5, "Aumentos.", "Eventuais › Salários › Alteração de Salário.")
p("Cada um desses já prepara o que precisa ser comunicado ao eSocial. Vale "
  "enviar as remessas ao longo do mês, e não tudo de uma vez no fim.")

h2("Na primeira quinzena, se a empresa adianta")
passo(6, "Calcular o adiantamento.", "Movimento Mês › Adiantamento Quinzenal › Calcular.")
passo(7, "Conferir e emitir os recibos.")

h2("No fechamento do mês")
passo(8, "Lançar o movimento.", "Movimento Mês › Lançar Eventos — horas extras, "
      "faltas, prêmios, descontos. Ou importe do ponto.")
passo(9, "Conferir as inconsistências.", "Cálculo › Verificar Inconsistências.")
passo(10, "Calcular a folha.", "Cálculo › Calcular Folha.")
passo(11, "Conferir.", "Cálculo › Visualizar Cálculo e Relatórios › Resumo da Folha.")
passo(12, "Emitir os relatórios.", "Folha de Pagamento, Contracheques e Relação dos Líquidos.")
passo(13, "Gerar o pagamento.", "Conexões › CNAB 240, em conta ou PIX.")
passo(14, "Fechar a folha.", "Nova Folha › Fechar esta Folha Calculada.")
passo(15, "Enviar a remuneração ao eSocial.", "eSocial › Eventos Periódicos — "
      "remuneração, pagamentos e, por fim, o fechamento.")
passo(16, "Conferir com o governo.", "eSocial › Verificação Folha10 × eSocial.")
passo(17, "Abrir o mês seguinte.", "Nova Folha › Novo Mês/Ano.")
dica("Achou algum erro depois de calcular? Reabra a folha, corrija e calcule "
     "de novo. Isso é normal e pode ser feito quantas vezes for preciso, "
     "enquanto o mês não estiver fechado no eSocial.")


# ======================================== PARTE 4 — QUANDO ALGO DÁ ERRADO
h1("Parte 4 — Quando algo não sai como esperado")
p("As situações mais comuns e o que fazer em cada uma.")

h2("Não consigo incluir nem alterar nada")
p("A folha provavelmente está calculada ou fechada. Vá em Nova Folha e "
  "reabra. Confira também, no alto da tela, se a competência é a que você quer.")

h2("O funcionário não aparece na tela")
item("Veja o filtro de situação da tela — muitas listas começam mostrando "
     "apenas os ativos.")
item("Confira se ele foi admitido em competência posterior à que está aberta.")
item("Confira se você está na empresa certa, quando tem mais de uma.")

h2("O relatório saiu em branco")
p("A folha ainda não foi calculada. Os relatórios leem o resultado do cálculo.")

h2("O holerite saiu sem INSS, sem FGTS ou sem imposto")
p("Confira a categoria do funcionário. Estagiário não tem INSS nem FGTS; "
  "diretor e sócio, em geral, não têm FGTS. É o que mais causa esse susto.")

h2("A média das férias ou da rescisão não bateu")
p("Confira, no cadastro da verba, se ela está marcada para entrar na média. "
  "Hora extra e comissão só refletem em férias, 13º e rescisão se estiverem "
  "marcadas assim.")

h2("O funcionário recebeu o adicional duas vezes")
p("Provavelmente o adicional está no cadastro dele e também como movimento "
  "fixo. Deixe em um lugar só — o normal é no cadastro.")

h2("O eSocial recusou o envio")
passo(1, "Leia a mensagem na fila.", "Ela mostra o que o governo respondeu.")
passo(2, "Corrija na origem.", "Quase sempre é dado de cadastro: CNPJ, "
      "endereço, categoria, data.")
passo(3, "Envie de novo.")
p("Se a recusa falar em rubrica ou lotação desconhecida, é sinal de que falta "
  "declarar as tabelas antes — o sistema já cria essas remessas para você na "
  "fila.")

h2("Não encontro uma remessa na fila do eSocial")
p("A fila mostra uma competência por vez. Troque o período no filtro. "
  "Afastamento que terminou no mês seguinte, por exemplo, tem o retorno na "
  "competência do mês do fim.")

h2("Deu “erro interno” ao enviar ao eSocial")
p("Costuma ser o certificado digital cadastrado em outro lugar. Cadastre o "
  "certificado direto no site, que é de onde os envios saem.")

h2("Cadastrei um funcionário por engano")
p("Se ele foi admitido no mês da folha aberta e nada foi enviado ao eSocial, "
  "use Cadastros › Funcionário › Limpar Funcionário. Fora dessas condições, o "
  "caminho correto é a rescisão.")

h2("Ainda com dúvida")
p("Duas ajudas moram dentro do próprio sistema e são mais rápidas que este "
  "manual:")
item("O botão verde “Dúvida?”, no alto das telas, explica aquela tela.")
item("O botão “?”, no canto inferior direito, faz um tour guiado apontando "
     "cada parte da tela, na ordem de uso.")

p()
p(f"Folha10 Simples — versão {VERSAO}. Manual do Usuário.", italico=True, cor=CINZA)

os.makedirs(DESTINO, exist_ok=True)
salvar(ARQUIVO)
print("OK:", ARQUIVO)
