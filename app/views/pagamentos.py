"""
Blueprint Pagamentos - Gestão de pagamentos e pagamentos múltiplos
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func, and_
from app import db
from app.models import Cliente, Venda, Pagamento, PagamentoMultiplo, PagamentoMultiploDetalhe, ItemVenda
from app.utils.helpers import (
    flash_success, flash_error, flash_warning, 
    format_currency, parse_currency, paginate_query
)
from app.utils.constants import ITEMS_PER_PAGE, STATUS_VENDA, FORMAS_PAGAMENTO
from app.views.auth import login_required
from datetime import date, timedelta
from decimal import Decimal


pagamentos_bp = Blueprint('pagamentos', __name__)


@pagamentos_bp.route('/')
@login_required
def index():
    """Histórico de pagamentos"""
    
    # Parâmetros de busca
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    forma_pagamento = request.args.get('forma_pagamento', 'todas')
    cliente_id = request.args.get('cliente_id', type=int)
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', ITEMS_PER_PAGE))
    
    # Query base com joins
    query = Pagamento.query.join(Venda).join(Cliente)
    
    # Filtros
    if cliente_id:
        query = query.filter(Venda.cliente_id == cliente_id)
    
    if forma_pagamento != 'todas':
        query = query.filter(Pagamento.forma_pagamento == forma_pagamento)
    
    if data_inicio:
        try:
            data_inicio_obj = date.fromisoformat(data_inicio)
            query = query.filter(Pagamento.data_pagamento >= data_inicio_obj)
        except ValueError:
            flash_error('Data de início inválida.')
    
    if data_fim:
        try:
            data_fim_obj = date.fromisoformat(data_fim)
            query = query.filter(Pagamento.data_pagamento <= data_fim_obj)
        except ValueError:
            flash_error('Data de fim inválida.')
    
    # Ordenação
    query = query.order_by(Pagamento.data_pagamento.desc(), Pagamento.data_criacao.desc())
    
    # Paginação
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    pagamentos = pagination.items
    
    # Estatísticas
    stats = {
        'total_pagamentos': Pagamento.query.count(),
        'pagamentos_hoje': Pagamento.query.filter(
            Pagamento.data_pagamento == date.today()
        ).count(),
        'valor_total_recebido': db.session.query(
            func.sum(Pagamento.valor)
        ).scalar() or 0,
        'valor_recebido_hoje': db.session.query(
            func.sum(Pagamento.valor)
        ).filter(
            Pagamento.data_pagamento == date.today()
        ).scalar() or 0
    }
    
    # Cliente selecionado
    cliente_selecionado = Cliente.query.get(cliente_id) if cliente_id else None
    
    return render_template(
        'pagamentos/index.html',
        pagamentos=pagamentos,
        pagination=pagination,
        stats=stats,
        data_inicio=data_inicio,
        data_fim=data_fim,
        forma_pagamento=forma_pagamento,
        cliente_selecionado=cliente_selecionado
    )


@pagamentos_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def create():
    """Registrar novo pagamento"""
    
    venda_id = request.args.get('venda_id', type=int)
    cliente_id = request.args.get('cliente_id', type=int)
    
    # Se venda específica for informada, carregar dados
    venda_selecionada = Venda.query.get(venda_id) if venda_id else None
    cliente_selecionado = Cliente.query.get(cliente_id) if cliente_id else None
    
    if request.method == 'POST':
        try:
            # Dados do pagamento
            venda_id = int(request.form.get('venda_id'))
            valor = parse_currency(request.form.get('valor', '0'))
            forma_pagamento = request.form.get('forma_pagamento', 'dinheiro')
            valor_recebido_str = request.form.get('valor_recebido', '')
            observacoes = request.form.get('observacoes', '').strip()
            
            # Validar venda
            venda = Venda.query.get(venda_id)
            if not venda:
                flash_error('Venda não encontrada.')
                return render_template('pagamentos/form.html', 
                                     venda_selecionada=venda_selecionada,
                                     cliente_selecionado=cliente_selecionado)
            
            if venda.status == STATUS_VENDA['PAGA']:
                flash_error('Esta venda já está paga.')
                return render_template('pagamentos/form.html', 
                                     venda_selecionada=venda_selecionada,
                                     cliente_selecionado=cliente_selecionado)
            
            # Validar valor
            if valor <= 0:
                flash_error('Valor do pagamento deve ser maior que zero.')
                return render_template('pagamentos/form.html', 
                                     venda_selecionada=venda_selecionada,
                                     cliente_selecionado=cliente_selecionado)
            
            if valor > venda.valor_restante:
                flash_error(f'Valor excede o restante da venda (R$ {venda.valor_restante:.2f}).')
                return render_template('pagamentos/form.html', 
                                     venda_selecionada=venda_selecionada,
                                     cliente_selecionado=cliente_selecionado)
            
            # Validar forma de pagamento
            if forma_pagamento not in FORMAS_PAGAMENTO.values():
                flash_error('Forma de pagamento inválida.')
                return render_template('pagamentos/form.html', 
                                     venda_selecionada=venda_selecionada,
                                     cliente_selecionado=cliente_selecionado)
            
            # Processar valor recebido (apenas para dinheiro)
            valor_recebido = None
            if forma_pagamento == FORMAS_PAGAMENTO['DINHEIRO'] and valor_recebido_str:
                valor_recebido = parse_currency(valor_recebido_str)
                if valor_recebido < valor:
                    flash_error('Valor recebido não pode ser menor que o valor do pagamento.')
                    return render_template('pagamentos/form.html', 
                                         venda_selecionada=venda_selecionada,
                                         cliente_selecionado=cliente_selecionado)
            
            # Criar pagamento
            pagamento = Pagamento(
                venda_id=venda_id,
                valor=valor,
                forma_pagamento=forma_pagamento,
                valor_recebido=valor_recebido,
                data_pagamento=date.today(),
                observacoes=observacoes if observacoes else None
            )
            
            # Calcular troco se for dinheiro
            if forma_pagamento == FORMAS_PAGAMENTO['DINHEIRO']:
                pagamento.calcular_troco()
            
            # Validar pagamento
            errors = pagamento.validate()
            if errors:
                for error in errors:
                    flash_error(error)
                return render_template('pagamentos/form.html', 
                                     venda_selecionada=venda_selecionada,
                                     cliente_selecionado=cliente_selecionado)
            
            # Salvar pagamento
            db.session.add(pagamento)
            
            # Atualizar status da venda
            venda.atualizar_status()
            
            db.session.commit()
            
            # Mensagem de sucesso
            flash_success(f'Pagamento de R$ {valor:.2f} registrado com sucesso!')
            
            # Se venda foi quitada, informar sobre impressão
            if venda.status == STATUS_VENDA['PAGA']:
                flash_success('Venda quitada! Comprovante disponível para impressão.')
            
            return redirect(url_for('vendas.view', id=venda_id))
            
        except Exception as e:
            db.session.rollback()
            flash_error(f'Erro ao registrar pagamento: {str(e)}')
            return render_template('pagamentos/form.html', 
                                 venda_selecionada=venda_selecionada,
                                 cliente_selecionado=cliente_selecionado)
    
    # GET - Mostrar formulário
    return render_template('pagamentos/form.html', 
                         venda_selecionada=venda_selecionada,
                         cliente_selecionado=cliente_selecionado)


@pagamentos_bp.route('/multiplo', methods=['GET', 'POST'])
@login_required
def multiplo():
    """Pagamento múltiplo - várias vendas de uma vez"""
    
    cliente_id = request.args.get('cliente_id', type=int)
    cliente_selecionado = Cliente.query.get(cliente_id) if cliente_id else None
    
    if request.method == 'POST':
        try:
            # Dados do pagamento múltiplo
            cliente_id = int(request.form.get('cliente_id'))
            vendas_selecionadas = request.form.getlist('vendas_selecionadas')
            valor_pago = parse_currency(request.form.get('valor_pago', '0'))
            forma_pagamento = request.form.get('forma_pagamento', 'dinheiro')
            valor_recebido_str = request.form.get('valor_recebido', '')
            observacoes = request.form.get('observacoes', '').strip()
            
            # Validar cliente
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                flash_error('Cliente não encontrado.')
                return render_template('pagamentos/multiplo.html', cliente_selecionado=cliente_selecionado)
            
            # Validar vendas selecionadas
            if not vendas_selecionadas:
                flash_error('Selecione pelo menos uma venda.')
                return render_template('pagamentos/multiplo.html', cliente_selecionado=cliente_selecionado)
            
            vendas_ids = [int(v) for v in vendas_selecionadas]
            vendas = Venda.query.filter(
                Venda.id.in_(vendas_ids),
                Venda.cliente_id == cliente_id,
                Venda.status == STATUS_VENDA['ABERTA']
            ).all()
            
            if len(vendas) != len(vendas_ids):
                flash_error('Uma ou mais vendas são inválidas.')
                return render_template('pagamentos/multiplo.html', cliente_selecionado=cliente_selecionado)
            
            # Calcular valor total das vendas
            valor_total_vendas = sum(v.valor_restante for v in vendas)
            
            # Validar valor pago
            if valor_pago <= 0:
                flash_error('Valor pago deve ser maior que zero.')
                return render_template('pagamentos/multiplo.html', cliente_selecionado=cliente_selecionado)
            
            if valor_pago > valor_total_vendas:
                flash_error(f'Valor pago maior que o total das vendas (R$ {valor_total_vendas:.2f}).')
                return render_template('pagamentos/multiplo.html', cliente_selecionado=cliente_selecionado)
            
            # Processar valor recebido (apenas para dinheiro)
            valor_recebido = None
            if forma_pagamento == FORMAS_PAGAMENTO['DINHEIRO'] and valor_recebido_str:
                valor_recebido = parse_currency(valor_recebido_str)
                if valor_recebido < valor_pago:
                    flash_error('Valor recebido não pode ser menor que o valor pago.')
                    return render_template('pagamentos/multiplo.html', cliente_selecionado=cliente_selecionado)
            
            # Criar pagamento múltiplo
            pagamento_multiplo = PagamentoMultiplo(
                cliente_id=cliente_id,
                valor_total_notas=valor_total_vendas,
                valor_pago=valor_pago,
                forma_pagamento=forma_pagamento,
                valor_recebido=valor_recebido,
                data_pagamento=date.today(),
                observacoes=observacoes if observacoes else None
            )
            
            db.session.add(pagamento_multiplo)
            db.session.flush()  # Para obter o ID
            
            # Distribuir pagamento proporcionalmente entre as vendas
            valor_restante_distribuir = valor_pago
            
            for venda in vendas:
                if valor_restante_distribuir <= 0:
                    break
                
                # Calcular valor proporcional para esta venda
                proporcao = venda.valor_restante / valor_total_vendas
                valor_para_venda = min(
                    valor_pago * proporcao,
                    venda.valor_restante,
                    valor_restante_distribuir
                )
                
                # Arredondar para evitar problemas de centavos
                valor_para_venda = round(valor_para_venda, 2)
                
                # Criar detalhe do pagamento múltiplo
                detalhe = PagamentoMultiploDetalhe(
                    pagamento_multiplo_id=pagamento_multiplo.id,
                    venda_id=venda.id,
                    valor_original=venda.valor_restante,
                    valor_pago=valor_para_venda
                )
                
                db.session.add(detalhe)
                
                # Criar pagamento individual para a venda
                pagamento_individual = Pagamento(
                    venda_id=venda.id,
                    valor=valor_para_venda,
                    forma_pagamento=forma_pagamento,
                    data_pagamento=date.today(),
                    observacoes=f'Pagamento múltiplo #{pagamento_multiplo.id}'
                )
                
                db.session.add(pagamento_individual)
                
                # Atualizar status da venda
                venda.atualizar_status()
                
                valor_restante_distribuir -= valor_para_venda
            
            # Se sobrou valor, criar venda de restante
            venda_restante = None
            if pagamento_multiplo.valor_restante > 0:
                # Criar nova venda para o restante
                venda_restante = Venda(
                    cliente_id=cliente_id,
                    data_venda=date.today(),
                    eh_restante=True,
                    pagamento_multiplo_id=pagamento_multiplo.id,
                    observacoes=f'Restante do pagamento múltiplo #{pagamento_multiplo.id}'
                )
                
                # Gerar data de vencimento
                venda_restante.gerar_data_vencimento()
                
                db.session.add(venda_restante)
                db.session.flush()
                
                # Criar item para o restante
                item_restante = ItemVenda.criar_item_restante(
                    valor_restante=pagamento_multiplo.valor_restante,
                    notas_ids=vendas_ids,
                    data_pagamento=date.today()
                )
                
                item_restante.venda_id = venda_restante.id
                db.session.add(item_restante)
                
                # Recalcular totais da venda de restante
                venda_restante.calcular_totais()
            
            # Salvar tudo
            db.session.commit()
            
            # Mensagens de sucesso
            flash_success(f'Pagamento múltiplo de R$ {valor_pago:.2f} registrado com sucesso!')
            flash_success(f'{len(vendas)} venda(s) processada(s).')
            
            if venda_restante:
                flash_warning(f'Saldo restante de R$ {venda_restante.total:.2f} gerou uma nova venda (#{venda_restante.id}).')
            
            # Verificar se alguma venda foi quitada
            vendas_quitadas = [v for v in vendas if v.status == STATUS_VENDA['PAGA']]
            if vendas_quitadas:
                flash_success(f'{len(vendas_quitadas)} venda(s) quitada(s)!')
            
            return redirect(url_for('clientes.view', id=cliente_id))
            
        except Exception as e:
            db.session.rollback()
            flash_error(f'Erro ao processar pagamento múltiplo: {str(e)}')
            return render_template('pagamentos/multiplo.html', cliente_selecionado=cliente_selecionado)
    
    # GET - Mostrar formulário
    return render_template('pagamentos/multiplo.html', cliente_selecionado=cliente_selecionado)


# APIs AJAX

@pagamentos_bp.route('/api/vendas-abertas/<int:cliente_id>')
@login_required
def api_vendas_abertas(cliente_id):
    """API para obter vendas em aberto de um cliente"""
    
    try:
        cliente = Cliente.query.get_or_404(cliente_id)
        
        vendas = cliente.vendas_em_aberto.order_by(Venda.data_vencimento).all()
        
        resultado = []
        for venda in vendas:
            resultado.append({
                'id': venda.id,
                'data_venda': venda.data_venda.strftime('%d/%m/%Y'),
                'data_vencimento': venda.data_vencimento.strftime('%d/%m/%Y'),
                'total': float(venda.total),
                'valor_restante': float(venda.valor_restante),
                'dias_atraso': venda.dias_atraso,
                'esta_vencida': venda.esta_vencida,
                'eh_restante': venda.eh_restante,
                'itens_resumo': ', '.join([item.descricao for item in venda.itens.limit(3)])
            })
        
        return jsonify({
            'success': True,
            'vendas': resultado,
            'total_vendas': len(resultado),
            'valor_total': sum(v['valor_restante'] for v in resultado)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@pagamentos_bp.route('/api/simular-distribuicao', methods=['POST'])
@login_required
def api_simular_distribuicao():
    """API para simular distribuição de pagamento múltiplo"""
    
    try:
        data = request.json
        vendas_ids = data.get('vendas_ids', [])
        valor_pago = Decimal(str(data.get('valor_pago', 0)))
        
        if not vendas_ids or valor_pago <= 0:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos'
            }), 400
        
        # Carregar vendas
        vendas = Venda.query.filter(
            Venda.id.in_(vendas_ids),
            Venda.status == STATUS_VENDA['ABERTA']
        ).all()
        
        valor_total_vendas = sum(v.valor_restante for v in vendas)
        
        # Simular distribuição
        distribuicao = []
        valor_restante_distribuir = valor_pago
        
        for venda in vendas:
            if valor_restante_distribuir <= 0:
                valor_para_venda = Decimal('0')
            else:
                proporcao = venda.valor_restante / valor_total_vendas
                valor_para_venda = min(
                    valor_pago * proporcao,
                    venda.valor_restante,
                    valor_restante_distribuir
                )
                valor_para_venda = valor_para_venda.quantize(Decimal('0.01'))
                valor_restante_distribuir -= valor_para_venda
            
            distribuicao.append({
                'venda_id': venda.id,
                'valor_original': float(venda.valor_restante),
                'valor_pago': float(valor_para_venda),
                'valor_restante': float(venda.valor_restante - valor_para_venda),
                'quitada': valor_para_venda >= venda.valor_restante
            })
        
        valor_restante_total = valor_total_vendas - valor_pago
        
        return jsonify({
            'success': True,
            'distribuicao': distribuicao,
            'valor_total_vendas': float(valor_total_vendas),
            'valor_pago': float(valor_pago),
            'valor_restante': float(max(valor_restante_total, 0)),
            'gera_restante': valor_restante_total > 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# Context processor para dados do módulo
@pagamentos_bp.app_context_processor
def inject_pagamentos_data():
    """Injetar dados do módulo pagamentos nos templates"""
    return {
        'formas_pagamento': [
            ('todas', 'Todas'),
            ('dinheiro', 'Dinheiro'),
            ('cartao', 'Cartão'),
            ('pix', 'PIX')
        ]
    }