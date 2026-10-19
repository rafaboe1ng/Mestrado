"""Proveniencia de resultados: todo numero da documentacao nasce aqui.

``registrar(experimento, resultado, comando, dados)`` grava em ``resultados/`` um JSON com:
comando, commit (hash, branch, se havia alteracao nao commitada), versoes (python, numpy, so),
hash dos dados usados, numero da execucao sobre esses mesmos dados e se ela vale como
"fora da amostra" (so a primeira vale; CONTRIBUTING, regra 6).
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
PASTA_RESULTADOS = RAIZ / "resultados"


def _git(*args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except Exception:
        return None


def info_git() -> dict:
    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    return {
        "commit": commit,
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "sujo": bool(status) if status is not None else None,
        "arquivos_nao_commitados": status.splitlines() if status else [],
    }


def versoes() -> dict:
    return {"python": sys.version.split()[0], "numpy": np.__version__, "plataforma": platform.platform()}


def hash_dados(caminhos) -> dict:
    """SHA-256 do conteudo (e do caminho relativo) de todos os arquivos sob os caminhos dados."""
    h = hashlib.sha256()
    arquivos: list[str] = []
    for c in caminhos:
        c = Path(c)
        itens = sorted(p for p in c.rglob("*") if p.is_file()) if c.is_dir() else [c]
        for p in itens:
            rel = p.relative_to(RAIZ).as_posix() if p.is_relative_to(RAIZ) else p.name
            h.update(rel.encode("utf-8"))
            h.update(p.read_bytes())
            arquivos.append(rel)
    return {"sha256": h.hexdigest(), "n_arquivos": len(arquivos), "caminhos": [str(Path(c)) for c in caminhos]}


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if dataclasses.is_dataclass(o):
        return dataclasses.asdict(o)
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def registrar(experimento: str, resultado: dict, comando: str | None = None, dados=(), pasta: Path = PASTA_RESULTADOS) -> Path:
    agora = dt.datetime.now().astimezone()
    git = info_git()
    dh = hash_dados(dados) if dados else None
    pasta.mkdir(parents=True, exist_ok=True)
    mesma_base = 0
    for p in pasta.glob(f"{experimento}__*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if dh is not None and (d.get("dados") or {}).get("sha256") == dh["sha256"]:
            mesma_base += 1
    avisos = []
    if git["commit"] is None:
        avisos.append("sem repositorio git: resultado nao esta ligado a um commit")
    elif git["sujo"]:
        avisos.append("havia alteracoes nao commitadas: resultado nao e reprodutivel a partir do commit")
    registro = {
        "experimento": experimento,
        "executado_em": agora.isoformat(timespec="seconds"),
        "comando": comando or " ".join(sys.argv),
        "git": git,
        "versoes": versoes(),
        "dados": dh,
        "execucao_numero_para_estes_dados": mesma_base + 1,
        "vale_como_fora_da_amostra": mesma_base == 0,
        "avisos": avisos,
        "resultado": resultado,
    }
    caminho = pasta / f"{experimento}__{agora.strftime('%Y%m%dT%H%M%S')}.json"
    caminho.write_text(json.dumps(registro, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    return caminho


def ultimo_resultado(experimento: str, pasta: Path = PASTA_RESULTADOS) -> dict | None:
    candidatos = sorted(pasta.glob(f"{experimento}__*.json"))
    if not candidatos:
        return None
    return json.loads(candidatos[-1].read_text(encoding="utf-8"))
