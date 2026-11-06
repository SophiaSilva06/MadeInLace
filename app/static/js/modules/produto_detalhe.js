/**
 * MADE IN LACE — PRODUTO DETALHE
 * Módulo JavaScript com interação completa:
 * - Carrossel da galeria superior com miniaturas
 * - Seleção de tamanho e cor com risco de indisponibilidade
 * - Acordeões acessíveis
 * - Lightbox de avaliações com carrossel de fotos/vídeos (8_MadeInLace Produtos2)
 * - Paginação de 3 em 3 para avaliações sem mídia
 */

document.addEventListener("DOMContentLoaded", () => {
    initGaleriaProduto();
    initVariacoesProduto();
    initModalAvaliacoesMidia();
    initCarregarMaisAvaliacoes();
    initFormCarrinho();
});

/* --------------------------------------------------------------------------
   1. Carrossel da Galeria Superior
   -------------------------------------------------------------------------- */
function initGaleriaProduto() {
    const imgPrincipal = document.getElementById("produto-galeria-principal");
    const btnPrev = document.getElementById("btn-galeria-prev");
    const btnNext = document.getElementById("btn-galeria-next");
    const thumbs = Array.from(document.querySelectorAll(".produto-thumb-item"));

    if (!imgPrincipal || thumbs.length === 0) return;

    let currentIndex = 0;

    function atualizarImagem(index) {
        if (index < 0) index = thumbs.length - 1;
        if (index >= thumbs.length) index = 0;

        currentIndex = index;
        const targetThumb = thumbs[currentIndex];
        const novaUrl = targetThumb.getAttribute("data-img-url");
        const altText = targetThumb.getAttribute("data-alt") || imgPrincipal.alt;

        imgPrincipal.style.opacity = "0.4";
        setTimeout(() => {
            imgPrincipal.src = novaUrl;
            imgPrincipal.alt = altText;
            imgPrincipal.style.opacity = "1";
        }, 120);

        thumbs.forEach((t, i) => {
            const isActive = i === currentIndex;
            t.classList.toggle("is-active", isActive);
            t.setAttribute("aria-selected", isActive ? "true" : "false");
        });
    }

    if (btnPrev) {
        btnPrev.addEventListener("click", () => atualizarImagem(currentIndex - 1));
    }

    if (btnNext) {
        btnNext.addEventListener("click", () => atualizarImagem(currentIndex + 1));
    }

    thumbs.forEach((thumb, idx) => {
        thumb.addEventListener("click", () => atualizarImagem(idx));
    });

    // Navegação por teclado nas setas
    imgPrincipal.parentElement?.addEventListener("keydown", (e) => {
        if (e.key === "ArrowLeft") atualizarImagem(currentIndex - 1);
        if (e.key === "ArrowRight") atualizarImagem(currentIndex + 1);
    });
}

/* --------------------------------------------------------------------------
   2. Seleção de Variações (Tamanho e Cor)
   -------------------------------------------------------------------------- */
function initVariacoesProduto() {
    const chipsTamanho = document.querySelectorAll(".produto-chip[data-tipo='tamanho']");
    const chipsCor = document.querySelectorAll(".produto-chip[data-tipo='cor']");
    const labelTamanho = document.getElementById("selected-tamanho-display");
    const labelCor = document.getElementById("selected-cor-display");
    const inputTamanho = document.getElementById("input-tamanho-selecionado");
    const inputCor = document.getElementById("input-cor-selecionada");

    chipsTamanho.forEach((chip) => {
        chip.addEventListener("click", () => {
            if (chip.classList.contains("is-unavailable")) return;

            chipsTamanho.forEach((c) => {
                c.classList.remove("is-selected");
                c.setAttribute("aria-checked", "false");
            });

            chip.classList.add("is-selected");
            chip.setAttribute("aria-checked", "true");

            const val = chip.getAttribute("data-valor") || "";
            if (labelTamanho) labelTamanho.textContent = val;
            if (inputTamanho) inputTamanho.value = val;
        });
    });

    chipsCor.forEach((chip) => {
        chip.addEventListener("click", () => {
            if (chip.classList.contains("is-unavailable")) return;

            chipsCor.forEach((c) => {
                c.classList.remove("is-selected");
                c.setAttribute("aria-checked", "false");
            });

            chip.classList.add("is-selected");
            chip.setAttribute("aria-checked", "true");

            const val = chip.getAttribute("data-valor") || "";
            if (labelCor) labelCor.textContent = val;
            if (inputCor) inputCor.value = val;
        });
    });
}

/* --------------------------------------------------------------------------
   3. Modal / Lightbox de Fotos e Vídeos (8_MadeInLace Produtos2)
   -------------------------------------------------------------------------- */
