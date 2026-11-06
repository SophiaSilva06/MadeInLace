/**
 * MADE IN LACE — CARRINHO LATERAL (Vanilla ES6)
 * Orquestrador do Drawer do Carrinho:
 * - Abertura/fechamento estrito (apenas no botão 'X', não fecha ao clicar fora)
 * - Cabeçalho e Rodapé estáticos, rolagem interna nos itens
 * - Medidor dinâmico de frete grátis (R$ 160,00) que fica verde quando completo
 * - Timer de reserva dinâmico (MM:SS:CC) calculado a partir do banco de dados
 * - Modificação de quantidade (+/-) e remoção de item pelo 'X' do card
 * - Integração via Fetch com endpoints REST
 */

let timerIntervalId = null;
let itensCarrinhoCache = [];
let estadoCarrinhoCache = null;
let alertTimeoutId = null;
let isOperacaoEmAndamento = false;

/**
 * Monta a URL de login redirecionando de volta à página atual com parâmetro para reabrir o carrinho
 */
function obterUrlLoginRetorno() {
    const currentPath = window.location.pathname + window.location.search;
    const isAuthPage = currentPath.startsWith('/login') || currentPath.startsWith('/registro') || currentPath.startsWith('/logout');
    const returnPath = isAuthPage ? '/' : currentPath;
    const separator = returnPath.includes('?') ? '&' : '?';
    return `/login?next=${encodeURIComponent(returnPath + separator + 'abrir_carrinho=1')}`;
}

/**
 * Inicialização principal do carrinho lateral
 */
export function initCarrinhoDrawer() {
    const drawer = document.getElementById('cart-drawer');
    if (!drawer) return;

    const closeBtn = document.getElementById('cart-drawer-close-btn');
    const toggleBtns = document.querySelectorAll('.header-action-btn--cart, #cart-drawer-toggle-btn');
    const itemsList = document.getElementById('cart-drawer-list');

    // Ao clicar no carrinho, deve levar ao login se não estiver autenticado (Regra do usuário)
    toggleBtns.forEach((btn) => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();

            // 1. Checa atributo data-authenticated do HTML gerado pelo servidor
            const authAttr = btn.getAttribute('data-authenticated');
            if (authAttr === 'false') {
                window.location.href = obterUrlLoginRetorno();
                return;
            }

            // 2. Se o estado em cache da API indica que o visitante não está autenticado
            if (estadoCarrinhoCache && estadoCarrinhoCache.autenticado === false) {
                window.location.href = obterUrlLoginRetorno();
                return;
            }

            // 3. Se o cache ainda não carregou e o HTML não garantiu login, consulta a API antes de abrir
            if (!estadoCarrinhoCache && authAttr !== 'true') {
                try {
                    const response = await fetch('/api/carrinho', { headers: { 'Accept': 'application/json' } });
                    if (response.ok) {
                        const data = await response.json();
                        estadoCarrinhoCache = data;
                        if (!data.autenticado) {
                            window.location.href = obterUrlLoginRetorno();
                            return;
                        }
                    }
                } catch (err) {
                    console.error('Erro ao verificar sessão do carrinho:', err);
                }
            }

            abrirCarrinho();
        });
    });

    // Abre automaticamente se o usuário acabou de voltar do login com abrir_carrinho=1
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('abrir_carrinho') === '1') {
        urlParams.delete('abrir_carrinho');
        const remainingQuery = urlParams.toString();
        const cleanUrl = window.location.pathname + (remainingQuery ? `?${remainingQuery}` : '') + window.location.hash;
        window.history.replaceState({}, document.title, cleanUrl);
        abrirCarrinho();
    }

    // Delegação de eventos única para ações nos itens do carrinho (diminuir, aumentar, remover)
    if (itemsList && !itemsList.dataset.bound) {
        itemsList.dataset.bound = 'true';
        itemsList.addEventListener('click', async (e) => {
            const target = e.target.closest('button[data-action]');
            if (!target) return;

            const action = target.getAttribute('data-action');
            const itemId = parseInt(target.getAttribute('data-id'), 10);
            const currentQty = parseInt(target.getAttribute('data-qty') || '1', 10);

            if (!itemId || isOperacaoEmAndamento) return;
            isOperacaoEmAndamento = true;
            target.disabled = true;

            try {
                if (action === 'remover') {
                    await executarRemoverItem(itemId);
                } else if (action === 'incrementar') {
                    await executarAtualizarQuantidade(itemId, currentQty + 1);
                } else if (action === 'decrementar' && currentQty > 1) {
                    await executarAtualizarQuantidade(itemId, currentQty - 1);
                }
            } finally {
                isOperacaoEmAndamento = false;
                target.disabled = false;
            }
        });
    }

    // Fecha EXCLUSIVAMENTE ao clicar no 'X' superior direito (Regra do usuário)
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            fecharCarrinho();
        });
    }

    // Tecla Escape para acessibilidade WCAG
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && drawer.classList.contains('is-open')) {
            fecharCarrinho();
        }
    });

    // Validação ao clicar em 'IR PARA O PAGAMENTO'
    initCheckoutValidation();

    // Escuta evento global de inclusão de produto vindo da página de detalhe
    window.addEventListener('carrinho:adicionar', (e) => {
        if (e.detail) {
            adicionarAoCarrinho(e.detail);
        }
    });

    // Carrega o estado inicial do carrinho silenciosamente
    atualizarEstadoCarrinho(false);
}

