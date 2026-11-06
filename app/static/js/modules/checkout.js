/**
 * MADE IN LACE — MÓDULO DE CHECKOUT E PAGAMENTO
 * Controla a seleção de endereço, modal de modificação, método de pagamento único
 * e submissão da compra simulada com redirecionamento ao perfil de pedidos.
 */

document.addEventListener('DOMContentLoaded', () => {
    initCheckoutPage();
});

function initCheckoutPage() {
    const modalEnderecos = document.getElementById('modal-modificar-enderecos');
    const btnAbrirModal = document.getElementById('btn-trocar-endereco');
    const btnFecharModal = document.getElementById('btn-fechar-modal-enderecos');
    const btnAddMore = document.getElementById('btn-add-more-checkout-address');
    const formNovoEndereco = document.getElementById('form-novo-endereco-checkout');
    const btnSalvarNovoEndereco = document.getElementById('btn-salvar-novo-endereco');
    const btnConfirmarSelecao = document.getElementById('btn-confirmar-endereco-selecao');
    const btnFinalizarCompra = document.getElementById('btn-finalizar-compra');

    // Estado local de checkout
    const state = {
        enderecoId: document.getElementById('selected-address-id')?.value || null,
        metodoPagamento: document.querySelector('input[name="metodo_pagamento"]:checked')?.value || 'Pix',
    };

    // 1. Controle do Modal
    function abrirModal() {
        if (!modalEnderecos) return;
        modalEnderecos.classList.add('is-active');
        modalEnderecos.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    }

    function fecharModal() {
        if (!modalEnderecos) return;
        modalEnderecos.classList.remove('is-active');
        modalEnderecos.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        if (formNovoEndereco) formNovoEndereco.style.display = 'none';
    }

    if (btnAbrirModal) btnAbrirModal.addEventListener('click', abrirModal);
    if (btnFecharModal) btnFecharModal.addEventListener('click', fecharModal);

    modalEnderecos?.addEventListener('click', (e) => {
        if (e.target === modalEnderecos) fecharModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modalEnderecos?.classList.contains('is-active')) {
            fecharModal();
        }
    });

    // 2. Alternar exibição do formulário de novo endereço ao clicar no "+"
    if (btnAddMore && formNovoEndereco) {
        btnAddMore.addEventListener('click', () => {
            const isHidden = formNovoEndereco.style.display === 'none' || !formNovoEndereco.style.display;
            formNovoEndereco.style.display = isHidden ? 'block' : 'none';
            if (isHidden) {
                document.getElementById('checkout-end-nome')?.focus();
            }
        });
    }

    // 3. Consulta automática de CEP via ViaCEP
    const inputCep = document.getElementById('checkout-end-cep');
    if (inputCep) {
        inputCep.addEventListener('blur', async () => {
            const rawCep = inputCep.value.replace(/\D/g, '');
            if (rawCep.length === 8) {
                try {
                    const res = await fetch(`https://viacep.com.br/ws/${rawCep}/json/`);
                    const data = await res.json();
                    if (!data.erro) {
                        const logr = document.getElementById('checkout-end-logradouro');
                        const bairro = document.getElementById('checkout-end-bairro');
                        const cidade = document.getElementById('checkout-end-cidade');
                        const estado = document.getElementById('checkout-end-estado');

                        if (logr && !logr.value) logr.value = data.logradouro || '';
                        if (bairro && !bairro.value) bairro.value = data.bairro || '';
                        if (cidade && !cidade.value) cidade.value = data.localidade || '';
                        if (estado && !estado.value) estado.value = data.uf || '';
                        document.getElementById('checkout-end-numero')?.focus();
                    }
                } catch (err) {
                    // Silencioso em caso de falta de conexão
                }
            }
        });
    }

    // 4. Salvar novo endereço via API
    if (btnSalvarNovoEndereco) {
        btnSalvarNovoEndereco.addEventListener('click', async (e) => {
            e.preventDefault();
            const nome = document.getElementById('checkout-end-nome')?.value.trim();
            const cep = document.getElementById('checkout-end-cep')?.value.trim();
            const logradouro = document.getElementById('checkout-end-logradouro')?.value.trim();
            const numero = document.getElementById('checkout-end-numero')?.value.trim();
            const complemento = document.getElementById('checkout-end-complemento')?.value.trim();
            const bairro = document.getElementById('checkout-end-bairro')?.value.trim();
            const cidade = document.getElementById('checkout-end-cidade')?.value.trim();
            const estado = document.getElementById('checkout-end-estado')?.value.trim().toUpperCase();

            if (!nome || !cep || !logradouro || !numero || !bairro || !cidade || !estado) {
                alert('Preencha os campos obrigatórios do endereço (Nome, CEP, Logradouro, Número, Bairro, Cidade e Estado).');
                return;
            }

            try {
                btnSalvarNovoEndereco.disabled = true;
                btnSalvarNovoEndereco.textContent = 'Salvando...';

                const res = await fetch('/checkout/endereco', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        nome,
                        cep,
                        logradouro,
                        numero,
                        complemento: complemento || null,
                        bairro,
                        cidade,
                        estado,
                    }),
                });

                const data = await res.json();
                if (data.success && data.endereco) {
                    state.enderecoId = data.endereco.id;
                    atualizarDisplayEndereco(data.endereco);
                    if (data.resumo) {
                        atualizarDisplayTotais(data.resumo);
                    }
                    fecharModal();
                    // Recarrega página para sincronizar cartões na lista
                    window.location.href = `/checkout?endereco_id=${data.endereco.id}`;
                } else {
                    alert(data.message || 'Erro ao cadastrar endereço.');
                }
            } catch (err) {
                alert('Erro de conexão ao salvar endereço.');
            } finally {
                btnSalvarNovoEndereco.disabled = false;
                btnSalvarNovoEndereco.textContent = 'Salvar Endereço';
            }
        });
    }

    // 5. Seleção de endereço existente no modal
    document.querySelectorAll('.checkout-address-radio-input').forEach((radio) => {
        radio.addEventListener('change', (e) => {
            state.enderecoId = e.target.value;
            document.querySelectorAll('.checkout-address-item-card').forEach((card) => {
                card.classList.toggle('is-selected', card.dataset.addressId === state.enderecoId);
            });
        });
    });

    if (btnConfirmarSelecao) {
        btnConfirmarSelecao.addEventListener('click', async () => {
            const radioSelecionado = document.querySelector('.checkout-address-radio-input:checked');
            if (radioSelecionado) {
                state.enderecoId = radioSelecionado.value;
                const card = radioSelecionado.closest('.checkout-address-item-card');
                if (card) {
                    const texto = card.dataset.summaryText || '';
                    const displayElement = document.getElementById('checkout-current-address-text');
                    if (displayElement) displayElement.textContent = texto;
                }
                // Recalcula totais com o novo endereço
                await recalcularValoresCheckout(state.enderecoId);
            }
            fecharModal();
        });
    }

    // 5.1 Remoção lógica de endereço no checkout com bloqueio do último ativo
    const listaCardsCheckout = document.getElementById('checkout-addresses-cards-list');
    if (listaCardsCheckout) {
        listaCardsCheckout.addEventListener('click', async (e) => {
            const btnRemover = e.target.closest('.js-remover-endereco');
            if (btnRemover) {
                e.stopPropagation();
                const cardsAtivos = listaCardsCheckout.querySelectorAll('.checkout-address-item-card');
                if (cardsAtivos.length <= 1) {
                    alert('Não é possível remover o único endereço ativo da conta.');
                    return;
                }

                const endId = btnRemover.dataset.enderecoId;
                if (!endId) return;

                if (!confirm('Deseja realmente remover este endereço?')) return;

                try {
                    btnRemover.disabled = true;
                    btnRemover.textContent = 'Removendo...';
                    const res = await fetch(`/checkout/endereco/remover/${endId}`, { method: 'POST' });
                    const data = await res.json();
                    if (data.success) {
                        const cardRemover = btnRemover.closest('.checkout-address-item-card');
                        if (cardRemover) {
                            cardRemover.style.opacity = '0';
                            cardRemover.style.transform = 'scale(0.95)';
                            setTimeout(async () => {
                                cardRemover.remove();
                                if (state.enderecoId === String(endId)) {
                                    const primeiroRadio = listaCardsCheckout.querySelector('.checkout-address-radio-input');
                                    if (primeiroRadio) {
                                        primeiroRadio.checked = true;
                                        primeiroRadio.dispatchEvent(new Event('change', { bubbles: true }));
                                        state.enderecoId = primeiroRadio.value;
                                        await recalcularValoresCheckout(state.enderecoId);
                                    }
                                }
                            }, 200);
                        }
                        alert('Endereço removido com sucesso!');
                    } else {
                        alert(data.message || 'Não foi possível remover o endereço.');
                        btnRemover.disabled = false;
                        btnRemover.textContent = 'Remover';
                    }
                } catch (err) {
                    alert('Erro de conexão ao remover endereço.');
                    btnRemover.disabled = false;
                    btnRemover.textContent = 'Remover';
                }
            }
        });
    }

    // 6. Recalcular valores do checkout via API
    async function recalcularValoresCheckout(enderecoId) {
        try {
            const res = await fetch(`/checkout/recalcular?endereco_id=${enderecoId}`);
            const data = await res.json();
            if (data.success && data.resumo) {
                atualizarDisplayTotais(data.resumo);
                const hiddenInput = document.getElementById('selected-address-id');
                if (hiddenInput) hiddenInput.value = enderecoId;
            }
        } catch (err) {
            console.error('Falha ao recalcular frete:', err);
        }
    }

    function atualizarDisplayEndereco(endereco) {
        const displayElement = document.getElementById('checkout-current-address-text');
        if (displayElement && endereco) {
            displayElement.textContent = `${endereco.nome}: ${endereco.cep} - ${endereco.logradouro}, ${endereco.numero}`;
        }
        const hiddenInput = document.getElementById('selected-address-id');
        if (hiddenInput && endereco) hiddenInput.value = endereco.id;
    }

    function atualizarDisplayTotais(resumo) {
        const subtotalEl = document.getElementById('checkout-subtotal-val');
        const freteEl = document.getElementById('checkout-frete-val');
        const totalEl = document.getElementById('checkout-total-val');
        const freeShippingNotice = document.getElementById('checkout-free-shipping-notice');
        const discountRow = document.getElementById('checkout-discount-row');
        const discountVal = document.getElementById('checkout-discount-val');

        if (subtotalEl) subtotalEl.textContent = resumo.subtotal_formatado;
        if (freteEl) freteEl.textContent = resumo.frete_formatado;
        if (totalEl) totalEl.textContent = resumo.total_formatado;

        if (freeShippingNotice) {
            freeShippingNotice.style.display = resumo.frete_gratis ? 'block' : 'none';
        }

        if (discountRow && discountVal) {
            if (resumo.primeira_compra && resumo.valor_desconto > 0) {
                discountRow.style.display = 'flex';
                discountVal.textContent = `- ${resumo.valor_desconto_formatado}`;
            } else {
                discountRow.style.display = 'none';
            }
        }
    }

    // 7. Seleção de método de pagamento (garante que apenas 1 esteja selecionado)
    document.querySelectorAll('input[name="metodo_pagamento"]').forEach((radio) => {
        radio.addEventListener('change', (e) => {
            state.metodoPagamento = e.target.value;
        });
    });

    // 8. Botão "Pagar E Finalizar"
    if (btnFinalizarCompra) {
        btnFinalizarCompra.addEventListener('click', async (e) => {
            e.preventDefault();

            const enderecoId = document.getElementById('selected-address-id')?.value || state.enderecoId;
            const metodoRadio = document.querySelector('input[name="metodo_pagamento"]:checked');
            const metodoPagamento = metodoRadio ? metodoRadio.value : state.metodoPagamento;

            if (!enderecoId) {
                alert('Por favor, selecione ou adicione um endereço para entrega.');
                abrirModal();
                return;
            }

            if (!metodoPagamento) {
                alert('Por favor, selecione um método de pagamento.');
                return;
            }

            try {
                btnFinalizarCompra.disabled = true;
                btnFinalizarCompra.textContent = 'Processando...';

                const res = await fetch('/checkout/finalizar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        endereco_id: Number(enderecoId),
                        metodo_pagamento: metodoPagamento,
                    }),
                });

                const data = await res.json();
                if (data.success && data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    alert(data.message || 'Falha ao processar pagamento.');
                    btnFinalizarCompra.disabled = false;
                    btnFinalizarCompra.textContent = 'Pagar E Finalizar';
                }
            } catch (err) {
                alert('Ocorreu um erro de rede ao finalizar a compra.');
                btnFinalizarCompra.disabled = false;
                btnFinalizarCompra.textContent = 'Pagar E Finalizar';
            }
        });
    }
}
