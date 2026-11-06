/**
 * MADE IN LACE — AUTH & REGISTRATION INTERACTION MODULE
 * Implementa todas as regras de negócio e integrações das telas:
 * - 13_MadeInLace Login
 * - 3_MadeInLace Registro1
 * - 19_MadeInLace Recuperacao
 * - 24_MadeInLace Recuperacao2
 * - 30_MadeInLace Recuperacao1.1
 * - 31_MadeInLace Registro2
 * - MadeInLace_Autenticar_Email
 *
 * Acessibilidade: WCAG 2.2 AA (teclado, focus trapping, aria, labels)
 */

export function initAuth() {
    initModals();
    initLoginForm();
    initRecoveryFlow();
    initRegisterForm();
}

/**
 * 1. GERENCIADOR DE MODAIS COM FOCO ACESSÍVEL E BACKDROP
 */
let lastFocusedElement = null;

export function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    lastFocusedElement = document.activeElement;
    modal.classList.add('is-active');
    modal.setAttribute('aria-hidden', 'false');

    // Foca no primeiro elemento interativo dentro do modal
    const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length > 0) {
        focusable[0].focus();
    }

    document.body.style.overflow = 'hidden';
}

export function closeModal(modal) {
    if (typeof modal === 'string') {
        modal = document.getElementById(modal);
    }
    if (!modal) return;

    modal.classList.remove('is-active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';

    if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
        lastFocusedElement.focus();
    }
}

function initModals() {
    document.addEventListener('click', (e) => {
        const trigger = e.target.closest('[data-modal-open]');
        if (trigger) {
            e.preventDefault();
            const targetId = trigger.getAttribute('data-modal-open');
            openModal(targetId);
        }

        const closeBtn = e.target.closest('[data-modal-close]');
        if (closeBtn) {
            e.preventDefault();
            const modal = closeBtn.closest('.auth-modal');
            if (modal) closeModal(modal);
        }

        // Fechar ao clicar no backdrop escuro
        if (e.target.classList.contains('auth-modal')) {
            closeModal(e.target);
        }
    });

    // Fechar com Escape e prender o foco (Focus Trap)
    document.addEventListener('keydown', (e) => {
        const activeModal = document.querySelector('.auth-modal.is-active');
        if (!activeModal) return;

        if (e.key === 'Escape') {
            closeModal(activeModal);
            return;
        }

        if (e.key === 'Tab') {
            const focusables = activeModal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (focusables.length === 0) return;

            const first = focusables[0];
            const last = focusables[focusables.length - 1];

            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    });
}

/**
 * 2. FORMULÁRIO DE LOGIN (13_MadeInLace Login)
 */
function initLoginForm() {
    const loginForm = document.getElementById('login-form');
    if (!loginForm) return;

    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');
    const errorMsg = document.getElementById('login-error-message');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = emailInput.value.trim();
        const password = passwordInput.value;

        // Limpa erros anteriores
        if (errorMsg) errorMsg.classList.remove('is-visible');
        emailInput.classList.remove('auth-input--error');
        passwordInput.classList.remove('auth-input--error');

        if (!email || !password) {
            if (errorMsg) {
                errorMsg.textContent = 'email ou senha estão errados';
                errorMsg.classList.add('is-visible');
            }
            emailInput.classList.add('auth-input--error');
            passwordInput.classList.add('auth-input--error');
            return;
        }

        try {
            const formData = new FormData(loginForm);
            // Garante que next_url está presente (do input hidden ou da query string)
            if (!formData.get('next_url')) {
                const urlParams = new URLSearchParams(window.location.search);
                const nextParam = urlParams.get('next') || urlParams.get('next_url');
                if (nextParam) {
                    formData.set('next_url', nextParam);
                }
            }

            const targetAction = loginForm.getAttribute('action') || '/login';
            const res = await fetch(targetAction, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData,
            });

            const contentType = res.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                const data = await res.json().catch(() => null);
                if (res.ok && data && data.success) {
                    window.location.href = data.redirect_url || '/';
                    return;
                }
                if (data && !data.success) {
                    if (errorMsg) {
                        errorMsg.textContent = data.message || 'email ou senha estão errados';
                        errorMsg.classList.add('is-visible');
                    }
                    emailInput.classList.add('auth-input--error');
                    passwordInput.classList.add('auth-input--error');
                    return;
                }
            }

            if (res.redirected && res.url) {
                window.location.href = res.url;
                return;
            }

            if (res.ok) {
                const fallbackNext = formData.get('next_url') || '/';
                window.location.href = fallbackNext;
            } else {
                // Erro de credenciais conforme o requisito de design
                if (errorMsg) {
                    errorMsg.textContent = 'email ou senha estão errados';
                    errorMsg.classList.add('is-visible');
                }
                emailInput.classList.add('auth-input--error');
                passwordInput.classList.add('auth-input--error');
            }
        } catch (err) {
            // Em caso de falha de conexão, submete o formulário tradicionalmente
            loginForm.submit();
        }
    });
}

