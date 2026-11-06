/**
 * MADE IN LACE — MAIN JAVASCRIPT (Vanilla ES6)
 * Orquestrador principal da aplicação:
 * - Inicialização dos Carrosséis (Hero e Produtos)
 * - Navegação Mobile e Drawer
 * - Busca Rápida no Header
 * - Validação e Redirecionamento da Newsletter/Login 10%
 */

import { initAllCarousels } from './modules/carousel.js';
import { initCarrinhoDrawer } from './modules/carrinho.js';
import { initCatalogo } from './modules/catalogo.js';
import { initPerfil } from './modules/perfil.js';

function startApp() {
    // 1. Inicialização dos carrosséis
    initAllCarousels();

    // 2. Menu Mobile Drawer
    initMobileMenu();

    // 2.1 Aba Hover 'Explorar' (Linhas Recentes)
    initExplorarDropdown();

    // 3. Busca Rápida no Header
    initSearchDrawer();

    // 4. Catálogo e Filtros (quando presente)
    initCatalogo();

    // 5. Carrinho Lateral Drawer
    initCarrinhoDrawer();

    // 6. Perfil do Usuário e Pós-Venda (quando presente)
    if (document.querySelector('.perfil-page-container')) {
        initPerfil();
    }

    // 7. Formulário do Footer (Faça Login e Receba 10%)
    initFooterNewsletter();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startApp);
} else {
    startApp();
}

/**
 * Controle de abertura/fechamento do menu de navegação mobile
 */
function initMobileMenu() {
    const menuBtn = document.getElementById('mobile-menu-btn');
    const siteNav = document.getElementById('site-nav');

    if (!menuBtn || !siteNav) return;

    function toggleMenu(open) {
        const isOpen = open !== undefined ? open : !siteNav.classList.contains('is-open');
        siteNav.classList.toggle('is-open', isOpen);
        menuBtn.classList.toggle('is-active', isOpen);
        menuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');

        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    }

    menuBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleMenu();
    });

    // Fecha ao clicar fora
    document.addEventListener('click', (e) => {
        if (siteNav.classList.contains('is-open') && !siteNav.contains(e.target) && !menuBtn.contains(e.target)) {
            toggleMenu(false);
        }
    });

    // Fecha com tecla Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && siteNav.classList.contains('is-open')) {
            toggleMenu(false);
            menuBtn.focus();
        }
    });
}

/**
 * Controle de acessibilidade e interação da aba de hover Explorar (18_Made In lace Explorar)
 */
function initExplorarDropdown() {
    const item = document.getElementById('nav-explorar-item');
    const link = document.getElementById('nav-explorar-link');
    const dropdown = document.getElementById('explorar-dropdown');

    if (!item || !link || !dropdown) return;

    let timeoutId = null;

    function abrir() {
        if (timeoutId) clearTimeout(timeoutId);
        link.setAttribute('aria-expanded', 'true');
        dropdown.classList.add('is-open');
    }

    function fechar() {
        timeoutId = setTimeout(() => {
            link.setAttribute('aria-expanded', 'false');
            dropdown.classList.remove('is-open');
        }, 120);
    }

    // Hover com pequeno debounce para suavidade
    item.addEventListener('mouseenter', abrir);
    item.addEventListener('mouseleave', fechar);

    // Navegação por teclado (WCAG 2.2 AA)
    item.addEventListener('focusin', abrir);
    item.addEventListener('focusout', (e) => {
        if (!item.contains(e.relatedTarget)) {
            fechar();
        }
    });

    item.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            link.setAttribute('aria-expanded', 'false');
            dropdown.classList.remove('is-open');
            link.focus();
        }
    });

    // Mobile: toque para expandir se estiver no menu mobile
    link.addEventListener('click', (e) => {
        if (window.innerWidth <= 768) {
            if (!item.classList.contains('is-expanded')) {
                e.preventDefault();
                item.classList.add('is-expanded');
                link.setAttribute('aria-expanded', 'true');
            }
        }
    });
}

/**
 * Controle da gaveta expansível de busca rápida sobreposta no header (27 & 9)
 */
