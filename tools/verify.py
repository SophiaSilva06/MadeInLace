#!/usr/bin/env python3
"""Verificação determinística: ruff -> mypy -> pytest. Imprime só coordenadas e o código de saída.

Uso:
  python tools/verify.py                                  # tudo, suíte completa (homologação)
  python tools/verify.py --alvo app/x.py --testes tests/test_x.py::test_a   # iteração

Saída (stdout), uma linha por erro, ordenada por arquivo, linha, coluna e código:
  ESTAGIO arquivo:linha:coluna CODIGO mensagem
Última linha, sempre:  EXIT <n>
  0 = tudo verde | 1 = falha de código (para no primeiro estágio que falha) | 2 = não verificável
Só homologa (EXIT 0 em rodada completa) sem --alvo/--testes; com eles a linha final é EXIT 0 PARCIAL.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUFF = re.compile(r"^(?P<f>[^\s:][^:]*):(?P<l>\d+):(?P<c>\d+): (?P<k>[A-Z]+\d+|invalid-syntax) ?(?P<m>.*)$")
MYPY = re.compile(r"^(?P<f>[^\s:][^:]*):(?P<l>\d+):(?:(?P<c>\d+):)? error: (?P<m>.*?)(?:  \[(?P<k>[\w-]+)\])?$")
HEAD = re.compile(r"^_{2,} (?P<n>.+?) _{2,}$")
FRAME = re.compile(r"^(?P<f>[^\s:][^:]*):(?P<l>\d+): (?:in |\w*Error|$)")
FAILED = re.compile(r"^(?:FAILED|ERROR) (?P<id>\S+)(?: - (?P<m>.*))?$")
LIB = ("site-packages", "/lib/python", "\\lib\\python", "_pytest")
Item = tuple[str, str, int, int, str, str]  # estágio, arquivo, linha, coluna, código, mensagem


def linhas(txt: str) -> list[str]:
    return [ANSI.sub("", s).rstrip() for s in txt.splitlines()]


def p_ruff(txt: str) -> list[Item]:
    return [("RUFF", m["f"], int(m["l"]), int(m["c"]), m["k"], m["m"]) for s in linhas(txt) if (m := RUFF.match(s))]


def p_mypy(txt: str) -> list[Item]:
    return [("MYPY", m["f"], int(m["l"]), int(m["c"] or 0), m["k"] or "mypy", m["m"])
            for s in linhas(txt) if (m := MYPY.match(s))]


def p_pytest(txt: str) -> list[Item]:
    ls = linhas(txt)
    blocos: dict[str, dict] = {}
    atual: dict | None = None
    for s in ls:
        if (h := HEAD.match(s)):
            atual = blocos.setdefault(h["n"], {"fr": [], "e": []})
        elif s.startswith("=") and ("short test summary" in s or "warnings summary" in s):
            atual = None
        elif atual is not None:
            if (f := FRAME.match(s)) and not any(x in f["f"] for x in LIB):
                atual["fr"].append((f["f"], int(f["l"])))
            elif s.startswith("E  ") and len(atual["e"]) < 3:
                atual["e"].append(s[1:].strip())
    saida: list[Item] = []
    for m in filter(None, (FAILED.match(s) for s in ls)):
        nome = m["id"].split("::")[-1].split("[")[0]
        b = next((v for k, v in blocos.items() if nome in k or k.startswith("ERROR collecting")), None)
        arq, lin = b["fr"][-1] if b and b["fr"] else (m["id"].split("::")[0], 0)
        msg = " | ".join(b["e"]) if b and b["e"] else (m["m"] or "falhou")
        saida.append(("PYTEST", arq, lin, 0, m["id"], msg))
    return saida


def rodar(cmd: list[str], timeout: int) -> tuple[int, str]:
    env = {**os.environ, "NO_COLOR": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, ""
    return p.returncode, f"{p.stdout}\n{p.stderr}"


def mypy_configurado(raiz: Path) -> bool:
    if (raiz / "mypy.ini").exists() or (raiz / ".mypy.ini").exists():
        return True
    for nome, marca in (("pyproject.toml", "[tool.mypy]"), ("setup.cfg", "[mypy]"), ("tox.ini", "[mypy]")):
        arq = raiz / nome
        if arq.exists() and marca in arq.read_text(encoding="utf-8", errors="ignore"):
            return True
    return False


def banco_inseguro() -> str | None:
    for var in ("DATABASE_URL", "DB_NAME", "MYSQL_DATABASE"):
        v = os.environ.get(var)
        if v and "_test" not in v.lower():
            return var
    return None


def emitir(itens: list[Item], estagio: str, bruto: str, limite: int) -> None:
    if not itens:  # saída não reconhecida: nunca engolir a falha
        itens = [(estagio, "?", 0, 0, "SAIDA_NAO_RECONHECIDA", " ".join(linhas(bruto)[-3:])[:200])]
    ordenados = sorted(set(itens), key=lambda i: (i[1], i[2], i[3], i[4]))
    for e, f, ln, c, k, m in ordenados[:limite]:
        print(f"{e} {f}:{ln}" + (f":{c}" if c else "") + f" {k} {m}".rstrip())
    if len(ordenados) > limite:
        print(f"OMITIDOS {len(ordenados) - limite}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alvo", nargs="*", default=["."])
    ap.add_argument("--testes", nargs="*", default=[])
    ap.add_argument("--max-itens", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=900, help="segundos por estágio")
    a = ap.parse_args()
    raiz = Path.cwd()
    scripts_dir = str(Path(sys.executable).parent)
    if scripts_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = scripts_dir + os.pathsep + os.environ.get("PATH", "")

    if (var := banco_inseguro()):
        print(f"BANCO_NAO_TESTE {var}\nEXIT 2")
        return 2
    usa_mypy = mypy_configurado(raiz)
    faltam = [t for t in ("ruff", "pytest", *(("mypy",) if usa_mypy else ())) if shutil.which(t) is None]
    if faltam:
        print(f"FERRAMENTA_AUSENTE {' '.join(faltam)}\nEXIT 2")
        return 2

    estagios = [("RUFF", ["ruff", "check", "--output-format=concise", "--no-cache", *a.alvo], p_ruff)]
    if usa_mypy:
        estagios.append(("MYPY", ["mypy", "--show-column-numbers", "--show-error-codes", "--no-error-summary",
                                  "--no-pretty", "--no-color-output", *a.alvo], p_mypy))
    estagios.append(("PYTEST", ["pytest", "-q", "--tb=short", "-p", "no:cacheprovider", "--color=no",
                                "-rfE", *a.testes], p_pytest))
    for nome, cmd, parser in estagios:
        cod, bruto = rodar(cmd, a.timeout)
        if cod == 124:
            print(f"{nome} TIMEOUT {a.timeout}s\nEXIT 2")
            return 2
        if cod != 0:
            emitir(parser(bruto), nome, bruto, a.max_itens)
            print("EXIT 1")
            return 1
    parcial = a.alvo != ["."] or bool(a.testes)
    print("EXIT 0" + (" PARCIAL" if parcial else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