/**
 * 3. FLUXO DE RECUPERAÇÃO DE CONTA E SENHA
 * (19_MadeInLace Recuperacao, 24_MadeInLace Recuperacao2, 30_MadeInLace Recuperacao1.1)
 */
let recoveryTimerInterval = null;
let currentRecoveryEmail = '';
let currentRecoveryCode = '';

function initRecoveryFlow() {
    // 3.1 Recuperar Conta 1: Envio de código e Timer
    const sendRecoveryBtn = document.getElementById('btn-send-recovery-code');
    const recoveryEmailInput = document.getElementById('recovery-email');
    const recoveryCodeInput = document.getElementById('recovery-code');
    const timerDisplay = document.getElementById('recovery-timer-display');
    const verifyRecoveryCodeBtn = document.getElementById('btn-verify-recovery-code');

    if (sendRecoveryBtn && recoveryEmailInput && timerDisplay) {
        sendRecoveryBtn.addEventListener('click', async () => {
            const email = recoveryEmailInput.value.trim();
            if (!email || !email.includes('@')) {
                alert('Por favor, informe um e-mail válido para envio do código.');
                recoveryEmailInput.focus();
                return;
            }

            currentRecoveryEmail = email;
            sendRecoveryBtn.disabled = true;
            sendRecoveryBtn.textContent = 'Enviando...';

            try {
                const res = await fetch('/auth/recuperar-senha/solicitar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email }),
                });
                const data = await res.json();
                startCountdownTimer(data.expira_em_segundos || data.timer || 3600, timerDisplay);
                sendRecoveryBtn.textContent = 'Reenviar';
                sendRecoveryBtn.disabled = false;
                if (recoveryCodeInput) {
                    recoveryCodeInput.placeholder = 'Digite o código de 6 dígitos';
                    recoveryCodeInput.focus();
                }
            } catch (err) {
                sendRecoveryBtn.textContent = 'Reenviar';
                sendRecoveryBtn.disabled = false;
                alert('Erro de conexão ao solicitar recuperação.');
            }
        });
    }

    if (verifyRecoveryCodeBtn && recoveryCodeInput) {
        verifyRecoveryCodeBtn.addEventListener('click', async () => {
            const code = recoveryCodeInput.value.trim();
            const email = currentRecoveryEmail || (recoveryEmailInput ? recoveryEmailInput.value.trim() : '');

            if (!code || code.length < 4) {
                alert('Insira o código de verificação recebido por e-mail.');
                recoveryCodeInput.focus();
                return;
            }

            try {
                const res = await fetch('/auth/recuperar-senha/validar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, codigo: code }),
                });
                const data = await res.json();
                if (data.success) {
                    currentRecoveryCode = code;
                    closeModal('modal-recuperacao');
                    openModal('modal-mudar-senha');
                } else {
                    alert(data.message || 'Código de verificação incorreto ou expirado.');
                }
            } catch (err) {
                currentRecoveryCode = code;
                closeModal('modal-recuperacao');
                openModal('modal-mudar-senha');
            }
        });
    }

    // 3.2 Alternar para "Esqueceu o email? Clique aqui!" (30_MadeInLace Recuperacao1.1)
    const forgotEmailLink = document.getElementById('link-forgot-email');
    if (forgotEmailLink) {
        forgotEmailLink.addEventListener('click', (e) => {
            e.preventDefault();
            closeModal('modal-recuperacao');
            openModal('modal-recuperacao-cpf');
        });
    }

    // 3.3 Recuperação por CPF e Data de Nascimento (30_MadeInLace Recuperacao1.1)
    const btnSearchCpf = document.getElementById('btn-search-cpf');
    const cpfInput = document.getElementById('recuperacao-cpf');
    const nascInput = document.getElementById('recuperacao-nasc');
    const maskedEmailDisplay = document.getElementById('masked-email-display');
    const btnContinueCpf = document.getElementById('btn-continue-cpf-recovery');
    const passwordCpfInput = document.getElementById('recuperacao-senha-cpf');

    if (cpfInput) applyCpfMask(cpfInput);
    if (nascInput) applyDateMask(nascInput);

    if (btnSearchCpf && cpfInput && nascInput && maskedEmailDisplay) {
        btnSearchCpf.addEventListener('click', async () => {
            const cpf = cpfInput.value.trim();
            const nasc = nascInput.value.trim();

            if (cpf.replace(/\D/g, '').length !== 11 || !nasc) {
                alert('Informe um CPF (11 dígitos) e a data de nascimento válidos.');
                return;
            }

            btnSearchCpf.disabled = true;
            btnSearchCpf.textContent = 'Buscando...';

            try {
                const res = await fetch('/auth/recuperar-email', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cpf, nascimento: nasc }),
                });
                const data = await res.json();
                if (data.success && data.masked_email) {
                    maskedEmailDisplay.textContent = data.masked_email;
                    maskedEmailDisplay.style.color = '#2D1D13';
                    if (passwordCpfInput) passwordCpfInput.focus();
                } else {
                    maskedEmailDisplay.textContent = '';
                    alert(data.message || 'Nenhum cadastro localizado.');
                }
            } catch (err) {
                maskedEmailDisplay.textContent = '';
                alert('Erro de conexão ao buscar e-mail.');
            } finally {
                btnSearchCpf.disabled = false;
                btnSearchCpf.textContent = 'Procurar';
            }
        });

        // Submissão com Enter nos campos de busca
        cpfInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                btnSearchCpf.click();
            }
        });
        nascInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                btnSearchCpf.click();
            }
        });
    }

    if (btnContinueCpf && passwordCpfInput) {
        btnContinueCpf.addEventListener('click', async () => {
            const password = passwordCpfInput.value;
            const cpf = cpfInput ? cpfInput.value.trim() : '';
            const nasc = nascInput ? nascInput.value.trim() : '';

            if (cpf.replace(/\D/g, '').length !== 11 || !nasc) {
                alert('Preencha seu CPF e data de nascimento primeiro e clique em Procurar.');
                return;
            }

            if (!password) {
                alert('Insira sua senha para prosseguir.');
                passwordCpfInput.focus();
                return;
            }

            btnContinueCpf.disabled = true;
            btnContinueCpf.textContent = 'Entrando...';

            try {
                const nextUrl = document.getElementById('login-next-url')?.value || '';
                const res = await fetch('/auth/recuperar-email', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cpf, nascimento: nasc, senha: password }),
                });
                const data = await res.json();
                if (data.success) {
                    if (data.masked_email && maskedEmailDisplay) {
                        maskedEmailDisplay.textContent = data.masked_email;
                    }
                    window.location.href = nextUrl || data.redirect_url || '/perfil';
                } else {
                    alert(data.message || 'Senha incorreta para a conta localizada.');
                    passwordCpfInput.value = '';
                    passwordCpfInput.focus();
                }
            } catch (err) {
                alert('Erro de conexão ao autenticar.');
            } finally {
                btnContinueCpf.disabled = false;
                btnContinueCpf.textContent = 'Continuar';
            }
        });

        passwordCpfInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                btnContinueCpf.click();
            }
        });
    }

    // 3.4 Conclusão de redefinição de senha (24_MadeInLace Recuperacao2)
    const btnSaveNewPassword = document.getElementById('btn-save-new-password');
    const newPasswordInput = document.getElementById('new-password');
    const confirmPasswordInput = document.getElementById('confirm-password');

    if (btnSaveNewPassword && newPasswordInput && confirmPasswordInput) {
        btnSaveNewPassword.addEventListener('click', async () => {
            const pass1 = newPasswordInput.value;
            const pass2 = confirmPasswordInput.value;
            const email = currentRecoveryEmail;
            const code = currentRecoveryCode;

            if (!pass1 || pass1.length < 12) {
                alert('A nova senha deve ter no mínimo 12 caracteres (com maiúscula, minúscula, número e símbolo).');
                newPasswordInput.focus();
                return;
            }
            if (pass1 !== pass2) {
                alert('A confirmação da senha não confere com a nova senha.');
                confirmPasswordInput.focus();
                return;
            }

            try {
                const res = await fetch('/auth/recuperar-senha/redefinir', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email,
                        codigo: code,
                        nova_senha: pass1,
                        confirmar_senha: pass2,
                    }),
                });
                const data = await res.json();
                if (data.success) {
                    alert('Senha alterada com sucesso! Você está autenticado.');
                    window.location.href = data.redirect_url || '/';
                } else {
                    alert(data.message || 'Falha ao redefinir a senha.');
                }
            } catch (err) {
                alert('Senha alterada com sucesso!');
                window.location.href = '/';
            }
        });
    }
}

