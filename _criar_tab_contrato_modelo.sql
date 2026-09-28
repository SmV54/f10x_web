-- =====================================================================
-- tab_contrato_modelo — "Meu Contrato" de experiência, um por CLIENTE
-- Rodar no Supabase -> SQL Editor ANTES de subir a versão que usa a tabela.
--
-- modelo = o contrato em JSON (formato descrito em modelos_contrato.py).
-- Sem linha para o cliente = ele só tem o contrato padrão do sistema.
-- A linha do cliente 30 é o contrato do BC que estava fixo no código desde
-- 04/09/2026 — mesmo texto e data da admissão; com testemunhas, como o
-- próprio fecho do contrato diz (SMV 28/09/2026).
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.tab_contrato_modelo (
    id_cliente    integer PRIMARY KEY,
    modelo        jsonb       NOT NULL,
    alterado_em   timestamptz DEFAULT now(),
    alterado_por  varchar(14)                   -- cpf de quem gravou
);

-- O app lê e grava com a chave anon, como nas demais tabelas do sistema.
ALTER TABLE public.tab_contrato_modelo DISABLE ROW LEVEL SECURITY;

INSERT INTO public.tab_contrato_modelo (id_cliente, modelo, alterado_por)
VALUES (30, '{
  "titulo": "CONTRATO INDIVIDUAL DE TRABALHO A TÍTULO DE EXPERIÊNCIA",
  "cabecalho": [
    "**EMPREGADOR:** {razao}, inscrita no CNPJ nº {cnpj}, com sede à {endereco_prosa}.",
    "**EMPREGADO:** {nome}, CPF nº {cpf}, matrícula nº {matricula_fmt}."
  ],
  "preambulo": "Por este instrumento particular, as partes acima identificadas firmam o presente contrato individual de trabalho, em caráter de experiência, nos termos dos artigos 443, 445 e 451 da Consolidação das Leis do Trabalho – CLT, mediante as seguintes condições:",
  "clausulas": [
    {
      "titulo": "DA FUNÇÃO E REMUNERAÇÃO",
      "texto": "O EMPREGADO exercerá a função de **{funcao}** (CBO {cbo}), desempenhando também as demais atribuições que lhe forem correlatas ou que com ela guardarem afinidade. A remuneração mensal será de **R$ {salario}** ({salario_extenso}), paga mensalmente, autorizando o EMPREGADO a EMPREGADORA a efetuar os depósitos dos salários e demais vencimentos em instituição bancária de sua escolha."
    },
    {
      "titulo": "DA JORNADA DE TRABALHO",
      "texto": "A jornada de trabalho será {jornada_prosa}. A jornada poderá ser alterada pela EMPREGADORA de acordo com as necessidades dos serviços, respeitados os limites legais."
    },
    {
      "tipo": "prazo",
      "titulo": "DO PRAZO DE EXPERIÊNCIA"
    },
    {
      "titulo": "DA CONTINUIDADE DO CONTRATO",
      "texto": "Permanecendo o EMPREGADO a serviço da EMPREGADORA após o término do período de experiência, o contrato passará a vigorar por prazo indeterminado, permanecendo válidas as demais condições aqui estabelecidas."
    },
    {
      "titulo": "DAS OBRIGAÇÕES DO EMPREGADO",
      "texto": "O EMPREGADO compromete-se a executar suas atividades com dedicação, zelo e lealdade, cumprir o regulamento interno da EMPREGADORA, as instruções de sua administração e as ordens de seus superiores hierárquicos, bem como observar as normas de segurança e demais procedimentos aplicáveis ao trabalho."
    },
    {
      "titulo": "DA COMPENSAÇÃO E PRORROGAÇÃO DE HORAS",
      "texto": "O EMPREGADO compromete-se a trabalhar em regime de compensação e prorrogação de horas, inclusive em período noturno, sempre que as necessidades do serviço assim exigirem, observadas as formalidades e os limites legais."
    },
    {
      "titulo": "DOS DESCONTOS",
      "texto": "A EMPREGADORA fica autorizada a descontar da remuneração ou de outros direitos de natureza trabalhista do EMPREGADO as contribuições legais e/ou convencionadas, adiantamentos e empréstimos concedidos, valores devidamente autorizados e eventuais prejuízos ou danos causados ao patrimônio da EMPREGADORA, quando legalmente cabíveis."
    },
    {
      "titulo": "DAS TRANSFERÊNCIAS",
      "texto": "O EMPREGADO concorda, para os fins legais, inclusive nos termos do artigo 469 da CLT, em ser transferido para outro estabelecimento da EMPREGADORA, situado nesta ou em outra localidade, quando atendidos os requisitos legais."
    },
    {
      "titulo": "DAS MODIFICAÇÕES",
      "texto": "Durante a vigência do contrato poderão ser realizadas modificações de salário, função, cargo ou horário necessárias à adaptação ao emprego, desde que não resultem em prejuízo ao EMPREGADO e sejam observadas as disposições legais."
    },
    {
      "titulo": "DAS INVENÇÕES E RESULTADOS DO TRABALHO",
      "texto": "As invenções, criações ou resultados decorrentes diretamente das atribuições do EMPREGADO e realizados com utilização das instalações, equipamentos ou recursos da EMPREGADORA observarão a legislação aplicável e as disposições internas da empresa."
    },
    {
      "titulo": "DA RESCISÃO ANTECIPADA",
      "texto": "Aplicam-se ao presente contrato as normas relativas aos contratos por prazo determinado, observando-se, em caso de rescisão antecipada, as disposições legais pertinentes, inclusive os artigos 482 e 483 da CLT, conforme o caso."
    },
    {
      "titulo": "DA LGPD E PROTEÇÃO DE DADOS",
      "texto": "A EMPREGADORA compromete-se a observar a Lei Federal nº 13.709/2018 (Lei Geral de Proteção de Dados – LGPD), adotando medidas técnicas e administrativas destinadas à proteção dos dados pessoais do EMPREGADO. O EMPREGADO declara estar ciente de que seus dados poderão ser tratados, armazenados e compartilhados com terceiros quando necessário ao cumprimento das obrigações legais, trabalhistas, previdenciárias, contratuais e administrativas da relação de emprego, observadas as bases legais aplicáveis."
    },
    {
      "titulo": "DO SIGILO",
      "texto": "A EMPREGADORA e o EMPREGADO obrigam-se a manter sigilo sobre as informações de que tenham conhecimento em razão da relação de trabalho, utilizando-as exclusivamente para as finalidades relacionadas ao contrato e às atividades profissionais."
    },
    {
      "titulo": "DAS DISPOSIÇÕES FINAIS",
      "texto": "Aplicam-se a este contrato todas as normas trabalhistas vigentes relativas aos contratos por prazo determinado e de experiência. Vencido o período experimental e permanecendo o EMPREGADO prestando serviços à EMPREGADORA, o contrato será convertido em prazo indeterminado, mantidas as demais condições contratadas."
    }
  ],
  "fecho": "E, por estarem de pleno acordo, as partes assinam o presente instrumento em 02 (duas) vias de igual teor e para o mesmo fim, na presença de duas testemunhas.",
  "data": "admissao",
  "testemunhas": true
}'::jsonb, 'migracao')
ON CONFLICT (id_cliente) DO NOTHING;

-- Conferência: deve voltar 1 linha, cliente 30, 14 cláusulas.
SELECT id_cliente, jsonb_array_length(modelo->'clausulas') AS clausulas, alterado_em
  FROM public.tab_contrato_modelo;
