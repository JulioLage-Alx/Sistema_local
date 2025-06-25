/* ============================================
   Sistema Crediário Açougue - Main JavaScript
   ============================================ */

// Namespace da aplicação
window.App = {
    config: {
        baseUrl: '',
        csrfToken: '',
        userLogged: false,
        debug: false
    },
    
    // Inicialização da aplicação
    init: function() {
        this.loadConfig();
        this.initComponents();
        this.bindEvents();
        this.initMasks();
        this.initTooltips();
        this.initFormValidation();
        
        if (this.config.debug) {
            console.log('App initialized successfully');
        }
    },
    
    // Carregar configurações globais
    loadConfig: function() {
        if (window.APP_CONFIG) {
            this.config = Object.assign(this.config, window.APP_CONFIG);
        }
    },
    
    // Inicializar componentes
    initComponents: function() {
        // Configurar moment.js para português
        if (typeof moment !== 'undefined') {
            moment.locale('pt-br');
        }
        
        // Configurar Chart.js padrões
        if (typeof Chart !== 'undefined') {
            Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
            Chart.defaults.color = '#858796';
        }
        
        // Auto-hide alerts após 5 segundos
        setTimeout(() => {
            $('.alert:not(.alert-permanent)').fadeOut();
        }, 5000);
        
        // Inicializar dropdowns
        $('.dropdown-toggle').dropdown();
    },
    
    // Vincular eventos globais
    bindEvents: function() {
        // Confirmação de exclusão
        $(document).on('click', '[data-confirm]', this.handleConfirmAction);
        
        // Loading em formulários
        $(document).on('submit', 'form[data-loading]', this.handleFormLoading);
        
        // AJAX setup
        this.setupAjax();
        
        // Teclas de atalho
        this.bindKeyboardShortcuts();
        
        // Auto-save para alguns formulários
        this.initAutoSave();
    },
    
    // Configurar máscaras de input
    initMasks: function() {
        // CPF
        $('.mask-cpf').mask('000.000.000-00', {
            reverse: false,
            placeholder: '___.___.___-__'
        });
        
        // Telefone
        $('.mask-phone').mask('(00) 00000-0000', {
            placeholder: '(__) _____-____'
        });
        
        // CEP
        $('.mask-cep').mask('00000-000', {
            placeholder: '_____-___'
        });
        
        // Dinheiro
        $('.mask-money').mask('#.##0,00', {
            reverse: true,
            placeholder: '0,00'
        });
        
        // Quantidade/Peso
        $('.mask-quantity').mask('#.##0,000', {
            reverse: true,
            placeholder: '0,000'
        });
        
        // Data
        $('.mask-date').mask('00/00/0000', {
            placeholder: '__/__/____'
        });
    },
    
    // Inicializar tooltips
    initTooltips: function() {
        $('[data-toggle="tooltip"]').tooltip();
        $('[data-toggle="popover"]').popover();
    },
    
    // Validação de formulários
    initFormValidation: function() {
        // Bootstrap validation
        $('.needs-validation').on('submit', function(e) {
            if (!this.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            $(this).addClass('was-validated');
        });
        
        // Validação customizada de CPF
        $('.validate-cpf').on('blur', function() {
            const cpf = $(this).val().replace(/\D/g, '');
            if (cpf && !App.utils.validateCPF(cpf)) {
                $(this).addClass('is-invalid');
                $(this).siblings('.invalid-feedback').text('CPF inválido');
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        // Validação de email
        $('.validate-email').on('blur', function() {
            const email = $(this).val();
            if (email && !App.utils.validateEmail(email)) {
                $(this).addClass('is-invalid');
                $(this).siblings('.invalid-feedback').text('Email inválido');
            } else {
                $(this).removeClass('is-invalid');
            }
        });
    },
    
    // Configurar AJAX
    setupAjax: function() {
        // CSRF Token para requisições AJAX
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", App.config.csrfToken);
                }
            }
        });
        
        // Loading global para AJAX
        $(document).ajaxStart(function() {
            App.ui.showLoading();
        }).ajaxStop(function() {
            App.ui.hideLoading();
        });
        
        // Tratamento de erros AJAX
        $(document).ajaxError(function(event, xhr, settings, thrownError) {
            App.ui.hideLoading();
            
            if (xhr.status === 401) {
                App.ui.showAlert('Sessão expirada. Faça login novamente.', 'warning');
                setTimeout(() => {
                    window.location.href = '/auth/login';
                }, 2000);
            } else if (xhr.status === 403) {
                App.ui.showAlert('Acesso negado.', 'danger');
            } else if (xhr.status >= 500) {
                App.ui.showAlert('Erro interno do servidor. Tente novamente.', 'danger');
            }
        });
    },
    
    // Atalhos de teclado
    bindKeyboardShortcuts: function() {
        $(document).on('keydown', function(e) {
            // Ctrl + S para salvar formulários
            if ((e.ctrlKey || e.metaKey) && e.keyCode === 83) {
                e.preventDefault();
                const form = $('form:visible').first();
                if (form.length) {
                    form.submit();
                }
            }
            
            // Esc para fechar modais
            if (e.keyCode === 27) {
                $('.modal:visible').modal('hide');
            }
            
            // Ctrl + N para nova entrada (se aplicável)
            if ((e.ctrlKey || e.metaKey) && e.keyCode === 78) {
                const newBtn = $('[data-action="new"]:visible').first();
                if (newBtn.length) {
                    e.preventDefault();
                    newBtn.click();
                }
            }
        });
    },
    
    // Auto-save para formulários longos
    initAutoSave: function() {
        let autoSaveTimeout;
        
        $('form[data-autosave]').on('input change', function() {
            clearTimeout(autoSaveTimeout);
            const form = $(this);
            
            autoSaveTimeout = setTimeout(() => {
                const formData = form.serialize();
                const key = 'autosave_' + (form.data('autosave-key') || window.location.pathname);
                
                try {
                    localStorage.setItem(key, formData);
                    App.ui.showToast('Rascunho salvo automaticamente', 'info', 2000);
                } catch (e) {
                    console.warn('Erro ao salvar rascunho:', e);
                }
            }, 30000); // Auto-save a cada 30 segundos
        });
        
        // Restaurar dados salvos
        $('form[data-autosave]').each(function() {
            const form = $(this);
            const key = 'autosave_' + (form.data('autosave-key') || window.location.pathname);
            
            try {
                const savedData = localStorage.getItem(key);
                if (savedData) {
                    App.ui.showAlert(
                        'Dados salvos automaticamente foram encontrados. <a href="#" id="restore-autosave">Restaurar?</a>',
                        'info'
                    );
                    
                    $('#restore-autosave').on('click', function(e) {
                        e.preventDefault();
                        App.utils.populateForm(form, savedData);
                        localStorage.removeItem(key);
                        $(this).closest('.alert').fadeOut();
                    });
                }
            } catch (e) {
                console.warn('Erro ao recuperar rascunho:', e);
            }
        });
    },
    
    // Manipulação de ação de confirmação
    handleConfirmAction: function(e) {
        e.preventDefault();
        const element = $(this);
        const message = element.data('confirm') || 'Tem certeza que deseja realizar esta ação?';
        const title = element.data('confirm-title') || 'Confirmação';
        const action = element.attr('href') || element.data('action');
        
        App.ui.showConfirm(message, title, function() {
            if (action) {
                if (element.is('form') || element.closest('form').length) {
                    element.closest('form').submit();
                } else {
                    window.location.href = action;
                }
            }
        });
    },
    
    // Loading em formulários
    handleFormLoading: function(e) {
        const form = $(this);
        const submitBtn = form.find('button[type="submit"]');
        
        submitBtn.prop('disabled', true);
        submitBtn.html('<i class="fas fa-spinner fa-spin"></i> Processando...');
        
        // Restaurar estado após 10 segundos (fallback)
        setTimeout(() => {
            submitBtn.prop('disabled', false);
            submitBtn.html(submitBtn.data('original-text') || 'Salvar');
        }, 10000);
    }
};

