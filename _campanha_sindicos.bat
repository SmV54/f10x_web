@echo off
REM Retomada da campanha de WhatsApp dos condominios (fonte coteibem).
REM Chamado pelo Agendador de Tarefas do Windows.
REM O proprio script respeita a janela (9h-17h, 2a a 6a) e pula quem ja recebeu.
REM
REM O python roda em um CONSOLE PROPRIO (start ... cmd /c). Rodando no mesmo
REM console da tarefa, um Ctrl+C ou o fechamento daquela janela matava o
REM processo no meio da espera de 12 minutos - foi o que derrubou as duas
REM execucoes de 06/08/2026 (o .err terminava em ^C, resultado 0xC000013A).
REM Com console proprio, o .bat termina na hora e a campanha segue sozinha.
REM
REM Isso NAO substitui rodar com o usuario desconectado: para isso a tarefa
REM precisa de LogonType S4U ("executar estando o usuario conectado ou nao"),
REM que exige PowerShell elevado.
cd /d C:\folha10-simples
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set HOJE=%%c%%b%%a

REM Trava simples contra duas campanhas ao mesmo tempo. E o melhor esforco: a
REM protecao de verdade contra mensagem repetida esta no proprio script (log
REM CSV + coluna DataUltimaMensagem), que pula quem ja recebeu.
tasklist /fi "windowtitle eq Campanha Condominios*" 2>nul | find /i "cmd.exe" >nul
if not errorlevel 1 (
    echo Campanha ja esta rodando - nada a fazer.
    exit /b 0
)

start "Campanha Condominios" /min cmd /c "python enviar_whatsapp_sindicos.py --fonte coteibem --intervalo 720 1>> _saida_condominios_%HOJE%.log 2>> _saida_condominios_%HOJE%.err"
