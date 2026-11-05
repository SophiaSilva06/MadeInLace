#!/usr/bin/env bash
# audit_deps.sh - audita dependencias Python e JS do projeto com as ferramentas disponiveis.
# Uso: bash audit_deps.sh [diretorio-do-projeto]   (padrao: diretorio atual)
# Saida: relatorio no terminal. Codigo de saida 1 se alguma ferramenta reportar vulnerabilidades.
# Importante: precisa de rede para consultar as bases de vulnerabilidades. Sem rede, o resultado
# NAO significa "sem vulnerabilidades"; reporte a lacuna ao usuario.

cd "${1:-.}" || exit 2
STATUS=0
RAN=0

have() { command -v "$1" >/dev/null 2>&1; }
section() { printf '\n=== %s ===\n' "$1"; }

# ---------- Python ----------
PYFILES=$(ls requirements*.txt 2>/dev/null)
if [ -n "$PYFILES" ] || [ -f pyproject.toml ] || [ -f poetry.lock ] || [ -f Pipfile.lock ] || [ -f uv.lock ]; then
  section "Python"
  if have pip-audit; then
    RAN=1
    for f in $PYFILES; do
      echo "-- pip-audit -r $f"
      pip-audit -r "$f" --desc || STATUS=1
    done
    if [ -z "$PYFILES" ]; then
      echo "-- pip-audit (ambiente/pyproject)"
      pip-audit --desc || STATUS=1
    fi
  else
    echo "pip-audit nao encontrado. Instale: pip install pip-audit"
  fi
  # Checagens de higiene
  for f in $PYFILES; do
    if grep -nE '^[A-Za-z0-9_.\-]+\s*(>=|>|~=)?\s*[0-9]' "$f" >/dev/null 2>&1 && ! grep -qE '==|--hash' "$f"; then
      echo "AVISO: $f sem versoes fixadas (==) nem hashes. Use pip-compile --generate-hashes."
    fi
    grep -nE '^\s*(git\+|https?://)' "$f" && echo "AVISO: $f instala de URL/git; fixe commit e verifique a origem."
    grep -nE -- '--extra-index-url' "$f" && echo "AVISO: --extra-index-url favorece dependency confusion."
  done
fi

# ---------- JavaScript ----------
if [ -f package.json ]; then
  section "JavaScript/TypeScript"
  if [ -f package-lock.json ] && have npm; then
    RAN=1; echo "-- npm audit --audit-level=high"; npm audit --audit-level=high || STATUS=1
  elif [ -f pnpm-lock.yaml ] && have pnpm; then
    RAN=1; echo "-- pnpm audit"; pnpm audit --audit-level high || STATUS=1
  elif [ -f yarn.lock ] && have yarn; then
    RAN=1; echo "-- yarn audit"; yarn audit --level high || STATUS=1
  else
    echo "AVISO: sem lockfile ou gerenciador disponivel; commite o lockfile e use 'npm ci'."
  fi
fi

# ---------- Multi-ecossistema e containers ----------
if have osv-scanner; then
  section "osv-scanner"
  RAN=1; osv-scanner -r . || STATUS=1
fi
if [ -f Dockerfile ] && have trivy; then
  section "trivy config (Dockerfile/IaC)"
  RAN=1; trivy config --severity HIGH,CRITICAL . || STATUS=1
fi

section "Resumo"
if [ "$RAN" -eq 0 ]; then
  echo "NENHUMA ferramenta de auditoria executou (nao instaladas ou sem manifestos)."
  echo "Nao conclua que nao ha vulnerabilidades. Recomende pip-audit, npm audit e osv-scanner no CI."
  exit 3
fi
[ "$STATUS" -eq 0 ] && echo "Nenhuma vulnerabilidade reportada pelas ferramentas executadas (confira se houve erro de rede acima)." \
                    || echo "Vulnerabilidades ou avisos reportados: avalie alcance e versao corrigida (ver references/secrets-and-supply-chain.md)."
exit $STATUS
