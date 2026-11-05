# Segredos, dependências e supply chain

Conteúdo: O que é segredo · Detecção · Prevenção · Auditoria de dependências (Python e npm) · Avaliar um pacote novo · Docker · GitHub Actions / CI · SBOM

---

## O que conta como segredo

Chaves de API e tokens (cloud, GitHub, Stripe, SendGrid, Slack, OpenAI/Anthropic...), senhas, strings de conexão com credencial (`postgres://user:senha@host/db`), chaves privadas (SSH, TLS, JWT, assinatura), `SECRET_KEY` de frameworks, tokens de sessão/JWT reais, certificados `.pfx/.p12`, arquivos `.env`, credenciais de service accounts (`*.json`, `credentials`, `.npmrc`/`.pypirc` com token), webhooks com segredo na URL, e **dados pessoais reais** (CPF, e-mail, cartões) usados em fixtures/testes.

Onde procurar além do código: testes e fixtures, notebooks, Dockerfiles (`ENV`, `ARG`), `docker-compose`, workflows de CI, comentários, docs/README, arquivos de configuração, scripts de deploy, migrations, dumps SQL, logs commitados e **histórico do git** (um segredo apagado no commit seguinte continua no histórico).

Valores obviamente falsos (`changeme`, `xxxx`, `<SUA_CHAVE>`, `example`) são aceitáveis em `.env.example`; um valor com formato real de chave não é, mesmo em teste. Se o time precisar de fixture, gere valores aleatórios em tempo de execução ou use credenciais de sandbox claramente identificadas.

## Detecção

- **Local/PR:** `python .agent/skills/secops-guardian/scripts/scan_diff.py --base origin/main` (heurísticas rápidas só nas linhas adicionadas) + uma ferramenta dedicada:
  - `gitleaks detect --redact` (histórico) / `gitleaks protect --staged` (pre-commit)
  - `detect-secrets scan` com baseline (`.secrets.baseline`)
  - `trufflehog git file://. --only-verified` (valida se o segredo ainda funciona)
- **Plataforma:** ative *Secret Scanning* e *Push Protection* (GitHub/GitLab).
- **Revisão manual** procura o que regex não pega: senha em linguagem natural, token fragmentado em duas variáveis, base64 de credencial, segredo em URL de webhook, valor em comentário "temporário".
- Cada achado: confirme se o valor é real; se for, execute o **protocolo de resposta** do SKILL.md (revogar primeiro).

## Prevenção

```gitignore
.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
credentials*.json
service-account*.json
.npmrc
.pypirc
*.sqlite3
```
- Configuração por ambiente: variáveis de ambiente injetadas pela plataforma (12-factor) ou **secret manager** (AWS Secrets Manager/SSM, GCP Secret Manager, Azure Key Vault, HashiCorp Vault, Doppler, 1Password CLI). Em Kubernetes, `Secret` + criptografia em repouso/External Secrets.
- Código falha cedo se a variável faltar; nunca um default com segredo real.
- **Menor privilégio e escopo:** token específico por serviço, somente as permissões necessárias, expiração curta, rotação periódica; prefira credenciais temporárias/OIDC a chaves estáticas de longa duração.
- Separe segredos por ambiente (dev ≠ staging ≠ prod).
- **pre-commit** (arquivo pronto em `pr-gate-and-report.md`).
- Docker: não use `ENV SENHA=...` nem `ARG` para segredo (ficam nas camadas/`docker history`); use `--mount=type=secret` no BuildKit ou injete em runtime.
- Logs e erros nunca devem imprimir segredos; mascare.

## Auditoria de dependências

### Python
```bash
pip-audit -r requirements.txt                 # base PyPI Advisory / OSV
pip-audit --strict --desc                     # falha em achados, mostra descrição
pip install pip-tools && pip-compile --generate-hashes requirements.in   # lock com hashes
pip install --require-hashes -r requirements.txt                          # instala só o que bate com o hash
poetry lock && poetry export ...              # ou uv lock / uv pip compile
osv-scanner --lockfile=poetry.lock            # alternativa multi-ecossistema
```
Boas práticas: manifestos **fixados** (`==`) com lockfile e hashes; separar `requirements-dev`; remover o que não usa; atualizar com frequência (Dependabot/Renovate) com testes automáticos; fixar versão do Python e da imagem base; evitar `pip install git+https://...` sem commit/hash; usar índice privado/espelho para evitar *dependency confusion* (prefixo/namespace interno, `--index-url` único, nunca `--extra-index-url` misturando público e interno).

