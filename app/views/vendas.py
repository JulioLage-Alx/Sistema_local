"""
Blueprint Vendas - CRUD completo de vendas a crediário
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func, or_, and_
from app import db
from app.models import Cliente, Venda, ItemVenda, Pagamento
from app.utils.helpers import (
    flash_success, flash_error, flash_warning, 
    format_currency, parse_currency, paginate_query
)
from app.utils.constants import ITEMS_PER_PAGE, STATUS_VENDA, DIAS_VENCIMENTO_PADRAO
from app.views.auth import login_required
from datetime import date, timedelta
from decimal import Decimal


vendas_bp = Blueprint('vendas', __name__)


@vendas_bp.route('/')
@login_required
def index():
    """Listagem de vendas com filtros"""
    
    # Parâmetros de busca
    termo_busca = request.args.get('q', '').strip()
    cliente_id = request.args.get('cliente_id', type=int)
    status = request.args.get('status', 'todas')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', ITEMS_PER_PAGE))
    
    # Query base com join do cliente
    query = Venda.query.join(Cliente)
    
    # Filtro por cliente específico
    if cliente_id:
        query = query.filter(Venda.cliente_id == cliente_id)
    
    # Filtro por status
    if status == 'abertas':
        query = query.filter(Venda.status == STATUS_VENDA['ABERTA'])
    elif status == 'pagas':
        query = query.filter(Venda.status == STATUS_VENDA['PAGA'])
    elif status == 'vencidas':
        data_hoje = date.today()
        query = query.filter(
            Venda.status == STATUS_VENDA['ABERTA'],
            Venda.data_vencimento < data_hoje
        )
    elif status == 'restantes':
        query = query.filter(Venda.eh_restante == True)
    
    # Filtro por período
    if data_inicio:
        try:
            data_inicio_obj = date.fromisoformat(data_inicio)
            query = query.filter(Venda.data_venda >= data_inicio_obj)
        except ValueError:
            flash_error('Data de início inválida.')
    
    if data_fim:
        try:
            data_fim_obj = date.fromisoformat(data_fim)
            query = query.filter(Venda.data_venda <= data_fim_obj)
        except ValueError:
            flash_error('Data de fim inválida.')
    
    # Busca por termo
    if termo_busca:
        if termo_busca.isdigit():
            # Busca por ID da venda
            query = query.filter(Venda.id == int(termo_busca))
        else:
            # Busca por nome do cliente
            query = query.filter(Cliente.nome.ilike(f'%{termo_busca}%'))
    
    # Ordenação
    ordenacao = request.args.get('ordem', 'data_desc')
    if ordenacao == 'data_asc':
        query = query.order_by(Venda.data_venda.asc())
    elif ordenacao == 'valor_desc':
        query = query.order_by(Venda.total.desc())
    elif ordenacao == 'valor_asc':
        query = query.order_by(Venda.total.asc())
    elif ordenacao == 'cliente':
        query = query.order_by(Cliente.nome)
    elif ordenacao == 'vencimento':
        query = query.order_by(Venda.data_vencimento)
    else:  # data_desc (padrão)
        query = query.order_by(Venda.data_venda.desc())
    
    # Paginação
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    vendas = pagination.items
    
    # Estatísticas para o header
    stats = {
        'total_vendas': Venda.query.count(),
        'vendas_abertas': Venda.query.filter(Venda.status == STATUS_VENDA['ABERTA']).count(),
        'vendas_vencidas': Venda.vendas_vencidas().count(),
        'valor_total_aberto': db.session.query(
            func.sum(Venda.total)
        ).filter(Venda.status == STATUS_VENDA['ABERTA']).scalar() or 0,
        'vendas_hoje': Venda.vendas_hoje().count()
    }
    
    # Cliente selecionado (se aplicável)
    cliente_selecionado = Cliente.query.get(cliente_id) if cliente_id else None
    
    return render_template(
        'vendas/index.html',
        vendas=vendas,
        pagination=pagination,
        stats=stats,
        termo_busca=termo_busca,
        cliente_selecionado=cliente_selecionado,
        status=status,
        data_inicio=data_inicio,
        data_fim=data_fim,
        ordenacao=ordenacao
    )


@vendas_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def create():
    """Criar nova venda"""
    
    cliente_id = request.args.get('cliente_id', type=int)
    cliente_selecionado = Cliente.query.get(cliente_id) if cliente_id else None
    
    if request.method == 'POST':
        try:
            # Dados básicos da venda
            cliente_id = int(request.form.get('cliente_id'))
            data_venda = request.form.get('data_venda', date.today().isoformat())
            data_vencimento = request.form.get('data_vencimento', '')
            observacoes = request.form.get('observacoes', '').strip()
            
            # Validar cliente
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                flash_error('Cliente não encontrado.')
                return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
            
            if not cliente.ativo:
                flash_error('Cliente inativo não pode realizar compras.')
                return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
            
            # Processar data da venda
            try:
                data_venda_obj = date.fromisoformat(data_venda)
            except ValueError:
                flash_error('Data da venda inválida.')
                return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
            
            # Processar data de vencimento
            if data_vencimento:
                try:
                    data_vencimento_obj = date.fromisoformat(data_vencimento)
                    if data_vencimento_obj < data_venda_obj:
                        flash_error('Data de vencimento não pode ser anterior à data da venda.')
                        return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
                except ValueError:
                    flash_error('Data de vencimento inválida.')
                    return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
            else:
                # Gerar data de vencimento automaticamente
                data_vencimento_obj = data_venda_obj + timedelta(days=DIAS_VENCIMENTO_PADRAO)
            
            # Processar itens da venda
            itens_data = []
            item_index = 0
            
            while f'item_{item_index}_descricao' in request.form:
                descricao = request.form.get(f'item_{item_index}_descricao', '').strip()
                quantidade_str = request.form.get(f'item_{item_index}_quantidade', '0')
                valor_unitario_str = request.form.get(f'item_{item_index}_valor_unitario', '0')
                
                if descricao:  # Apenas processar itens com descrição
                    try:
                        quantidade = parse_currency(quantidade_str)
                        valor_unitario = parse_currency(valor_unitario_str)
                        
                        if quantidade <= 0:
                            flash_error(f'Item {item_index + 1}: Quantidade deve ser maior que zero.')
                            return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
                        
                        if valor_unitario <= 0:
                            flash_error(f'Item {item_index + 1}: Valor unitário deve ser maior que zero.')
                            return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
                        
                        itens_data.append({
                            'descricao': descricao,
                            'quantidade': quantidade,
                            'valor_unitario': valor_unitario
                        })
                        
                    except Exception as e:
                        flash_error(f'Item {item_index + 1}: Valores inválidos.')
                        return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
                
                item_index += 1
            
            if not itens_data:
                flash_error('A venda deve ter pelo menos um item.')
                return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
            
            # Calcular total da venda
            total_venda = sum(item['quantidade'] * item['valor_unitario'] for item in itens_data)
            
            # Verificar limite de crédito
            if not cliente.verificar_limite_credito(total_venda):
                credito_disponivel = cliente.credito_disponivel
                flash_error(
                    f'Venda excede o limite de crédito do cliente. '
                    f'Crédito disponível: R$ {credito_disponivel:.2f}'
                )
                return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
            
            # Criar a venda
            venda = Venda(
                cliente_id=cliente_id,
                data_venda=data_venda_obj,
                data_vencimento=data_vencimento_obj,
                observacoes=observacoes if observacoes else None
            )
            
            db.session.add(venda)
            db.session.flush()  # Para obter o ID da venda
            
            # Adicionar itens
            for item_data in itens_data:
                item = ItemVenda(
                    venda_id=venda.id,
                    descricao=item_data['descricao'],
                    quantidade=item_data['quantidade'],
                    valor_unitario=item_data['valor_unitario']
                )
                item.calcular_subtotal()
                db.session.add(item)
            
            # Recalcular totais da venda
            db.session.flush()
            venda.calcular_totais()
            venda.atualizar_status()
            
            # Validar venda completa
            errors = venda.validate()
            if errors:
                for error in errors:
                    flash_error(error)
                db.session.rollback()
                return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
            
            # Salvar tudo
            db.session.commit()
            
            flash_success(f'Venda #{venda.id} registrada com sucesso!')
            return redirect(url_for('vendas.view', id=venda.id))
            
        except Exception as e:
            db.session.rollback()
            flash_error(f'Erro ao registrar venda: {str(e)}')
            return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)
    
    # GET - Mostrar formulário
    return render_template('vendas/nova.html', cliente_selecionado=cliente_selecionado)


@vendas_bp.route('/<int:id>')
@login_required
def view(id):
    """Visualizar detalhes da venda"""
    
    venda = Venda.query.get_or_404(id)
    
    # Histórico de pagamentos
    pagamentos = venda.pagamentos.order_by(Pagamento.data_pagamento.desc()).all()
    
    # Informações de restante (se aplicável)
    info_restante = None
    if venda.eh_restante and venda.pagamento_multiplo_origem:
        info_restante = venda.descricao_restante
    
    return render_template(
        'vendas/detalhes.html',
        venda=venda,
        pagamentos=pagamentos,
        info_restante=info_restante
    )


@vendas_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Editar venda (apenas se não paga)"""
    
    venda = Venda.query.get_or_404(id)
    
    # Verificar se pode editar
    if venda.status == STATUS_VENDA['PAGA']:
        flash_error('Não é possível editar vendas já pagas.')
        return redirect(url_for('vendas.view', id=id))
    
    if venda.eh_restante:
        flash_error('Não é possível editar vendas de restante.')
        return redirect(url_for('vendas.view', id=id))
    
    if venda.pagamentos.count() > 0:
        flash_error('Não é possível editar vendas que já receberam pagamentos.')
        return redirect(url_for('vendas.view', id=id))
    
    if request.method == 'POST':
        try:
            # Dados básicos
            data_venda = request.form.get('data_venda', venda.data_venda.isoformat())
            data_vencimento = request.form.get('data_vencimento', venda.data_vencimento.isoformat())
            observacoes = request.form.get('observacoes', '').strip()
            
            # Processar datas
            try:
                data_venda_obj = date.fromisoformat(data_venda)
                data_vencimento_obj = date.fromisoformat(data_vencimento)
                
                if data_vencimento_obj < data_venda_obj:
                    flash_error('Data de vencimento não pode ser anterior à data da venda.')
                    return render_template('vendas/form.html', venda=venda)
                    
            except ValueError:
                flash_error('Datas inválidas.')
                return render_template('vendas/form.html', venda=venda)
            
            # Remover itens existentes
            for item in venda.itens:
                db.session.delete(item)
            
            # Processar novos itens
            itens_data = []
            item_index = 0
            
            while f'item_{item_index}_descricao' in request.form:
                descricao = request.form.get(f'item_{item_index}_descricao', '').strip()
                quantidade_str = request.form.get(f'item_{item_index}_quantidade', '0')
                valor_unitario_str = request.form.get(f'item_{item_index}_valor_unitario', '0')
                
                if descricao:
                    try:
                        quantidade = parse_currency(quantidade_str)
                        valor_unitario = parse_currency(valor_unitario_str)
                        
                        if quantidade <= 0 or valor_unitario <= 0:
                            flash_error(f'Item {item_index + 1}: Valores devem ser maiores que zero.')
                            return render_template('vendas/form.html', venda=venda)
                        
                        itens_data.append({
                            'descricao': descricao,
                            'quantidade': quantidade,
                            'valor_unitario': valor_unitario
                        })
                        
                    except Exception:
                        flash_error(f'Item {item_index + 1}: Valores inválidos.')
                        return render_template('vendas/form.html', venda=venda)
                
                item_index += 1
            
            if not itens_data:
                flash_error('A venda deve ter pelo menos um item.')
                return render_template('vendas/form.html', venda=venda)
            
            # Calcular novo total
            total_venda = sum(item['quantidade'] * item['valor_unitario'] for item in itens_data)
            
            # Verificar limite de crédito (considerando outras vendas em aberto)
            valor_outras_vendas = venda.cliente.valor_total_em_aberto - venda.total
            if (valor_outras_vendas + total_venda) > venda.cliente.limite_credito:
                credito_disponivel = venda.cliente.limite_credito - valor_outras_vendas
                flash_error(
                    f'Venda excede o limite de crédito do cliente. '
                    f'Crédito disponível: R$ {credito_disponivel:.2f}'
                )
                return render_template('vendas/form.html', venda=venda)
            
            # Atualizar venda
            venda.data_venda = data_venda_obj
            venda.data_vencimento = data_vencimento_obj
            venda.observacoes = observacoes if observacoes else None
            
            # Adicionar novos itens
            for item_data in itens_data:
                item = ItemVenda(
                    venda_id=venda.id,
                    descricao=item_data['descricao'],
                    quantidade=item_data['quantidade'],
                    valor_unitario=item_data['valor_unitario']
                )
                item.calcular_subtotal()
                db.session.add(item)
            
            # Recalcular totais
            db.session.flush()
            venda.calcular_totais()
            venda.atualizar_status()
            
            # Salvar alterações
            db.session.commit()
            
            flash_success(f'Venda #{venda.id} atualizada com sucesso!')
            return redirect(url_for('vendas.view', id=venda.id))
            
        except Exception as e:
            db.session.rollback()
            flash_error(f'Erro ao atualizar venda: {str(e)}')
            return render_template('vendas/form.html', venda=venda)
    
    # GET - Mostrar formulário de edição
    return render_template('vendas/form.html', venda=venda)


