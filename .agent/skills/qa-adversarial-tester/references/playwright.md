# Playwright com pytest

Sumário: Setup · Padrões · Atacando a UI · Rede · Console · Diagnóstico · Fluxo completo

## Setup
```bash
pip install pytest-playwright pytest-timeout
playwright install chromium   # firefox e webkit para multi-browser
```
Rode: `pytest --browser chromium --browser firefox --tracing retain-on-failure --timeout=60`.

## Padrões
- Locators por papel/label/texto: `page.get_by_role("button", name="Finalizar compra")`.
- Asserts web-first com auto-retry: `expect(locator).to_be_visible()`, `to_have_text`, `to_have_url`.
- Nunca `time.sleep` nem `wait_for_timeout`. Espere por uma condição observável (elemento, URL, resposta de rede).
- Cada teste usa seu próprio `context` (a fixture `page` já faz isso). Estado inicial via API/fixture, não via UI.
- Page Object para fluxos repetidos; seletores num único lugar.
- Base URL em `--base-url` ou fixture `base_url`, nunca hardcoded.

## Atacando a UI
- Submit com tudo vazio; campos com 10 mil caracteres; emoji, `<script>`, aspas.
- Duplo clique e clique repetido rápido no botão de pagar (deve gerar um único pedido).
- Voltar/avançar do navegador no meio do checkout; recarregar a página; abrir em duas abas.
- Sessão expirada (apague cookies no meio do fluxo); acesso direto a URL protegida sem login.
- Viewport móvel (`page.set_viewport_size({"width": 375, "height": 667})`), teclado apenas (Tab/Enter), zoom 200%.
- Offline: `context.set_offline(True)`.

## Rede: simular falhas
```python
from playwright.sync_api import Page, expect

def test_erro_500_mostra_mensagem_tratada(page: Page, base_url):
    page.route("**/api/pedidos", lambda r: r.fulfill(status=500, body="boom"))
    page.goto(f"{base_url}/checkout")
    page.get_by_role("button", name="Finalizar compra").click()
    expect(page.get_by_role("alert")).to_contain_text("Tente novamente")

def test_json_malformado_nao_quebra_a_tela(page: Page, base_url):
    page.route("**/api/produtos", lambda r: r.fulfill(status=200, body="{nao e json"))
    page.goto(f"{base_url}/produtos")
    expect(page.get_by_role("alert")).to_be_visible()

def test_api_que_nunca_responde(page: Page, base_url):
    page.route("**/api/produtos", lambda r: None)  # fica pendurada
    page.goto(f"{base_url}/produtos")
    expect(page.get_by_text("Carregando")).to_be_hidden(timeout=15000)  # a UI precisa ter timeout próprio
```

## Erros de console e requisições falhas
```python
import pytest

@pytest.fixture(autouse=True)
def sem_erros_de_console(page):
    erros = []
    page.on("pageerror", lambda e: erros.append(str(e)))
    page.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    yield
    assert not erros, f"Erros de console: {erros}"
```
Se a fixture acusar erro, o defeito está no front-end; não a remova.

## Diagnóstico
`--tracing retain-on-failure`, `--screenshot only-on-failure`, `--video retain-on-failure`. Abra o trace com `playwright show-trace trace.zip`. Isso serve para entender a falha, nunca para justificar retry ou skip.

## Fluxo completo
```python
import re
from playwright.sync_api import Page, expect

def test_compra_completa(page: Page, base_url, usuario_logado):
    page.goto(f"{base_url}/produtos")
    page.get_by_role("link", name="Vestido Floral").click()
    page.get_by_role("button", name="Adicionar à sacola").click()
    page.get_by_role("link", name="Sacola").click()
    expect(page.get_by_text("Vestido Floral")).to_be_visible()
    page.get_by_role("button", name="Finalizar compra").click()
    expect(page).to_have_url(re.compile(r"/pedido/\d+/confirmacao"))
```
(Ajuste nomes e rotas ao projeto real.)
