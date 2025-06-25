"""
Blueprint Vendas - Gestão completa de vendas
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, jsonify, abort, current_app
)
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import joinedload

from app import db
from app.models import Cliente, Venda, ItemVenda, Pagamento
from app.services import venda_service, pagamento_service
from app.utils.helpers import (
    flash_success, flash_error, flash_warning, 
    format_currency, parse_currency, get_page_from_request,
    get_per_page_from_request, build_filters_from_request
)
from app.utils.constants import ITEMS_PER_PAGE, STATUS_VENDA, FORMAS_PAGAMENTO
from app.utils.decorators import log_action, handle_db_errors
from app.views.auth import login_required
from datetime import date, datetime
from decimal import Decimal


vendas_bp = Blueprint('vendas', __name__)


@vendas_bp.route('/')
@login_required
def index():
    """Listagem de vendas com filtros e busca"""
    
    # Parâmetros de busca e filtros
    termo_busca = request.args.get('q', '').strip()
    page = get_page_from_request()
    per_page = get_per_page_from_request()
    
    # Filtros permitidos
    filtros = build_filters_from_request([
        'cliente_id', 'status', 'data_inicio', 'data_fim',
        'valor_min', 'valor_max', 'ordenacao'
    ])
    
    try:
        if termo_busca:
            # Busca por termo
            resultado = venda_service.buscar_vendas(
                termo=termo_busca,
                page=page,
                per_page=per_page
            )
        else:
            # Listagem com filtros
            resultado = venda_service.listar_vendas(
                filtros=filtros,
                page=page,
                per_page=per_page
            )
        
        # Obter cliente selecionado se houver
        cliente_selecionado = None
        if filtros.get('cliente_id'):
            cliente_selecionado = Cliente.query.get(filtros['cliente_id'])
        
        return render_template(
            'vendas/index.html',
            vendas=resultado['vendas'],
            pagination=resultado['pagination'],
            stats=resultado['stats'],
            termo_busca=termo_busca,
            filtros=filtros,
            cliente_selecionado=cliente_selecionado
        )
        
    except Exception as e:
        flash_error(f'Erro ao carregar vendas: {str(e)}')
        return render_template(
            'vendas/index.html',
            vendas=[],
            pagination=None,
            stats={},
            termo_busca='',
            filtros={},
            cliente_selecionado=None
        )


@vendas_bp.route('/nova', methods=['GET', 'POST'])
@login_required
@log_action('create', 'Criação de nova venda')
@handle_db_errors
def create():
    """Criar nova venda"""
    
    if request.method == 'POST':
        try:
            # Dados do formulário
            cliente_id = request.form.get('cliente_id', type=int)
            observacoes = request.form.get('observacoes', '').strip()
            
            # Validações básicas
            if not cliente_id:
                flash_error('Cliente é obrigatório.')
                return render_template('vendas/nova.html')
            
            # Processar itens da venda
            itens = []
            item_index = 0
            
            while True:
                descricao = request.form.get(f'itens[{item_index}][descricao]')
                if not descricao:
                    break
                
                quantidade_str = request.form.get(f'itens[{item_index}][quantidade]', '0')
                valor_unitario_str = request.form.get(f'itens[{item_index}][valor_unitario]', '0')
                
                try:
                    quantidade = float(quantidade_str.replace(',', '.'))
                    valor_unitario = parse_currency(valor_unitario_str)
                    
                    if quantidade > 0 and valor_unitario > 0:
                        itens.append({
                            'descricao': descricao.strip(),
                            'quantidade': quantidade,
                            'valor_unitario': float(valor_unitario)
                        })
                except (ValueError, TypeError):
                    flash_error(f'Valores inválidos no item {item_index + 1}.')
                    return render_template('vendas/nova.html')
                
                item_index += 1
            
            if not itens:
                flash_error('Adicione pelo menos um item à venda.')
                return render_template('vendas/nova.html')
            
            # Criar venda usando service
            sucesso, mensagem, venda = venda_service.criar_venda(
                cliente_id=cliente_id,
                itens=itens,
                observacoes=observacoes if observacoes else None
            )
            
            if sucesso:
                flash_success(mensagem)
                return redirect(url_for('vendas.view', id=venda.id))
            else:
                flash_error(mensagem)
                return render_template('vendas/nova.html')
                
        except Exception as e:
            flash_error(f'Erro ao criar venda: {str(e)}')
            return render_template('vendas/nova.html')
    
    # GET - Exibir formulário
    return render_template('vendas/nova.html')


@vendas_bp.route('/<int:id>')
@login_required
def view(id):
    """Visualizar detalhes da venda"""
    
    venda = venda_service.obter_venda(id, incluir_relacionamentos=True)
    
    if not venda:
        flash_error('Venda não encontrada.')
        return redirect(url_for('vendas.index'))
    
    return render_template('vendas/detalhes.html', venda=venda)


@vendas_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@log_action('update', 'Edição de venda')
@handle_db_errors
def edit(id):
    """Editar venda existente"""
    
    venda = venda_service.obter_venda(id)
    
    if not venda:
        flash_error('Venda não encontrada.')
        return redirect(url_for('vendas.index'))
    
    # Verificar se pode editar
    if venda.status != STATUS_VENDA['ABERTA']:
        flash_error('Apenas vendas em aberto podem ser editadas.')
        return redirect(url_for('vendas.view', id=id))
    
    if venda.eh_restante:
        flash_error('Vendas de restante não podem ser editadas.')
        return redirect(url_for('vendas.view', id=id))
    
    if request.method == 'POST':
        try:
            # Dados do formulário
            dados = {
                'observacoes': request.form.get('observacoes', '').strip()
            }
            
            # Data de vencimento (se fornecida)
            data_vencimento = request.form.get('data_vencimento')
            if data_vencimento:
                dados['data_vencimento'] = data_vencimento
            
            # Processar itens se fornecidos
            if request.form.get('atualizar_itens') == 'true':
                itens = []
                item_index = 0
                
                while True:
                    descricao = request.form.get(f'itens[{item_index}][descricao]')
                    if not descricao:
                        break
                    
                    quantidade_str = request.form.get(f'itens[{item_index}][quantidade]', '0')
                    valor_unitario_str = request.form.get(f'itens[{item_index}][valor_unitario]', '0')
                    
                    try:
                        quantidade = float(quantidade_str.replace(',', '.'))
                        valor_unitario = parse_currency(valor_unitario_str)
                        
                        if quantidade > 0 and valor_unitario > 0:
                            itens.append({
                                'descricao': descricao.strip(),
                                'quantidade': quantidade,
                                'valor_unitario': float(valor_unitario)
                            })
                    except (ValueError, TypeError):
                        flash_error(f'Valores inválidos no item {item_index + 1}.')
                        return render_template('vendas/form.html', venda=venda)
                    
                    item_index += 1
                
                if itens:
                    dados['itens'] = itens
            
            # Atualizar venda usando service
            sucesso, mensagem, venda_atualizada = venda_service.atualizar_venda(
                venda_id=id,
                dados=dados
            )
            
            if sucesso:
                flash_success(mensagem)
                return redirect(url_for('vendas.view', id=id))
            else:
                flash_error(mensagem)
                return render_template('vendas/form.html', venda=venda)
                
        except Exception as e:
            flash_error(f'Erro ao atualizar venda: {str(e)}')
            return render_template('vendas/form.html', venda=venda)
    
    # GET - Exibir formulário de edição
    return render_template('vendas/form.html', venda=venda)


@vendas_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
@log_action('delete', 'Exclusão de venda')
@handle_db_errors
def delete(id):
    """Excluir venda"""
    
    sucesso, mensagem = venda_service.excluir_venda(id)
    
    if sucesso:
        flash_success(mensagem)
    else:
        flash_error(mensagem)
    
    return redirect(url_for('vendas.index'))


@vendas_bp.route('/<int:id>/pagar', methods=['GET', 'POST'])
@login_required
@log_action('payment', 'Registro de pagamento')
@handle_db_errors
def payment(id):
    """Registrar pagamento para venda"""
    
    venda = venda_service.obter_venda(id, incluir_relacionamentos=True)
    
    if not venda:
        flash_error('Venda não encontrada.')
        return redirect(url_for('vendas.index'))
    
    # Verificar se venda pode receber pagamento
    if venda.status == STATUS_VENDA['PAGA']:
        flash_warning('Esta venda já foi paga.')
        return redirect(url_for('vendas.view', id=id))
    
    if request.method == 'POST':
        try:
            # Dados do pagamento
            valor_str = request.form.get('valor', '0')
            forma_pagamento = request.form.get('forma_pagamento', FORMAS_PAGAMENTO['DINHEIRO'])
            valor_recebido_str = request.form.get('valor_recebido', '')
            observacoes = request.form.get('observacoes', '').strip()
            imprimir_comprovante = request.form.get('imprimir_comprovante') == 'on'
            
            # Validar valor
            try:
                valor = parse_currency(valor_str)
                if valor <= 0:
                    flash_error('Valor do pagamento deve ser maior que zero.')
                    return render_template('vendas/pagamento.html', venda=venda)
            except (ValueError, TypeError):
                flash_error('Valor do pagamento inválido.')
                return render_template('vendas/pagamento.html', venda=venda)
            
            # Preparar dados do pagamento
            dados_pagamento = {
                'valor': float(valor),
                'forma_pagamento': forma_pagamento,
                'observacoes': observacoes if observacoes else None
            }
            
            # Valor recebido (para dinheiro)
            if forma_pagamento == FORMAS_PAGAMENTO['DINHEIRO'] and valor_recebido_str:
                try:
                    valor_recebido = parse_currency(valor_recebido_str)
                    dados_pagamento['valor_recebido'] = float(valor_recebido)
                except (ValueError, TypeError):
                    flash_error('Valor recebido inválido.')
                    return render_template('vendas/pagamento.html', venda=venda)
            
            # Registrar pagamento usando service
            sucesso, mensagem, pagamento = pagamento_service.registrar_pagamento_simples(
                venda_id=id,
                dados_pagamento=dados_pagamento
            )
            
            if sucesso:
                flash_success(mensagem)
                
                # Imprimir comprovante se solicitado
                if imprimir_comprovante and pagamento:
                    try:
                        from app.services.impressora_service import ImpressoraService
                        impressora_service = ImpressoraService()
                        
                        # Gerar dados do comprovante
                        dados_comprovante = pagamento_service.gerar_dados_comprovante(
                            pagamento.id, 'individual'
                        )
                        
                        if dados_comprovante:
                            impressora_service.imprimir_comprovante(dados_comprovante)
                            flash_success('Comprovante impresso com sucesso!')
                        else:
                            flash_warning('Erro ao gerar dados do comprovante.')
                            
                    except Exception as e:
                        flash_warning(f'Erro ao imprimir comprovante: {str(e)}')
                
                return redirect(url_for('vendas.view', id=id))
            else:
                flash_error(mensagem)
                return render_template('vendas/pagamento.html', venda=venda)
                
        except Exception as e:
            flash_error(f'Erro ao registrar pagamento: {str(e)}')
            return render_template('vendas/pagamento.html', venda=venda)
    
    # GET - Exibir formulário de pagamento
    return render_template('vendas/pagamento.html', venda=venda)


@vendas_bp.route('/pagamento-multiplo', methods=['GET', 'POST'])
@login_required
@log_action('multiple_payment', 'Pagamento múltiplo')
@handle_db_errors
def multiple_payment():
    """Pagamento de múltiplas vendas"""
    
    if request.method == 'POST':
        try:
            # Dados do formulário
            cliente_id = request.form.get('cliente_id', type=int)
            valor_pago_str = request.form.get('valor_pago', '0')
            forma_pagamento = request.form.get('forma_pagamento', FORMAS_PAGAMENTO['DINHEIRO'])
            valor_recebido_str = request.form.get('valor_recebido', '')
            observacoes = request.form.get('observacoes', '').strip()
            imprimir_comprovante = request.form.get('imprimir_comprovante') == 'on'
            
            # Validações básicas
            if not cliente_id:
                flash_error('Cliente é obrigatório.')
                return render_template('vendas/pagamento_multiplo.html')
            
            try:
                valor_pago = parse_currency(valor_pago_str)
                if valor_pago <= 0:
                    flash_error('Valor pago deve ser maior que zero.')
                    return render_template('vendas/pagamento_multiplo.html')
            except (ValueError, TypeError):
                flash_error('Valor pago inválido.')
                return render_template('vendas/pagamento_multiplo.html')
            
            # Processar vendas selecionadas
            vendas_selecionadas = []
            venda_index = 0
            
            while True:
                venda_id = request.form.get(f'vendas[{venda_index}][venda_id]', type=int)
                if not venda_id:
                    break
                
                valor_venda_str = request.form.get(f'vendas[{venda_index}][valor_pago]', '0')
                selecionada = request.form.get(f'vendas[{venda_index}][selecionada]') == 'on'
                
                if selecionada:
                    try:
                        valor_venda = parse_currency(valor_venda_str)
                        if valor_venda > 0:
                            vendas_selecionadas.append({
                                'venda_id': venda_id,
                                'valor_pago': float(valor_venda)
                            })
                    except (ValueError, TypeError):
                        flash_error(f'Valor inválido para venda #{venda_id}.')
                        return render_template('vendas/pagamento_multiplo.html')
                
                venda_index += 1
            
            if not vendas_selecionadas:
                flash_error('Selecione pelo menos uma venda.')
                return render_template('vendas/pagamento_multiplo.html')
            
            # Valor recebido (para dinheiro)
            valor_recebido = None
            if forma_pagamento == FORMAS_PAGAMENTO['DINHEIRO'] and valor_recebido_str:
                try:
                    valor_recebido = float(parse_currency(valor_recebido_str))
                except (ValueError, TypeError):
                    flash_error('Valor recebido inválido.')
                    return render_template('vendas/pagamento_multiplo.html')
            
            # Processar pagamento múltiplo usando service
            sucesso, mensagem, pagamento_multiplo = pagamento_service.processar_pagamento_multiplo(
                cliente_id=cliente_id,
                vendas_selecionadas=vendas_selecionadas,
                valor_pago=float(valor_pago),
                forma_pagamento=forma_pagamento,
                valor_recebido=valor_recebido,
                observacoes=observacoes if observacoes else None
            )
            
            if sucesso:
                flash_success(mensagem)
                
                # Imprimir comprovante se solicitado
                if imprimir_comprovante and pagamento_multiplo:
                    try:
                        from app.services.impressora_service import ImpressoraService
                        impressora_service = ImpressoraService()
                        
                        # Gerar dados do comprovante
                        dados_comprovante = pagamento_service.gerar_dados_comprovante(
                            pagamento_multiplo.id, 'multiplo'
                        )
                        
                        if dados_comprovante:
                            impressora_service.imprimir_comprovante(dados_comprovante)
                            flash_success('Comprovante impresso com sucesso!')
                        else:
                            flash_warning('Erro ao gerar dados do comprovante.')
                            
                    except Exception as e:
                        flash_warning(f'Erro ao imprimir comprovante: {str(e)}')
                
                return redirect(url_for('vendas.index', cliente_id=cliente_id))
            else:
                flash_error(mensagem)
                return render_template('vendas/pagamento_multiplo.html')
                
        except Exception as e:
            flash_error(f'Erro ao processar pagamento múltiplo: {str(e)}')
            return render_template('vendas/pagamento_multiplo.html')
    
    # GET - Exibir formulário
    return render_template('vendas/pagamento_multiplo.html')


# APIs AJAX

@vendas_bp.route('/api/calcular-total', methods=['POST'])
@login_required
def api_calcular_total():
    """API para calcular total da venda (AJAX)"""
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não fornecidos'
            }), 400
        
        itens = data.get('itens', [])
        resultado = venda_service.calcular_totais_itens(itens)
        
        return jsonify({
            'success': True,
            'data': resultado
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@vendas_bp.route('/api/verificar-limite/<int:cliente_id>/<valor>')
@login_required
def api_verificar_limite(cliente_id, valor):
    """API para verificar limite de crédito"""
    
    try:
        valor_float = float(valor.replace(',', '.'))
        pode_comprar, mensagem, dados_cliente = venda_service.verificar_limite_cliente(
            cliente_id, valor_float
        )
        
        return jsonify({
            'success': True,
            'pode_comprar': pode_comprar,
            'mensagem': mensagem,
            'cliente': dados_cliente
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@vendas_bp.route('/api/vendas-cliente/<int:cliente_id>')
@login_required
def api_vendas_cliente(cliente_id):
    """API para obter vendas em aberto de um cliente"""
    
    try:
        vendas = pagamento_service.obter_vendas_em_aberto_cliente(cliente_id)
        
        return jsonify({
            'success': True,
            'vendas': vendas
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@vendas_bp.route('/api/calcular-troco', methods=['POST'])
@login_required
def api_calcular_troco():
    """API para calcular troco"""
    
    try:
        data = request.get_json()
        valor_recebido = float(data.get('valor_recebido', 0))
        valor_total = float(data.get('valor_total', 0))
        
        valido, mensagem, troco = pagamento_service.calcular_troco(valor_recebido, valor_total)
        
        return jsonify({
            'success': valido,
            'mensagem': mensagem,
            'troco': troco,
            'troco_formatado': format_currency(troco)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Context processor para dados do módulo
@vendas_bp.app_context_processor
def inject_vendas_data():
    """Injetar dados do módulo vendas nos templates"""
    return {
        'status_vendas': [
            ('todas', 'Todas'),
            ('abertas', 'Em Aberto'),
            ('pagas', 'Pagas'),
            ('vencidas', 'Vencidas'),
            ('restantes', 'Restantes')
        ],
        'ordenacao_vendas': [
            ('data_desc', 'Data (Recente)'),
            ('data_asc', 'Data (Antiga)'),
            ('valor_desc', 'Maior Valor'),
            ('valor_asc', 'Menor Valor'),
            ('cliente', 'Cliente'),
            ('vencimento', 'Vencimento')
        ],
        'formas_pagamento': [
            (FORMAS_PAGAMENTO['DINHEIRO'], 'Dinheiro'),
            (FORMAS_PAGAMENTO['CARTAO'], 'Cartão'),
            (FORMAS_PAGAMENTO['PIX'], 'PIX')
        ]
    }


# Template filters
@vendas_bp.app_template_filter('status_badge_class')
def status_badge_class_filter(status):
    """Filter para classe CSS do badge de status"""
    classes = {
        STATUS_VENDA['ABERTA']: 'badge-warning',
        STATUS_VENDA['PAGA']: 'badge-success',
    }
    return classes.get(status, 'badge-secondary')


@vendas_bp.app_template_filter('currency')
def currency_filter(value):
    """Filter para formatação de moeda"""
    return format_currency(value)


# Error handlers específicos do módulo
@vendas_bp.errorhandler(404)
def venda_not_found(error):
    """Handler para venda não encontrada"""
    flash_error('Venda não encontrada.')
    return redirect(url_for('vendas.index'))


@vendas_bp.errorhandler(403)
def venda_forbidden(error):
    """Handler para acesso negado à venda"""
    flash_error('Acesso negado a esta venda.')
    return redirect(url_for('vendas.index'))