@vendas_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
def delete(id):
    """Excluir venda (apenas se não paga e sem pagamentos)"""
    
    venda = Venda.query.get_or_404(id)
    
    try:
        # Verificar se pode excluir
        if venda.status == STATUS_VENDA['PAGA']:
            flash_error('Não é possível excluir vendas já pagas.')
            return redirect(url_for('vendas.view', id=id))
        
        if venda.pagamentos.count() > 0:
            flash_error('Não é possível excluir vendas que já receberam pagamentos.')
            return redirect(url_for('vendas.view', id=id))
        
        if venda.eh_restante:
            flash_error('Não é possível excluir vendas de restante.')
            return redirect(url_for('vendas.view', id=id))
        
        cliente_nome = venda.cliente.nome
        venda_id = venda.id
        
        # Excluir venda (cascade vai excluir os itens)
        db.session.delete(venda)
        db.session.commit()
        
        flash_success(f'Venda #{venda_id} de {cliente_nome} excluída com sucesso!')
        return redirect(url_for('vendas.index'))
        
    except Exception as e:
        db.session.rollback()
        flash_error(f'Erro ao excluir venda: {str(e)}')
        return redirect(url_for('vendas.view', id=id))


# APIs AJAX

@vendas_bp.route('/api/calcular-total', methods=['POST'])
@login_required
def api_calcular_total():
    """API para calcular total da venda (AJAX)"""
    
    try:
        itens = request.json.get('itens', [])
        total = Decimal('0.00')
        
        for item in itens:
            quantidade = parse_currency(str(item.get('quantidade', 0)))
            valor_unitario = parse_currency(str(item.get('valor_unitario', 0)))
            total += quantidade * valor_unitario
        
        return jsonify({
            'success': True,
            'total': float(total),
            'total_formatado': format_currency(total)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@vendas_bp.route('/api/verificar-limite/<int:cliente_id>/<valor>')
@login_required
def api_verificar_limite(cliente_id, valor):
    """API para verificar limite de crédito"""
    
    try:
        cliente = Cliente.query.get_or_404(cliente_id)
        valor_decimal = parse_currency(valor)
        
        pode_comprar = cliente.verificar_limite_credito(valor_decimal)
        credito_disponivel = cliente.credito_disponivel
        
        return jsonify({
            'success': True,
            'pode_comprar': pode_comprar,
            'credito_disponivel': float(credito_disponivel),
            'credito_disponivel_formatado': format_currency(credito_disponivel),
            'limite_total': float(cliente.limite_credito),
            'valor_em_aberto': float(cliente.valor_total_em_aberto)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


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
        ]
    }