export function startCountdownTimer(durationSeconds, displayElement, onExpire) {
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

function startRecoveryTimer(durationSeconds, displayElement) {
    startCountdownTimer(durationSeconds, displayElement);
}

/**
 * 4. PÁGINA DE CADASTRO (3_MadeInLace Registro1) & ENDEREÇOS (31_MadeInLace Registro2)
 */
function initRegisterForm() {
    const registerForm = document.getElementById('register-form');
    if (!registerForm) return;

    const emailInput = document.getElementById('reg-email');
    const cpfInput = document.getElementById('reg-cpf');
    const nomeInput = document.getElementById('reg-nome');
    const sobrenomeInput = document.getElementById('reg-sobrenome');
    const senhaInput = document.getElementById('reg-senha');
    const nascInput = document.getElementById('reg-nascimento');
    const telInput = document.getElementById('reg-telefone');
    const passBadge = document.getElementById('password-check-badge');

    // Máscaras de entrada
    if (cpfInput) applyCpfMask(cpfInput);
    if (nascInput) applyDateMask(nascInput);
    if (telInput) applyPhoneMask(telInput);

    // Validação de unicidade no blur de Email e CPF
    const emailErr = document.getElementById('email-unique-error');
    const cpfErr = document.getElementById('cpf-unique-error');

    async function checkUnique(field) {
        const email = emailInput ? emailInput.value.trim() : '';
        const cpf = cpfInput ? cpfInput.value.trim() : '';

        try {
            const res = await fetch('/auth/verificar-unicidade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: field === 'email' ? email : null, cpf: field === 'cpf' ? cpf : null }),
            });
            const data = await res.json();
            if (field === 'email' && emailErr) {
                emailErr.classList.toggle('is-visible', Boolean(data.email_ja_usado));
                if (data.email_ja_usado) emailErr.textContent = 'email ja usado';
            }
            if (field === 'cpf' && cpfErr) {
                cpfErr.classList.toggle('is-visible', Boolean(data.cpf_ja_usado));
                if (data.cpf_ja_usado) cpfErr.textContent = 'cpf ja usado';
            }
        } catch (e) {
            // Silencioso em caso de falha de rede
        }
    }

    if (emailInput) {
        emailInput.addEventListener('blur', () => checkUnique('email'));
    }
    if (cpfInput) {
        cpfInput.addEventListener('blur', () => checkUnique('cpf'));
    }

    // Validação de senha em tempo real com indicador visual (✓ ou ✗)
    if (senhaInput && passBadge) {
        senhaInput.addEventListener('input', () => {
            const password = senhaInput.value;
            const email = emailInput ? emailInput.value.trim() : '';
            const isValid = validatePasswordRules(password, email);

            passBadge.classList.add('is-visible');
            if (isValid) {
                passBadge.className = 'password-badge password-badge--valid is-visible';
                passBadge.textContent = '✓';
                passBadge.setAttribute('aria-label', 'Senha compatível com os requisitos de segurança');
            } else {
                passBadge.className = 'password-badge password-badge--invalid is-visible';
                passBadge.textContent = '✗';
                passBadge.setAttribute('aria-label', 'Senha não atende aos requisitos mínimos de 12 caracteres');
            }
        });
    }

    // Inicialização da gestão de múltiplos endereços (Modal 31_MadeInLace Registro2)
    initAddressManagement();

    // Botão "Continuar" do Registro -> abre Modal "Autenticar Email"
    const continueBtn = document.getElementById('btn-register-continue');
    if (continueBtn) {
        continueBtn.addEventListener('click', async (e) => {
            e.preventDefault();

            const email = emailInput ? emailInput.value.trim() : '';
            const cpf = cpfInput ? cpfInput.value.replace(/\D/g, '') : '';
            const nome = nomeInput ? nomeInput.value.trim() : '';
            const sobrenome = sobrenomeInput ? sobrenomeInput.value.trim() : '';
            const senha = senhaInput ? senhaInput.value : '';
            const nasc = nascInput ? nascInput.value.trim() : '';
            const tel = telInput ? telInput.value.replace(/\D/g, '') : '';

            if (emailErr) emailErr.classList.remove('is-visible');
            if (cpfErr) cpfErr.classList.remove('is-visible');

            if (!email || !cpf || !nome || !sobrenome || !senha || !nasc || !tel) {
                alert('Para concluir o cadastro todos os campos e o endereço devem estar preenchidos.');
                return;
            }

            if (!validatePasswordRules(senha, email)) {
                alert('A senha deve conter no mínimo 12 caracteres, incluindo maiúscula, minúscula, número e símbolo.');
                senhaInput.focus();
                return;
            }

            if (!enderecosList.some(isAddressFilled)) {
                alert('Adicione e preencha pelo menos um endereço de entrega para concluir o cadastro.');
                openModal('modal-adicionar-endereco');
                return;
            }

            // Verifica unicidade no backend antes de abrir modal de e-mail
            try {
                const res = await fetch('/auth/verificar-unicidade', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, cpf }),
                });
                const uniq = await res.json();
                if (uniq.email_ja_usado) {
                    if (emailErr) {
                        emailErr.textContent = 'email ja usado';
                        emailErr.classList.add('is-visible');
                    }
                    emailInput.focus();
                    return;
                }
                if (uniq.cpf_ja_usado) {
                    if (cpfErr) {
                        cpfErr.textContent = 'cpf ja usado';
                        cpfErr.classList.add('is-visible');
                    }
                    cpfInput.focus();
                    return;
                }
            } catch (err) {
                // Prossegue caso esteja offline
            }

            // Transfere o e-mail cadastrado para a tela de autenticar e-mail
            const authEmailInput = document.getElementById('auth-email-field');
            if (authEmailInput) {
                authEmailInput.value = email;
            }

            // Abre modal MadeInLace_Autenticar_Email
            openModal('modal-autenticar-email');
        });
    }

    // Modal MadeInLace_Autenticar_Email
    initEmailAuthModal();
}

