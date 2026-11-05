# Biblioteca de componentes de interface responsivos

Sumário: 1. Regras gerais · 2. Navegação · 3. Botões e ações · 4. Cards e listas · 5. Formulários e inputs · 6. Tabelas · 7. Overlays · 8. Feedback · 9. Layouts de página · 10. Contrato de componente

## 1. Regras gerais (valem para todo componente)

- **Intrínseco antes de breakpoint**: use `minmax()`, `auto-fit`, `clamp()`, `flex-wrap` e container queries; media query só para mudanças estruturais (ex.: menu hambúrguer → barra).
- Cada componente se adapta ao **próprio contêiner** (`container-type: inline-size`), não à janela. Assim funciona em sidebar, modal ou página inteira.
- Variantes por classe/atributo (`.btn--lg`, `[data-size="lg"]`), nunca por cópia de CSS.
- Todos os estados desenhados: padrão, hover, focus-visible, active, disabled, loading, erro, vazio, selecionado.
- Alvos de toque ≥ 44px em mobile; área clicável pode ser maior que o visual (padding/pseudo-elemento).
- Teste em 320px, 375px, 768px, 1024px, 1440px e com zoom de 200%. Textos 30–40% maiores (idiomas como alemão/português) não podem quebrar o layout.
- **Contratos de dados intocados**: o frontend consome APIs e esquemas de banco como estão. Nunca renomeie campos, mude tipos, status codes, formatos de payload ou migrações para "facilitar" a UI. Se a UI precisar de outra forma, adapte no cliente (mapper/adapter) e, se a mudança de contrato for realmente necessária, apenas proponha por escrito, sem implementar.

## 2. Navegação

| Componente | Mobile | Desktop | Observações |
|---|---|---|---|
| Header/navbar | Logo + botão de menu; painel em tela cheia ou drawer | Links horizontais + CTA | `aria-expanded`, `aria-controls`, Esc fecha, foco volta ao botão |
| Sidebar | Drawer sobreposto (`<dialog>` ou `popover`) | Coluna fixa/recolhível (`grid-template-columns: 16rem 1fr`) | Recolhida: mantenha rótulos acessíveis (tooltip + `aria-label`) |
| Tabs | Rolagem horizontal com `scroll-snap` ou vira `<select>`/accordion | Linha de abas | Padrão ARIA tabs (ver `javascript-interacao.md`) |
| Breadcrumb | Oculta níveis do meio com "…" | Completo | `<nav aria-label="Breadcrumb"><ol>`; `aria-current="page"` no último |
| Paginação | Anterior/Próximo + "Página X de Y" | Números com reticências | `<nav aria-label="Paginação">`, `aria-current` na página atual |
| Bottom nav (app) | 3–5 itens, ícone + rótulo | Some ou vira sidebar | Respeite `env(safe-area-inset-bottom)` |

## 3. Botões e ações

- Hierarquia: **um** primário por tela/seção; secundário (contorno) e terciário (ghost/link) para o resto.
- Texto de ação com verbo claro ("Salvar alterações"), nunca só ícone sem `aria-label`.
- Largura total no mobile quando for a ação principal do formulário; `min-inline-size` e `padding-inline` consistentes.
- Loading: mantenha a largura (spinner no lugar do ícone), `aria-busy="true"`, desabilite reenvio.
- Grupo de botões: `display: flex; flex-wrap: wrap; gap`. Ordem no DOM = ordem de prioridade.

## 4. Cards e listas

- Grade: `repeat(auto-fit, minmax(min(100%, 16rem), 1fr))`. Alinhe rodapés com `subgrid` ou `grid-template-rows: auto 1fr auto`.
- Card clicável inteiro: um único link no título com `::after { content:""; position:absolute; inset:0 }` (evita link dentro de link e mantém texto selecionável nos demais).
- Mídia com `aspect-ratio`; título limitado com `line-clamp` apenas se o conteúdo completo estiver acessível em outro lugar.
- Lista densa (feed, tabela de dados): linhas ≥ 44px de altura, separação por borda sutil, ações secundárias reveladas em hover **e** foco.
- Estado vazio e esqueleto de carregamento (`skeleton`) fazem parte do componente.