function initModalAvaliacoesMidia() {
    const backdrop = document.getElementById("modal-avaliacao-backdrop");
    if (!backdrop) return;

    const dataScript = document.getElementById("dados-avaliacoes-midia");
    let listaMidias = [];
    if (dataScript && dataScript.textContent) {
        try {
            listaMidias = JSON.parse(dataScript.textContent);
        } catch (err) {
            console.error("Erro ao processar dados de avaliações com mídia:", err);
        }
    }

    if (!Array.isArray(listaMidias) || listaMidias.length === 0) return;

    const btnFechar = document.getElementById("modal-fechar-btn");
    const btnPrev = document.getElementById("modal-midia-prev");
    const btnNext = document.getElementById("modal-midia-next");
    const imgElemento = document.getElementById("modal-midia-img");
    const videoElemento = document.getElementById("modal-midia-video");
    const nomeElemento = document.getElementById("modal-avaliacao-nome");
    const notaElemento = document.getElementById("modal-avaliacao-nota-val");
    const tamanhoElemento = document.getElementById("modal-avaliacao-tamanho-val");
    const textoElemento = document.getElementById("modal-avaliacao-texto-val");

    let activeIndex = 0;

    function renderizarItem(index) {
        if (index < 0) index = listaMidias.length - 1;
        if (index >= listaMidias.length) index = 0;

        activeIndex = index;
        const item = listaMidias[activeIndex];
        if (!item) return;

        // Trata mídia (vídeo ou imagem)
        if (videoElemento) {
            videoElemento.pause();
            videoElemento.currentTime = 0;
        }

        if (item.midia_tipo === "video") {
            if (imgElemento) imgElemento.style.display = "none";
            if (videoElemento) {
                videoElemento.style.display = "block";
                videoElemento.src = item.midia_url;
                videoElemento.load();
            }
        } else {
            if (videoElemento) videoElemento.style.display = "none";
            if (imgElemento) {
                imgElemento.style.display = "block";
                imgElemento.src = item.midia_url;
                imgElemento.alt = `Foto de avaliação enviada por ${item.autor_nome}`;
            }
        }

        // Dados do comprador
        if (nomeElemento) nomeElemento.textContent = item.autor_nome || "Cliente";
        if (notaElemento) notaElemento.textContent = Number(item.nota || 5).toFixed(1);
        if (tamanhoElemento) tamanhoElemento.textContent = item.tamanho_comprado || "Único";
        if (textoElemento) textoElemento.textContent = item.comentario || "";
    }

    function abrirModal(index = 0) {
        renderizarItem(index);
        backdrop.classList.add("is-open");
        backdrop.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        btnFechar?.focus();
    }

    function fecharModal() {
        if (videoElemento) {
            videoElemento.pause();
        }
        backdrop.classList.remove("is-open");
        backdrop.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
    }

    // Gatilhos para abrir o modal
    const thumbs = document.querySelectorAll(".comprador-thumb-btn");
    thumbs.forEach((thumb) => {
        thumb.addEventListener("click", () => {
            const idx = parseInt(thumb.getAttribute("data-midia-index") || "0", 10);
            abrirModal(idx);
        });
    });

    const btnVerMais = document.getElementById("btn-ver-mais-avaliacoes");
    if (btnVerMais) {
        btnVerMais.addEventListener("click", () => abrirModal(0));
    }

    // Controles do modal
    btnFechar?.addEventListener("click", fecharModal);
    btnPrev?.addEventListener("click", () => renderizarItem(activeIndex - 1));
    btnNext?.addEventListener("click", () => renderizarItem(activeIndex + 1));

    // Fechar ao clicar fora no backdrop
    backdrop.addEventListener("click", (e) => {
        if (e.target === backdrop) fecharModal();
    });

    // Teclado
    document.addEventListener("keydown", (e) => {
        if (!backdrop.classList.contains("is-open")) return;
        if (e.key === "Escape") fecharModal();
        if (e.key === "ArrowLeft") renderizarItem(activeIndex - 1);
        if (e.key === "ArrowRight") renderizarItem(activeIndex + 1);
    });
}

/* --------------------------------------------------------------------------
   4. Botão Carregar Mais Avaliações Sem Mídia (3 em 3)
   -------------------------------------------------------------------------- */
function initCarregarMaisAvaliacoes() {
    const btnCarregarMais = document.getElementById("btn-carregar-mais-avaliacoes");
    if (!btnCarregarMais) return;

    btnCarregarMais.addEventListener("click", () => {
        const ocultos = document.querySelectorAll(".avaliacao-card.is-hidden");
        const limite = 3;

        for (let i = 0; i < Math.min(limite, ocultos.length); i++) {
            ocultos[i].classList.remove("is-hidden");
        }

        // Se acabaram as avaliações ocultas, esconde o botão
        if (document.querySelectorAll(".avaliacao-card.is-hidden").length === 0) {
            btnCarregarMais.style.display = "none";
        }
    });
}

/* --------------------------------------------------------------------------
   5. Adicionar ao Carrinho & Abertura da Sacola
   -------------------------------------------------------------------------- */
function initFormCarrinho() {
    const form = document.getElementById("form-add-carrinho");
    if (!form) return;

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        // Dispara evento global para o carrinho lateral
        window.dispatchEvent(
            new CustomEvent("carrinho:adicionar", {
                detail: {
                    produtoId: form.querySelector("input[name='produto_id']")?.value,
                    tamanho: form.querySelector("input[name='tamanho']")?.value,
                    cor: form.querySelector("input[name='cor']")?.value,
                },
            })
        );
    });
}
