# OWASP Top 10:2025 aplicado a Python + Web

Conteúdo: A01 Controle de Acesso · A02 Configuração · A03 Supply Chain · A04 Criptografia · A05 Injeção · A06 Design Inseguro · A07 Autenticação · A08 Integridade · A09 Logging · A10 Condições Excepcionais · Mapeamento 2021→2025 · Listas complementares

A edição 2025 mudou a ordem em relação a 2021: Configuração Incorreta subiu para #2, "Componentes Vulneráveis" virou **Falhas na Cadeia de Suprimentos de Software** (#3), **Manejo Inadequado de Condições Excepcionais** é nova (#10), e **SSRF foi absorvido por A01**. Ao citar achados, use a numeração 2025 e, se o time ainda usa 2021, informe o equivalente (tabela no final).

Para cada categoria: **o que procurar** → **exemplo** → **perguntas de revisão**.

---

## A01:2025 — Perda de Controle de Acesso (inclui SSRF)
Autorização ausente, só no cliente, ou falha em verificar a **posse do objeto**. É a categoria mais frequente: assuma que toda rota nova é vulnerável até provar o contrário.

**Procurar:** rota sem dependência de autenticação/permissão; consulta por ID sem filtrar por dono (`select(Pedido).where(Pedido.id == id)` sem `cliente_id == user.id`); IDs sequenciais expostos; campos como `is_admin`, `role`, `owner_id`, `preco` aceitos do corpo (mass assignment); modelo de resposta que devolve campos internos; CORS permissivo; endpoints "internos" sem auth; path traversal; redirect aberto; `httpx.get(url_do_usuario)` (SSRF).

```python
# VULNERÁVEL (IDOR/BOLA): qualquer usuário logado lê pedido de outro
pedido = db.get(Pedido, pedido_id)
# SEGURO: o filtro de posse faz parte da consulta; 404 evita enumerar IDs
pedido = db.scalar(select(Pedido).where(Pedido.id == pedido_id, Pedido.cliente_id == user.id))
if pedido is None:
    raise HTTPException(404)
```
```python
# VULNERÁVEL (mass assignment)
db.query(Usuario).filter(Usuario.id == user.id).update(payload)   # payload = dict cru do corpo (permite is_admin)
# SEGURO: esquema explícito (allowlist de campos editáveis)
class PerfilIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str
    telefone: str | None = None
```
**SSRF:** valide esquema (só https), resolva o DNS e bloqueie IPs privados/loopback/link-local (`10/8`, `172.16/12`, `192.168/16`, `127/8`, `169.254.169.254`), desabilite redirects ou revalide a cada salto, use allowlist de domínios quando possível, defina timeout e limite de tamanho.

**Perguntar:** quem pode chamar isto? Onde está a checagem, no servidor? A consulta é filtrada pelo dono? O que acontece se eu trocar o ID? E o método HTTP (PUT/DELETE) tem a mesma proteção do GET? Deny-by-default está valendo?

## A02:2025 — Configuração de Segurança Incorreta
**Procurar:** modo debug/reload ligado em produção (`uvicorn --reload`, `debug=True`); segredo/`SECRET_KEY` literal; credenciais padrão; `/docs`, `/redoc`, `/openapi.json`, `/metrics` e painéis expostos; stack trace ao cliente; CORS `*`; cookies sem `Secure/HttpOnly/SameSite`; headers de segurança ausentes; `StaticFiles` apontando para diretório com arquivos sensíveis; banco MySQL exposto à internet ou com usuário `root`; Docker como root; portas desnecessárias; XXE (parsers XML com entidades externas — use `defusedxml`).

```python
# FastAPI: configuração mínima de produção
class Settings(BaseSettings):                       # pydantic-settings
    database_url: str                               # sem default: falha ao iniciar se faltar
    session_secret: str
    allowed_hosts: list[str]

settings = Settings()
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(HTTPSRedirectMiddleware)         # ou redirecione no proxy
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret,
                   https_only=True, same_site="lax", max_age=3600)
```
**Perguntar:** o que muda entre dev e prod? O default é seguro se a variável não for definida? Os headers de `frontend-web.md` são enviados por um middleware ou pelo proxy?

## A03:2025 — Falhas na Cadeia de Suprimentos de Software
Dependências vulneráveis **e** comprometidas: CVEs, typosquatting, pacote abandonado, versão sem pin, `postinstall` malicioso, GitHub Action adulterada, imagem base não confiável, pipeline com permissões excessivas.
**Procurar no PR:** pacote novo (avalie nome, mantenedor, idade, downloads), `>=` sem teto, ausência de lockfile/hash, `pip install` de URL/git sem commit fixo, `npm install` em CI (use `npm ci`), `curl | sh`, actions por tag móvel. Detalhes e comandos em `secrets-and-supply-chain.md`.
**Perguntar:** preciso mesmo desta dependência? Está fixada e auditada? Quem pode alterar o pipeline que gera o artefato?