## 5. Formulários e inputs

- Layout: 1 coluna no mobile; 2 colunas só para campos curtos relacionados (cidade/UF, validade/CVV) em ≥ 40em.
- Label sempre visível acima do campo; texto de ajuda em `aria-describedby`; erro abaixo com ícone + texto.
- Campos nativos antes de custom: `<select>`, `<input type="date">`, `<input type="range">`; estilize com `accent-color`, `appearance`. Só construa combobox/datepicker próprio se o nativo não atender e implemente o padrão ARIA completo.
- Checkbox/radio: área clicável do rótulo inteiro; toggle é `<button role="switch" aria-checked>` ou checkbox com `role="switch"`.
- Máscaras e tipos: `inputmode`, `autocomplete`, `enterkeyhint`; teclado numérico no mobile para CPF/CEP/telefone.

## 6. Tabelas

- Semântica real: `<table>`, `<caption>`, `<th scope>`; ordenação com `aria-sort` e botão no cabeçalho.
- Responsiva: (a) contêiner `overflow-x: auto` com `tabindex="0"` e `role="region" aria-label`, ou (b) transformar linhas em cards no mobile via `display: grid` + `data-label` (mantenha `<table>` no DOM e teste com leitor de tela).
- Coluna de identificação fixa (`position: sticky; inset-inline-start: 0`) em tabelas largas.

## 7. Overlays

- **Modal**: `<dialog>.showModal()`; no mobile vira *bottom sheet* (`max-block-size: 90dvh`, cantos superiores arredondados), no desktop centralizado com `max-inline-size`.
- **Popover/menu/tooltip**: atributo `popover`; tooltip nunca é o único lugar de informação essencial; aparece em hover **e** foco, é dispensável com Esc e não some ao passar o mouse sobre ele (WCAG 1.4.13).
- **Toast**: `role="status"`; erros críticos `role="alert"`; tempo suficiente para ler e pausa em hover/foco.
- **Drawer**: mesmo contrato de modal (foco preso, Esc, foco devolvido).

## 8. Feedback

- Progresso: `<progress>`/`<meter>` ou `role="progressbar"` com `aria-valuenow`.
- Skeleton com `aria-hidden` + região `aria-busy`; spinner com texto alternativo oculto ("Carregando…").
- Validação inline, banner de erro global com resumo e links para os campos.
- Mensagens humanas e específicas ("E-mail já cadastrado. Entrar?"), sem culpar o usuário.

## 9. Layouts de página (padrões reaproveitáveis)

- **Holy grail / app shell**: `grid-template: "header header" auto "nav main" 1fr / 16rem 1fr` → no mobile, uma coluna.
- **Hero**: texto + mídia em 2 colunas ≥ 48em; empilha com texto primeiro.
- **Seção de recursos**: grade auto-fit de cards.
- **Pricing**: cards lado a lado ≥ 64em; empilhados com o plano recomendado primeiro no mobile; tabela comparativa como `<table>` rolável.
- **Dashboard**: grid de 12 colunas lógicas com `grid-column: span N` por container query.
- **Formulário em etapas**: `<ol>` de passos, `aria-current="step"`, salvar progresso, botão Voltar sempre disponível.

## 10. Contrato de componente (como entregar cada um)

Para cada componente novo, entregue: (1) HTML de exemplo mínimo, (2) CSS com variáveis locais (`--btn-bg`…) e variantes, (3) JS só se necessário, com `init(el)` idempotente, (4) estados e atributos ARIA documentados em comentário de 2–3 linhas, (5) comportamento em 320px e em 1440px. Reaproveite os tokens do projeto; não crie cores ou espaçamentos fora da escala.
