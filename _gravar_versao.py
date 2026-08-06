"""Grava versaoxxx.txt com a data/hora de Brasilia.

Uso:  python _gravar_versao.py

A versao e' carimbo de quando o codigo mudou, entao tem que sair do relogio,
nunca digitada a mao — foi assim que o arquivo passou o dia 06/08/2026 com
horas inventadas, algumas 4h adiantadas.

Usa a MESMA regra do _agora_brasilia() do app.py: UTC-3 fixo, sem horario de
verao (extinto em 2019). Assim o carimbo sai igual rodando aqui ou no Render,
que roda em UTC.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

ARQ = Path(__file__).with_name("versaoxxx.txt")


def agora_brasilia():
    return (datetime.now(timezone.utc) - timedelta(hours=3)).replace(tzinfo=None)


def main():
    versao = agora_brasilia().strftime("%Y%m%d-%H%M")
    anterior = ARQ.read_text(encoding="utf-8").strip() if ARQ.exists() else "(nova)"
    ARQ.write_text(versao + "\n", encoding="utf-8")
    print(f"versaoxxx.txt: {anterior} -> {versao}")


if __name__ == "__main__":
    main()
