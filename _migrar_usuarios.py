# -*- coding: utf-8 -*-
"""
Migra cada cliente do tab_cliente para um usuario TITULAR em tab_usuario.

O login passou a ler tab_usuario em vez de tab_cliente. Sem esta migracao
ninguem consegue entrar. Rode DEPOIS de criar a tabela com o
_criar_tab_usuario.sql e ANTES de subir o app.py novo.

Uso:
    python _migrar_usuarios.py             # SIMULA, nao grava (padrao)
    python _migrar_usuarios.py --gravar    # grava de verdade

E idempotente: CPF que ja existe em tab_usuario e pulado, entao rodar de novo
so completa o que faltou.
"""
import os, sys, argparse
import requests
import urllib3
from dotenv import load_dotenv

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = os.path.dirname(os.path.abspath(__file__))
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv(os.path.join(BASE, ".env"))

URL = os.getenv("SUPABASE_URL", "").rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY") or ""
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
     "Content-Type": "application/json"}


def get(tabela, **params):
    r = requests.get(f"{URL}/rest/v1/{tabela}", params=params, headers=H,
                     verify=False, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"GET {tabela} -> {r.status_code}: {r.text[:300]}")
    return r.json()


def insert(tabela, linhas):
    r = requests.post(f"{URL}/rest/v1/{tabela}",
                      headers={**H, "Prefer": "return=representation"},
                      json=linhas, verify=False, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"POST {tabela} -> {r.status_code}: {r.text[:300]}")
    return r.json()


def so_numeros(v):
    return "".join(c for c in str(v or "") if c.isdigit())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true",
                    help="Grava de verdade (sem isso apenas simula)")
    args = ap.parse_args()

    if not URL or not KEY:
        print("[ABORTADO] SUPABASE_URL/KEY nao encontrados no .env")
        sys.exit(1)

    clientes = get("tab_cliente",
                   select="id_cliente,cpf,nome,celular,email,senha",
                   order="id_cliente")
    try:
        ja = get("tab_usuario", select="cpf,id_cliente,titular")
    except RuntimeError as e:
        print(f"[ABORTADO] tab_usuario nao encontrada — rode antes o "
              f"_criar_tab_usuario.sql no SQL Editor do Supabase.\n   {e}")
        sys.exit(1)

    cpfs_existentes = {str(u.get("cpf") or "") for u in ja}

    novos, pulados, sem_cpf = [], [], []
    for c in clientes:
        cpf = so_numeros(c.get("cpf"))
        if len(cpf) != 11:
            sem_cpf.append(c)
            continue
        if cpf in cpfs_existentes:
            pulados.append(c)
            continue
        novos.append({
            "id_cliente": c.get("id_cliente"),
            "cpf":        cpf,
            "nome":       (c.get("nome") or "").strip()[:80] or "TITULAR",
            "senha":      (c.get("senha") or "").strip() or None,
            "situacao":   "A",
            "titular":    "S",
            "celular":    so_numeros(c.get("celular"))[:11] or None,
            "email":      (c.get("email") or "").strip()[:120] or None,
        })

    print("=" * 66)
    print(f"Clientes em tab_cliente ....... {len(clientes)}")
    print(f"Usuarios ja em tab_usuario .... {len(ja)}")
    print(f"A criar como TITULAR .......... {len(novos)}")
    print(f"Pulados (CPF ja e usuario) .... {len(pulados)}")
    if sem_cpf:
        print(f"SEM CPF valido (ficam de fora): {len(sem_cpf)}")
        for c in sem_cpf:
            print(f"   id_cliente={c.get('id_cliente')} cpf={c.get('cpf')!r} "
                  f"nome={c.get('nome')!r}")
    sem_senha = [n for n in novos if not n["senha"]]
    if sem_senha:
        print(f"ATENCAO: {len(sem_senha)} sem senha — nao vao conseguir entrar:")
        for n in sem_senha:
            print(f"   {n['cpf']} {n['nome']}")
    print(f"Modo .......................... "
          f"{'GRAVACAO REAL' if args.gravar else 'SIMULACAO (use --gravar)'}")
    print("=" * 66)

    for n in novos[:10]:
        print(f"   {n['cpf']}  {n['nome'][:40]:<40} cliente={n['id_cliente']}")
    if len(novos) > 10:
        print(f"   ... e mais {len(novos) - 10}")

    if not args.gravar:
        print("\nNada foi gravado. Rode com --gravar para efetivar.")
        return
    if not novos:
        print("\nNada a fazer — todos os clientes ja tem usuario titular.")
        return

    criados = 0
    for i in range(0, len(novos), 100):          # em lotes, para nao estourar
        criados += len(insert("tab_usuario", novos[i:i + 100]))
    print(f"\nOK: {criados} usuario(s) titular(es) criado(s).")

    # Conferencia: todo cliente com CPF valido tem que ter usuario agora
    depois = {str(u.get("cpf") or "") for u in get("tab_usuario", select="cpf")}
    faltando = [c for c in clientes
                if len(so_numeros(c.get("cpf"))) == 11
                and so_numeros(c.get("cpf")) not in depois]
    if faltando:
        print(f"[ALERTA] {len(faltando)} cliente(s) continuam sem usuario:")
        for c in faltando:
            print(f"   id_cliente={c.get('id_cliente')} cpf={c.get('cpf')}")
    else:
        print("Conferencia OK: todo cliente com CPF valido tem usuario titular.")


if __name__ == "__main__":
    main()
