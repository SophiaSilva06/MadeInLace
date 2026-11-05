# Segurança em backend Python (FastAPI + Jinja2 + MySQL)

Conteúdo: Padrões transversais · FastAPI · Jinja2 e páginas server-side · CSRF em formulários · SQLAlchemy, SQL cru e MySQL · Uploads e arquivos · Requests de saída (SSRF) · Senhas, sessões e JWT · Tarefas assíncronas · Logging · Ferramentas automatizadas

---

## Padrões transversais

**Validação de entrada por esquema, na borda.** Valide tipo, tamanho, formato e faixa com Pydantic. Prefira **allowlist** (o que é permitido) a blocklist. Rejeite campos desconhecidos (`model_config = ConfigDict(extra="forbid")`) para evitar mass assignment. Validação no frontend é só UX.

**Autorização em duas perguntas, em toda rota:** (1) o usuário está autenticado? (2) ele pode fazer **esta ação neste objeto**? Centralize em dependências reutilizáveis (`Depends`) para que esquecer seja difícil. Deny-by-default: rota sem dependência de autenticação deve falhar em teste.

**Segredos e configuração:** leia de variáveis de ambiente/secret manager; falhe na inicialização se faltar. `pydantic-settings` tipa e valida (um campo sem default obriga a definir a variável). Nunca commite `.env`; versione apenas `.env.example` sem valores reais.

**Erros:** resposta genérica ao cliente (`{"detail": "Erro interno"}`), detalhe e stack trace só no log. Registre handlers de exceção para que erros inesperados nunca devolvam traceback.

**Tempo e recursos:** timeout em toda chamada externa e em queries; limite tamanho de corpo, de upload e de paginação (`page_size` máximo).

---

## FastAPI

- Autenticação por **dependência** (`Depends(get_current_user)`) aplicada no router inteiro (`APIRouter(dependencies=[...])`) para não depender de lembrar rota a rota.
- Autorização por objeto dentro da consulta, não depois dela:
```python
@router.get("/pedidos/{pedido_id}")
def ver_pedido(pedido_id: int, user: User = Depends(usuario_atual), db: Session = Depends(get_db)):
    pedido = db.scalar(select(Pedido).where(Pedido.id == pedido_id, Pedido.cliente_id == user.id))
    if pedido is None:
        raise HTTPException(404)      # 404 em vez de 403 evita enumerar IDs de outros usuários
    return pedido
```
- Modelos Pydantic **separados** para entrada e saída (`UsuarioIn`, `UsuarioOut`) para nunca devolver `senha_hash` nem campos internos. Campos como `is_admin`, `cliente_id` e `preco` nunca vêm do corpo.
- Desabilite `/docs`, `/redoc`, `/openapi.json` em produção (`FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`) ou proteja-os.
- Middlewares: `TrustedHostMiddleware` (hosts explícitos), `HTTPSRedirectMiddleware` (ou redirecionamento no proxy), `CORSMiddleware` com `allow_origins` explícito (`"*"` com `allow_credentials=True` é perigoso), e um middleware que acrescenta os headers de segurança de `frontend-web.md`.
- Limite o tamanho do corpo (proxy/middleware); valide `UploadFile` (tipo real, tamanho).
- Não bloqueie o event loop: `async def` com chamada bloqueante (SDK síncrono, `time.sleep`, query síncrona) congela o servidor inteiro, o que vira DoS barato. Use `def` (thread pool) ou bibliotecas async.
- Rate limit em login, cadastro, recuperação de senha e demais ações abusáveis (`slowapi` ou no proxy/WAF).
- JWT: `PyJWT`/`authlib` com `algorithms=[...]` fixo; verifique `exp`, `aud`, `iss`.

## Jinja2 e páginas server-side

- `Jinja2Templates` do Starlette ativa **autoescape** para templates `.html`: mantenha. Os pontos de XSS são `|safe`, `Markup(...)`, `{% autoescape false %}` e `Environment(autoescape=False)`. Todo `|safe` precisa de justificativa e de dado vindo exclusivamente do servidor ou sanitizado (`nh3`/`bleach`).
- **SSTI:** `Template(entrada)`, `env.from_string(entrada)` ou renderizar template cujo texto veio do usuário = execução de código no servidor. Templates são sempre arquivos estáticos; o dado do usuário entra apenas como contexto.
- Dados para JavaScript dentro do template: `{{ dados | tojson }}` em `<script type="application/json">` e leitura com `JSON.parse`, nunca `var x = "{{ valor }}"`.
- Atributos HTML sempre entre aspas (`value="{{ v }}"`); URLs dinâmicas em `href`/`src` precisam de validação de esquema (bloquear `javascript:`).
- Não renderize mensagens de erro internas, SQL ou stack trace na página.

