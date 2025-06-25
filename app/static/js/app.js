/**
 * Sistema Crediário Açougue - JavaScript Global
 * Funcionalidades globais da aplicação
 */

// Namespace global da aplicação
window.App = window.App || {};

// Configurações globais
App.config = {
    baseUrl: window.appConfig?.baseUrl || '/',
    staticUrl: window.appConfig?.staticUrl || '/static/',
    csrfToken: window.appConfig?.csrfToken || '',
    currentUser: window.appConfig?.currentUser || '',
    debug: window.appConfig?.debug || false,
    locale: 'pt-BR',
    currency: 'BRL',
    
    // Configurações de UI
    fadeSpeed: 300,
    loadingDelay: 100,
    toastTimeout: 5000,
    sessionCheckInterval: 300000, // 5 minutos
    
    // Configurações de validação
    maxFileSize: 16 * 1024 * 1024, // 16MB
    allowedFileTypes: ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'],
    
    // URLs da API
    endpoints: {
        checkSession: '/auth/check-session',
        extendSession: '/auth/extend-session',
        alerts: '/api/alerts',
        clientesBuscar: '/api/clientes/buscar'
    }
};

// Utilitários globais
App.utils = {
    
    /**
     * Formatar valor como moeda brasileira
     */
    formatMoney: function(value, includeSymbol = true) {
        if (value === null || value === undefined || isNaN(value)) {
            return includeSymbol ? 'R$ 0,00' : '0,00';
        }
        
        const formatter = new Intl.NumberFormat('pt-BR', {
            style: includeSymbol ? 'currency' : 'decimal',
            currency: 'BRL',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        
        return formatter.format(value);
    },
    
    /**
     * Converter string de moeda para número
     */
    parseMoney: function(value) {
        if (typeof value === 'number') {
            return value;
        }
        
        if (!value || typeof value !== 'string') {
            return 0;
        }
        
        // Remover símbolos e converter vírgula para ponto
        const cleanValue = value
            .replace(/[R$\s]/g, '')
            .replace(/\./g, '')
            .replace(',', '.');
        
        const parsed = parseFloat(cleanValue);
        return isNaN(parsed) ? 0 : parsed;
    },
    
    /**
     * Formatar CPF
     */
    formatCPF: function(value) {
        if (!value) return '';
        
        const cpf = value.replace(/\D/g, '');
        if (cpf.length <= 11) {
            return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        }
        return value;
    },
    
    /**
     * Formatar telefone
     */
    formatPhone: function(value) {
        if (!value) return '';
        
        const phone = value.replace(/\D/g, '');
        if (phone.length === 11) {
            return phone.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
        } else if (phone.length === 10) {
            return phone.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
        }
        return value;
    },
    
    /**
     * Validar CPF
     */
    validateCPF: function(cpf) {
        if (!cpf) return false;
        
        const cleanCPF = cpf.replace(/\D/g, '');
        
        if (cleanCPF.length !== 11) return false;
        if (/^(\d)\1{10}$/.test(cleanCPF)) return false;
        
        let sum = 0;
        for (let i = 0; i < 9; i++) {
            sum += parseInt(cleanCPF.charAt(i)) * (10 - i);
        }
        
        let remainder = 11 - (sum % 11);
        if (remainder === 10 || remainder === 11) remainder = 0;
        if (remainder !== parseInt(cleanCPF.charAt(9))) return false;
        
        sum = 0;
        for (let i = 0; i < 10; i++) {
            sum += parseInt(cleanCPF.charAt(i)) * (11 - i);
        }
        
        remainder = 11 - (sum % 11);
        if (remainder === 10 || remainder === 11) remainder = 0;
        if (remainder !== parseInt(cleanCPF.charAt(10))) return false;
        
        return true;
    },
    
    /**
     * Validar email
     */
    validateEmail: function(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },
    
    /**
     * Gerar slug a partir de string
     */
    slugify: function(text) {
        return text
            .toString()
            .toLowerCase()
            .trim()
            .replace(/\s+/g, '-')
            .replace(/[^\w\-]+/g, '')
            .replace(/\-\-+/g, '-')
            .replace(/^-+/, '')
            .replace(/-+$/, '');
    },
    
    /**
     * Escapar HTML
     */
    escapeHtml: function(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    },
    
    /**
     * Truncar texto
     */
    truncate: function(text, length = 50, suffix = '...') {
        if (!text || text.length <= length) {
            return text;
        }
        return text.substring(0, length - suffix.length) + suffix;
    },
    
    /**
     * Debounce função
     */
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
    
    /**
     * Throttle função
     */
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Componentes de UI
App.ui = {
    
    /**
     * Mostrar loading overlay
     */
    showLoading: function(message = 'Carregando...') {
        const overlay = $('#loading-overlay');
        overlay.find('p').text(message);
        overlay.fadeIn(App.config.fadeSpeed);
    },
    
    /**
     * Ocultar loading overlay
     */
    hideLoading: function() {
        $('#loading-overlay').fadeOut(App.config.fadeSpeed);
    },
    
    /**
     * Mostrar toast/notificação
     */
    showToast: function(message, type = 'info', timeout = null) {
        const alertClass = type === 'error' ? 'danger' : type;
        const iconClass = {
            'success': 'fa-check-circle',
            'danger': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation-circle',
            'info': 'fa-info-circle'
        }[alertClass] || 'fa-info-circle';
        
        const toast = $(`
            <div class="alert alert-${alertClass} alert-dismissible fade show toast-notification" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                <i class="fas ${iconClass} mr-2"></i>
                ${App.utils.escapeHtml(message)}
                <button type="button" class="close" data-dismiss="alert">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
        `);
        
        $('body').append(toast);
        
        // Auto remove
        setTimeout(() => {
            toast.fadeOut(App.config.fadeSpeed, () => toast.remove());
        }, timeout || App.config.toastTimeout);
    },
    
    /**
     * Mostrar modal de confirmação
     */
    showConfirm: function(options) {
        const defaults = {
            title: 'Confirmação',
            message: 'Tem certeza que deseja realizar esta ação?',
            confirmText: 'Confirmar',
            cancelText: 'Cancelar',
            confirmClass: 'btn-danger',
            onConfirm: null,
            onCancel: null
        };
        
        const settings = $.extend({}, defaults, options);
        
        const modal = $('#confirmModal');
        modal.find('.modal-title').text(settings.title);
        modal.find('#confirmModalMessage').html(settings.message);
        modal.find('#confirmModalButton')
            .text(settings.confirmText)
            .removeClass()
            .addClass(`btn ${settings.confirmClass}`);
        
        // Limpar eventos anteriores
        modal.find('#confirmModalButton').off('click');
        
        // Configurar eventos
        modal.find('#confirmModalButton').on('click', function() {
            modal.modal('hide');
            if (settings.onConfirm && typeof settings.onConfirm === 'function') {
                settings.onConfirm();
            }
        });
        
        modal.off('hidden.bs.modal').on('hidden.bs.modal', function() {
            if (settings.onCancel && typeof settings.onCancel === 'function') {
                settings.onCancel();
            }
        });
        
        modal.modal('show');
    },
    
    /**
     * Animar contadores
     */
    animateCounter: function(element, target, duration = 1000) {
        const $element = $(element);
        const start = parseInt($element.text()) || 0;
        const increment = (target - start) / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
                current = target;
                clearInterval(timer);
            }
            $element.text(Math.round(current));
        }, 16);
    },
    
    /**
     * Aplicar máscaras em campos
     */
    applyMasks: function(context = document) {
        // Máscara de moeda
        $(context).find('.money-mask').each(function() {
            $(this).on('input', function() {
                let value = $(this).val().replace(/\D/g, '');
                value = (parseInt(value) / 100).toFixed(2);
                value = App.utils.formatMoney(parseFloat(value), false);
                $(this).val(value);
            });
        });
        
        // Máscara de CPF
        $(context).find('.cpf-mask').on('input', function() {
            $(this).val(App.utils.formatCPF($(this).val()));
        });
        
        // Máscara de telefone
        $(context).find('.phone-mask').on('input', function() {
            $(this).val(App.utils.formatPhone($(this).val()));
        });
        
        // Máscara de CEP
        $(context).find('.cep-mask').on('input', function() {
            let value = $(this).val().replace(/\D/g, '');
            if (value.length <= 8) {
                value = value.replace(/(\d{5})(\d{1,3})/, '$1-$2');
            }
            $(this).val(value);
        });
    },
    
    /**
     * Configurar datepickers
     */
    setupDatepickers: function(context = document) {
        // Configurar campos de data
        $(context).find('input[type="date"]').each(function() {
            if (!$(this).attr('max')) {
                $(this).attr('max', new Date().toISOString().split('T')[0]);
            }
        });
    },
    
    /**
     * Configurar validação de formulários
     */
    setupFormValidation: function(form) {
        $(form).on('submit', function(e) {
            const $form = $(this);
            let isValid = true;
            
            // Reset validation
            $form.find('.is-invalid').removeClass('is-invalid');
            
            // Validar campos obrigatórios
            $form.find('[required]').each(function() {
                const $field = $(this);
                const value = $field.val().trim();
                
                if (!value) {
                    $field.addClass('is-invalid');
                    isValid = false;
                }
            });
            
            // Validar CPF
            $form.find('.cpf-validate').each(function() {
                const $field = $(this);
                const value = $field.val().trim();
                
                if (value && !App.utils.validateCPF(value)) {
                    $field.addClass('is-invalid');
                    isValid = false;
                }
            });
            
            // Validar email
            $form.find('input[type="email"]').each(function() {
                const $field = $(this);
                const value = $field.val().trim();
                
                if (value && !App.utils.validateEmail(value)) {
                    $field.addClass('is-invalid');
                    isValid = false;
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                App.ui.showToast('Por favor, corrija os campos destacados', 'error');
                
                // Focar no primeiro campo inválido
                $form.find('.is-invalid').first().focus();
            }
        });
    }
};

// AJAX helpers
App.ajax = {
    
    /**
     * Configurações padrão para AJAX
     */
    defaults: {
        timeout: 30000,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    },
    
    /**
     * GET request
     */
    get: function(url, data = {}, options = {}) {
        return this.request('GET', url, data, options);
    },
    
    /**
     * POST request
     */
    post: function(url, data = {}, options = {}) {
        return this.request('POST', url, data, options);
    },
    
    /**
     * PUT request
     */
    put: function(url, data = {}, options = {}) {
        return this.request('PUT', url, data, options);
    },
    
    /**
     * DELETE request
     */
    delete: function(url, options = {}) {
        return this.request('DELETE', url, {}, options);
    },
    
    /**
     * Request genérico
     */
    request: function(method, url, data, options = {}) {
        const settings = $.extend({}, this.defaults, options, {
            method: method,
            url: url,
            data: method === 'GET' ? data : JSON.stringify(data),
            contentType: method === 'GET' ? undefined : 'application/json',
            dataType: 'json'
        });
        
        // Adicionar CSRF token
        if (App.config.csrfToken && ['POST', 'PUT', 'DELETE'].includes(method)) {
            settings.headers['X-CSRFToken'] = App.config.csrfToken;
        }
        
        return $.ajax(settings)
            .fail(function(xhr, status, error) {
                if (xhr.status === 401) {
                    App.session.handleExpired();
                } else if (xhr.status >= 500) {
                    App.ui.showToast('Erro interno do servidor', 'error');
                } else if (xhr.responseJSON && xhr.responseJSON.error) {
                    App.ui.showToast(xhr.responseJSON.error, 'error');
                } else {
                    App.ui.showToast('Erro na comunicação com o servidor', 'error');
                }
            });
    }
};

// Gerenciamento de sessão
App.session = {
    
    checkInterval: null,
    
    /**
     * Iniciar verificação de sessão
     */
    startChecking: function() {
        this.checkInterval = setInterval(() => {
            this.checkStatus();
        }, App.config.sessionCheckInterval);
    },
    
    /**
     * Parar verificação de sessão
     */
    stopChecking: function() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    },
    
    /**
     * Verificar status da sessão
     */
    checkStatus: function() {
        App.ajax.get(App.config.endpoints.checkSession)
            .done((response) => {
                if (!response.logged_in) {
                    this.handleExpired();
                }
            })
            .fail(() => {
                // Silenciosamente ignorar erros de verificação de sessão
            });
    },
    
    /**
     * Estender sessão
     */
    extend: function() {
        return App.ajax.post(App.config.endpoints.extendSession);
    },
    
    /**
     * Lidar com sessão expirada
     */
    handleExpired: function() {
        this.stopChecking();
        
        App.ui.showConfirm({
            title: 'Sessão Expirada',
            message: 'Sua sessão expirou. Você será redirecionado para a página de login.',
            confirmText: 'OK',
            cancelText: '',
            onConfirm: () => {
                window.location.href = '/auth/login';
            }
        });
    }
};

// Autocomplete helper
App.autocomplete = {
    
    /**
     * Configurar autocomplete de clientes
     */
    setupClienteAutocomplete: function(selector, options = {}) {
        const defaults = {
            minLength: 2,
            delay: 300,
            onSelect: null,
            placeholder: 'Digite o nome do cliente...',
            showId: false
        };
        
        const settings = $.extend({}, defaults, options);
        
        $(selector).each(function() {
            const $input = $(this);
            let currentRequest = null;
            
            $input.attr('placeholder', settings.placeholder);
            
            $input.on('input', App.utils.debounce(function() {
                const query = $(this).val().trim();
                
                if (query.length < settings.minLength) {
                    $input.removeData('selected-client');
                    return;
                }
                
                // Cancelar request anterior
                if (currentRequest) {
                    currentRequest.abort();
                }
                
                currentRequest = App.ajax.get(App.config.endpoints.clientesBuscar, {
                    q: query,
                    limit: 10
                }).done((response) => {
                    if (response.success && response.clientes) {
                        App.autocomplete.showSuggestions($input, response.clientes, settings);
                    }
                }).always(() => {
                    currentRequest = null;
                });
                
            }, settings.delay));
            
            // Limpar dados quando campo for limpo
            $input.on('blur', function() {
                setTimeout(() => {
                    const suggestions = $input.siblings('.autocomplete-suggestions');
                    if (!suggestions.is(':hover')) {
                        suggestions.hide();
                    }
                }, 200);
            });
        });
    },
    
    /**
     * Mostrar sugestões de autocomplete
     */
    showSuggestions: function($input, clientes, settings) {
        let $suggestions = $input.siblings('.autocomplete-suggestions');
        
        if ($suggestions.length === 0) {
            $suggestions = $('<div class="autocomplete-suggestions list-group" style="position: absolute; z-index: 1000; width: 100%; max-height: 300px; overflow-y: auto;"></div>');
            $input.after($suggestions);
        }
        
        $suggestions.empty();
        
        if (clientes.length === 0) {
            $suggestions.append('<div class="list-group-item text-muted">Nenhum cliente encontrado</div>');
        } else {
            clientes.forEach(cliente => {
                const displayText = settings.showId ? 
                    `#${cliente.id} - ${cliente.nome}` : 
                    cliente.nome;
                
                const telefoneText = cliente.telefone ? ` - ${cliente.telefone}` : '';
                
                const $item = $(`
                    <a href="#" class="list-group-item list-group-item-action">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${App.utils.escapeHtml(displayText)}</h6>
                            <small class="text-muted">${App.utils.escapeHtml(telefoneText)}</small>
                        </div>
                    </a>
                `);
                
                $item.on('click', function(e) {
                    e.preventDefault();
                    $input.val(cliente.nome);
                    $input.data('selected-client', cliente);
                    $suggestions.hide();
                    
                    if (settings.onSelect && typeof settings.onSelect === 'function') {
                        settings.onSelect(cliente);
                    }
                });
                
                $suggestions.append($item);
            });
        }
        
        $suggestions.show();
    }
};

// Inicialização quando documento estiver pronto
$(document).ready(function() {
    
    // Configurar CSRF token para AJAX
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", App.config.csrfToken);
            }
        }
    });
    
    // Aplicar máscaras
    App.ui.applyMasks();
    
    // Configurar datepickers
    App.ui.setupDatepickers();
    
    // Configurar validação de formulários
    $('form').each(function() {
        App.ui.setupFormValidation(this);
    });
    
    // Iniciar verificação de sessão se usuário estiver logado
    if (App.config.currentUser) {
        App.session.startChecking();
    }
    
    // Configurar tooltips do Bootstrap
    $('[data-toggle="tooltip"]').tooltip();
    
    // Configurar popovers do Bootstrap
    $('[data-toggle="popover"]').popover();
    
    // Auto-dismiss de alertas
    $('.alert[data-auto-dismiss]').each(function() {
        const timeout = $(this).data('auto-dismiss') || 5000;
        setTimeout(() => {
            $(this).fadeOut();
        }, timeout);
    });
    
    // Scroll to top button
    $(window).scroll(function() {
        if ($(this).scrollTop() > 100) {
            $('.scroll-to-top').fadeIn();
        } else {
            $('.scroll-to-top').fadeOut();
        }
    });
    
    $('.scroll-to-top').click(function() {
        $('html, body').animate({scrollTop: 0}, 600);
        return false;
    });
    
    // Loading em formulários
    $('form').on('submit', function() {
        const $form = $(this);
        const $submitBtn = $form.find('button[type="submit"]');
        
        if (!$form.hasClass('no-loading')) {
            $submitBtn.prop('disabled', true);
            $submitBtn.html('<i class="fas fa-spinner fa-spin"></i> Processando...');
        }
    });
    
    // Confirmar ações de exclusão
    $('[data-confirm-delete]').on('click', function(e) {
        e.preventDefault();
        
        const $this = $(this);
        const message = $this.data('confirm-delete') || 'Tem certeza que deseja excluir este item?';
        const action = $this.attr('href') || $this.data('url');
        
        App.ui.showConfirm({
            title: 'Confirmar Exclusão',
            message: message,
            confirmText: 'Excluir',
            confirmClass: 'btn-danger',
            onConfirm: () => {
                if ($this.is('a')) {
                    window.location.href = action;
                } else if ($this.data('form')) {
                    $($this.data('form')).submit();
                }
            }
        });
    });
    
    console.log('Sistema Crediário Açougue - JavaScript carregado');
});