## A04:2025 — Falhas Criptográficas
**Procurar:** MD5/SHA-1 para senha ou assinatura; senha sem hash ou com hash rápido sem sal; `random`/`Math.random` para token, reset de senha, ID de sessão; chaves/IV fixos ou derivados de constantes; AES-ECB; TLS desligado (`verify=False`, `rejectUnauthorized:false`); dado sensível em texto puro (banco, log, URL, localStorage); JWT `alg:none` ou HS256 com segredo fraco; criptografia "caseira".
```python
import secrets
token = secrets.token_urlsafe(32)                 # não use random
# senhas: argon2id (argon2-cffi) ou bcrypt, nunca hash rápido (md5/sha)
from argon2 import PasswordHasher; ph = PasswordHasher(); hash_ = ph.hash(senha)
# comparação em tempo constante para segredos
import hmac; hmac.compare_digest(a, b)
```
**Perguntar:** que dado sensível existe aqui e como é protegido em trânsito e em repouso? A biblioteca é padrão (cryptography, PyNaCl) ou invenção?

## A05:2025 — Injeção (SQL, comando, template, NoSQL, LDAP, XSS)
Regra única: **dado nunca vira código**. Separe dados de comandos com parametrização, escape contextual ou APIs que não interpretam.

**SQL**
```python
# VULNERÁVEL
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")
cur.execute("SELECT * FROM users WHERE email = '%s'" % email)
db.execute(text(f"SELECT ... WHERE x = '{x}'"))   # text() com f-string
# SEGURO
cur.execute("SELECT * FROM users WHERE email = %s", (email,))
db.scalar(select(Usuario).where(Usuario.email == email))   # ORM parametriza
db.execute(text("SELECT ... WHERE x = :x"), {"x": x})
```
Atenção: nomes de coluna/tabela e `ORDER BY` não aceitam parâmetro; use **allowlist** (`{"nome","preco"}`) e nunca concatene a entrada. `LIKE` precisa escapar `%` e `_` quando a busca for literal. ORM não é imune: `text()`/`execute()` com f-string, `order_by(text(request_param))` e `filter(text(...))` continuam injetáveis.

**Comando do SO**
```python
# VULNERÁVEL
os.system(f"convert {arquivo} out.png");  subprocess.run(cmd, shell=True)
# SEGURO: lista de argumentos, sem shell, com allowlist/validação do argumento
subprocess.run(["convert", str(caminho_validado), "out.png"], check=True, timeout=10)
```
**Template (SSTI):** `Template(user_input)`, `env.from_string(user_input)` no Jinja2 → execução de código no servidor. Use templates estáticos (arquivos) e passe dados apenas como contexto.
**NoSQL:** `collection.find(request.json)` permite operadores (`{"$ne": null}`); valide tipos e esquema.
**XSS:** escape contextual (HTML, atributo, JS, URL, CSS). O `Jinja2Templates` do Starlette escapa por padrão em `.html`; o risco está em `|safe`, `Markup(...)`, `autoescape false`, `innerHTML` e `href` com `javascript:`. Sanitize HTML rico com biblioteca confiável (`nh3`/`bleach`, DOMPurify) e use CSP. Mais em `python-backend.md` (Jinja2) e `frontend-web.md`.
**Header/log injection:** remova CR/LF de valores em headers e logs.
**Perguntar:** este valor chega a algum interpretador? Está parametrizado ou concatenado? A allowlist é do servidor?

## A06:2025 — Design Inseguro
Falha na **concepção**, não só no código: sem modelo de ameaças, sem limites de negócio, sem rate limit, fluxo de recuperação de senha enumerável, regras de negócio burláveis (preço vindo do cliente, quantidade negativa, cupom reutilizável, race condition em saldo/estoque), segredos "de segurança" (perguntas secretas).
**Faça:** modelagem STRIDE rápida para features novas; validação de regras no servidor (preço/total sempre recalculado do banco); idempotência e transações (`select_for_update`, constraints únicas); limites por usuário/IP; fluxos de falha seguros; separação de ambientes e privilégios.
**Perguntar:** qual é o pior que um usuário malicioso autenticado consegue fazer com este fluxo? E em paralelo (corrida)? E repetindo mil vezes?