## CSRF em formulários (ponto crítico quando há cookie de sessão)

O FastAPI **não traz proteção CSRF**. Em um site com Jinja2 + formulários e sessão por cookie, toda ação que altera estado (login, cadastro, alteração de dados, troca de senha, pedidos e pagamentos) precisa de:
1. Cookie de sessão `HttpOnly; Secure; SameSite=Lax` (ou `Strict`);
2. Token CSRF por sessão (padrão *synchronizer token* ou *double submit* assinado, ex. biblioteca `starlette-csrf`/`fastapi-csrf-protect`) incluído em campo oculto `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">` e validado no servidor com comparação em tempo constante;
3. Validação de `Origin`/`Referer` como camada extra;
4. Nenhuma alteração de estado por `GET` (logout, exclusão e qualquer escrita devem ser `POST`/`DELETE`).

Se o login for por `Authorization: Bearer` e não por cookie, o CSRF clássico não se aplica (mas aí o risco passa a ser o armazenamento do token no navegador).

`SessionMiddleware` do Starlette guarda a sessão **assinada, mas não criptografada**, dentro do cookie: nunca coloque dados sensíveis nela; guarde só o ID do usuário/sessão. Defina `https_only=True`, `same_site="lax"`, `max_age` curto e `secret_key` forte vindo do ambiente. Prefira sessão do lado do servidor (ID opaco + tabela/Redis) quando precisar invalidar sessões.

## SQLAlchemy, SQL cru e MySQL

```python
# VULNERÁVEL
db.execute(text(f"SELECT * FROM produtos WHERE nome LIKE '%{q}%'"))
cur.execute(f"SELECT * FROM usuarios WHERE email = '{email}'")      # PyMySQL / mysql-connector
# SEGURO
db.execute(text("SELECT * FROM produtos WHERE nome LIKE :q"), {"q": f"%{q}%"})
cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))   # %s é placeholder do driver, não formatação
# colunas/ordenação dinâmicas: allowlist
ORDENAVEIS = {"preco": Produto.preco, "nome": Produto.nome}
query = query.order_by(ORDENAVEIS.get(sort, Produto.nome))
```
- Nomes de tabela/coluna e `ORDER BY` não aceitam parâmetro: use **allowlist**. `LIKE` deve escapar `%` e `_` quando a busca for literal.
- O ORM não torna `text()`, `execute()` e `.filter(text(...))` seguros se houver concatenação.
- **Princípio do menor privilégio no MySQL:** usuário da aplicação com `SELECT/INSERT/UPDATE/DELETE` apenas nas tabelas necessárias (sem `DROP`, `GRANT`, `FILE`, `SUPER`); migrações usam outra credencial; o banco não escuta na internet (bind em rede privada, firewall), TLS na conexão (`ssl_ca`), sem usuário `root` remoto e sem senha vazia. Use `utf8mb4` e `sql_mode` estrito (`STRICT_TRANS_TABLES`).
- **Integridade de valores e transações:** valores monetários e quantidades nunca são confiados ao formulário: recalcule/valide no servidor a partir do banco. Operações que alteram saldo ou contadores devem ser atômicas (`SELECT ... FOR UPDATE` ou `UPDATE ... SET qtd = qtd - 1 WHERE id=:id AND qtd > 0` verificando `rowcount`) para evitar corrida, e restrições de unicidade ficam no banco (`UNIQUE`), não só na aplicação. As regras de negócio específicas do projeto vêm do documento de requisitos: confronte o PR com ele.
- **Dados pessoais** (LGPD): endereço, CPF, telefone e e-mail são dados pessoais; minimize o que coleta, não logue, e considere criptografar campos muito sensíveis. Senha nunca em texto: apenas hash Argon2id/bcrypt.

## Uploads e arquivos

- Valide **tamanho**, extensão por allowlist **e** tipo real (assinatura/magic bytes, `python-magic`), não confie em `Content-Type`.
- **Gere o nome do arquivo** (UUID); nunca use o nome enviado.
- Path traversal: resolva e confirme que o caminho final está dentro do diretório base.
```python
base = Path(UPLOAD_DIR).resolve()
alvo = (base / nome).resolve()
if base not in alvo.parents:
    raise HTTPException(400)
```
- Armazene fora do diretório servido como estático (ou em bucket privado com URLs assinadas); sirva com `X-Content-Type-Options: nosniff`. `StaticFiles` em diretório de upload expõe tudo que for enviado: nunca monte o diretório de uploads cru.
- Imagens: reprocese (Pillow), limite dimensões (`Image.MAX_IMAGE_PIXELS`) e descarte metadados.
- Arquivos compactados: valide cada membro (zip slip), número e tamanho descompactado; `tarfile.extractall` sem `filter="data"` (Python ≥ 3.12) é inseguro.

