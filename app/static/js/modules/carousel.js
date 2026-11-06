/**
 * MADE IN LACE — CAROUSEL MODULE (Vanilla ES6)
 * Gerenciador modular de carrosséis:
 * 1. HeroCarousel: carrossel fade/slide com autoplay, pausa no hover/foco, navegação por setas, touch swipe e a11y.
 * 2. ProductTrackCarousel: carrossel horizontal de produtos com rolagem suave por step, snap e setas dinâmicas.
 */

export class HeroCarousel {
    /**
     * @param {HTMLElement} rootElement Elemento raiz [data-carousel="hero"]
     * @param {Object} options Configurações opcionais
     */
    constructor(rootElement, options = {}) {
        if (!rootElement) return;

        this.root = rootElement;
        this.slides = Array.from(this.root.querySelectorAll('.hero-carousel__slide'));
        this.prevBtn = this.root.querySelector('[data-carousel-prev]');
        this.nextBtn = this.root.querySelector('[data-carousel-next]');
        this.dots = Array.from(this.root.querySelectorAll('[data-slide-to]'));

        this.currentIndex = 0;
        this.totalSlides = this.slides.length;
        this.autoplayInterval = options.interval || 6000;
        this.timer = null;
        this.touchStartX = 0;
        this.touchEndX = 0;

        this.init();
    }

    init() {
        if (this.totalSlides <= 1) return;

        // Eventos das setas
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => {
                this.prev();
                this.restartAutoplay();
            });
        }

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => {
                this.next();
                this.restartAutoplay();
            });
        }

        // Eventos dos dots de paginação
        this.dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                this.goTo(index);
                this.restartAutoplay();
            });
        });

        // Suporte a teclado acessível (ArrowLeft e ArrowRight)
        this.root.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                this.prev();
                this.restartAutoplay();
            } else if (e.key === 'ArrowRight') {
                this.next();
                this.restartAutoplay();
            }
        });

        // Pausa autoplay quando o mouse estiver sobre o carrossel ou foco do teclado
        this.root.addEventListener('mouseenter', () => this.stopAutoplay());
        this.root.addEventListener('mouseleave', () => this.startAutoplay());
        this.root.addEventListener('focusin', () => this.stopAutoplay());
        this.root.addEventListener('focusout', () => this.startAutoplay());

        // Suporte a Touch Swipe Mobile
        this.root.addEventListener('touchstart', (e) => {
            this.touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });

        this.root.addEventListener('touchend', (e) => {
            this.touchEndX = e.changedTouches[0].screenX;
            this.handleSwipe();
        }, { passive: true });

        // Inicia slide e autoplay
        this.updateSlides();
        this.startAutoplay();
    }

    handleSwipe() {
        const threshold = 40;
        const diff = this.touchStartX - this.touchEndX;

        if (Math.abs(diff) > threshold) {
            if (diff > 0) {
                // Deslize para a esquerda -> próximo
                this.next();
            } else {
                // Deslize para a direita -> anterior
                this.prev();
            }
            this.restartAutoplay();
        }
    }

    goTo(index) {
        if (index < 0) {
            this.currentIndex = this.totalSlides - 1;
        } else if (index >= this.totalSlides) {
            this.currentIndex = 0;
        } else {
            this.currentIndex = index;
        }
        this.updateSlides();
    }

    next() {
        this.goTo(this.currentIndex + 1);
    }

    prev() {
        this.goTo(this.currentIndex - 1);
    }

    updateSlides() {
        this.slides.forEach((slide, idx) => {
            const isActive = idx === this.currentIndex;
            slide.classList.toggle('is-active', isActive);
            slide.setAttribute('aria-hidden', !isActive);

            const link = slide.querySelector('a');
            if (link) {
                link.setAttribute('tabindex', isActive ? '0' : '-1');
            }
        });

        // Atualiza indicadores visuais e acessíveis
        this.dots.forEach((dot, idx) => {
            const isActive = idx === this.currentIndex;
            dot.classList.toggle('is-active', isActive);
            dot.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });
    }

    startAutoplay() {
        this.stopAutoplay();
        this.timer = setInterval(() => {
            this.next();
        }, this.autoplayInterval);
    }

    stopAutoplay() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    restartAutoplay() {
        this.stopAutoplay();
        this.startAutoplay();
    }
}

export class ProductTrackCarousel {
    /**
     * @param {HTMLElement} rootElement Elemento raiz [data-carousel="products"]
     */
    constructor(rootElement) {
        if (!rootElement) return;

        this.root = rootElement;
        this.trackWrapper = this.root.querySelector('[data-carousel-track-wrapper]');
        this.track = this.root.querySelector('[data-carousel-track]');
        this.prevBtn = this.root.querySelector('[data-carousel-prev]');
        this.nextBtn = this.root.querySelector('[data-carousel-next]');

        if (!this.trackWrapper) return;

        this.init();
    }

    init() {
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => this.scrollByDirection(-1));
        }

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => this.scrollByDirection(1));
        }

        // Suporte a teclado nas setas laterais ou track
        this.trackWrapper.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this.scrollByDirection(-1);
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                this.scrollByDirection(1);
            }
        });

        // Monitora evento de scroll para atualizar visibilidade das setas
        this.trackWrapper.addEventListener('scroll', () => {
            this.updateArrows();
        }, { passive: true });

        // Atualização em redimensionamento
        window.addEventListener('resize', () => {
            this.updateArrows();
        }, { passive: true });

        this.updateArrows();
    }

    /**
     * @param {number} direction -1 para esquerda, 1 para direita
     */
    scrollByDirection(direction) {
        const firstItem = this.track.querySelector('.product-carousel__item');
        if (!firstItem) return;

        const itemWidth = firstItem.getBoundingClientRect().width;
        const gap = 24; // Espaçamento estimado entre cards
        const scrollDistance = (itemWidth + gap) * direction;

        this.trackWrapper.scrollBy({
            left: scrollDistance,
            behavior: 'smooth'
        });
    }

    updateArrows() {
        if (!this.prevBtn || !this.nextBtn) return;

        const { scrollLeft, scrollWidth, clientWidth } = this.trackWrapper;

        // Se está no início
        const isAtStart = scrollLeft <= 4;
        // Se alcançou o final
        const isAtEnd = scrollLeft + clientWidth >= scrollWidth - 6;

        this.prevBtn.disabled = isAtStart;
        this.nextBtn.disabled = isAtEnd;

        this.prevBtn.setAttribute('aria-disabled', isAtStart ? 'true' : 'false');
        this.nextBtn.setAttribute('aria-disabled', isAtEnd ? 'true' : 'false');
    }
}

/**
 * Inicializador automático de todos os carrosséis da página
 */
export function initAllCarousels() {
    // 1. Inicializa o Hero Carousel
    const heroEl = document.querySelector('[data-carousel="hero"]');
    let heroInstance = null;
    if (heroEl) {
        heroInstance = new HeroCarousel(heroEl, { interval: 6000 });
    }

    // 2. Inicializa os Carrosséis de Produtos (Promoções e Best Sellers)
    const productCarousels = document.querySelectorAll('[data-carousel="products"]');
    const productInstances = [];
    productCarousels.forEach((el) => {
        productInstances.push(new ProductTrackCarousel(el));
    });

    return {
        hero: heroInstance,
        products: productInstances
    };
}
