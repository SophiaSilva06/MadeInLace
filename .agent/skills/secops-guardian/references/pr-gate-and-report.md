# Gate de PR: relatório, checklist e automação

Conteúdo: Formato do relatório · Exemplo de achado · Checklist de liberação · Workflow de CI (GitHub Actions) · pre-commit · Proteção de branch

---

## Formato do relatório

Use sempre esta estrutura (adapte a largura, mantenha as seções). Escreva no idioma do usuário.

```markdown
# Auditoria de Segurança — <PR/branch/commit>

**Veredito:** 🔴 BLOQUEAR | 🟡 APROVAR COM RESSALVAS | 🟢 APROVAR
**Escopo auditado:** <arquivos/linhas, base...head> · **Linhas adicionadas/alteradas:** N
**Verificações executadas:** ✅ revisão linha a linha · ✅/⚠️ scan de segredos · ✅/⚠️ auditoria de dependências · ✅/⚠️ SAST
**Limitações:** <o que não foi possível verificar e por quê, ex.: sem rede para pip-audit>

## Resumo
2–4 frases: o que o PR faz, o maior risco, o que precisa mudar para liberar.

## Achados
| # | Sev. | Categoria | Local | Resumo |
|---|---|---|---|---|
| 1 | CRÍTICA | A05 Injeção · CWE-89 | api/orders.py:42 | SQL por f-string com `sort` do usuário |

### #1 — <título curto> (CRÍTICA)
- **Onde:** `arquivo:linha`
- **Categoria:** OWASP A05:2025 · CWE-89
- **Caminho do dado:** `request.GET["sort"]` → `build_query()` → `cursor.execute(f"... ORDER BY {sort}")`
- **Impacto:** leitura/alteração arbitrária do banco por qualquer usuário autenticado.
- **Prova de conceito mínima (ambiente de teste):** `?sort=id;SELECT pg_sleep(5)--` provoca atraso de 5 s.
- **Correção:**
  ```python
  ORDENAVEIS = {"id": "id", "data": "created_at"}
  col = ORDENAVEIS.get(sort, "id")
  cur.execute(f"SELECT ... ORDER BY {col}")      # col vem de allowlist, nunca da entrada
  ```
- **Como validar:** teste automatizado que envia `sort` malicioso e espera `400`/ordenação padrão.

## Segredos
Nenhum encontrado | ou lista mascarada (`AKIA****…`) + ação de rotação.

## Dependências
| Pacote | Antes → Depois | Situação | Ação |
|---|---|---|---|

## Ressalvas e dívida de segurança (MÉDIA/BAIXA)
Cada item com sugestão de issue e prazo.

## Pontos positivos
Controles bem aplicados (reforça boas práticas e dá contexto de que a revisão foi equilibrada).

## Próximos passos
1. Corrigir #1 e #2 → 2. Rotacionar a chave → 3. Reenviar para reauditoria das linhas alteradas.
```

**Regras de redação:** cite `arquivo:linha`; mascare segredos (`AKIA****`); correções em código pronto para colar; ordene por severidade; sem alarmismo nem jargão desnecessário (explique a sigla na primeira vez); se não há achado, diga o que foi verificado, pois "tudo ok" sem lastro não ajuda ninguém. Se o PR for pequeno e limpo, o relatório pode ser curto: veredito, o que foi verificado e limitações.

## Checklist de liberação de PR

Marque cada item como ✅ verificado, ❌ falhou, ⚠️ não verificável (explique).

**Código**
- [ ] Toda linha nova/alterada lida; fluxo source→sink dos pontos de entrada novos traçado
- [ ] Sem injeção (SQL/comando/template/NoSQL/HTML) — tudo parametrizado ou com allowlist
- [ ] Autenticação e **autorização por objeto** em toda rota/ação nova; deny-by-default
- [ ] Entrada validada por esquema no servidor; campos desconhecidos rejeitados
- [ ] Saída com escape contextual; sem sinks HTML/JS perigosos sem sanitização
- [ ] Criptografia/aleatoriedade/hash adequados (`secrets`, Argon2/bcrypt, TLS verificado)
- [ ] Erros fail-closed, sem vazar detalhe interno; timeouts e limites de tamanho
- [ ] Logs úteis para auditoria e sem dados sensíveis
- [ ] Upload/arquivo/URL externa tratados (tipo real, caminho, SSRF)

**Segredos**
- [ ] Scan do diff limpo (`scan_diff.py` + gitleaks/detect-secrets)
- [ ] Nenhum `.env`, chave, token, dump ou dado pessoal real no PR ou nos testes
- [ ] Configurações sensíveis lidas do ambiente/secret manager

**Dependências**
- [ ] Manifest e lockfile consistentes; versões fixadas
- [ ] `pip-audit`/`npm audit`/`osv-scanner` sem CVE crítico/alto alcançável
- [ ] Pacotes novos avaliados (nome, mantenedor, necessidade)

**Configuração/Infra**
- [ ] `DEBUG` off, hosts/CORS/cookies/headers/CSP corretos em produção
- [ ] Dockerfile não-root, base fixada, sem segredos nas camadas
- [ ] Workflow com `permissions` mínimas, actions fixadas, sem injeção em `run:`

**Testes**
- [ ] Há testes de segurança (acesso negado a outro usuário, entrada maliciosa, limites)

## Workflow de CI (GitHub Actions)

```yaml
name: security
on:
  pull_request:
  push: { branches: [main] }
  schedule: [{ cron: "0 6 * * 1" }]     # reauditoria semanal de dependências
permissions:
  contents: read
jobs:
  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4        # em produção, fixe pelo SHA do commit
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }

  sast-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install bandit pip-audit semgrep ruff
      - run: bandit -r src -ll
      - run: ruff check --select S src
      - run: semgrep scan --config p/owasp-top-ten --config p/python --error
      - run: pip-audit -r requirements.txt --strict

  deps-node:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: npm ci --ignore-scripts
      - run: npm audit --audit-level=high

  container:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t app:ci .
      - uses: aquasecurity/trivy-action@0.28.0
        with: { image-ref: app:ci, severity: "HIGH,CRITICAL", exit-code: "1", ignore-unfixed: true }
```
Ajuste caminhos (`src`, `requirements.txt`) ao projeto. Os checks devem ser **obrigatórios** na proteção de branch. Versões de actions acima são ilustrativas: confirme as atuais e fixe por SHA.

## pre-commit (barreira local)

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2            # confirme a versão atual
    hooks: [{ id: gitleaks }]
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.10
    hooks: [{ id: bandit, args: ["-ll", "-r", "src"] }]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks: [{ id: ruff, args: ["--select", "S,E,F"] }]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks: [{ id: detect-private-key }, { id: check-added-large-files }]
```
Instale com `pip install pre-commit && pre-commit install`. Hooks locais podem ser pulados (`--no-verify`), por isso o CI continua sendo a barreira que vale.

## Proteção de branch (configuração recomendada)
- PR obrigatório, ≥1–2 aprovações, aprovação invalidada ao novo push, resolver conversas
- Status checks obrigatórios: testes, `security`, build
- CODEOWNERS para auth, pagamentos, `.github/workflows`, infra, dependências
- Sem force-push nem deleção da branch; commits assinados; histórico linear
- Dependabot/Renovate + Secret Scanning + Push Protection + Code Scanning (CodeQL) ativos
