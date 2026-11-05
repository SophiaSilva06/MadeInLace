#!/usr/bin/env python3
"""Gerenciador de Git Worktrees para execução multi-agente isolada.

Uso:
  python tools/worktree.py add <nome-do-agente-ou-tarefa> <nome-da-branch>
  python tools/worktree.py list
  python tools/worktree.py remove <nome-do-agente-ou-tarefa>
"""
import argparse
import subprocess
import sys
from pathlib import Path

WORKTREES_DIR = Path(".worktrees")


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def add_worktree(nome: str, branch: str) -> int:
    destino = WORKTREES_DIR / nome
    if destino.exists():
        print(f"Erro: Worktree '{nome}' já existe em {destino}")
        return 1

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "worktree", "add", str(destino), "-b", branch]
    proc = run_cmd(cmd)
    if proc.returncode != 0:
        print(f"Falha ao criar worktree:\n{proc.stderr}")
        return proc.returncode

    # Copia o .env de desenvolvimento para o worktree isolado se existir
    env_orig = Path(".env")
    env_dest = destino / ".env"
    if env_orig.exists() and not env_dest.exists():
        env_dest.write_text(env_orig.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Worktree criado com sucesso em: {destino.resolve()}")
    print(f"Branch ativa: {branch}")
    return 0


def list_worktrees() -> int:
    proc = run_cmd(["git", "worktree", "list"])
    print(proc.stdout)
    return proc.returncode


def remove_worktree(nome: str, force: bool = False) -> int:
    destino = WORKTREES_DIR / nome
    cmd = ["git", "worktree", "remove", str(destino)]
    if force:
        cmd.append("--force")
    proc = run_cmd(cmd)
    if proc.returncode != 0:
        print(f"Falha ao remover worktree:\n{proc.stderr}")
        return proc.returncode
    print(f"Worktree '{nome}' removido com sucesso.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Git Worktrees Helper para Agentes")
    sub = parser.add_subparsers(dest="acao", required=True)

    add_parser = sub.add_parser("add")
    add_parser.add_argument("nome", help="Nome identificador do worktree (ex: agente-catalogo)")
    add_parser.add_argument("branch", help="Nome da branch para a tarefa (ex: feat/catalogo)")

    sub.add_parser("list")

    rm_parser = sub.add_parser("remove")
    rm_parser.add_argument("nome", help="Nome do worktree a remover")
    rm_parser.add_argument("--force", action="store_true", help="Forçar remoção")

    args = parser.parse_args()

    if args.acao == "add":
        return add_worktree(args.nome, args.branch)
    elif args.acao == "list":
        return list_worktrees()
    elif args.acao == "remove":
        return remove_worktree(args.nome, args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
