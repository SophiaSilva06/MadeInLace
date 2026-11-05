#!/usr/bin/env python3
"""Gate de integridade: garante que a suíte está 100% verde sem trapaça.

Uso:  python check_integrity.py [--base HEAD] [--tests tests] [args extras do pytest]

Verifica:
 1. Padrões proibidos em testes e configuração (skip, xfail, filtros, ignores).
 2. Arquivos de teste modificados/apagados em relação à base do git (para revisão).
 3. Executa a suíte COMPLETA e exige: 0 falhas, 0 erros, 0 skipped, 0 xfailed, 0 deselected.
Código de saída 0 = aprovado.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_IN_TESTS = [
    (r"pytest\.mark\.(skip|skipif|xfail)\b", "marca skip/skipif/xfail"),
    (r"pytest\.(skip|xfail)\(", "chamada pytest.skip()/xfail()"),
    (r"unittest\.(skip|skipIf|skipUnless|expectedFailure)\b", "skip/expectedFailure do unittest"),
    (r"pytest\.importorskip\(", "importorskip (esconde teste se a dependência faltar)"),
    (r"mark\.flaky|reruns\s*=", "retry/flaky para mascarar instabilidade"),
]
FORBIDDEN_IN_CONFIG = [
    (r"--deselect", "--deselect em addopts"),
    (r"(^|\s)-k\s", "filtro -k em addopts"),
    (r"--maxfail", "--maxfail em addopts"),
    (r"--reruns", "--reruns em addopts"),
    (r"collect_ignore", "collect_ignore no conftest"),
]
CONFIG_FILES = ["pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini", "conftest.py"]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def find_test_files(root: Path, tests_dir: str):
    base = root / tests_dir
    files = []
    if base.exists():
        files += list(base.rglob("test_*.py")) + list(base.rglob("*_test.py"))
    files += list(root.glob("test_*.py")) + list(root.glob("*_test.py"))
    return sorted(set(files))


def scan(files, patterns, problems):
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for rx, label in patterns:
            for m in re.finditer(rx, text, flags=re.MULTILINE):
                line = text.count("\n", 0, m.start()) + 1
                problems.append(f"{f}:{line}: {label}")


IGNORE_RX = re.compile(r"--ignore(?:-glob)?(?:=|\s+)([^\s\"',\]]+)")


def ignores_tests(path: str, tests_dir: str) -> bool:
    """True se o --ignore/--ignore-glob mira testes (e não docs, build, etc.)."""
    p = path.strip("\"'").replace("\\", "/").lstrip("./")
    td = tests_dir.strip("/")
    name = p.rsplit("/", 1)[-1]
    return (
        p == td or p.startswith(td + "/")
        or "test" in name.lower()  # test_x.py, *_test.py, **/test*, conftest-like globs
    )


def scan_ignores(files, tests_dir, problems):
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in IGNORE_RX.finditer(text):
            if ignores_tests(m.group(1), tests_dir):
                line = text.count("\n", 0, m.start()) + 1
                problems.append(f"{f}:{line}: --ignore esconde testes ({m.group(1)})")


def git_changes(base, tests_dir):
    inside = run(["git", "rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0:
        return None
    out = run(["git", "diff", "--name-status", base, "--", tests_dir, "conftest.py"])
    new = run(["git", "ls-files", "--others", "--exclude-standard", "--", tests_dir])
    return out.stdout.strip(), new.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="HEAD", help="ref do git para comparar os testes")
    ap.add_argument("--tests", default="tests", help="diretório de testes")
    a, extra = ap.parse_known_args()

    root = Path.cwd()
    problems = []

    files = find_test_files(root, a.tests)
    if not files:
        print("ERRO: nenhum arquivo de teste encontrado.")
        return 2
    scan(files, FORBIDDEN_IN_TESTS, problems)
    config = [root / c for c in CONFIG_FILES if (root / c).exists()]
    scan(config, FORBIDDEN_IN_CONFIG, problems)
    scan_ignores(config, a.tests, problems)

    print("== 1) Padrões proibidos ==")
    print("\n".join(problems) if problems else "nenhum")

    print("\n== 2) Testes modificados em relação a", a.base, "==")
    changes = git_changes(a.base, a.tests)
    if changes is None:
        print("(não é um repositório git; revise manualmente se algum teste foi enfraquecido)")
    else:
        diff, new = changes
        print(diff or "nenhuma alteração em testes existentes")
        if new:
            print("novos (não rastreados):\n" + new)
        if any(l.startswith(("M", "D", "R")) for l in diff.splitlines()):
            print("ATENÇÃO: testes existentes foram alterados/apagados. Revise o diff "
                  "(git diff) e confirme que nenhum assert foi enfraquecido; "
                  "alterações em teste exigem aprovação do usuário.")

    print("\n== 3) Suíte completa ==")
    r = run([sys.executable, "-m", "pytest", "-ra", "-p", "no:cacheprovider", *extra])
    print(r.stdout[-6000:])
    if r.stderr.strip():
        print(r.stderr[-2000:])
    summary = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    bad = [w for w in ("failed", "error", "skipped", "xfailed", "xpassed", "deselected")
           if re.search(rf"\b\d+ {w}", summary)]
    ok = r.returncode == 0 and not bad and not problems

    print("\n== Veredito ==")
    if ok:
        print("APROVADO: 100% verde, sem skips/xfails/filtros.")
        return 0
    if r.returncode != 0:
        print("REPROVADO: pytest retornou", r.returncode, "- corrija o CÓDIGO, não o teste.")
    if bad:
        print("REPROVADO: o resumo contém:", ", ".join(bad))
    if problems:
        print("REPROVADO: há padrões proibidos listados acima.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