### JavaScript/TypeScript
```bash
npm ci                                       # instala exatamente o lockfile
npm audit --audit-level=high --omit=dev      # ajuste conforme a política
osv-scanner --lockfile=package-lock.json
npm ls <pacote>                              # quem puxa a dependência transitiva
```
Overrides/resolutions para forçar versão corrigida de dependência transitiva, quando o upstream demora.

### Como interpretar um achado de CVE
Não reporte só o ID: avalie **alcance** (a função vulnerável é usada? está em dev-only?), **explorabilidade** (rede, autenticação, EPSS/KEV se disponível), **correção** (versão mínima corrigida; é *breaking*?). Registre: pacote, versão atual → corrigida, CVE/GHSA, severidade CVSS, e se há mitigação enquanto não atualiza. CVE crítico/alto em código alcançável em produção = **bloqueia o PR**. Nunca cite um CVE ou número de versão de memória como fato; confirme na base ou diga que precisa ser confirmada.

## Avaliando um pacote novo (checklist de 1 minuto)
1. Nome correto? Compare com o pacote popular (typosquatting: `reqeusts`, `python-dateutils`, `colourama`).
2. Precisa mesmo? Há alternativa na stdlib ou já instalada?
3. Mantenedor ativo, histórico de releases, repositório real, licença compatível, número de usuários.
4. Dependências transitivas pesadas ou suspeitas? Scripts de instalação (`setup.py` customizado, `postinstall`)?
5. Releases muito recentes ou mudança súbita de dono = atenção redobrada.
6. Fixe a versão e inclua no lockfile.

## Docker e imagens

- Imagem base oficial, enxuta e **fixada** por tag específica ou digest (`python:3.12-slim@sha256:...`), nunca `latest`.
- **Multi-stage build:** compile em um estágio, copie só o artefato ao final.
- **Usuário não-root:** `RUN useradd -r app && USER app`; `--read-only` e `cap_drop: [ALL]` quando possível; sem `--privileged`; sem montar `docker.sock`.
- `.dockerignore` com `.git`, `.env*`, `node_modules`, chaves, testes (evita `COPY . .` vazar segredo).
- Sem `curl | sh`; verifique checksum/assinatura do que baixar.
- Escaneie: `trivy image app:tag`, `docker scout`, `grype`; e o Dockerfile/IaC: `trivy config .`, `hadolint`.
- Exponha só as portas necessárias; healthcheck; atualize a imagem base regularmente.

## GitHub Actions / CI-CD

```yaml
permissions:            # no topo: negue por padrão, conceda por job
  contents: read
```
- **Fixe actions por SHA de commit** (`uses: actions/checkout@<sha> # v4.x`), principalmente as de terceiros; Dependabot mantém atualizado.
- `pull_request_target` e `workflow_run` rodam com segredos: **nunca** faça checkout/execução de código do PR nesses gatilhos sem isolamento; para PRs de forks use `pull_request` (sem segredos).
- **Injeção de script:** não interpole `${{ github.event.pull_request.title }}`/`head_ref`/`body` diretamente em `run:`; passe por `env:` e use a variável do shell entre aspas.
- Segredos só em `secrets.*`/environments com aprovação; nunca `echo` de segredo; cuidado com `set -x`. Prefira **OIDC** a chaves de nuvem estáticas.
- Runners self-hosted só para repositórios privados e efêmeros.
- Proteja a branch principal: PR obrigatório, revisões, checks obrigatórios (testes + SAST + SCA + secrets), commits assinados, sem force-push, CODEOWNERS para pastas críticas (`.github/`, auth, pagamentos).
- Artefatos: gere SBOM, assine (cosign/Sigstore) e registre *provenance* (SLSA).

## SBOM e inventário

Gere um SBOM (CycloneDX/SPDX) a cada build (`cyclonedx-py`, `cyclonedx-npm`, `syft`) e guarde-o com o artefato: quando um novo CVE sair, você consegue responder em minutos "estamos afetados?". Reavalie periodicamente (job agendado), pois uma dependência segura hoje pode ter CVE amanhã sem nenhum commit novo.