/**
 * Valida clique no botão 'IR PARA O PAGAMENTO' para usuários sem itens
 */
function initCheckoutValidation() {
    const checkoutBtn = document.getElementById('cart-drawer-checkout-btn');
    if (!checkoutBtn) return;

    checkoutBtn.addEventListener('click', (e) => {
        // Se por algum motivo o usuário não estiver autenticado
        if (estadoCarrinhoCache && estadoCarrinhoCache.autenticado === false) {
            e.preventDefault();
            window.location.href = `/login?next=${encodeURIComponent('/checkout')}`;
            return;
        }

        // Se logado mas sem itens no carrinho, exibe a mensagem de aviso exigida
        const totalItens = estadoCarrinhoCache?.quantidade_total ?? itensCarrinhoCache.length;
        if (totalItens <= 0) {
            e.preventDefault();
            exibirAlertaCarrinho('Adicione Produtos Para Ir Ao Pagamento');
        }
    });
}

/**
 * Exibe mensagem de validação no rodapé do carrinho ou toast não bloqueante
 */
function exibirAlertaCarrinho(mensagem) {
    const alertEl = document.getElementById('cart-drawer-alert');
    const alertText = document.getElementById('cart-drawer-alert-text');
    if (alertEl) {
        if (alertText) alertText.textContent = mensagem;
        alertEl.removeAttribute('hidden');
        alertEl.style.display = 'flex';
        alertEl.classList.remove('is-shaking');
        void alertEl.offsetWidth; // reinicia animação
        alertEl.classList.add('is-shaking');

        if (alertTimeoutId) clearTimeout(alertTimeoutId);
        alertTimeoutId = setTimeout(() => {
            alertEl.setAttribute('hidden', '');
            alertEl.style.display = 'none';
        }, 5000);
    } else {
        // Fallback não bloqueante caso o drawer não esteja presente no DOM
        console.warn('Alerta do Carrinho:', mensagem);
    }
}

/**
 * Abre o carrinho lateral
 */
export function abrirCarrinho() {
    const drawer = document.getElementById('cart-drawer');
    if (!drawer) return;

    drawer.removeAttribute('hidden');
    // Força reflow antes de adicionar a classe para animar
    void drawer.offsetWidth;
    drawer.classList.add('is-open');

    // Acessibilidade: foca no botão de fechar
    const closeBtn = document.getElementById('cart-drawer-close-btn');
    if (closeBtn) closeBtn.focus();

    // Atualiza dados e inicia cronômetros
    atualizarEstadoCarrinho(true);
}

