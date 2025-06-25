/* ============================================
   Sistema Crediário Açougue - Vendas JavaScript
   ============================================ */

// Namespace para módulo de vendas
window.Vendas = {
    config: {
        maxItems: 20,
        autoSaveInterval: 30000,
        defaultDueDays: 30
    },
    
    // Estado da venda atual
    state: {
        items: [],
        total: 0,
        clienteId: null,
        clienteInfo: null
    },
    
    // Inicialização do módulo
    init: function() {
        this.bindEvents();
        this.initAutoSave();
        this.loadSavedData();
    },
    
    // Vincular eventos
    bindEvents: function() {
        // Eventos de item
        $(document).on('input', '.item-quantidade, .item-valor', this.onItemChange.bind(this));
        $(document).on('blur', '.item-descricao', this.onItemDescriptionChange.bind(this));
        
        // Eventos de cliente
        $(document).on('change', '#cliente_id', this.onClienteChange.bind(this));
        
        // Eventos de formulário
        $(document).on('submit', '#vendaForm', this.onFormSubmit.bind(this));
        
        // Teclas de atalho
        $(document).on('keydown', this.onKeyDown.bind(this));
    },
    
    // Mudança em item
    onItemChange: function(e) {
        const item = $(e.target).closest('.item-venda');
        this.calcularSubtotalItem(item);
        this.debounce(this.calcularTotal.bind(this), 300)();
        this.updateState();
    },
    
    // Mudança na descrição do item
    onItemDescriptionChange: function(e) {
        const descricao = $(e.target).val().trim();
        if (descricao) {
            this.saveItemSuggestion(descricao);
        }
    },
    
    // Mudança de cliente
    onClienteChange: function(e) {
        const clienteId = $(e.target).val();
        if (clienteId) {
            this.loadClienteInfo(clienteId);
        } else {
            this.clearClienteInfo();
        }
    },
    
    // Submissão do formulário
    onFormSubmit: function(e) {
        if (!this.validateForm()) {
            e.preventDefault();
            return false;
        }
        
        this.clearSavedData();
        return true;
    },
    
    // Teclas de atalho
    onKeyDown: function(e) {
        // Ctrl + I para adicionar item
        if ((e.ctrlKey || e.metaKey) && e.keyCode === 73) {
            e.preventDefault();
            window.adicionarItem();
        }
        
        // Delete para remover item focado
        if (e.keyCode === 46 && $(e.target).closest('.item-venda').length) {
            e.preventDefault();
            const removeBtn = $(e.target).closest('.item-venda').find('button[onclick*="removerItem"]');
            if (removeBtn.length) {
                removeBtn.click();
            }
        }
        
        // Tab para navegar entre campos de item
        if (e.keyCode === 9) {
            this.handleTabNavigation(e);
        }
    },
    
    // Navegação com Tab
    handleTabNavigation: function(e) {
        const current = $(e.target);
        const item = current.closest('.item-venda');
        
        if (!item.length) return;
        
        // Se está no último campo do item, ir para próximo item ou criar novo
        if (current.hasClass('item-valor') && !e.shiftKey) {
            const nextItem = item.next('.item-venda');
            if (nextItem.length) {
                e.preventDefault();
                nextItem.find('.item-descricao').focus();
            } else if (this.shouldCreateNewItem(item)) {
                e.preventDefault();
                window.adicionarItem();
            }
        }
    },
    
    // Verificar se deve criar novo item
    shouldCreateNewItem: function(currentItem) {
        const descricao = currentItem.find('.item-descricao').val().trim();
        const quantidade = currentItem.find('.item-quantidade').val();
        const valor = currentItem.find('.item-valor').val();
        
        return descricao && quantidade && valor && $('.item-venda').length < this.config.maxItems;
    },
    
    // Carregar informações do cliente
    loadClienteInfo: function(clienteId) {
        App.ui.showLoading('Carregando informações do cliente...');
        
        $.get(`/clientes/api/${clienteId}/resumo`)
            .done(data => {
                this.state.clienteId = clienteId;
                this.state.clienteInfo = data;
                this.displayClienteInfo(data);
                this.checkCreditLimit();
            })
            .fail(() => {
                App.ui.showAlert('Erro ao carregar informações do cliente', 'danger');
            })
            .always(() => {
                App.ui.hideLoading();
            });
    },
    
    // Exibir informações do cliente
    displayClienteInfo: function(cliente) {
        $('#cliente-nome').text(cliente.nome);
        $('#cliente-telefone').text(cliente.telefone || '-');
        $('#cliente-limite').text(App.utils.formatMoney(cliente.limite_credito));
        $('#cliente-disponivel').text(App.utils.formatMoney(cliente.credito_disponivel));
        
        $('#cliente-info').slideDown();
        
        // Exibir alertas
        this.displayClienteAlertas(cliente);
    },
    
    // Exibir alertas do cliente
    displayClienteAlertas: function(cliente) {
        const alertDiv = $('#cliente-alerta');
        alertDiv.empty().hide();
        
        const alertas = [];
        
        if (!cliente.ativo) {
            alertas.push({
                type: 'danger',
                icon: 'user-slash',
                message: 'Cliente inativo'
            });
        }
        
        if (cliente.esta_inadimplente) {
            alertas.push({
                type: 'danger',
                icon: 'exclamation-triangle',
                message: 'Cliente inadimplente'
            });
        }
        
        if (cliente.credito_disponivel <= 0) {
            alertas.push({
                type: 'danger',
                icon: 'credit-card',
                message: 'Limite de crédito esgotado'
            });
        } else if (cliente.credito_disponivel < 100) {
            alertas.push({
                type: 'warning',
                icon: 'exclamation-triangle',
                message: 'Crédito baixo'
            });
        }
        
        if (alertas.length > 0) {
            const html = alertas.map(alert => 
                `<div class="alert alert-${alert.type} alert-sm mb-1">
                    <i class="fas fa-${alert.icon}"></i> ${alert.message}
                </div>`
            ).join('');
            
            alertDiv.html(html).slideDown();
        }
    },
    
    // Limpar informações do cliente
    clearClienteInfo: function() {
        this.state.clienteId = null;
        this.state.clienteInfo = null;
        $('#cliente-info').slideUp();
    },
    
    // Calcular subtotal de um item
    calcularSubtotalItem: function(item) {
        const quantidade = App.utils.parseMoney(item.find('.item-quantidade').val() || '0');
        const valorUnitario = App.utils.parseMoney(item.find('.item-valor').val() || '0');
        const subtotal = quantidade * valorUnitario;
        
        item.find('.item-subtotal').text(App.utils.formatMoney(subtotal));
        
        // Feedback visual
        if (subtotal > 0) {
            item.removeClass('border-warning').addClass('border-success');
        } else {
            item.removeClass('border-success');
        }
        
        return subtotal;
    },
    
    // Calcular total da venda
    calcularTotal: function() {
        let total = 0;
        const items = [];
        
        $('.item-venda').each(function() {
            const item = $(this);
            const descricao = item.find('.item-descricao').val().trim();
            const quantidade = App.utils.parseMoney(item.find('.item-quantidade').val() || '0');
            const valorUnitario = App.utils.parseMoney(item.find('.item-valor').val() || '0');
            const subtotal = quantidade * valorUnitario;
            
            if (descricao && quantidade > 0 && valorUnitario > 0) {
                items.push({
                    descricao,
                    quantidade,
                    valorUnitario,
                    subtotal
                });
                
                total += subtotal;
            }
        });
        
        this.state.items = items;
        this.state.total = total;
        
        this.updateTotalDisplay(total);
        this.checkCreditLimit(total);
        
        return total;
    },
    
    // Atualizar exibição do total
    updateTotalDisplay: function(total) {
        const formatted = App.utils.formatMoney(total);
        $('#subtotal-display, #total-display').text(formatted);
        
        // Animação no total
        if (total > 0) {
            $('#total-display').addClass('text-success').removeClass('text-muted');
        } else {
            $('#total-display').addClass('text-muted').removeClass('text-success');
        }
    },
    
    // Verificar limite de crédito
    checkCreditLimit: function(total = null) {
        if (!this.state.clienteId) {
            $('#credit-check').slideUp();
            return;
        }
        
        if (total === null) {
            total = this.state.total;
        }
        
        if (total <= 0) {
            $('#credit-check').slideUp();
            return;
        }
        
        const cliente = this.state.clienteInfo;
        if (!cliente) return;
        
        const checkDiv = $('#credit-check');
        const disponivel = cliente.credito_disponivel;
        
        if (total <= disponivel) {
            checkDiv.removeClass('alert-danger alert-warning')
                   .addClass('alert-success')
                   .html(`<i class="fas fa-check"></i> Dentro do limite (disponível: ${App.utils.formatMoney(disponivel - total)})`)
                   .slideDown();
        } else {
            const excesso = total - disponivel;
            checkDiv.removeClass('alert-success alert-warning')
                   .addClass('alert-danger')
                   .html(`<i class="fas fa-times"></i> Excede em ${App.utils.formatMoney(excesso)} o limite disponível`)
                   .slideDown();
        }
    },
    
    // Validar formulário
    validateForm: function() {
        const errors = [];
        
        // Validar cliente
        if (!this.state.clienteId) {
            errors.push('Selecione um cliente');
        }
        
        // Validar se cliente pode comprar
        if (this.state.clienteInfo && !this.state.clienteInfo.pode_comprar) {
            errors.push('Cliente não pode realizar compras');
        }
        
        // Validar itens
        if (this.state.items.length === 0) {
            errors.push('Adicione pelo menos um item');
        }
        
        // Validar limite de crédito
        if (this.state.clienteInfo && this.state.total > this.state.clienteInfo.credito_disponivel) {
            errors.push('Venda excede o limite de crédito disponível');
        }
        
        // Validar cada item
        $('.item-venda').each(function(index) {
            const item = $(this);
            const descricao = item.find('.item-descricao').val().trim();
            const quantidade = App.utils.parseMoney(item.find('.item-quantidade').val() || '0');
            const valor = App.utils.parseMoney(item.find('.item-valor').val() || '0');
            
            if (descricao && (quantidade <= 0 || valor <= 0)) {
                errors.push(`Item ${index + 1}: Quantidade e valor devem ser maiores que zero`);
            }
        });
        
        // Exibir erros
        if (errors.length > 0) {
            App.ui.showAlert(errors.join('<br>'), 'danger');
            return false;
        }
        
        return true;
    },
    
    // Atualizar estado
    updateState: function() {
        this.calcularTotal();
        this.saveData();
    },
    
    // Auto-save
    initAutoSave: function() {
        setInterval(() => {
            if (this.state.items.length > 0 || this.state.clienteId) {
                this.saveData();
            }
        }, this.config.autoSaveInterval);
    },
    
    // Salvar dados no localStorage
    saveData: function() {
        try {
            const data = {
                clienteId: this.state.clienteId,
                items: this.state.items,
                timestamp: Date.now()
            };
            
            localStorage.setItem('venda_rascunho', JSON.stringify(data));
        } catch (e) {
            console.warn('Erro ao salvar rascunho:', e);
        }
    },
    
    // Carregar dados salvos
    loadSavedData: function() {
        try {
            const saved = localStorage.getItem('venda_rascunho');
            if (saved) {
                const data = JSON.parse(saved);
                
                // Verificar se não é muito antigo (24 horas)
                if (Date.now() - data.timestamp < 24 * 60 * 60 * 1000) {
                    this.showRestoreDialog(data);
                } else {
                    this.clearSavedData();
                }
            }
        } catch (e) {
            console.warn('Erro ao carregar rascunho:', e);
        }
    },
    
    // Mostrar diálogo de restauração
    showRestoreDialog: function(data) {
        const message = `
            Encontramos um rascunho de venda salvo automaticamente.<br>
            <strong>Cliente:</strong> ${data.clienteId || 'Não selecionado'}<br>
            <strong>Itens:</strong> ${data.items.length}<br>
            <strong>Total:</strong> ${App.utils.formatMoney(data.items.reduce((sum, item) => sum + item.subtotal, 0))}<br><br>
            Deseja restaurar este rascunho?
        `;
        
        App.ui.showConfirm(message, 'Restaurar Rascunho', () => {
            this.restoreData(data);
        });
    },
    
    // Restaurar dados
    restoreData: function(data) {
        // Restaurar cliente
        if (data.clienteId) {
            $('#cliente_id').val(data.clienteId).trigger('change');
        }
        
        // Restaurar itens
        data.items.forEach(item => {
            window.adicionarItemRapido(item.descricao, item.quantidade.toString(), item.valorUnitario.toString());
        });
        
        App.ui.showToast('Rascunho restaurado com sucesso', 'success');
        this.clearSavedData();
    },
    
    // Limpar dados salvos
    clearSavedData: function() {
        localStorage.removeItem('venda_rascunho');
    },
    
    // Salvar sugestão de item
    saveItemSuggestion: function(descricao) {
        try {
            let suggestions = JSON.parse(localStorage.getItem('item_suggestions') || '[]');
            
            // Adicionar se não existe
            if (!suggestions.includes(descricao)) {
                suggestions.unshift(descricao);
                suggestions = suggestions.slice(0, 50); // Manter apenas 50
                localStorage.setItem('item_suggestions', JSON.stringify(suggestions));
            }
        } catch (e) {
            console.warn('Erro ao salvar sugestão:', e);
        }
    },
    
    // Obter sugestões de itens
    getItemSuggestions: function() {
        try {
            return JSON.parse(localStorage.getItem('item_suggestions') || '[]');
        } catch (e) {
            return [];
        }
    },
    
    // Debounce utility
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
    }
};