## A07:2025 — Falhas de Autenticação
**Procurar:** login sem rate limit/lockout/CAPTCHA; mensagens que revelam se o usuário existe; senha fraca aceita; sem MFA para contas privilegiadas; ID de sessão em URL; sessão não rotacionada após login/troca de senha; logout que não invalida; reset de senha com token previsível/sem expiração/reutilizável; JWT sem validação de `exp`, `aud`, `iss`, algoritmo explícito; API keys sem rotação; "lembrar-me" eterno; credenciais em query string.
```python
payload = jwt.decode(token, key, algorithms=["RS256"], audience="minha-api", issuer="https://auth.exemplo")
```
**Perguntar:** como um atacante faz força bruta ou credential stuffing? O que invalida a sessão? Quanto vale um token roubado e por quanto tempo?

## A08:2025 — Falhas de Integridade de Software ou Dados
**Procurar:** `pickle`, `marshal`, `shelve`, `yaml.load` (sem `safe_load`), `jsonpickle`, `dill` com dados externos (**RCE**); atualizações/plugins sem verificação de assinatura; CDN sem SRI; pipeline CI/CD que executa código de PR externo com segredos; cookies/estado de cliente sem assinatura; `tarfile`/`zipfile` extraídos sem validar caminhos (zip slip).
```python
data = yaml.safe_load(texto)          # nunca yaml.load sem Loader seguro
data = json.loads(texto)              # prefira formatos que não executam código
```
**Perguntar:** de onde vêm estes bytes e quem os assinou? Dá para virar objeto/código só por desserializar?

## A09:2025 — Falhas de Registro, Alerta e Monitoramento
**Procurar:** ausência de log em login, falha de autorização, mudança de privilégio, ações administrativas; logs sem contexto (quem/quando/de onde/o quê); **dados sensíveis nos logs** (senha, token, cartão, CPF, corpo de request inteiro); log injection; logs graváveis pelo app que ele mesmo lê; sem alerta para picos de 401/403/5xx.
```python
logger.info("login_falhou", extra={"user_id": uid, "ip": ip})   # sem a senha, sem o token
```
**Perguntar:** se isto for atacado hoje, eu perceberia? O log ajuda a investigar sem criar um novo vazamento?

## A10:2025 — Manejo Inadequado de Condições Excepcionais (novo)
Erros e estados anormais tratados de forma insegura: **fail-open** (exceção na checagem de permissão libera acesso), `except Exception: pass`, `except:` engolindo falha de autenticação, erro que vaza stack trace/SQL/caminhos, recursos não liberados (conexões, arquivos, locks), estado parcial sem rollback, falta de timeout, DoS por entrada gigante/regex catastrófica (ReDoS)/decompressão bomba, `assert` removido com `-O` usado como controle.
```python
# VULNERÁVEL: fail-open
try:
    autorizado = checar_permissao(user, recurso)
except Exception:
    autorizado = True
# SEGURO: fail-closed + log + resposta genérica
try:
    autorizado = checar_permissao(user, recurso)
except Exception:
    logger.exception("falha_checagem_permissao")
    raise PermissionDenied
```
**Perguntar:** quando isto falha, o sistema fica **aberto ou fechado**? O cliente vê detalhes internos? Há timeout e limite de tamanho?

---

## Mapeamento 2021 → 2025
| 2021 | 2025 |
|---|---|
| A01 Broken Access Control (+ A10 SSRF) | A01 Perda de Controle de Acesso |
| A05 Security Misconfiguration | A02 Configuração Incorreta |
| A06 Vulnerable and Outdated Components | A03 Falhas na Cadeia de Suprimentos |
| A02 Cryptographic Failures | A04 Falhas Criptográficas |
| A03 Injection (inclui XSS) | A05 Injeção |
| A04 Insecure Design | A06 Design Inseguro |
| A07 Identification and Authentication Failures | A07 Falhas de Autenticação |
| A08 Software and Data Integrity Failures | A08 Falhas de Integridade |
| A09 Security Logging and Monitoring Failures | A09 Falhas de Registro e Alerta |
| (novo) | A10 Condições Excepcionais |

## Listas complementares (use quando o contexto pedir)
- **OWASP API Security Top 10** para APIs REST/GraphQL: BOLA, autenticação quebrada, BOPLA (exposição/atribuição excessiva de propriedades), consumo irrestrito de recursos, BFLA, fluxos de negócio sensíveis, SSRF, configuração, inventário de APIs, consumo inseguro de APIs de terceiros. GraphQL: desligue introspection em prod, limite profundidade/complexidade.
- **OWASP Top 10 for LLM Applications** se o projeto integra IA: prompt injection, vazamento de dados, saída tratada como confiável (nunca execute/renderize a saída do modelo sem escape), agência excessiva.
- **OWASP ASVS** como checklist de verificação detalhado (níveis 1–3) e **CWE Top 25** para classificar o achado.
