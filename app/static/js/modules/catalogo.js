/**
 * MADE IN LACE — CATÁLOGO E FILTROS REATIVOS (Vanilla ES6)
 * Gerencia a filtragem em tempo real, ordenação global, slider de preço,
 * checkboxes de múltiplos tamanhos e categorias, tags de filtros ativos e
 * paginação modular (9 por vez + Carregar Mais).
 */

export function initCatalogo() {
    if (window.__catalogo_initialized) return;
    const rawDataElem = document.getElementById('produtos-dados');
    if (!rawDataElem) return;
    window.__catalogo_initialized = true;

    let todosProdutos = [];
    try {
        todosProdutos = JSON.parse(rawDataElem.textContent || '[]');
    } catch (e) {
        console.error('Erro ao ler dados dos produtos:', e);
        return;
    }

    const grid = document.getElementById('catalog-products-grid');
    const loadMoreBtn = document.getElementById('catalog-load-more-btn');
    const emptyState = document.getElementById('catalog-empty-state');
    const activeFiltersBar = document.getElementById('active-filters-bar');

    // Configurações do preço
    const priceSlider = document.getElementById('price-slider-input');
    const priceCircle = document.getElementById('price-slider-circle');
    const priceMaxInput = document.getElementById('price-max-input');
    const priceMinInput = document.getElementById('price-min-input');
    
    // Teto dinâmico baseado no produto mais caro presente nesta listagem
    let precoTeto = parseInt(priceSlider?.getAttribute('max') || '500', 10);
    if (todosProdutos.length > 0) {
        precoTeto = Math.ceil(Math.max(...todosProdutos.map((p) => p.preco_efetivo)));
    }

    // Estado reativo da página
    const state = {
        limiteVisivel: 9,
        precoMin: 0,
        precoMax: precoTeto,
        precoTetoAtual: precoTeto,
        precoAjustadoManualmente: false,
        tamanhosRoupa: [],
        tamanhosSapato: [],
        categorias: [],
        filtroGlobal: 'best_sellers',
        filtroLinha: null,
        filtroNome: null,
        filtroPesquisa: null,
    };

    // Lê filtros herdados da URL (ex: ?linha=Florestal ou ?nome=dark ou ?q=ball)
    const urlParams = new URLSearchParams(window.location.search);
    const paramLinha = urlParams.get('linha');
    const paramNome = urlParams.get('nome');
    const paramQ = urlParams.get('q');
    const paramTipoBusca = (urlParams.get('tipo_busca') || '').toLowerCase();
    const paramOrdenacao = urlParams.get('ordenacao');

    if (paramLinha) {
        state.filtroLinha = paramLinha.trim();
    } else if (paramQ && paramTipoBusca === 'linhas') {
        state.filtroLinha = paramQ.trim();
    }

    if (paramNome) {
        state.filtroNome = paramNome.trim();
    } else if (paramQ && paramTipoBusca === 'produtos') {
        state.filtroNome = paramQ.trim();
    }

    if (paramQ && !paramNome && !paramLinha && (!paramTipoBusca || paramTipoBusca === 'tudo')) {
        state.filtroPesquisa = paramQ.trim();
    }

    if (paramOrdenacao) {
        state.filtroGlobal = paramOrdenacao;
    }

    // Se a listagem inicial veio com filtro pré-selecionado e poucos produtos em memória,
    // carrega a lista completa da página base em segundo plano para permitir restauração instantânea.
    let produtosBasePromise = null;
    const temFiltroPreSelecionado = Boolean(paramLinha || paramNome || paramQ);
    if (temFiltroPreSelecionado) {
        produtosBasePromise = fetch(window.location.pathname)
            .then((r) => (r.ok ? r.text() : ''))
            .then((htmlText) => {
                if (!htmlText) return;
                const match = htmlText.match(/<script id="produtos-dados"[^>]*>([\s\S]*?)<\/script>/i);
                if (match && match[1]) {
                    try {
                        const listaCompleta = JSON.parse(match[1]);
                        if (Array.isArray(listaCompleta) && listaCompleta.length > todosProdutos.length) {
                            todosProdutos = listaCompleta;
                        }
                    } catch (e) {
                        console.warn('Erro ao processar catálogo base:', e);
                    }
                }
            })
            .catch((e) => {
                console.warn('Erro ao pré-carregar produtos base:', e);
            });
    }

    // Inicializa Dropdown dos Filtros Globais (Best Sellers)
    initGlobalFilterDropdown(state, () => {
        state.limiteVisivel = 9;
        aplicarFiltrosERenderizar();
    });

    // Inicializa Acordeões de Seção
    initAccordions();

    // Inicializa Slider de Preço
    const syncSliderVisual = (val, maxVal) => {
        if (!priceCircle) return;
        const teto = maxVal !== undefined ? maxVal : state.precoTetoAtual;
        const pct = teto > 0 ? Math.max(0, Math.min(100, (val / teto) * 100)) : 100;
        priceCircle.style.left = `${pct}%`;
    };

    if (priceSlider && priceMaxInput) {
        priceSlider.max = state.precoTetoAtual;
        priceSlider.value = state.precoMax;
        priceMaxInput.max = state.precoTetoAtual;
        priceMaxInput.value = state.precoMax;
        syncSliderVisual(state.precoMax, state.precoTetoAtual);

        priceSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value, 10);
            state.precoMax = val;
            state.precoAjustadoManualmente = val < state.precoTetoAtual;
            priceMaxInput.value = val;
            syncSliderVisual(val, state.precoTetoAtual);
            state.limiteVisivel = 9;
            aplicarFiltrosERenderizar();
        });

        priceMaxInput.addEventListener('change', (e) => {
            let val = parseInt(e.target.value, 10);
            if (isNaN(val) || val < 0) val = 0;
            if (val > state.precoTetoAtual) val = state.precoTetoAtual;
            state.precoMax = val;
            state.precoAjustadoManualmente = val < state.precoTetoAtual;
            priceSlider.value = val;
            priceMaxInput.value = val;
            syncSliderVisual(val, state.precoTetoAtual);
            state.limiteVisivel = 9;
            aplicarFiltrosERenderizar();
        });

        if (priceMinInput) {
            priceMinInput.addEventListener('change', (e) => {
                let val = parseInt(e.target.value, 10);
                if (isNaN(val) || val < 0) val = 0;
                if (val > state.precoMax) val = state.precoMax;
                state.precoMin = val;
                priceMinInput.value = val;
                state.limiteVisivel = 9;
                aplicarFiltrosERenderizar();
            });
        }
    }

    // Inicializa Checkboxes de Tamanho Roupa com query direta
    const chksRoupa = document.querySelectorAll('input[data-filter="tamanho-roupa"]');
    chksRoupa.forEach((chk) => {
        chk.addEventListener('change', () => {
            state.tamanhosRoupa = Array.from(
                document.querySelectorAll('input[data-filter="tamanho-roupa"]:checked')
            ).map((c) => c.value);
            state.limiteVisivel = 9;
            aplicarFiltrosERenderizar();
        });
    });

    // Inicializa Checkboxes de Tamanho Sapato
    const chksSapato = document.querySelectorAll('input[data-filter="tamanho-sapato"]');
    chksSapato.forEach((chk) => {
        chk.addEventListener('change', () => {
            state.tamanhosSapato = Array.from(
                document.querySelectorAll('input[data-filter="tamanho-sapato"]:checked')
            ).map((c) => c.value);
            state.limiteVisivel = 9;
            aplicarFiltrosERenderizar();
        });
    });

    // Inicializa Checkboxes de Categoria com a regra:
    // "você pode selecionar mais de um ao mesmo tempo mas selecionar os 3 tira a seleção dos 3 mostrando todas categorias novamente"
    const catCheckboxes = document.querySelectorAll('input[data-filter="categoria"]');
    catCheckboxes.forEach((chk) => {
        chk.addEventListener('change', () => {
            let selecionadas = Array.from(
                document.querySelectorAll('input[data-filter="categoria"]:checked')
            ).map((c) => c.value);

            // Se selecionou todas as 3 categorias, desseleciona as 3 e exibe tudo de novo!
            if (selecionadas.length >= 3) {
                catCheckboxes.forEach((c) => {
                    c.checked = false;
                });
                selecionadas = [];
            }

            state.categorias = selecionadas;
            state.limiteVisivel = 9;
            aplicarFiltrosERenderizar();
        });
    });

    // Botão "Carregar Mais"
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', (e) => {
            e.preventDefault();
            state.limiteVisivel += 9;
            aplicarFiltrosERenderizar();
        });
    }

    // Botão "Limpar todos os filtros"
    const resetFiltersBtn = document.getElementById('catalog-reset-filters-btn');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            resetAllFilters();
        });
    }

    async function resetAllFilters() {
        if (produtosBasePromise) {
            await produtosBasePromise;
        }
        state.precoMin = 0;
        state.precoAjustadoManualmente = false;
        if (todosProdutos.length > 0) {
            state.precoTetoAtual = Math.ceil(Math.max(...todosProdutos.map((p) => p.preco_efetivo)));
        } else {
            state.precoTetoAtual = precoTeto;
        }
        state.precoMax = state.precoTetoAtual;
        state.tamanhosRoupa = [];
        state.tamanhosSapato = [];
        state.categorias = [];
        state.filtroLinha = null;
        state.filtroNome = null;
        state.filtroPesquisa = null;
        state.limiteVisivel = 9;

        // Desmarca todos os checkboxes
        document.querySelectorAll('input[type="checkbox"]').forEach((c) => {
            c.checked = false;
        });

        // Reseta slider
        if (priceSlider) {
            priceSlider.max = state.precoTetoAtual;
            priceSlider.value = state.precoTetoAtual;
        }
        if (priceMaxInput) {
            priceMaxInput.max = state.precoTetoAtual;
            priceMaxInput.value = state.precoTetoAtual;
        }
        if (priceMinInput) priceMinInput.value = 0;
        syncSliderVisual(state.precoTetoAtual, state.precoTetoAtual);

        // Limpa query params da URL se houver
        if (window.history && window.history.pushState) {
            window.history.pushState({}, '', window.location.pathname);
        }

        if (todosProdutos.length <= 1) {
            window.location.href = window.location.pathname;
            return;
        }

        aplicarFiltrosERenderizar();
    }

    /**
     * Aplica toda a lógica de filtros e ordenação e renderiza os produtos
     */
    function aplicarFiltrosERenderizar() {
        let candidatos = [...todosProdutos];

        // 1. Filtro de Linha herdado
        if (state.filtroLinha) {
            const linhaTermo = state.filtroLinha.toLowerCase();
            candidatos = candidatos.filter((p) => (p.linha_nome || '').toLowerCase().includes(linhaTermo));
        }

        // 2. Filtro de Nome herdado
        if (state.filtroNome) {
            const nomeTermo = state.filtroNome.toLowerCase();
            candidatos = candidatos.filter((p) => (p.nome || '').toLowerCase().includes(nomeTermo));
        }

        // 3. Filtro de Pesquisa ampla (nome ou linha)
        if (state.filtroPesquisa) {
            const qTermo = state.filtroPesquisa.toLowerCase();
            candidatos = candidatos.filter(
                (p) =>
                    (p.nome || '').toLowerCase().includes(qTermo) ||
                    (p.linha_nome || '').toLowerCase().includes(qTermo)
            );
        }

        // 4. Filtro de Tamanho Roupa
        if (state.tamanhosRoupa.length > 0) {
            candidatos = candidatos.filter(
                (p) => p.tamanhos && p.tamanhos.some((t) => state.tamanhosRoupa.includes(t))
            );
        }

        // 5. Filtro de Tamanho Sapato
        if (state.tamanhosSapato.length > 0) {
            candidatos = candidatos.filter(
                (p) => p.tamanhos && p.tamanhos.some((t) => state.tamanhosSapato.includes(t))
            );
        }

        // 6. Filtro de Categoria
        if (state.categorias.length > 0) {
            const catsLower = state.categorias.map((c) => c.toLowerCase());
            candidatos = candidatos.filter((p) => {
                const tipo = (p.tipo || '').toLowerCase();
                if (catsLower.includes(tipo)) return true;
                if (catsLower.includes('vestidos') && tipo === 'roupa') return true;
                if (catsLower.includes('sapatos') && tipo === 'calcado') return true;
                if (catsLower.includes('corsets') && tipo === 'corset') return true;
                return false;
            });
        }

        // Atualiza dinamicamente o preço máximo do slider com base no produto mais caro listado
        if (candidatos.length > 0) {
            const maiorPreco = Math.ceil(Math.max(...candidatos.map((p) => p.preco_efetivo)));
            state.precoTetoAtual = maiorPreco;
            if (!state.precoAjustadoManualmente || state.precoMax > state.precoTetoAtual) {
                state.precoMax = state.precoTetoAtual;
            }
        }

        // Sincroniza atributos max e values do slider no DOM
        if (priceSlider) {
            priceSlider.max = state.precoTetoAtual;
            priceSlider.value = state.precoMax;
        }
        if (priceMaxInput) {
            priceMaxInput.max = state.precoTetoAtual;
            priceMaxInput.value = state.precoMax;
        }
        syncSliderVisual(state.precoMax, state.precoTetoAtual);

        // 7. Filtro de Preço
        let lista = candidatos.filter(
            (p) => p.preco_efetivo >= state.precoMin && p.preco_efetivo <= state.precoMax
        );

        // 8. Filtro Global / Ordenação
        lista = ordenarProdutos(lista, state.filtroGlobal);

        // Atualiza a Barra de Filtros Ativos
        renderActiveFiltersBar();

        // Renderiza no Grid e controla Empty State
        renderProductsGrid(lista);
    }

    /**
     * Ordena a lista conforme o filtro global ativo
     */
    function ordenarProdutos(lista, criterio) {
        const arr = [...lista];
        switch (criterio) {
            case 'preco_asc':
                arr.sort((a, b) => a.preco_efetivo - b.preco_efetivo);
                break;
            case 'preco_desc':
                arr.sort((a, b) => b.preco_efetivo - a.preco_efetivo);
                break;
            case 'data_asc':
                arr.sort((a, b) => (a.data_criacao || '').localeCompare(b.data_criacao || ''));
                break;
            case 'data_desc':
                arr.sort((a, b) => (b.data_criacao || '').localeCompare(a.data_criacao || ''));
                break;
            case 'alpha_asc':
                arr.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
                break;
            case 'alpha_desc':
                arr.sort((a, b) => b.nome.localeCompare(a.nome, 'pt-BR'));
                break;
            case 'promocao':
                arr.sort((a, b) => {
                    if (a.tem_promocao !== b.tem_promocao) {
                        return a.tem_promocao ? -1 : 1;
                    }
                    return b.porcentagem_promocao - a.porcentagem_promocao;
                });
                break;
            case 'best_sellers':
            default:
                arr.sort((a, b) => {
                    if (a.is_best_seller !== b.is_best_seller) {
                        return a.is_best_seller ? -1 : 1;
                    }
                    return b.id - a.id;
                });
                break;
        }
        return arr;
    }

    /**
     * Renderiza a barra superior de filtros ativos não-globais com o botão [X]
     */
    function renderActiveFiltersBar() {
        if (!activeFiltersBar) return;
        activeFiltersBar.innerHTML = '';

        const tags = [];

        // Filtro de Preço
        if (state.precoAjustadoManualmente || state.precoMin > 0 || state.precoMax < state.precoTetoAtual) {
            tags.push({
                tipo: 'preco',
                label: `R$${state.precoMin} - R$${state.precoMax}`,
                onRemove: () => {
                    state.precoMin = 0;
                    state.precoMax = state.precoTetoAtual;
                    state.precoAjustadoManualmente = false;
                    if (priceSlider) {
                        priceSlider.max = state.precoTetoAtual;
                        priceSlider.value = state.precoTetoAtual;
                    }
                    if (priceMaxInput) {
                        priceMaxInput.max = state.precoTetoAtual;
                        priceMaxInput.value = state.precoTetoAtual;
                    }
                    if (priceMinInput) priceMinInput.value = 0;
                    syncSliderVisual(state.precoTetoAtual, state.precoTetoAtual);
                    state.limiteVisivel = 9;
                    aplicarFiltrosERenderizar();
                },
            });
        }

        // Filtro de Tamanho Roupa
        if (state.tamanhosRoupa.length > 0) {
            tags.push({
                tipo: 'tamanho-roupa',
                label: state.tamanhosRoupa.join(', '),
                onRemove: () => {
                    state.tamanhosRoupa = [];
                    document.querySelectorAll('input[data-filter="tamanho-roupa"]').forEach((c) => {
                        c.checked = false;
                    });
                    state.limiteVisivel = 9;
                    aplicarFiltrosERenderizar();
                },
            });
        }

        // Filtro de Tamanho Sapato
        if (state.tamanhosSapato.length > 0) {
            tags.push({
                tipo: 'tamanho-sapato',
                label: state.tamanhosSapato.join(', '),
                onRemove: () => {
                    state.tamanhosSapato = [];
                    document.querySelectorAll('input[data-filter="tamanho-sapato"]').forEach((c) => {
                        c.checked = false;
                    });
                    state.limiteVisivel = 9;
                    aplicarFiltrosERenderizar();
                },
            });
        }

        // Filtro de Categoria
        if (state.categorias.length > 0) {
            tags.push({
                tipo: 'categoria',
                label: state.categorias.join(', '),
                onRemove: () => {
                    state.categorias = [];
                    document.querySelectorAll('input[data-filter="categoria"]').forEach((c) => {
                        c.checked = false;
                    });
                    state.limiteVisivel = 9;
                    aplicarFiltrosERenderizar();
                },
            });
        }

        // Filtro de Linha herdado
        if (state.filtroLinha) {
            tags.push({
                tipo: 'linha',
                label: `Linha: ${state.filtroLinha}`,
                onRemove: async () => {
                    state.filtroLinha = null;
                    state.limiteVisivel = 9;
                    if (produtosBasePromise) {
                        await produtosBasePromise;
                    }
                    if (window.history && window.history.pushState) {
                        const url = new URL(window.location);
                        url.searchParams.delete('linha');
                        url.searchParams.delete('q');
                        url.searchParams.delete('tipo_busca');
                        window.history.pushState({}, '', url.pathname + (url.search ? url.search : ''));
                    }
                    if (todosProdutos.length <= 1) {
                        window.location.href = window.location.pathname;
                        return;
                    }
                    aplicarFiltrosERenderizar();
                },
            });
        }

        // Filtro de Nome herdado
        if (state.filtroNome) {
            tags.push({
                tipo: 'nome',
                label: `Nome: ${state.filtroNome}`,
                onRemove: async () => {
                    state.filtroNome = null;
                    state.limiteVisivel = 9;
                    if (produtosBasePromise) {
                        await produtosBasePromise;
                    }
                    if (window.history && window.history.pushState) {
                        const url = new URL(window.location);
                        url.searchParams.delete('nome');
                        url.searchParams.delete('q');
                        url.searchParams.delete('tipo_busca');
                        window.history.pushState({}, '', url.pathname + (url.search ? url.search : ''));
                    }
                    if (todosProdutos.length <= 1) {
                        window.location.href = window.location.pathname;
                        return;
                    }
                    aplicarFiltrosERenderizar();
                },
            });
        }

        // Filtro de Pesquisa ampla
        if (state.filtroPesquisa) {
            tags.push({
                tipo: 'pesquisa',
                label: `Pesquisa: ${state.filtroPesquisa}`,
                onRemove: async () => {
                    state.filtroPesquisa = null;
                    state.limiteVisivel = 9;
                    if (produtosBasePromise) {
                        await produtosBasePromise;
                    }
                    if (window.history && window.history.pushState) {
                        const url = new URL(window.location);
                        url.searchParams.delete('q');
                        url.searchParams.delete('tipo_busca');
                        window.history.pushState({}, '', url.pathname + (url.search ? url.search : ''));
                    }
                    if (todosProdutos.length <= 1) {
                        window.location.href = window.location.pathname;
                        return;
                    }
                    aplicarFiltrosERenderizar();
                },
            });
        }

        if (tags.length === 0) {
            return;
        }

        tags.forEach((tag) => {
            const el = document.createElement('div');
            el.className = 'filter-tag';

            const spanText = document.createElement('span');
            spanText.textContent = tag.label;
            el.appendChild(spanText);

            const btnRemove = document.createElement('button');
            btnRemove.type = 'button';
            btnRemove.className = 'filter-tag__remove';
            btnRemove.setAttribute('aria-label', `Remover filtro ${tag.label}`);
            btnRemove.innerHTML = '&#10005;'; // '✕'

            btnRemove.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                tag.onRemove();
            });

            el.appendChild(btnRemove);
            activeFiltersBar.appendChild(el);
        });
    }

    /**
     * Renderiza o grid de produtos (9 por vez + Carregar Mais) e sincroniza estado vazio
     */
    function renderProductsGrid(lista) {
        if (!grid) return;

        if (lista.length === 0) {
            // Nenhum produto encontrado com os filtros
            grid.style.display = 'none';
            if (emptyState) {
                emptyState.removeAttribute('hidden');
                emptyState.classList.add('is-visible');
            }
            if (loadMoreBtn) {
                loadMoreBtn.setAttribute('hidden', '');
                loadMoreBtn.style.display = 'none';
            }
            return;
        }

        // Produtos encontrados: exibe grid e esconde empty state
        grid.style.display = 'grid';
        if (emptyState) {
            emptyState.setAttribute('hidden', '');
            emptyState.classList.remove('is-visible');
        }

        const visiveis = lista.slice(0, state.limiteVisivel);

        grid.innerHTML = visiveis
            .map((p) => {
                const imgUrl = p.imagem_principal
                    ? `/static/${p.imagem_principal.replace(/^\/?(static\/)?/, '')}`
                    : '/static/img/produtos/midday-phantom-dress-1.png';

                const ratingHtml =
                    p.media_avaliacoes !== null && p.media_avaliacoes > 0
                        ? `<div class="catalog-card__rating">
                                <span class="catalog-card__rating-val">${p.media_avaliacoes.toFixed(1)}</span>
                                <span class="catalog-card__star">&#9733;</span>
                                <span class="catalog-card__rating-count">(${p.total_avaliacoes})</span>
                           </div>`
                        : '';

                const precoFormatado = p.preco.toLocaleString('pt-BR', {
                    style: 'currency',
                    currency: 'BRL',
                });

                let precosHtml = `<span class="catalog-card__price-current">${precoFormatado}</span>`;
                if (p.tem_promocao && p.preco_promocional !== null) {
                    const promoFormatado = p.preco_promocional.toLocaleString('pt-BR', {
                        style: 'currency',
                        currency: 'BRL',
                    });
                    precosHtml = `
                        <span class="catalog-card__price-original">${precoFormatado}</span>
                        <span class="catalog-card__price-current">${promoFormatado}</span>
                    `;
                }

                let badgeHtml = '';
                if (p.tem_promocao) {
                    badgeHtml = `<span class="catalog-badge">Promoção</span>`;
                } else if (p.is_best_seller) {
                    badgeHtml = `<span class="catalog-badge">Best Seller</span>`;
                }

                return `
                    <article class="catalog-product-card" data-product-id="${p.id}">
                        <a href="/produtos/${p.id}" class="catalog-card__media-link" aria-label="Ver detalhes de ${escapeHtml(p.nome)}">
                            <img 
                                src="${imgUrl}" 
                                alt="${escapeHtml(p.nome)}" 
                                class="catalog-card__img"
                                loading="lazy"
                                width="320" 
                                height="420"
                            >
                        </a>
                        <div class="catalog-card__content">
                            <h2 class="catalog-card__title">
                                <a href="/produtos/${p.id}">${escapeHtml(p.nome)}</a>
                            </h2>
                            <div class="catalog-card__info-row">
                                <div class="catalog-card__prices">
                                    ${precosHtml}
                                </div>
                                ${ratingHtml}
                            </div>
                            ${badgeHtml ? `<div class="catalog-card__badges">${badgeHtml}</div>` : ''}
                        </div>
                    </article>
                `;
            })
            .join('');

        // Controle de visibilidade do botão "Carregar Mais"
        if (loadMoreBtn) {
            if (lista.length > state.limiteVisivel) {
                loadMoreBtn.removeAttribute('hidden');
                loadMoreBtn.style.display = 'inline-flex';
            } else {
                loadMoreBtn.setAttribute('hidden', '');
                loadMoreBtn.style.display = 'none';
            }
        }
    }

    // Primeira renderização
    aplicarFiltrosERenderizar();
}

