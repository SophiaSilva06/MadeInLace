# Autenticação e autorização (FastAPI + Jinja2)

Conteúdo: escolha da abordagem · hash de senha · model de usuário · login/logout por sessão · dependências de autorização · CSRF · rate limiting · alternativa JWT

## Qual abordagem usar

Para aplicações com páginas renderizadas no servidor, **sessão por cookie assinado** é o padrão mais simples e seguro: o navegador envia o cookie automaticamente e o servidor sabe quem é o usuário. Use JWT quando houver também clientes não-navegador (app desktop/mobile consumindo uma API). Nesse caso, mantenha as rotas HTML na sessão e exponha uma API separada sob `/api` com `Authorization: Bearer`.

## Hash de senha (`app/core/security.py`)

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def hash_senha(senha: str) -> str:
    return _ph.hash(senha)


def verificar_senha(senha: str, hash_: str) -> bool:
    try:
        return _ph.verify(hash_, senha)
    except VerifyMismatchError:
        return False
```

Nunca armazene senha em texto puro nem com SHA/MD5. Armazene o hash em `String(255)`. Valide tamanho mínimo (≥ 8) e mensagens de erro genéricas no login ("e-mail ou senha inválidos"), sem revelar qual dos dois falhou.

## Model de usuário

```python
class Usuario(TimestampMixin, Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    papel: Mapped[str] = mapped_column(String(20), default="cliente")  # "cliente" | "admin"
    ativo: Mapped[bool] = mapped_column(default=True)
```

Normalize o e-mail (`.strip().lower()`) antes de salvar e antes de buscar.

## Sessão por cookie

Em `main.py`:

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="sessao",
    max_age=60 * 60 * 8,      # 8 horas
    same_site="lax",
    https_only=not settings.debug,   # Secure em produção
)
```

O `SessionMiddleware` assina o cookie (não o criptografa): guarde só o `usuario_id`, nunca dados sensíveis.

Rotas:

```python
@router.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), senha: str = Form(...), db: Session = Depends(get_db)):
    usuario = db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))
    if not usuario or not usuario.ativo or not verificar_senha(senha, usuario.senha_hash):
        return templates.TemplateResponse(request, "auth/login.html",
            {"erro": "E-mail ou senha inválidos.", "email": email}, status_code=401)
    request.session.clear()                       # evita fixação de sessão
    request.session["usuario_id"] = usuario.id
    return RedirectResponse(request.url_for("home"), status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(request.url_for("login_form"), status_code=303)
```

## Dependências de autorização

```python
from fastapi import Depends, HTTPException, Request, status


def usuario_atual_opcional(request: Request, db: Session = Depends(get_db)) -> Usuario | None:
    uid = request.session.get("usuario_id")
    if not uid:
        return None
    usuario = db.get(Usuario, uid)
    return usuario if usuario and usuario.ativo else None


def exigir_login(usuario: Usuario | None = Depends(usuario_atual_opcional)) -> Usuario:
    if usuario is None:
        raise HTTPException(status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return usuario


def exigir_login_api(usuario: Usuario | None = Depends(usuario_atual_opcional)) -> Usuario:
    """Para rotas /api: responde 401 em vez de redirecionar para a página de login."""
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado.")
    return usuario


def exigir_papel(*papeis: str):
    def dependencia(usuario: Usuario = Depends(exigir_login)) -> Usuario:
        if usuario.papel not in papeis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado.")
        return usuario
    return dependencia
```

Uso:

```python
@router.get("/admin/produtos", dependencies=[Depends(exigir_papel("admin"))])
def painel(): ...

@router.get("/minha-conta")
def conta(request: Request, usuario: Usuario = Depends(exigir_login)): ...
```

Para o template saber quem está logado, passe `usuario` no contexto ou registre um global que leia a sessão. Cheque **propriedade do recurso** além do papel: um cliente só pode ver os próprios pedidos (`pedido.cliente_id == usuario.cliente_id`), senão qualquer um acessa `/pedidos/123` trocando o número.

Páginas de erro amigáveis: registre `@app.exception_handler(HTTPException)` que renderize `errors/403.html`, `404.html` quando a requisição aceitar HTML.

## CSRF

Com autenticação por cookie, formulários POST precisam de proteção CSRF (o `SameSite=Lax` ajuda, mas não substitui). Implementação simples com token na sessão:

```python
import secrets

def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = request.session["csrf"] = secrets.token_urlsafe(32)
    return token


def validar_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    esperado = request.session.get("csrf")
    if not esperado or not secrets.compare_digest(esperado, csrf_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token CSRF inválido.")
```

Aplique `dependencies=[Depends(validar_csrf)]` nas rotas POST/PUT/DELETE de formulário e registre `templates.env.globals["csrf_token"] = csrf_token`. Bibliotecas prontas (ex.: `starlette-csrf`) também servem; o que importa é que toda mutação seja protegida.

## Proteção contra força bruta

Limite tentativas de login por IP/e-mail (ex.: `slowapi`, ou contador em tabela/Redis) e considere bloqueio temporário após N falhas. Registre em log tentativas falhas, sem gravar a senha.

## Alternativa: JWT para API

Se for necessário, use `pyjwt`: access token curto (15–30 min), claims `sub` (id do usuário) e `exp`, assinado com `HS256` e `settings.secret_key`; valide expiração e assinatura em uma dependência que leia `Authorization: Bearer`. Se o token for guardado em cookie, use `HttpOnly`, `Secure`, `SameSite` e mantenha CSRF. Não coloque dados sensíveis no payload (é apenas codificado, não criptografado).

## Checklist de segurança

- [ ] Senhas com Argon2/bcrypt
- [ ] `session.clear()` no login e no logout
- [ ] Cookie `HttpOnly`, `SameSite=Lax`, `Secure` em produção
- [ ] CSRF em todo POST de formulário
- [ ] Autorização por papel **e** por propriedade do recurso
- [ ] `SECRET_KEY` forte, vinda do ambiente
- [ ] Mensagens de login genéricas e limite de tentativas
- [ ] Senha nunca aparece em logs, templates ou respostas