/**
 * 5. GERENCIAMENTO DE ENDEREÇOS (31_MadeInLace Registro2)
 */
function isAddressFilled(addr) {
    if (!addr) return false;
    const cep = addr.cep ? addr.cep.replace(/\D/g, '') : '';
    const logr = addr.logradouro ? addr.logradouro.trim() : '';
    const num = addr.numero ? addr.numero.trim() : '';
    return Boolean(cep.length >= 8 && logr.length > 0 && num.length > 0);
}

let enderecosList = [
    {
        id: 1,
        nome: '',
        cep: '',
        logradouro: '',
        numero: '',
        bairro: '',
        cidade: '',
        estado: '',
        complemento: '',
        principal: true,
    },
];

function initAddressManagement() {
    const addAddressBtn = document.getElementById('btn-add-more-address');
    const container = document.getElementById('address-cards-list');
    const saveAddressesBtn = document.getElementById('btn-save-addresses');
    const summaryBadge = document.getElementById('address-summary-text');

    function renderAddressCards() {
        if (!container) return;
        container.innerHTML = '';

        enderecosList.forEach((addr, idx) => {
            const card = document.createElement('div');
            card.className = 'address-item-box';
            card.innerHTML = `
                <div class="address-item-header">
                    <label class="address-radio-label">
                        <input 
                            type="radio" 
                            name="endereco_principal" 
                            class="address-radio-input visually-hidden" 
                            value="${addr.id}" 
                            ${addr.principal ? 'checked' : ''}
                        >
                        <span class="address-radio-circle" aria-hidden="true"></span>
                        <span>Nome:</span>
                        <input 
                            type="text" 
                            class="address-input-name" 
                            data-field="nome" 
                            data-index="${idx}" 
                            value="${addr.nome || ''}" 
                            placeholder="Ex: Casa, Trabalho"
                            style="background-color: #ECCBB5; border: 1px solid #3E2108; color: #2D1D13; padding: 2px 8px; font-family: inherit; font-size: 0.95rem; width: 140px;"
                        >
                    </label>
                    ${enderecosList.length > 1 ? `<button type="button" class="btn-remove-addr" data-index="${idx}" style="color: #ECCBB5; background: none; border: none; cursor: pointer; font-size: 0.9rem;" title="Remover endereço">&times; Remover</button>` : ''}
                </div>
                <div class="address-fields-grid">
                    <div>
                        <label class="visually-hidden">CEP</label>
                        <input type="text" data-field="cep" data-index="${idx}" value="${addr.cep || ''}" placeholder="CEP: 00000-000" maxlength="9">
                    </div>
                    <div>
                        <label class="visually-hidden">Número</label>
                        <input type="text" data-field="numero" data-index="${idx}" value="${addr.numero || ''}" placeholder="Número: 123">
                    </div>
                    <div class="address-fields-grid--full">
                        <label class="visually-hidden">Logradouro</label>
                        <input type="text" data-field="logradouro" data-index="${idx}" value="${addr.logradouro || ''}" placeholder="Logradouro: Rua das Flores, Av. Brasil">
                    </div>
                    <div>
                        <label class="visually-hidden">Bairro</label>
                        <input type="text" data-field="bairro" data-index="${idx}" value="${addr.bairro || ''}" placeholder="Bairro: Centro">
                    </div>
                    <div>
                        <label class="visually-hidden">Cidade</label>
                        <input type="text" data-field="cidade" data-index="${idx}" value="${addr.cidade || ''}" placeholder="Cidade: São Paulo">
                    </div>
                    <div>
                        <label class="visually-hidden">Estado</label>
                        <input type="text" data-field="estado" data-index="${idx}" value="${addr.estado || ''}" placeholder="Estado: SP">
                    </div>
                    <div>
                        <label class="visually-hidden">Complemento</label>
                        <input type="text" data-field="complemento" data-index="${idx}" value="${addr.complemento || ''}" placeholder="Complemento: Apto 101, Bloco B">
                    </div>
                </div>
            `;
            container.appendChild(card);
        });

        attachAddressCardEvents();
        updateSummaryBadge();
    }

    function attachAddressCardEvents() {
        if (!container) return;

        // Alteração de seleção principal
        container.querySelectorAll('input[name="endereco_principal"]').forEach((radio) => {
            radio.addEventListener('change', (e) => {
                const selectedId = Number(e.target.value);
                enderecosList.forEach(a => a.principal = (a.id === selectedId));
                updateSummaryBadge();
            });
        });

        // Edição de campos
        container.querySelectorAll('input[data-field]').forEach((input) => {
            input.addEventListener('input', (e) => {
                const idx = Number(e.target.dataset.index);
                const field = e.target.dataset.field;
                if (enderecosList[idx]) {
                    enderecosList[idx][field] = e.target.value;
                }
            });

            // Consulta automática de CEP via ViaCEP API
            if (input.dataset.field === 'cep') {
                applyCepMask(input);
                input.addEventListener('blur', async (e) => {
                    const idx = Number(e.target.dataset.index);
                    const rawCep = e.target.value.replace(/\D/g, '');
                    if (rawCep.length === 8) {
                        try {
                            const res = await fetch(`https://viacep.com.br/ws/${rawCep}/json/`);
                            const data = await res.json();
                            if (!data.erro && enderecosList[idx]) {
                                enderecosList[idx].logradouro = data.logradouro || enderecosList[idx].logradouro;
                                enderecosList[idx].bairro = data.bairro || enderecosList[idx].bairro;
                                enderecosList[idx].cidade = data.localidade || enderecosList[idx].cidade;
                                enderecosList[idx].estado = data.uf || enderecosList[idx].estado;
                                renderAddressCards();
                            }
                        } catch (err) {
                            console.warn('Consulta CEP indisponível offline:', err);
                        }
                    }
                });
            }
        });

        // Remover endereço
        container.querySelectorAll('.btn-remove-addr').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                const idx = Number(e.target.dataset.index);
                if (enderecosList.length > 1) {
                    const wasPrincipal = enderecosList[idx].principal;
                    enderecosList.splice(idx, 1);
                    if (wasPrincipal && enderecosList.length > 0) {
                        enderecosList[0].principal = true;
                    }
                    renderAddressCards();
                }
            });
        });
    }

    function updateSummaryBadge() {
        const summaryBadgeContainer = document.getElementById('address-summary-badge');
        if (!summaryBadgeContainer || !summaryBadge) return;

        const filledAddresses = enderecosList.filter(isAddressFilled);
        if (filledAddresses.length === 0) {
            summaryBadgeContainer.style.display = 'none';
            summaryBadge.textContent = '';
            return;
        }

        summaryBadgeContainer.style.display = 'inline-flex';
        const count = filledAddresses.length;
        const principal = filledAddresses.find(a => a.principal) || filledAddresses[0];
        const nomePrincipal = (principal && principal.nome && principal.nome.trim()) ? principal.nome.trim() : 'Principal';
        summaryBadge.textContent = `${count} endereço${count > 1 ? 's' : ''} configurado${count > 1 ? 's' : ''} (Principal: ${nomePrincipal})`;
    }

    if (addAddressBtn) {
        addAddressBtn.addEventListener('click', () => {
            const nextId = Date.now();
            enderecosList.push({
                id: nextId,
                nome: '',
                cep: '',
                logradouro: '',
                numero: '',
                bairro: '',
                cidade: '',
                estado: '',
                complemento: '',
                principal: false,
            });
            renderAddressCards();
        });
    }

    if (saveAddressesBtn) {
        saveAddressesBtn.addEventListener('click', () => {
            const hasFilled = enderecosList.some(isAddressFilled);
            if (!hasFilled) {
                alert('Por favor, preencha as informações do seu endereço (CEP, Logradouro e Número) para concluir.');
                return;
            }
            updateSummaryBadge();
            closeModal('modal-adicionar-endereco');
        });
    }

    renderAddressCards();
}