// Utilitários
App.utils = {
    // Validar CPF
    validateCPF: function(cpf) {
        cpf = cpf.replace(/\D/g, '');
        
        if (cpf.length !== 11 || /^(\d)\1+$/.test(cpf)) {
            return false;
        }
        
        let sum = 0;
        for (let i = 0; i < 9; i++) {
            sum += parseInt(cpf.charAt(i)) * (10 - i);
        }
        
        let remainder = 11 - (sum % 11);
        if (remainder === 10 || remainder === 11) remainder = 0;
        if (remainder !== parseInt(cpf.charAt(9))) return false;
        
        sum = 0;
        for (let i = 0; i < 10; i++) {
            sum += parseInt(cpf.charAt(i)) * (11 - i);
        }
        
        remainder = 11 - (sum % 11);
        if (remainder === 10 || remainder === 11) remainder = 0;
        
        return remainder === parseInt(cpf.charAt(10));
    },
    
    // Validar email
    validateEmail: function(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    },
    
    // Formatar dinheiro
    formatMoney: function(value) {
        return parseFloat(value).toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        });
    },
    
    // Converter dinheiro para número
    parseMoney: function(value) {
        return parseFloat(value.replace(/[^\d,]/g, '').replace(',', '.')) || 0;
    },
    
    // Formatar data
    formatDate: function(date, format = 'DD/MM/YYYY') {
        return moment(date).format(format);
    },
    
    // Popular formulário com dados
    populateForm: function(form, data) {
        if (typeof data === 'string') {
            // Se data é uma query string
            const params = new URLSearchParams(data);
            params.forEach((value, key) => {
                form.find(`[name="${key}"]`).val(value);
            });
        } else {
            // Se data é um objeto
            Object.keys(data).forEach(key => {
                form.find(`[name="${key}"]`).val(data[key]);
            });
        }
    },
    
    // Debounce
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Gerar ID único
    generateId: function() {
        return '_' + Math.random().toString(36).substr(2, 9);
    }
};