## Requests de saída (SSRF)

Quando o servidor busca uma URL fornecida por usuário (webhooks, preview de link, importação): `https` apenas, allowlist de domínios se possível, resolva o DNS e **bloqueie IPs privados/loopback/link-local/metadata** (`169.254.169.254`), valide novamente após redirects (ou desligue-os), conecte ao IP já validado (anti DNS rebinding), defina timeout e tamanho máximo, e não devolva a resposta bruta ao usuário. Integrações com serviço fixo devem usar URL base constante e validar o parâmetro dinâmico por formato (regex/tipo), escapando-o no caminho, nunca montando o host a partir da entrada.

```python
import ipaddress, socket
from urllib.parse import urlparse
def url_segura(u: str) -> bool:
    p = urlparse(u)
    if p.scheme != "https" or not p.hostname:
        return False
    for _fam, *_, addr in socket.getaddrinfo(p.hostname, p.port or 443):
        ip = ipaddress.ip_address(addr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True
```
(Ponto de partida: para proteção completa, fixe o IP validado na conexão.)

## Senhas, sessões e JWT

- Senhas: **Argon2id** (`argon2-cffi`) ou bcrypt/scrypt, com sal automático. A política de ≥ 12 caracteres com variedade é aplicada no servidor (Pydantic `field_validator`), e vale checar também contra senhas vazadas (HIBP k-anonymity). Mensagem de erro de validação pode detalhar a regra, mas o **login** nunca diz qual campo errou.
- Login: mesma mensagem e tempo aproximado para "e-mail inexistente" e "senha errada"; rate limit por IP e por conta; bloqueio progressivo.
- **Unicidade de e-mail:** `UNIQUE` no banco (a checagem da aplicação sozinha tem corrida); normalize (`strip().lower()`) antes de comparar.
- **Recuperação de senha/e-mail:** token aleatório (`secrets.token_urlsafe(32)`), guardado como **hash**, expiração curta (15–60 min), uso único, invalida ao trocar a senha, e resposta idêntica exista ou não o e-mail (não revela cadastros). Nunca envie a senha atual por e-mail: "recuperável" deve significar **redefinível**, jamais recuperar o texto original.
- Sessão: rotacione o ID após login e troca de senha, invalide no logout e na troca de senha, expire por inatividade.
- JWT (se usar): access curto (5–15 min) + refresh rotativo com revogação; algoritmo fixo; segredo ≥ 256 bits aleatórios; nada sensível no payload.
- Comparação de segredos/tokens com `hmac.compare_digest`.

## Tarefas assíncronas

`BackgroundTasks`, Celery ou RQ: use serializador **JSON** (nunca `pickle`); autentique e isole o broker (senha, TLS, fora da internet); trate payload da fila como entrada não confiável; idempotência e limites de retry; não passe segredos nos argumentos da task. Prazos de expiração (reservas, tokens, links) devem ser verificados por **timestamp no servidor** no momento do uso, sem depender só de job agendado.

## Logging

Estruture (JSON) com `request_id`, usuário, IP, ação e resultado. **Nunca** logue senhas, tokens, chaves, cookies, cartão, documentos pessoais completos nem corpos de request inteiros. Mascare campos sensíveis num filtro central. Sanitize CR/LF de valores controlados pelo usuário. Registre eventos de segurança (login falho/bem-sucedido, reset de senha, mudança de endereço/e-mail, 401/403 repetidos, compras suspeitas).

## Ferramentas automatizadas

| Objetivo | Ferramenta | Comando típico |
|---|---|---|
| SAST Python | **Bandit** | `bandit -r app -ll` |
| SAST com regras OWASP | **Semgrep** | `semgrep --config p/owasp-top-ten --config p/python --config p/jinja2 .` |
| Regras de segurança no linter | **Ruff** (`S` = flake8-bandit) | `ruff check --select S .` |
| Dependências Python | **pip-audit** / **osv-scanner** | `pip-audit -r requirements.txt` |
| Segredos | **gitleaks** / **detect-secrets** | `gitleaks detect --redact` |
| Tipos | **mypy/pyright** | reduz classes inteiras de bug |
| DAST (ambiente autorizado) | **OWASP ZAP baseline** | `zap-baseline.py -t https://staging...` |

Ferramenta automática encontra padrões; **não** encontra falhas de lógica de negócio e de autorização (regras de negócio, corridas, abuso de fluxos). Essas dependem da revisão manual do fluxo.