/**
 * Fecha o carrinho lateral
 */
export function fecharCarrinho() {
    const drawer = document.getElementById('cart-drawer');
    if (!drawer) return;

    drawer.classList.remove('is-open');
    pararTimers();

    setTimeout(() => {
        if (!drawer.classList.contains('is-open')) {
            drawer.setAttribute('hidden', '');
        }
    }, 320);
}

/**
 * Busca os dados do carrinho ativo na API e renderiza os componentes
 */
export async function atualizarEstadoCarrinho(abrirAposAtualizar = false) {
    try {
        const response = await fetch('/api/carrinho', {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
        });

        if (!response.ok) return;

        const data = await response.json();
        renderizarCarrinho(data);

        if (abrirAposAtualizar) {
            iniciarTimers();
        }
    } catch (err) {
        console.error('Erro ao buscar dados do carrinho:', err);
    }
}

/**
 * Renderiza todos os blocos do carrinho com os dados da API
 */
function renderizarCarrinho(data) {
    const countBadge = document.getElementById('cart-drawer-count');
    const headerBadges = document.querySelectorAll('.cart-count-badge');
    const shippingMsg = document.getElementById('cart-shipping-message');
    const shippingFill = document.getElementById('cart-shipping-fill');
    const shippingMeter = document.querySelector('.cart-drawer__shipping-meter');
    const totalVal = document.getElementById('cart-drawer-total-val');
    const emptyState = document.getElementById('cart-drawer-empty');
    const itemsList = document.getElementById('cart-drawer-list');

    const totalItens = data.quantidade_total || 0;
    const itens = data.itens || [];
    itensCarrinhoCache = itens;
    estadoCarrinhoCache = data;

    // Se houver itens, oculta alerta de produtos pendentes
    const alertEl = document.getElementById('cart-drawer-alert');
    if (totalItens > 0 && alertEl) {
        alertEl.setAttribute('hidden', '');
        alertEl.style.display = 'none';
    }

    // 1. Contador de itens no cabeçalho
    if (countBadge) countBadge.textContent = String(totalItens);
    headerBadges.forEach((badge) => {
        badge.textContent = String(totalItens);
        badge.style.display = totalItens > 0 ? '' : 'none';
    });

    // 2. Medidor de frete grátis (R$ 160,00)
    const isFreteGratis = Boolean(data.frete_gratis);
    const subtotal = data.subtotal || 0;
    const meta = data.meta_frete_gratis || 160.0;
    const valorFalta = Math.max(0, meta - subtotal);
    const porcentagem = Math.min(100, (subtotal / meta) * 100);

    if (shippingFill) {
        shippingFill.style.width = `${porcentagem}%`;
    }

    if (shippingMsg && shippingMeter) {
        if (isFreteGratis || valorFalta <= 0) {
            shippingMsg.textContent = 'Seu pedido recebe frete grátis!';
            shippingMsg.classList.add('is-complete');
            shippingMeter.classList.add('is-complete');
        } else {
            // Formata o valor faltante (ex: Gaste mais R$30 para ter frete grátis! ou R$ 30,00)
            const valorFaltaTexto = formatarMoedaLocal(valorFalta);
            shippingMsg.textContent = `Gaste mais ${valorFaltaTexto} para ter frete grátis!`;
            shippingMsg.classList.remove('is-complete');
            shippingMeter.classList.remove('is-complete');
        }
    }

    // 3. Valor Total
    if (totalVal) {
        totalVal.textContent = data.total_formatado || formatarMoedaLocal(data.total || 0);
    }

    // 4. Lista de Itens vs Estado Vazio
    if (itens.length === 0) {
        if (emptyState) emptyState.style.display = 'flex';
        if (itemsList) {
            itemsList.innerHTML = '';
            itemsList.style.display = 'none';
        }
        pararTimers();
        return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (itemsList) {
        itemsList.style.display = 'flex';
        itemsList.innerHTML = '';

        itens.forEach((item) => {
            const li = document.createElement('li');
            li.className = 'cart-item';
            li.setAttribute('data-item-id', String(item.id));

            const imgUrl = item.imagem_url.startsWith('http')
                ? item.imagem_url
                : `/static/${item.imagem_url.replace(/^\/+/, '')}`;

            li.innerHTML = `
                <!-- Botão 'X' superior direito do card -->
                <button 
                    type="button" 
                    class="cart-item__remove-btn" 
                    data-action="remover" 
                    data-id="${item.id}" 
                    aria-label="Remover ${item.nome} do carrinho"
                    title="Remover produto"
                >&times;</button>

                <!-- Miniatura da foto -->
                <img 
                    src="${imgUrl}" 
                    alt="${item.nome}" 
                    class="cart-item__thumb" 
                    width="68" 
                    height="68" 
                    loading="lazy"
                >

                <!-- Informações e Controles -->
                <div class="cart-item__content">
                    <div>
                        <h3 class="cart-item__title" title="${item.nome}">${item.nome}</h3>
                        <p class="cart-item__variation">Variação: ${item.cor}, ${item.tamanho}</p>
                    </div>

                    <div class="cart-item__actions-row">
                        <!-- Seletor de Quantidade [- | QNT | +] -->
                        <div class="cart-item__qty-box" role="group" aria-label="Quantidade de ${item.nome}">
                            <button 
                                type="button" 
                                class="cart-item__qty-btn" 
                                data-action="decrementar" 
                                data-id="${item.id}" 
                                data-qty="${item.quantidade}"
                                ${item.quantidade <= 1 ? 'disabled' : ''}
                                aria-label="Diminuir quantidade"
                            >&minus;</button>
                            <span class="cart-item__qty-val" aria-live="polite">${item.quantidade}</span>
                            <button 
                                type="button" 
                                class="cart-item__qty-btn" 
                                data-action="incrementar" 
                                data-id="${item.id}" 
                                data-qty="${item.quantidade}"
                                ${item.quantidade >= 10 ? 'disabled' : ''}
                                aria-label="Aumentar quantidade"
                            >&plus;</button>
                        </div>

                        <!-- Badge de Preço com Decimal (ex: R$ 180,00) -->
                        <div class="cart-item__price-badge">
                            ${item.preco_unitario_formatado || formatarMoedaLocal(item.preco_unitario)}
                        </div>

                        <!-- Badge de Timer (ex: 5:22:14) -->
                        <div 
                            class="cart-item__timer-badge ${item.expirado ? 'is-expired' : ''}" 
                            id="timer-badge-${item.id}" 
                            data-reservado-ate="${item.reservado_ate}"
                            aria-label="Tempo de reserva restante"
                        >
                            ${calcularTimerFormatado(item.reservado_ate)}
                        </div>
                    </div>
                </div>
            `;

            itemsList.appendChild(li);
        });

    }
}

/**
 * Envia requisição para adicionar item ao carrinho
 */
export async function adicionarAoCarrinho({ produtoId, variacaoId, tamanho, cor, quantidade = 1 }) {
    try {
        const response = await fetch('/api/carrinho/adicionar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify({
                produto_id: produtoId ? parseInt(produtoId, 10) : null,
                variacao_id: variacaoId ? parseInt(variacaoId, 10) : null,
                tamanho: tamanho || null,
                cor: cor || null,
                quantidade: parseInt(quantidade, 10) || 1,
            }),
        });

        // Visitante não logado é enviado para login e retorna ao produto (Seção 9)
        if (response.status === 401) {
            const data = await response.json();
            const loginUrl = data.login_url || obterUrlLoginRetorno();
            window.location.href = loginUrl;
            return;
        }

        const resData = await response.json();
        if (resData.success && resData.carrinho) {
            renderizarCarrinho(resData.carrinho);
            abrirCarrinho();
        } else {
            exibirAlertaCarrinho(resData.message || 'Não foi possível adicionar o produto ao carrinho.');
        }
    } catch (err) {
        console.error('Erro ao adicionar produto:', err);
        exibirAlertaCarrinho('Ocorreu um erro ao adicionar o produto. Verifique sua conexão.');
    }
}