// Funções auxiliares para compatibilidade com templates
window.VendasHelper = {
    // Adicionar autocomplete aos campos de descrição
    initItemAutocomplete: function(input) {
        const suggestions = Vendas.getItemSuggestions();
        if (suggestions.length === 0) return;
        
        $(input).autocomplete({
            source: suggestions,
            minLength: 2,
            select: function(event, ui) {
                $(this).val(ui.item.value);
                $(this).trigger('blur');
            }
        });
    },
    
    // Formatar campo de moeda
    formatCurrencyField: function(input) {
        $(input).on('blur', function() {
            const value = App.utils.parseMoney($(this).val());
            if (value > 0) {
                $(this).val(App.utils.formatMoney(value).replace('R$ ', '').replace('.', ','));
            }
        });
    },
    
    // Validar campo numérico
    validateNumericField: function(input, min = 0) {
        $(input).on('blur', function() {
            const value = App.utils.parseMoney($(this).val());
            if (value <= min) {
                $(this).addClass('is-invalid');
            } else {
                $(this).removeClass('is-invalid');
            }
        });
    }
};

// Inicializar quando documento estiver pronto
$(document).ready(function() {
    if ($('#vendaForm').length) {
        Vendas.init();
    }
});

// Exportar para escopo global
window.Vendas = Vendas;