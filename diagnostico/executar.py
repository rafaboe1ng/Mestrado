"""Linha de comando do diagnostico: imprime, por etapa, o que recebeu, o que entregou e, se
falhou, por onde comecar. Sai com codigo 1 se alguma etapa falhou."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from diagnostico.etapas import diagnosticar

RAIZ = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="diagnostico por etapa sobre um job")
    ap.add_argument("--dados", default=str(RAIZ / "dados" / "sintetico"))
    ap.add_argument("--job", default=None, help="job alvo (padrao: primeiro job de avaliacao)")
    args = ap.parse_args()
    rel = diagnosticar(args.dados, args.job)
    falhou = False
    for r in rel:
        status = "OK " if not r["erros"] else "ERR"
        print(f"[{status}] {r['etapa']}")
        print(f"      recebeu : {r['recebeu']}")
        if r["entregou"] is not None:
            print(f"      entregou: {r['entregou']}")
        for e in r["erros"]:
            falhou = True
            print(f"      erro    : {e}")
            print(f"      comece por: {r['se_falhar']}")
    print("resultado:", "FALHOU" if falhou else "todas as etapas passaram")
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