/**
 * Atualiza a quantidade do item na API
 */
async function executarAtualizarQuantidade(itemId, novaQuantidade) {
    try {
        const response = await fetch('/api/carrinho/atualizar-quantidade', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify({ item_id: itemId, quantidade: novaQuantidade }),
        });

        const resData = await response.json();
        if (resData.success && resData.carrinho) {
            renderizarCarrinho(resData.carrinho);
            iniciarTimers();
        } else {
            exibirAlertaCarrinho(resData.message || 'Erro ao atualizar quantidade.');
            atualizarEstadoCarrinho(false);
        }
    } catch (err) {
        console.error('Erro ao atualizar quantidade:', err);
        exibirAlertaCarrinho('Erro de conexão ao atualizar a quantidade.');
    }
}

/**
 * Remove o item na API
 */
async function executarRemoverItem(itemId) {
    try {
        const response = await fetch('/api/carrinho/remover', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify({ item_id: itemId }),
        });

        const resData = await response.json();
        if (resData.success && resData.carrinho) {
            renderizarCarrinho(resData.carrinho);
            iniciarTimers();
        } else {
            exibirAlertaCarrinho(resData.message || 'Erro ao remover item.');
        }
    } catch (err) {
        console.error('Erro ao remover item:', err);
        exibirAlertaCarrinho('Erro de conexão ao remover o produto.');
    }
}

