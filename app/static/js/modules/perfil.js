/**
 * MadeInLace - Módulo Interativo da Página de Perfil
 * Responsável pela alternância de abas, carrossel de itens de pedidos,
 * modais acessíveis, solicitação de troca/reembolso e persistência consolidada.
 */

function startCountdownTimer(durationSeconds, displayElement, onExpire) {
    if (!displayElement) return;
    if (displayElement._timerInterval) {
        clearInterval(displayElement._timerInterval);
    }

    let remaining = Math.max(0, parseInt(durationSeconds, 10) || 0);

    function update() {
        const hours = Math.floor(remaining / 3600);
        const minutes = Math.floor((remaining % 3600) / 60);
        const seconds = remaining % 60;

        if (hours > 0) {
            displayElement.textContent = `${hours}:${minutes < 10 ? '0' : ''}${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
        } else {
            displayElement.textContent = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
        }

        if (remaining <= 0) {
            clearInterval(displayElement._timerInterval);
            displayElement._timerInterval = null;
            displayElement.textContent = '0:00';
            if (typeof onExpire === 'function') onExpire();
            return;
        }
        remaining--;
    }

    update();
    displayElement._timerInterval = setInterval(update, 1000);
}

export function initPerfil() {
    // 1. Estado local de alterações pendentes
    const initialRadioPrincipal = document.querySelector('.checkout-address-radio-input:checked');
    const initialPrincipalBtn = document.querySelector('.endereco-radio-circle.is-selected');
    const initialAddrId = initialRadioPrincipal ? parseInt(initialRadioPrincipal.value, 10) : (initialPrincipalBtn && initialPrincipalBtn.dataset.enderecoId ? parseInt(initialPrincipalBtn.dataset.enderecoId, 10) : null);

    const state = {
        novaSenha: null,
        confirmarNovaSenha: null,
        senhaAtual: null,
        novoEmail: null,
        codigoEmailAtual: null,
        codigoEmailNovo: null,
        enderecos: [],
        enderecoPrincipalId: initialAddrId,
        pedidosOffset: 2,
        trocasOffset: 2,
        itemSelecionado: null,
    };

    // 2. Elementos DOM principais
    const navLinks = document.querySelectorAll('.js-perfil-tab-trigger');
    const tabPanes = document.querySelectorAll('.js-perfil-tab-pane');
    const btnTogglePedidos = document.getElementById('btn-toggle-pedidos');
    const pedidosSubmenu = document.getElementById('pedidos-submenu');
    const chevronPedidos = document.getElementById('chevron-pedidos');

    // Botões de acionamento de modais
    const btnAbrirSenha = document.getElementById('btn-abrir-modal-senha');
    const btnAbrirEmail = document.getElementById('btn-abrir-modal-email');
    const btnAbrirEnderecos = document.getElementById('btn-abrir-modal-enderecos');
    const btnSalvarTudo = document.getElementById('btn-salvar-perfil-tudo');

    // Modais
    const modalSenha = document.getElementById('modal-alterar-senha');
    const modalEmail = document.getElementById('modal-alterar-email');
    const modalEnderecos = document.getElementById('modal-modificar-enderecos');
    const modalItemDetalhe = document.getElementById('modal-item-detalhe');
    const modalFormTroca = document.getElementById('modal-form-troca');
    const modalFormReembolso = document.getElementById('modal-form-reembolso');

    // Helper para abrir/fechar modal
    function abrirModal(modal) {
        if (!modal) return;
        modal.classList.add('is-active');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    }

    function fecharModal(modal) {
        if (!modal) return;
        modal.classList.remove('is-active');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    // Fechar modais ao clicar no botão 'X' ou backdrop
    document.querySelectorAll('.js-modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const overlay = btn.closest('.checkout-modal-backdrop, .perfil-modal-overlay');
            fecharModal(overlay);
        });
    });

    document.querySelectorAll('.checkout-modal-backdrop, .perfil-modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                fecharModal(overlay);
            }
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.checkout-modal-backdrop.is-active, .perfil-modal-overlay.is-active').forEach(fecharModal);
        }
    });

    // 3. Controle de Abas
    function ativarAba(tabId) {
        tabPanes.forEach(pane => {
            if (pane.id === `tab-${tabId}`) {
                pane.classList.add('is-active');
            } else {
                pane.classList.remove('is-active');
            }
        });

        navLinks.forEach(link => {
            if (link.dataset.tab === tabId) {
                link.classList.add('is-active');
            } else {
                link.classList.remove('is-active');
            }
        });

        // Se for uma aba de pedidos, garante que o submenu esteja visível
        if (tabId.includes('pedidos') && pedidosSubmenu && chevronPedidos) {
            pedidosSubmenu.classList.remove('is-collapsed');
            chevronPedidos.classList.add('is-open');
        }
    }

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = link.dataset.tab;
            if (tabId) {
                ativarAba(tabId);
            }
        });
    });

    if (btnTogglePedidos && pedidosSubmenu && chevronPedidos) {
        btnTogglePedidos.addEventListener('click', (e) => {
            e.preventDefault();
            const isCollapsed = pedidosSubmenu.classList.toggle('is-collapsed');
            chevronPedidos.classList.toggle('is-open', !isCollapsed);
        });
    }

    // 4. Modal Alterar Senha (28_MadeInLace Perfil1.1)
    if (btnAbrirSenha) {
        btnAbrirSenha.addEventListener('click', () => abrirModal(modalSenha));
    }

    const btnConfirmarSenha = document.getElementById('btn-confirmar-senha-modal');
    if (btnConfirmarSenha) {
        btnConfirmarSenha.addEventListener('click', () => {
            const novaSenha = document.getElementById('input-modal-senha-nova')?.value || '';
            const senhaAntiga = document.getElementById('input-modal-senha-antiga')?.value || '';
            const confirmarSenha = document.getElementById('input-modal-senha-confirmar')?.value || '';
            const msgErro = document.getElementById('msg-erro-senha-modal');

            if (!senhaAntiga) {
                if (msgErro) msgErro.textContent = 'Informe sua senha atual.';
                return;
            }
            if (novaSenha.length < 12) {
                if (msgErro) msgErro.textContent = 'A nova senha deve ter no mínimo 12 caracteres.';
                return;
            }
            if (novaSenha !== confirmarSenha) {
                if (msgErro) msgErro.textContent = 'A confirmação da nova senha não confere.';
                return;
            }

            state.senhaAtual = senhaAntiga;
            state.novaSenha = novaSenha;
            state.confirmarNovaSenha = confirmarSenha;

            if (msgErro) msgErro.textContent = '';
            fecharModal(modalSenha);
            alert('Nova senha validada! Clique em "Salvar Informações" para gravar as mudanças.');
        });
    }

    // 5. Modal Alterar E-mail (14_MadeInLace Perfil1.2)
    if (btnAbrirEmail) {
        btnAbrirEmail.addEventListener('click', () => abrirModal(modalEmail));
    }

    const timerAtualEl = document.getElementById('timer-cod-email-atual');
    const timerNovoEl = document.getElementById('timer-cod-email-novo');

    const btnEnviarCodAtual = document.getElementById('btn-enviar-cod-email-atual');
    if (btnEnviarCodAtual) {
        btnEnviarCodAtual.addEventListener('click', async () => {
            try {
                btnEnviarCodAtual.disabled = true;
                btnEnviarCodAtual.textContent = 'Enviando...';
                const res = await fetch('/perfil/email/enviar-codigo-atual', { method: 'POST' });
                const data = await res.json().catch(() => null);
                if (res.ok && data && data.success) {
                    btnEnviarCodAtual.textContent = 'Reenviar Código';
                    const expira = data.expira_em_segundos || data.timer || 900;
                    if (timerAtualEl) {
                        startCountdownTimer(expira, timerAtualEl);
                    }
                    alert(data.message || 'Código enviado com sucesso!');
                } else {
                    btnEnviarCodAtual.textContent = 'Enviar Código';
                    alert(data.message || 'Erro ao enviar código.');
                }
            } catch (err) {
                btnEnviarCodAtual.textContent = 'Enviar Código';
                alert('Erro de conexão ao enviar código.');
            } finally {
                btnEnviarCodAtual.disabled = false;
            }
        });
    }

    const btnEnviarCodNovo = document.getElementById('btn-enviar-cod-email-novo');
    if (btnEnviarCodNovo) {
        btnEnviarCodNovo.addEventListener('click', async () => {
            const novoEmail = document.getElementById('input-modal-novo-email')?.value || '';
            if (!novoEmail || !novoEmail.includes('@')) {
                alert('Informe um endereço de e-mail novo válido.');
                return;
            }
            try {
                btnEnviarCodNovo.disabled = true;
                btnEnviarCodNovo.textContent = 'Enviando...';
                const res = await fetch('/perfil/email/enviar-codigo-novo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: novoEmail }),
                });
                const data = await res.json().catch(() => null);
                if (res.ok && data && data.success) {
                    btnEnviarCodNovo.textContent = 'Reenviar Código';
                    const expira = data.expira_em_segundos || data.timer || 900;
                    if (timerNovoEl) {
                        startCountdownTimer(expira, timerNovoEl);
                    }
                    alert(data.message || 'Código enviado para o novo e-mail!');
                } else {
                    btnEnviarCodNovo.textContent = 'Enviar Código';
                    alert(data.message || 'Erro ao enviar código.');
                }
            } catch (err) {
                btnEnviarCodNovo.textContent = 'Enviar Código';
                alert('Erro de conexão ao enviar código.');
            } finally {
                btnEnviarCodNovo.disabled = false;
            }
        });
    }

    const btnConfirmarEmail = document.getElementById('btn-confirmar-email-modal');
    if (btnConfirmarEmail) {
        btnConfirmarEmail.addEventListener('click', async () => {
            const codAtual = document.getElementById('input-modal-cod-email-atual')?.value || '';
            const senhaAtual = document.getElementById('input-modal-email-senha-atual')?.value || '';
            const novoEmail = document.getElementById('input-modal-novo-email')?.value || '';
            const codNovo = document.getElementById('input-modal-cod-email-novo')?.value || '';
            const emailAtualCadastrado = document.getElementById('perfil-input-email')?.value || '';
            const msgErro = document.getElementById('msg-erro-email-modal');

            if (!codAtual || !senhaAtual || !novoEmail || !codNovo) {
                if (msgErro) msgErro.textContent = 'Preencha todos os campos e códigos.';
                return;
            }

            try {
                btnConfirmarEmail.disabled = true;
                btnConfirmarEmail.textContent = 'Validando...';
                const res = await fetch('/perfil/email/validar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email_atual: emailAtualCadastrado,
                        codigo_atual: codAtual,
                        novo_email: novoEmail,
                        codigo_novo: codNovo,
                        senha_atual: senhaAtual,
                    }),
                });
                const data = await res.json();
                if (!data.success) {
                    if (msgErro) msgErro.textContent = data.message || 'código de verificação inválido';
                    return;
                }

                // Salva estado pendente
                state.senhaAtual = senhaAtual;
                state.novoEmail = novoEmail;
                state.codigoEmailAtual = codAtual;
                state.codigoEmailNovo = codNovo;

                // Atualiza visualmente o campo da aba principal
                const inputEmailPrincipal = document.getElementById('perfil-input-email');
                if (inputEmailPrincipal) {
                    inputEmailPrincipal.value = novoEmail;
                }

                if (msgErro) msgErro.textContent = '';
                fecharModal(modalEmail);
                alert('E-mail validado! Clique em "Salvar Informações" para consolidar a alteração no banco.');
            } catch (err) {
                if (msgErro) msgErro.textContent = 'Erro de comunicação com o servidor.';
            } finally {
                btnConfirmarEmail.disabled = false;
                btnConfirmarEmail.textContent = 'Continuar';
            }
        });
    }

    // 6. Modal Modificar Endereços (Design e Comportamento do Checkout)
    if (btnAbrirEnderecos) {
        btnAbrirEnderecos.addEventListener('click', () => abrirModal(modalEnderecos));
    }

    const btnAddMoreAddress = document.getElementById('btn-add-more-perfil-address') || document.getElementById('btn-add-more-checkout-address');
    const formNovoEnderecoPerfil = document.getElementById('form-novo-endereco-perfil');
    const listaCardsEnderecos = document.getElementById('checkout-addresses-cards-list');
    const btnSalvarNovoEnd = document.getElementById('btn-salvar-novo-endereco-perfil');
    const btnConfirmarEnderecoPerfil = document.getElementById('btn-confirmar-endereco-perfil');

    // Função segura para renderizar visualmente cartão de endereço idêntico ao checkout
    function criarCardEnderecoCheckout(end) {
        const card = document.createElement('div');
        card.className = 'checkout-address-item-card is-selected';
        card.dataset.addressId = String(end.id);

        const header = document.createElement('div');
        header.className = 'checkout-address-item-header';

        const label = document.createElement('label');
        label.className = 'checkout-modal-radio-label';
        label.setAttribute('for', `addr-radio-${end.id}`);

        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'perfil_selected_address';
        radio.id = `addr-radio-${end.id}`;
        radio.value = String(end.id);
        radio.className = 'checkout-address-radio-input visually-hidden';
        radio.checked = true;

        const radioCircle = document.createElement('span');
        radioCircle.className = 'checkout-modal-radio-circle';
        radioCircle.setAttribute('aria-hidden', 'true');

        const spanNome = document.createElement('span');
        spanNome.textContent = `Nome: ${end.nome}`;

        label.appendChild(radio);
        label.appendChild(radioCircle);
        label.appendChild(spanNome);

        const btnRemover = document.createElement('button');
        btnRemover.type = 'button';
        btnRemover.className = 'btn-remover-endereco js-remover-endereco';
        btnRemover.dataset.enderecoId = String(end.id);
        btnRemover.title = 'Remover este endereço';
        btnRemover.setAttribute('aria-label', `Remover endereço ${end.nome}`);
        btnRemover.textContent = 'Remover';

        header.appendChild(label);
        header.appendChild(btnRemover);
        card.appendChild(header);

        const grid = document.createElement('div');
        grid.className = 'checkout-address-fields-grid';

        function criarInputWrap(valor, isFull = false) {
            const wrap = document.createElement('div');
            if (isFull) wrap.className = 'checkout-address-fields-grid--full';
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'checkout-modal-input';
            input.value = valor || '';
            input.readOnly = true;
            wrap.appendChild(input);
            return wrap;
        }

        grid.appendChild(criarInputWrap(`CEP: ${end.cep}`));
        grid.appendChild(criarInputWrap(`Número: ${end.numero}`));
        grid.appendChild(criarInputWrap(`Logradouro: ${end.logradouro}`, true));
        grid.appendChild(criarInputWrap(`Bairro: ${end.bairro}`));
        grid.appendChild(criarInputWrap(`Cidade: ${end.cidade}`));
        grid.appendChild(criarInputWrap(`Estado: ${end.estado}`));
        grid.appendChild(criarInputWrap(`Complemento: ${end.complemento || ''}`));

        card.appendChild(grid);
        return card;
    }

    if (btnAddMoreAddress && formNovoEnderecoPerfil) {
        btnAddMoreAddress.addEventListener('click', () => {
            const isHidden = formNovoEnderecoPerfil.style.display === 'none' || !formNovoEnderecoPerfil.style.display;
            formNovoEnderecoPerfil.style.display = isHidden ? 'block' : 'none';
            if (isHidden) {
                document.getElementById('perfil-end-nome')?.focus();
            }
        });
    }

    // Consulta automática de CEP via ViaCEP
    const inputCepNovo = document.getElementById('perfil-end-cep');
    if (inputCepNovo) {
        inputCepNovo.addEventListener('blur', async () => {
            const rawCep = inputCepNovo.value.replace(/\D/g, '');
            if (rawCep.length === 8) {
                try {
                    const res = await fetch(`https://viacep.com.br/ws/${rawCep}/json/`);
                    const data = await res.json();
                    if (!data.erro) {
                        const logradouro = document.getElementById('perfil-end-logradouro');
                        const bairro = document.getElementById('perfil-end-bairro');
                        const cidade = document.getElementById('perfil-end-cidade');
                        const estado = document.getElementById('perfil-end-estado');
                        const numero = document.getElementById('perfil-end-numero');

                        if (logradouro && !logradouro.value) logradouro.value = data.logradouro || '';
                        if (bairro && !bairro.value) bairro.value = data.bairro || '';
                        if (cidade && !cidade.value) cidade.value = data.localidade || '';
                        if (estado && !estado.value) estado.value = data.uf || '';
                        numero?.focus();
                    }
                } catch (e) {
                    // Consulta silenciosa
                }
            }
        });
    }

    // Salvar novo endereço via API com persistência imediata
    if (btnSalvarNovoEnd) {
        btnSalvarNovoEnd.addEventListener('click', async (e) => {
            e.preventDefault();
            const nome = document.getElementById('perfil-end-nome')?.value.trim();
            const cep = document.getElementById('perfil-end-cep')?.value.trim();
            const logradouro = document.getElementById('perfil-end-logradouro')?.value.trim();
            const numero = document.getElementById('perfil-end-numero')?.value.trim();
            const complemento = document.getElementById('perfil-end-complemento')?.value.trim();
            const bairro = document.getElementById('perfil-end-bairro')?.value.trim();
            const cidade = document.getElementById('perfil-end-cidade')?.value.trim();
            const estado = document.getElementById('perfil-end-estado')?.value.trim().toUpperCase();

            if (!nome || !cep || !logradouro || !numero || !bairro || !cidade || !estado) {
                alert('Preencha os campos obrigatórios do endereço (Nome, CEP, Logradouro, Número, Bairro, Cidade e Estado).');
                return;
            }

            try {
                btnSalvarNovoEnd.disabled = true;
                btnSalvarNovoEnd.textContent = 'Salvando...';

                const res = await fetch('/perfil/enderecos/salvar', {
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
                    if (listaCardsEnderecos) {
                        listaCardsEnderecos.querySelectorAll('.checkout-address-item-card').forEach(c => c.classList.remove('is-selected'));
                        listaCardsEnderecos.querySelectorAll('.checkout-address-radio-input').forEach(r => { r.checked = false; });

                        const novoCard = criarCardEnderecoCheckout(data.endereco);
                        listaCardsEnderecos.appendChild(novoCard);
                    }

                    state.enderecoPrincipalId = data.endereco.id;

                    // Limpa formulário
                    ['perfil-end-nome', 'perfil-end-cep', 'perfil-end-logradouro', 'perfil-end-numero', 'perfil-end-complemento', 'perfil-end-bairro', 'perfil-end-cidade', 'perfil-end-estado'].forEach(id => {
                        const el = document.getElementById(id);
                        if (el) el.value = '';
                    });

                    if (formNovoEnderecoPerfil) {
                        formNovoEnderecoPerfil.style.display = 'none';
                    }

                    alert('Endereço cadastrado com sucesso!');
                } else {
                    alert(data.message || 'Erro ao cadastrar endereço.');
                }
            } catch (err) {
                alert('Erro de comunicação ao salvar endereço.');
            } finally {
                btnSalvarNovoEnd.disabled = false;
                btnSalvarNovoEnd.textContent = 'Salvar Endereço';
            }
        });
    }

    // Seleção e remoção de endereço no modal
    if (listaCardsEnderecos) {
        listaCardsEnderecos.addEventListener('change', async (e) => {
            const radio = e.target.closest('.checkout-address-radio-input');
            if (radio) {
                const endId = parseInt(radio.value, 10);
                state.enderecoPrincipalId = endId;

                listaCardsEnderecos.querySelectorAll('.checkout-address-item-card').forEach(c => {
                    c.classList.toggle('is-selected', c.dataset.addressId === String(endId));
                });

                if (endId > 0) {
                    try {
                        await fetch(`/perfil/enderecos/definir-principal/${endId}`, { method: 'POST' });
                    } catch (err) {
                        console.error('Falha ao definir endereço principal:', err);
                    }
                }
            }
        });

        listaCardsEnderecos.addEventListener('click', async (e) => {
            const btnRemover = e.target.closest('.js-remover-endereco');

            if (btnRemover) {
                e.stopPropagation();

                const cardsAtivos = listaCardsEnderecos.querySelectorAll('.checkout-address-item-card');
                if (cardsAtivos.length <= 1) {
                    alert('Não é possível remover o único endereço ativo da conta.');
                    return;
                }

                const endIdStr = btnRemover.dataset.enderecoId;
                if (!endIdStr) return;
                const endId = parseInt(endIdStr, 10);

                if (!confirm('Deseja realmente remover este endereço?')) return;

                try {
                    btnRemover.disabled = true;
                    btnRemover.textContent = 'Removendo...';
                    const res = await fetch(`/perfil/enderecos/remover/${endId}`, { method: 'POST' });
                    const data = await res.json();
                    if (data.success) {
                        const cardRemover = btnRemover.closest('.checkout-address-item-card');
                        if (cardRemover) {
                            cardRemover.style.opacity = '0';
                            cardRemover.style.transform = 'scale(0.95)';
                            setTimeout(() => {
                                cardRemover.remove();
                                if (state.enderecoPrincipalId === endId) {
                                    const primeiroRadio = listaCardsEnderecos.querySelector('.checkout-address-radio-input');
                                    if (primeiroRadio) {
                                        primeiroRadio.checked = true;
                                        primeiroRadio.dispatchEvent(new Event('change', { bubbles: true }));
                                    } else {
                                        state.enderecoPrincipalId = null;
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
                return;
            }

            const card = e.target.closest('.checkout-address-item-card');
            if (card && !e.target.closest('input')) {
                const radio = card.querySelector('.checkout-address-radio-input');
                if (radio && !radio.checked) {
                    radio.checked = true;
                    radio.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });
    }

    if (btnConfirmarEnderecoPerfil) {
        btnConfirmarEnderecoPerfil.addEventListener('click', () => {
            fecharModal(modalEnderecos);
        });
    }

    // 7. Botão Primário: Salvar Informações
    if (btnSalvarTudo) {
        btnSalvarTudo.addEventListener('click', async () => {
            const nome = document.getElementById('perfil-input-nome')?.value || '';
            const sobrenome = document.getElementById('perfil-input-sobrenome')?.value || '';
            const telefone = document.getElementById('perfil-input-telefone')?.value || '';

            if (!nome.trim() || !sobrenome.trim()) {
                alert('Nome e Sobrenome são obrigatórios.');
                return;
            }

            const payload = {
                nome: nome.trim(),
                sobrenome: sobrenome.trim(),
                telefone: telefone.trim(),
                senha_atual: state.senhaAtual,
                nova_senha: state.novaSenha,
                confirmar_nova_senha: state.confirmarNovaSenha,
                novo_email: state.novoEmail,
                codigo_email_atual: state.codigoEmailAtual,
                codigo_email_novo: state.codigoEmailNovo,
                enderecos: state.enderecos.length > 0 ? state.enderecos : null,
                endereco_principal_id: state.enderecoPrincipalId,
            };

            try {
                btnSalvarTudo.disabled = true;
                btnSalvarTudo.textContent = 'Salvando...';
                const res = await fetch('/perfil/salvar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await res.json();
                if (data.success) {
                    state.enderecos = [];
                    alert('Informações salvas com sucesso no banco!');
                    window.location.reload();
                } else {
                    alert(data.message || 'Erro ao salvar informações.');
                }
            } catch (err) {
                alert('Erro de comunicação ao salvar perfil.');
            } finally {
                btnSalvarTudo.disabled = false;
                btnSalvarTudo.textContent = 'Salvar Informações';
            }
        });
    }

    // 8. Carrossel Vertical de Itens do Pedido
    document.querySelectorAll('.js-pedido-carousel').forEach(carousel => {
        const items = carousel.querySelectorAll('.js-pedido-carousel-item');
        const btnUp = carousel.querySelector('.js-carousel-up');
        const btnDown = carousel.querySelector('.js-carousel-down');
        let currentIndex = 0;

        function updateCarousel() {
            items.forEach((it, idx) => {
                it.style.display = idx === currentIndex ? 'block' : 'none';
            });
        }

        if (btnUp) {
            btnUp.addEventListener('click', () => {
                currentIndex = (currentIndex - 1 + items.length) % items.length;
                updateCarousel();
            });
        }

        if (btnDown) {
            btnDown.addEventListener('click', () => {
                currentIndex = (currentIndex + 1) % items.length;
                updateCarousel();
            });
        }

        updateCarousel();
    });

    // 9. Modal de Detalhes do Item (23_MadeInLace Perfil2.1)
    document.querySelectorAll('.js-open-item-detalhe').forEach(thumb => {
        thumb.addEventListener('click', async () => {
            const itemId = thumb.dataset.itemId;
            if (!itemId) return;

            try {
                const res = await fetch(`/perfil/api/item-venda/${itemId}`);
                if (!res.ok) {
                    alert('Não foi possível carregar os detalhes do produto.');
                    return;
                }
                const data = await res.json();
                state.itemSelecionado = data;

                const imgElem = document.getElementById('item-detalhe-img');
                const nomeElem = document.getElementById('item-detalhe-nome');
                const tamElem = document.getElementById('item-detalhe-tamanho');
                const corElem = document.getElementById('item-detalhe-cor');
                const qtdElem = document.getElementById('item-detalhe-quantidade');
                const precoElem = document.getElementById('item-detalhe-preco');
                const actionsContainer = document.getElementById('item-detalhe-actions');

                if (imgElem) {
                    imgElem.src = data.imagem_url || '/static/img/site/MadeInLaceLogo.png';
                    imgElem.onerror = () => {
                        imgElem.src = '/static/img/site/MadeInLaceLogo.png';
                    };
                }
                if (nomeElem) nomeElem.textContent = data.produto_nome || '';
                if (tamElem) tamElem.textContent = `Tamanho: ${data.tamanho || '-'}`;
                if (corElem) corElem.textContent = `Cor: ${data.cor || '-'}`;
                if (qtdElem) qtdElem.textContent = `Quantidade: ${data.quantidade || 1}`;
                if (precoElem) precoElem.textContent = `Preço Unitário: ${data.preco_unitario_formatado || ''}`;

                // Botões Trocar e Reembolsar só aparecem se elegível
                const isEntregue = thumb.dataset.status === 'ENTREGUE';
                if (actionsContainer) {
                    actionsContainer.style.display = isEntregue && data.quantidade_disponivel > 0 ? 'flex' : 'none';
                }

                abrirModal(modalItemDetalhe);
            } catch (err) {
                alert('Erro ao buscar dados do produto.');
            }
        });
    });

    // 10. Botões Trocar e Reembolsar do Modal de Detalhe
    const btnIniciarTroca = document.getElementById('btn-iniciar-troca');
    if (btnIniciarTroca) {
        btnIniciarTroca.addEventListener('click', () => {
            if (!state.itemSelecionado) return;
            fecharModal(modalItemDetalhe);
            montarFormularioTroca(state.itemSelecionado);
            abrirModal(modalFormTroca);
        });
    }

    const btnIniciarReembolso = document.getElementById('btn-iniciar-reembolso');
    if (btnIniciarReembolso) {
        btnIniciarReembolso.addEventListener('click', () => {
            if (!state.itemSelecionado) return;
            fecharModal(modalItemDetalhe);
            montarFormularioReembolso(state.itemSelecionado);
            abrirModal(modalFormReembolso);
        });
    }

    // 11. Montagem Dinâmica do Formulário de Troca (5_MadeInLace Perfil2.2)
    function montarFormularioTroca(item) {
        document.getElementById('troca-nome-item').textContent = `Item: ${item.produto_nome}`;
        document.getElementById('troca-tam-item').textContent = `Tamanho: ${item.tamanho}`;
        document.getElementById('troca-cor-item').textContent = `Cor: ${item.cor}`;

        const inputQtd = document.getElementById('troca-quantidade-input');
        inputQtd.min = '1';
        inputQtd.max = String(item.quantidade_disponivel || 1);
        inputQtd.value = '1';

        function renderCaixasNovosProdutos(qtd) {
            const container = document.getElementById('troca-novos-produtos-container');
            if (!container) return;
            container.replaceChildren();

            for (let i = 1; i <= qtd; i++) {
                const box = document.createElement('div');
                box.className = 'posvenda-novo-produto-box';

                const titulo = document.createElement('span');
                titulo.textContent = 'Produto Novo A Receber:';
                titulo.style.fontWeight = '700';

                const selectVar = document.createElement('select');
                selectVar.className = 'js-select-variacao-troca';

                if (item.variacoes_disponiveis && item.variacoes_disponiveis.length > 0) {
                    item.variacoes_disponiveis.forEach(v => {
                        const opt = document.createElement('option');
                        opt.value = String(v.id);
                        opt.textContent = `Tamanho: ${v.tamanho} | Cor: ${v.cor}`;
                        selectVar.appendChild(opt);
                    });
                } else {
                    const opt = document.createElement('option');
                    opt.value = '';
                    opt.textContent = 'Nenhuma outra variação em estoque';
                    selectVar.appendChild(opt);
                }

                box.appendChild(titulo);
                box.appendChild(selectVar);
                container.appendChild(box);
            }
        }

        inputQtd.oninput = () => {
            let val = parseInt(inputQtd.value, 10);
            if (isNaN(val) || val < 1) val = 1;
            if (val > item.quantidade_disponivel) val = item.quantidade_disponivel;
            inputQtd.value = val;
            renderCaixasNovosProdutos(val);
        };

        renderCaixasNovosProdutos(1);
    }

    // Submissão do Formulário de Troca
    const btnEnviarTroca = document.getElementById('btn-enviar-troca-final');
    if (btnEnviarTroca) {
        btnEnviarTroca.addEventListener('click', async () => {
            if (!state.itemSelecionado) return;
            const qtd = parseInt(document.getElementById('troca-quantidade-input')?.value || '1', 10);
            const motivo = document.getElementById('troca-motivo-input')?.value || '';
            const selects = document.querySelectorAll('.js-select-variacao-troca');
            const variacoesNovas = [];

            selects.forEach(sel => {
                const vid = parseInt(sel.value, 10);
                if (vid) variacoesNovas.push(vid);
            });

            if (variacoesNovas.length !== qtd) {
                alert('Selecione uma variação disponível para cada unidade a trocar.');
                return;
            }

            try {
                btnEnviarTroca.disabled = true;
                btnEnviarTroca.textContent = 'Enviando...';
                const res = await fetch('/perfil/api/troca', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        item_venda_id: state.itemSelecionado.item_venda_id,
                        quantidade: qtd,
                        motivo: motivo.trim() || null,
                        variacoes_novas: variacoesNovas,
                    }),
                });
                const data = await res.json();
                if (data.success) {
                    alert('Solicitação de troca enviada com sucesso!');
                    fecharModal(modalFormTroca);
                    window.location.reload();
                } else {
                    alert(data.message || 'Falha ao solicitar troca.');
                }
            } catch (err) {
                alert('Erro de comunicação com o servidor.');
            } finally {
                btnEnviarTroca.disabled = false;
                btnEnviarTroca.textContent = 'Enviar';
            }
        });
    }

    // 12. Montagem Dinâmica do Formulário de Reembolso
    function montarFormularioReembolso(item) {
        document.getElementById('reembolso-nome-item').textContent = `Item: ${item.produto_nome}`;
        document.getElementById('reembolso-tam-item').textContent = `Tamanho: ${item.tamanho}`;
        document.getElementById('reembolso-cor-item').textContent = `Cor: ${item.cor}`;

        const inputQtd = document.getElementById('reembolso-quantidade-input');
        inputQtd.min = '1';
        inputQtd.max = String(item.quantidade_disponivel || 1);
        inputQtd.value = '1';

        inputQtd.oninput = () => {
            let val = parseInt(inputQtd.value, 10);
            if (isNaN(val) || val < 1) val = 1;
            if (val > item.quantidade_disponivel) val = item.quantidade_disponivel;
            inputQtd.value = val;
        };
    }

    // Submissão do Formulário de Reembolso
    const btnEnviarReembolso = document.getElementById('btn-enviar-reembolso-final');
    if (btnEnviarReembolso) {
        btnEnviarReembolso.addEventListener('click', async () => {
            if (!state.itemSelecionado) return;
            const qtd = parseInt(document.getElementById('reembolso-quantidade-input')?.value || '1', 10);
            const motivo = document.getElementById('reembolso-motivo-input')?.value || '';

            if (!motivo.trim()) {
                alert('O motivo do reembolso é obrigatório.');
                return;
            }

            try {
                btnEnviarReembolso.disabled = true;
                btnEnviarReembolso.textContent = 'Enviando...';
                const res = await fetch('/perfil/api/reembolso', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        item_venda_id: state.itemSelecionado.item_venda_id,
                        quantidade: qtd,
                        motivo: motivo.trim(),
                    }),
                });
                const data = await res.json();
                if (data.success) {
                    alert('Solicitação de reembolso enviada com sucesso!');
                    fecharModal(modalFormReembolso);
                    window.location.reload();
                } else {
                    alert(data.message || 'Falha ao solicitar reembolso.');
                }
            } catch (err) {
                alert('Erro de comunicação com o servidor.');
            } finally {
                btnEnviarReembolso.disabled = false;
                btnEnviarReembolso.textContent = 'Enviar';
            }
        });
    }

    // 13. Paginação de Pedidos e Trocas (Carregar Mais de 2 em 2)
    const btnCarregarMaisPedidos = document.getElementById('btn-carregar-mais-pedidos');
    if (btnCarregarMaisPedidos) {
        btnCarregarMaisPedidos.addEventListener('click', async () => {
            try {
                btnCarregarMaisPedidos.disabled = true;
                btnCarregarMaisPedidos.textContent = 'Carregando...';
                const res = await fetch(`/perfil/api/pedidos?filtro=todos&limit=2&offset=${state.pedidosOffset}`);
                const data = await res.json();
                if (data.pedidos && data.pedidos.length > 0) {
                    const container = document.getElementById('pedidos-list-container');
                    data.pedidos.forEach(p => {
                        const card = document.createElement('div');
                        card.className = 'pedido-card-item';

                        const colCarousel = document.createElement('div');
                        colCarousel.className = 'pedido-card__carousel-col';

                        const badge = document.createElement('div');
                        badge.className = 'pedido-card__badge';
                        badge.textContent = p.nome_exibicao;
                        colCarousel.appendChild(badge);

                        const thumb = document.createElement('img');
                        thumb.src = p.itens[0]?.imagem_url || '/static/img/site/MadeInLaceLogo.png';
                        thumb.onerror = () => {
                            thumb.src = '/static/img/site/MadeInLaceLogo.png';
                        };
                        thumb.alt = p.itens[0]?.produto_nome || 'Produto';
                        thumb.className = 'pedido-card__thumb js-open-item-detalhe';
                        thumb.dataset.itemId = p.itens[0]?.item_venda_id;
                        thumb.dataset.status = p.status_estado;
                        colCarousel.appendChild(thumb);

                        const infoGrid = document.createElement('div');
                        infoGrid.className = 'pedido-card__info-grid';

                        const chips = [
                            `Endereço: ${p.endereco_nome}`,
                            `Pagamento: ${p.metodo_pagamento}`,
                            `Data: ${p.data_formatada}`,
                            `Frete: ${p.frete_formatado}`,
                            `Preço Total: ${p.preco_total_formatado}`,
                            `Status: ${p.status_descricao}`,
                        ];
                        chips.forEach(texto => {
                            const chip = document.createElement('div');
                            chip.className = 'pedido-info-chip';
                            chip.textContent = texto;
                            infoGrid.appendChild(chip);
                        });

                        card.appendChild(colCarousel);
                        card.appendChild(infoGrid);
                        container.appendChild(card);
                    });
                    state.pedidosOffset += data.pedidos.length;
                    if (!data.tem_mais) {
                        btnCarregarMaisPedidos.style.display = 'none';
                    }
                } else {
                    btnCarregarMaisPedidos.style.display = 'none';
                }
            } catch (err) {
                alert('Erro ao carregar mais pedidos.');
            } finally {
                btnCarregarMaisPedidos.disabled = false;
                btnCarregarMaisPedidos.textContent = 'Carregar Mais Pedidos';
            }
        });
    }

    const btnCarregarMaisTrocas = document.getElementById('btn-carregar-mais-trocas');
    if (btnCarregarMaisTrocas) {
        btnCarregarMaisTrocas.addEventListener('click', async () => {
            try {
                btnCarregarMaisTrocas.disabled = true;
                btnCarregarMaisTrocas.textContent = 'Carregando...';
                const res = await fetch(`/perfil/api/trocas-reembolsos?limit=2&offset=${state.trocasOffset}`);
                const data = await res.json();
                if (data.itens && data.itens.length > 0) {
                    const container = document.getElementById('trocas-list-container');
                    data.itens.forEach(t => {
                        const card = document.createElement('div');
                        card.className = 'posvenda-card-item';

                        const colThumb = document.createElement('div');
                        colThumb.className = 'posvenda-card__thumb-col';

                        const badge = document.createElement('div');
                        badge.className = 'pedido-card__badge';
                        badge.textContent = t.titulo;
                        colThumb.appendChild(badge);

                        const thumb = document.createElement('img');
                        thumb.src = t.imagem_url;
                        thumb.alt = 'Produto';
                        thumb.className = 'posvenda-card__thumb';
                        colThumb.appendChild(thumb);

                        const infoGrid = document.createElement('div');
                        infoGrid.className = 'pedido-card__info-grid';

                        if (t.tipo === 'troca') {
                            const chips = [
                                `Data Criação: ${t.data_criacao}`,
                                `Status: ${t.status}`,
                                `Data Conclusão: ${t.data_conclusao}`,
                                `Novo Tamanho: ${t.novo_tamanho}`,
                                `Nova Cor: ${t.nova_cor}`,
                            ];
                            chips.forEach(texto => {
                                const chip = document.createElement('div');
                                chip.className = 'pedido-info-chip';
                                chip.textContent = texto;
                                infoGrid.appendChild(chip);
                            });
                        } else {
                            const chips = [
                                `Data Criação: ${t.data_criacao}`,
                                `Concluído: ${t.concluido}`,
                                `Data Conclusão: ${t.data_conclusao}`,
                            ];
                            chips.forEach(texto => {
                                const chip = document.createElement('div');
                                chip.className = 'pedido-info-chip';
                                chip.textContent = texto;
                                infoGrid.appendChild(chip);
                            });
                        }

                        card.appendChild(colThumb);
                        card.appendChild(infoGrid);
                        container.appendChild(card);
                    });
                    state.trocasOffset += data.itens.length;
                    if (!data.tem_mais) {
                        btnCarregarMaisTrocas.style.display = 'none';
                    }
                } else {
                    btnCarregarMaisTrocas.style.display = 'none';
                }
            } catch (err) {
                alert('Erro ao carregar mais trocas/reembolsos.');
            } finally {
                btnCarregarMaisTrocas.disabled = false;
                btnCarregarMaisTrocas.textContent = 'Carregar Mais';
            }
        });
    }
}