/**
 * Inicializa a caixa e dropdown dos Filtros Globais (Best Sellers)
 */
function initGlobalFilterDropdown(state, onChange) {
    const trigger = document.getElementById('global-filter-trigger');
    const dropdown = document.getElementById('global-filter-dropdown');
    const triggerLabel = document.getElementById('global-filter-label');

    if (!trigger || !dropdown) return;

    const labelsMap = {
        preco_asc: 'Preço. Baixo Para Alto',
        preco_desc: 'Preço. Alto para Baixo',
        data_asc: 'Data. Antigo para Novo',
        data_desc: 'Data. Novo para Antigo',
        alpha_asc: 'Alfabético. A-Z',
        alpha_desc: 'Alfabético. Z-A',
        best_sellers: 'Best Sellers',
        promocao: 'Promoção',
    };

    if (triggerLabel && labelsMap[state.filtroGlobal]) {
        triggerLabel.textContent = labelsMap[state.filtroGlobal];
    }

    function closeDropdown() {
        dropdown.classList.remove('is-open');
        dropdown.setAttribute('hidden', '');
        trigger.setAttribute('aria-expanded', 'false');
    }

    function openDropdown() {
        dropdown.classList.add('is-open');
        dropdown.removeAttribute('hidden');
        trigger.setAttribute('aria-expanded', 'true');
    }

    function toggleDropdown() {
        if (dropdown.classList.contains('is-open')) {
            closeDropdown();
        } else {
            openDropdown();
        }
    }

    // Começa explicitamente fechado
    closeDropdown();

    trigger.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleDropdown();
    });

    document.querySelectorAll('.global-filter-option').forEach((opt) => {
        opt.addEventListener('click', (e) => {
            e.preventDefault();
            const val = opt.getAttribute('data-value');
            if (!val) return;

            state.filtroGlobal = val;

            // Atualiza classe is-active (sublinhado)
            document.querySelectorAll('.global-filter-option').forEach((o) => {
                o.classList.toggle('is-active', o === opt);
            });

            if (triggerLabel && labelsMap[val]) {
                triggerLabel.textContent = labelsMap[val];
            }

            closeDropdown();
            onChange();
        });
    });

    // Fecha ao clicar fora ou com Escape
    document.addEventListener('click', (e) => {
        if (
            dropdown.classList.contains('is-open') &&
            !dropdown.contains(e.target) &&
            !trigger.contains(e.target)
        ) {
            closeDropdown();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && dropdown.classList.contains('is-open')) {
            closeDropdown();
            trigger.focus();
        }
    });
}

/**
 * Inicializa acordeões expansíveis das seções de filtros
 */
function initAccordions() {
    document.querySelectorAll('.filter-section__header').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const section = btn.closest('.filter-section');
            if (!section) return;
            const isCollapsed = section.classList.toggle('is-collapsed');
            btn.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
        });
    });
}

function escapeHtml(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Auto-inicialização segura contra timing de carregamento
function startCatalogoSafe() {
    if (window.__catalogo_started) return;
    window.__catalogo_started = true;
    initCatalogo();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startCatalogoSafe);
} else {
    startCatalogoSafe();
}