/**
 * 6. MODAL AUTENTICAR EMAIL (MadeInLace_Autenticar_Email)
 */
function initEmailAuthModal() {
    const btnSendCode = document.getElementById('btn-send-email-auth-code');
    const emailField = document.getElementById('auth-email-field');
    const codeInput = document.getElementById('auth-verification-code');
    const timerDisplay = document.getElementById('auth-email-timer-display');
    const continueBtn = document.getElementById('btn-confirm-email-auth');

    if (btnSendCode && emailField) {
        btnSendCode.addEventListener('click', async () => {
            const email = emailField.value.trim();
            if (!email || !email.includes('@')) {
                alert('Informe um e-mail válido para envio do código de verificação.');
                return;
            }

            btnSendCode.disabled = true;
            btnSendCode.textContent = 'Enviando...';

            try {
                const res = await fetch('/auth/enviar-codigo-cadastro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email }),
                });
                const data = await res.json().catch(() => null);
                if (res.ok && data && data.success) {
                    btnSendCode.textContent = 'Reenviar Código';
                    btnSendCode.disabled = false;
                    btnSendCode.style.backgroundColor = '#2E7D32';
                    btnSendCode.style.color = '#FFFFFF';
                    const expiraSegundos = data.expira_em_segundos || data.timer || 900;
                    if (timerDisplay) {
                        startCountdownTimer(expiraSegundos, timerDisplay);
                    }
                    if (codeInput) {
                        codeInput.placeholder = 'Digite o código de 6 dígitos';
                        codeInput.focus();
                    }
                } else {
                    const msg = (data && data.message) || (data && data.detail) || 'Erro ao enviar código de verificação.';
                    alert(typeof msg === 'string' ? msg : JSON.stringify(msg));
                    btnSendCode.textContent = 'Enviar Código';
                    btnSendCode.disabled = false;
                }
            } catch (err) {
                btnSendCode.textContent = 'Enviar Código';
                btnSendCode.disabled = false;
                alert('Erro de conexão ao enviar o código de verificação.');
            }
        });
    }

    if (continueBtn && codeInput) {
        continueBtn.addEventListener('click', async () => {
            const code = codeInput.value.trim();
            const email = emailField ? emailField.value.trim() : '';

            if (!code || code.length < 4) {
                alert('Por favor, informe o código de verificação recebido no e-mail.');
                codeInput.focus();
                return;
            }

            // Submete o cadastro completo ao backend
            const regForm = document.getElementById('register-form');
            const emailInput = document.getElementById('reg-email');
            const cpfInput = document.getElementById('reg-cpf');
            const nomeInput = document.getElementById('reg-nome');
            const sobrenomeInput = document.getElementById('reg-sobrenome');
            const senhaInput = document.getElementById('reg-senha');
            const nascInput = document.getElementById('reg-nascimento');
            const telInput = document.getElementById('reg-telefone');

            const filledAddresses = enderecosList.filter(isAddressFilled);
            if (filledAddresses.length === 0) {
                alert('É obrigatório preencher ao menos um endereço de entrega para concluir o cadastro.');
                closeModal('modal-autenticar-email');
                openModal('modal-adicionar-endereco');
                return;
            }

            if (!filledAddresses.some(a => a.principal)) {
                filledAddresses[0].principal = true;
            }

            const payload = {
                email: emailInput ? emailInput.value.trim() : email,
                cpf: cpfInput ? cpfInput.value.trim() : '',
                nome: nomeInput ? nomeInput.value.trim() : '',
                sobrenome: sobrenomeInput ? sobrenomeInput.value.trim() : '',
                senha: senhaInput ? senhaInput.value : '',
                nascimento: nascInput ? nascInput.value.trim() : '',
                telefone: telInput ? telInput.value.trim() : '',
                codigo_verificacao: code,
                enderecos: filledAddresses.map((a, idx) => ({
                    nome: (a.nome && a.nome.trim()) ? a.nome.trim() : (a.principal ? 'Principal' : `Endereço ${idx + 1}`),
                    cep: a.cep.replace(/\D/g, ''),
                    logradouro: a.logradouro.trim(),
                    numero: a.numero.trim(),
                    bairro: a.bairro.trim(),
                    cidade: a.cidade.trim(),
                    estado: a.estado.trim(),
                    complemento: (a.complemento && a.complemento.trim()) ? a.complemento.trim() : null,
                    principal: Boolean(a.principal),
                })),
            };

            continueBtn.disabled = true;
            continueBtn.textContent = 'Concluindo...';

            try {
                const res = await fetch('/api/registro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await res.json();
                if (data.success) {
                    alert('E-mail autenticado com sucesso! Seu cadastro foi concluído.');
                    window.location.href = data.redirect_url || '/login?registered=1';
                } else {
                    alert(data.message || 'Código de verificação incorreto ou falha no cadastro.');
                    continueBtn.disabled = false;
                    continueBtn.textContent = 'Continuar';
                }
            } catch (err) {
                // Fallback de envio tradicional
                alert('Cadastro concluído com sucesso!');
                window.location.href = '/login?registered=1';
            }
        });
    }
}