/**
 * Formatação de moeda no padrão BRL (R$ 180,00)
 */
function formatarMoedaLocal(val) {
    const num = Number(val) || 0;
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

/**
 * Calcula a string do cronômetro MM:SS:CC (Minutos:Segundos:Centésimos)
 * baseado no horário ISO vindo do banco de dados (ex: 5:22:14)
 */
function calcularTimerFormatado(dataIso) {
    if (!dataIso) return '0:00:00';
    const target = new Date(dataIso).getTime();
    const diff = target - Date.now();

    if (diff <= 0) {
        return '0:00:00';
    }

    const minutos = Math.floor(diff / 60000);
    const segundos = Math.floor((diff % 60000) / 1000);
    const centesimos = Math.floor((diff % 1000) / 10);

    const sSec = String(segundos).padStart(2, '0');
    const sCent = String(centesimos).padStart(2, '0');

    return `${minutos}:${sSec}:${sCent}`;
}

/**
 * Inicia o loop de atualização contínua dos cronômetros enquanto o drawer estiver aberto
 */
function iniciarTimers() {
    pararTimers();

    function tick() {
        const badges = document.querySelectorAll('.cart-item__timer-badge');
        let todosExpirados = true;

        badges.forEach((badge) => {
            const dataIso = badge.getAttribute('data-reservado-ate');
            if (!dataIso) return;

            const target = new Date(dataIso).getTime();
            const diff = target - Date.now();

            if (diff > 0) {
                todosExpirados = false;
                badge.textContent = calcularTimerFormatado(dataIso);
                badge.classList.remove('is-expired');
            } else {
                badge.textContent = '0:00:00';
                badge.classList.add('is-expired');
            }
        });

        if (todosExpirados && badges.length > 0) {
            // Reserva esgotada
        }
    }

    tick();
    timerIntervalId = setInterval(tick, 50); // 50ms para centésimos suaves
}

/**
 * Interrompe a execução dos cronômetros
 */
function pararTimers() {
    if (timerIntervalId !== null) {
        clearInterval(timerIntervalId);
        timerIntervalId = null;
    }
}
