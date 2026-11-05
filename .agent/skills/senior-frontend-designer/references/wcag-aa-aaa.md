# Conformidade WCAG 2.2: níveis AA (padrão) e AAA (quando pedido ou viável)

**Meta padrão: AA em tudo.** Aplique AAA nos critérios que não conflitam com o design (muitos são baratos) e **declare** o nível alcançado na entrega. AAA total não é exigido pela W3C para sites inteiros; quando o usuário pedir "AAA", aplique todos os critérios AAA aplicáveis e liste os que não puderam ser atendidos e por quê.

Sumário: 1. POUR · 2. Critérios por princípio (AA / AAA) · 3. Padrões de implementação · 3b. Teclado, ARIA e formulários · 4. Teste · 5. Declaração de conformidade

## 1. Princípios (POUR)

Perceptível, Operável, Compreensível, Robusto. Use HTML semântico primeiro; ARIA só para lacunas.

## 2. Critérios por princípio

### Perceptível
| Critério | AA | AAA |
|---|---|---|
| Texto alternativo (1.1.1) | `alt` útil ou vazio se decorativa | Alternativa equivalente para tudo que for tempo-dependente |
| Legendas/transcrição (1.2.x) | Legendas e audiodescrição em vídeo gravado | Língua de sinais, audiodescrição estendida, alternativa de mídia completa |
| Estrutura e relações (1.3.1) | Cabeçalhos, listas, tabelas, labels semânticos | — |
| Orientação (1.3.4) | Não travar retrato/paisagem | — |
| Finalidade do input (1.3.5) | `autocomplete` correto | Finalidade de ícones/controles (1.3.6) |
| Contraste de texto (1.4.3 / 1.4.6) | ≥ 4.5:1 (3:1 texto grande) | **≥ 7:1 (4.5:1 texto grande)** |
| Redimensionar (1.4.4) | Zoom 200% sem perda | — |
| Imagens de texto (1.4.5 / 1.4.9) | Evitar | Proibir (exceto logotipo) |
| Reflow (1.4.10) | Sem rolagem em 320px CSS (400%) | — |
| Contraste não textual (1.4.11) | UI e gráficos ≥ 3:1 | — |
| Espaçamento de texto (1.4.12) | Suporta `line-height 1.5`, `letter-spacing .12em`, `word-spacing .16em`, parágrafo `2em` sem corte | — |
| Conteúdo em hover/foco (1.4.13) | Dispensável, passável, persistente | — |
| Apresentação visual (1.4.8) | — | Largura ≤ 80 caracteres, sem justificado, entrelinha ≥ 1.5, escolha de cores pelo usuário |
| Áudio de fundo (1.4.7) | — | Fundo baixo (≥ 20 dB menor) ou desligável |

### Operável
| Critério | AA | AAA |
|---|---|---|
| Teclado (2.1.1 / 2.1.3) | Tudo por teclado, sem armadilha | Sem exceções de teclado |
| Atalhos de caractere (2.1.4) | Desativáveis/remapeáveis | — |
| Tempo (2.2.1 / 2.2.6) | Ajustável/estendível | Avisar sobre perda de dados por inatividade; sem limites de tempo (2.2.3) |
| Pausar, parar, ocultar (2.2.2) | Movimento > 5s controlável | Sem interrupções (2.2.4); reautenticar sem perda (2.2.5) |
| Flashes (2.3.1 / 2.3.2) | ≤ 3 por segundo | Nenhum flash acima de 3/s |
| Animação por interação (2.3.3) | — | Desativável (use `prefers-reduced-motion`) |
| Bypass blocks (2.4.1) | Skip link, landmarks | Cabeçalhos de seção (2.4.10) |
| Título, ordem de foco, propósito do link (2.4.2/3/4) | Sim | Propósito do link só pelo texto (2.4.9) |
| Múltiplas formas / cabeçalhos e rótulos (2.4.5/6) | Sim | Localização atual (breadcrumb/menu) (2.4.8) |
| **Foco visível (2.4.7)** e **não obscurecido (2.4.11)** | Foco visível e não coberto por sticky/overlay | Foco totalmente visível (2.4.12); aparência de foco reforçada (2.4.13: contorno ≥ 2px, contraste ≥ 3:1) |
| Gestos, ponteiro, cancelamento (2.5.1/2/4) | Alternativa a gestos de caminho; cancelável | — |
| Rótulo no nome (2.5.3) | Nome acessível contém o texto visível | — |
| **Arrastar (2.5.7)** | Alternativa por clique/toque | — |
| **Tamanho do alvo (2.5.8 / 2.5.5)** | ≥ 24×24px (ou espaçamento equivalente) | **≥ 44×44px** |
| Mecanismos de entrada concorrentes (2.5.6) | — | Não restringir a um tipo de entrada |