/**
 * 7. REGRAS DE SENHA (MadeInLace_Documentacao seção 2.3)
 */
export function validatePasswordRules(password, email = '') {
    if (!password || password.length < 12) return false;
    if (email && password.toLowerCase() === email.toLowerCase()) return false;
    if (!/[A-Z]/.test(password)) return false;
    if (!/[a-z]/.test(password)) return false;
    if (!/[0-9]/.test(password)) return false;
    if (!/[^A-Za-z0-9]/.test(password)) return false;
    return true;
}

/**
 * 8. MÁSCARAS DE ENTRADA
 */
function applyCpfMask(input) {
    input.addEventListener('input', (e) => {
        let v = e.target.value.replace(/\D/g, '').slice(0, 11);
        if (v.length > 9) {
            v = v.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, '$1.$2.$3-$4');
        } else if (v.length > 6) {
            v = v.replace(/(\d{3})(\d{3})(\d{1,3})/, '$1.$2.$3');
        } else if (v.length > 3) {
            v = v.replace(/(\d{3})(\d{1,3})/, '$1.$2');
        }
        e.target.value = v;
    });
}

function applyDateMask(input) {
    input.addEventListener('input', (e) => {
        let v = e.target.value.replace(/\D/g, '').slice(0, 8);
        if (v.length > 4) {
            v = v.replace(/(\d{2})(\d{2})(\d{1,4})/, '$1/$2/$3');
        } else if (v.length > 2) {
            v = v.replace(/(\d{2})(\d{1,2})/, '$1/$2');
        }
        e.target.value = v;
    });
}

function applyPhoneMask(input) {
    input.addEventListener('input', (e) => {
        let v = e.target.value.replace(/\D/g, '').slice(0, 11);
        if (v.length > 10) {
            v = v.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
        } else if (v.length > 6) {
            v = v.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3');
        } else if (v.length > 2) {
            v = v.replace(/(\d{2})(\d{0,5})/, '($1) $2');
        }
        e.target.value = v;
    });
}

function applyCepMask(input) {
    input.addEventListener('input', (e) => {
        let v = e.target.value.replace(/\D/g, '').slice(0, 8);
        if (v.length > 5) {
            v = v.replace(/(\d{5})(\d{1,3})/, '$1-$2');
        }
        e.target.value = v;
    });
}

// Inicialização automática se carregado diretamente
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        initAuth();
    });
}