function initSearchDrawer() {
    const searchBtn = document.getElementById('search-toggle-btn');
    const searchDrawer = document.getElementById('search-drawer');
    const closeBtn = document.getElementById('search-drawer-close');
    const searchInput = document.getElementById('header-search-input');
    const modeBtn = document.getElementById('search-mode-btn');
    const modeDropdown = document.getElementById('search-mode-dropdown');
    const modeLabel = document.getElementById('search-mode-label');
    const modeInput = document.getElementById('search-mode-input');

    if (!searchBtn || !searchDrawer) return;

    function openSearch() {
        searchDrawer.removeAttribute('hidden');
        searchBtn.setAttribute('aria-expanded', 'true');
        if (searchInput) {
            setTimeout(() => searchInput.focus(), 50);
        }
    }

    function closeSearch() {
        searchDrawer.setAttribute('hidden', '');
        searchBtn.setAttribute('aria-expanded', 'false');
        if (modeDropdown) modeDropdown.setAttribute('hidden', '');
    }

    searchBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const isHidden = searchDrawer.hasAttribute('hidden');
        if (isHidden) {
            openSearch();
        } else {
            closeSearch();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', () => closeSearch());
    }

    // Toggle do Dropdown de Modalidade de Pesquisa (Tudo / Produtos / Linhas)
    if (modeBtn && modeDropdown) {
        modeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isHidden = modeDropdown.hasAttribute('hidden');
            if (isHidden) {
                modeDropdown.removeAttribute('hidden');
                modeBtn.setAttribute('aria-expanded', 'true');
            } else {
                modeDropdown.setAttribute('hidden', '');
                modeBtn.setAttribute('aria-expanded', 'false');
            }
        });

        document.querySelectorAll('.search-mode-item').forEach((item) => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const mode = item.getAttribute('data-mode') || 'tudo';
                const text = item.textContent.trim();

                if (modeInput) modeInput.value = mode;
                if (modeLabel) modeLabel.textContent = `Pesquisar Por: ${text}`;

                document.querySelectorAll('.search-mode-item').forEach((i) => {
                    i.classList.toggle('is-selected', i === item);
                    i.setAttribute('aria-selected', i === item ? 'true' : 'false');
                });

                modeDropdown.setAttribute('hidden', '');
                modeBtn.setAttribute('aria-expanded', 'false');
                if (searchInput) searchInput.focus();
            });
        });

        document.addEventListener('click', (e) => {
            if (!modeDropdown.hasAttribute('hidden') && !modeDropdown.contains(e.target) && !modeBtn.contains(e.target)) {
                modeDropdown.setAttribute('hidden', '');
                modeBtn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // Sai da busca clicando fora da área onde ela fica aberta (27_MadeInLace Pesquisa)
    document.addEventListener('click', (e) => {
        if (!searchDrawer.hasAttribute('hidden')) {
            if (!searchDrawer.contains(e.target) && !searchBtn.contains(e.target)) {
                closeSearch();
            }
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !searchDrawer.hasAttribute('hidden')) {
            closeSearch();
            searchBtn.focus();
        }
    });
}

/**
 * Validação e redirecionamento do formulário de 10% de desconto no footer
 * Redireciona para /login?email=... preenchendo o email no formulário de login
 */
function initFooterNewsletter() {
    const form = document.getElementById('footer-newsletter-form');
    const emailInput = document.getElementById('footer-email-input');

    if (!form || !emailInput) return;

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const email = emailInput.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!email) {
            emailInput.focus();
            return;
        }

        if (!emailRegex.test(email)) {
            emailInput.setCustomValidity('Por favor, insira um e-mail válido.');
            emailInput.reportValidity();
            return;
        }

        emailInput.setCustomValidity('');

        // Redireciona para o login com parâmetro de email sanitizado
        const targetUrl = new URL('/login', window.location.origin);
        targetUrl.searchParams.set('email', email);
        targetUrl.searchParams.set('promo', '10off');

        window.location.href = targetUrl.toString();
    });

    emailInput.addEventListener('input', () => {
        emailInput.setCustomValidity('');
    });
}