### Compreensível
| Critério | AA | AAA |
|---|---|---|
| Idioma (3.1.1 / 3.1.2) | `lang` na página e trechos | Palavras incomuns/abreviações explicadas (3.1.3/4), nível de leitura (3.1.5), pronúncia (3.1.6) |
| Foco/entrada sem mudança de contexto (3.2.1/2) | Sem surpresas | Sem mudanças automáticas (3.2.5) |
| Navegação consistente (3.2.3/4) | Sim | — |
| **Ajuda consistente (3.2.6)** | Ajuda no mesmo lugar | — |
| Identificação e sugestão de erro (3.3.1/3.3.3) | Erro textual, sugestão de correção | Ajuda contextual (3.3.5) |
| Prevenção de erros (3.3.4) | Reversível/confirmável em dados legais/financeiros | Para todos os envios (3.3.6) |
| **Entrada redundante (3.3.7)** | Não pedir de novo o já informado | — |
| **Autenticação acessível (3.3.8 / 3.3.9)** | Sem teste cognitivo (permita colar, gerenciadores de senha, passkeys) | Sem nenhum teste cognitivo, inclusive reconhecimento de objetos |

### Robusto
- Nome, função e valor (4.1.2): controles nativos ou ARIA completo e correto.
- Mensagens de status (4.1.3): `role="status"`/`aria-live` para resultados, erros e progresso sem mover foco.
- HTML sem erros graves de parsing (IDs únicos, aninhamento válido).

## 3. Padrões de implementação (resumo)

- **Cor**: tokens com pares texto/fundo validados por `scripts/contrast.py`; para AAA, escolha dois conjuntos de tokens ou escureça/clareie o necessário. Nunca só cor para estado.
- **Foco**: `:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }` com ≥ 3:1 contra todos os fundos vizinhos; `scroll-padding-top` ≥ altura do header sticky.
- **Alvos**: `min-block-size: 2.75rem; min-inline-size: 2.75rem;` (44px) em controles; em linha de texto ≥ 24px de área efetiva.
- **Texto**: `max-inline-size: 70ch`, `line-height: 1.5–1.7`, `text-align: start` (não justificado em AAA), `rem` sempre; `overflow-wrap: anywhere` em conteúdo longo.
- **Movimento**: `prefers-reduced-motion` global; botão de pausa em carrosséis/autoplay.
- **Formulários**: `label`, `autocomplete`, `aria-describedby`, `aria-invalid`, resumo de erros com links, foco no primeiro erro, sem bloquear colar.
- **Modo de alto contraste**: `@media (forced-colors: active)` usando cores do sistema (`CanvasText`, `Canvas`, `Highlight`), bordas visíveis em botões/inputs (não depender de `box-shadow`/`background` para limites); `prefers-contrast: more` aumenta bordas e contraste.
- **Idioma**: `lang="pt-BR"` no `<html>`, `lang="en"` em trechos estrangeiros.
- **Tabelas, gráficos**: tabela de dados alternativa ou descrição textual; cores + padrões/rótulos diretos nos gráficos.

## 3b. Teclado, ARIA e formulários (padrões rápidos)

- **Teclado**: tudo operável por Tab/Shift+Tab/Enter/Space/Esc/setas; ordem do DOM = ordem visual; sem `tabindex` positivo; skip link `<a class="skip-link" href="#main">` como primeiro focável. Modal: `<dialog>.showModal()` (foco preso, Esc, fundo inerte) e foco devolvido ao gatilho.
- **ARIA**: HTML nativo primeiro. Menu: `aria-expanded` + `aria-controls`; item atual: `aria-current`; tabs com `role` e setas; regiões dinâmicas `aria-live="polite"`; botão só de ícone com `aria-label`; ícone decorativo `aria-hidden="true"`. ARIA errada é pior que nenhuma.
- **Formulários**: `label` visível, `fieldset/legend`, `autocomplete`/`type`/`inputmode`, erro em texto ligado por `aria-describedby` + `aria-invalid`, foco no primeiro campo inválido, botão com `aria-busy` e sem duplo envio.
- **Mídia**: `alt` descreve a função; decorativa `alt=""`; vídeo com legendas; autoplay só mudo e com pausa; SVG informativo com `role="img"` + `aria-label`.

## 4. Teste

1. **Automático**: axe-core/Lighthouse/pa11y se o ambiente permitir (cobre ~30–40% dos problemas).
2. **Contraste**: `python scripts/contrast.py` para cada par de tokens; testar estados (hover, disabled, foco, placeholder, links em texto).
3. **Teclado**: percorra a página inteira com Tab/Shift+Tab/Enter/Space/Esc/setas; foco sempre visível, sem armadilhas.
4. **Zoom e reflow**: 200% e 400% (320px); espaçamento de texto aumentado (bookmarklet/CSS de teste).
5. **Leitor de tela**: NVDA/VoiceOver/TalkBack nos fluxos principais (menu, formulário, modal, tabela).
6. **Preferências**: `prefers-reduced-motion`, `prefers-color-scheme`, `forced-colors`, `prefers-contrast`.
7. **Mobile**: alvos, orientação, gestos.

## 5. Declaração de conformidade (na resposta final)

Informe em 3–5 linhas: nível alvo (AA ou AAA), critérios AAA atendidos, **desvios conhecidos** (ex.: "contraste do texto sobre imagem do hero é 4.6:1; AAA exigiria escurecer o overlay"), o que foi verificado e o que o time ainda precisa testar manualmente (leitor de tela real). Não afirme "100% acessível" sem teste humano.