// Interface do usuário
App.ui = {
    // Mostrar loading
    showLoading: function(message = 'Carregando...') {
        const overlay = $('#loading-overlay');
        if (overlay.length) {
            overlay.find('.loading-spinner div').last().text(message);
            overlay.fadeIn();
        }
    },
    
    // Esconder loading
    hideLoading: function() {
        $('#loading-overlay').fadeOut();
    },
    
    // Mostrar alerta
    showAlert: function(message, type = 'info', dismissible = true) {
        const alertClass = type === 'error' ? 'danger' : type;
        const dismissibleHtml = dismissible ? `
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        ` : '';
        
        const alertHtml = `
            <div class="alert alert-${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                ${dismissibleHtml}
            </div>
        `;
        
        const container = $('.container-fluid').first();
        if (container.length) {
            container.prepend(alertHtml);
            
            // Auto-remove após 5 segundos
            if (dismissible) {
                setTimeout(() => {
                    container.find('.alert').first().fadeOut();
                }, 5000);
            }
        }
    },
    
    // Mostrar confirmação
    showConfirm: function(message, title = 'Confirmação', callback = null) {
        const modal = $('#confirmModal');
        if (modal.length) {
            modal.find('.modal-title').text(title);
            modal.find('.modal-body').html(message);
            
            modal.find('#confirmModalConfirm').off('click').on('click', function() {
                modal.modal('hide');
                if (callback) callback();
            });
            
            modal.modal('show');
        } else {
            // Fallback para confirm nativo
            if (confirm(`${title}\n\n${message}`)) {
                if (callback) callback();
            }
        }
    },
    
    // Mostrar toast (notification temporária)
    showToast: function(message, type = 'info', duration = 3000) {
        const toastId = App.utils.generateId();
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" 
                 style="position: fixed; top: 20px; right: 20px; z-index: 9999;">
                <div class="toast-header bg-${type} text-white">
                    <strong class="mr-auto">Sistema Açougue</strong>
                    <button type="button" class="ml-2 mb-1 close text-white" data-dismiss="toast" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        $('body').append(toastHtml);
        const toast = $(`#${toastId}`);
        
        toast.toast({
            delay: duration
        }).toast('show');
        
        // Remover do DOM após esconder
        toast.on('hidden.bs.toast', function() {
            $(this).remove();
        });
    },
    
    // Atualizar contador de badge
    updateBadge: function(selector, count) {
        const badge = $(selector);
        if (badge.length) {
            if (count > 0) {
                badge.text(count).show();
            } else {
                badge.hide();
            }
        }
    }
};

// API Helper
App.api = {
    // GET request
    get: function(url, data = {}) {
        return $.get(url, data);
    },
    
    // POST request
    post: function(url, data = {}) {
        return $.post(url, data);
    },
    
    // PUT request
    put: function(url, data = {}) {
        return $.ajax({
            url: url,
            type: 'PUT',
            data: data
        });
    },
    
    // DELETE request
    delete: function(url) {
        return $.ajax({
            url: url,
            type: 'DELETE'
        });
    },
    
    // Upload de arquivo
    upload: function(url, formData) {
        return $.ajax({
            url: url,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false
        });
    }
};

// Módulo de Vendas
App.vendas = {
    // Adicionar item à venda
    adicionarItem: function() {
        const template = $('#item-template').html();
        const container = $('#itens-container');
        const index = container.children().length;
        
        const itemHtml = template.replace(/INDEX/g, index);
        container.append(itemHtml);
        
        // Aplicar máscaras aos novos campos
        App.initMasks();
        
        // Focar no campo descrição
        container.find('.item-descricao').last().focus();
        
        // Atualizar numeração
        this.atualizarNumeracao();
    },
    
    // Remover item da venda
    removerItem: function(button) {
        $(button).closest('.item-venda').remove();
        this.atualizarNumeracao();
        this.calcularTotal();
    },
    
    // Atualizar numeração dos itens
    atualizarNumeracao: function() {
        $('#itens-container .item-venda').each(function(index) {
            $(this).find('.item-numero').text(index + 1);
        });
    },
    
    // Calcular total da venda
    calcularTotal: function() {
        let total = 0;
        
        $('#itens-container .item-venda').each(function() {
            const quantidade = App.utils.parseMoney($(this).find('.item-quantidade').val() || '0');
            const valorUnitario = App.utils.parseMoney($(this).find('.item-valor').val() || '0');
            const subtotal = quantidade * valorUnitario;
            
            $(this).find('.item-subtotal').text(App.utils.formatMoney(subtotal));
            total += subtotal;
        });
        
        $('#venda-total').text(App.utils.formatMoney(total));
        $('#venda-total-input').val(total.toFixed(2));
        
        return total;
    }
};

// Inicializar quando documento estiver pronto
$(document).ready(function() {
    App.init();
});

// Exportar para escopo global
window.App = App;