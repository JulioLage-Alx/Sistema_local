"""
Blueprint Clientes - CRUD completo de clientes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func, or_
from app import db
from app.models import Cliente, Venda
from app.utils.helpers import (
    flash_success, flash_error, flash_warning, 
    format_currency, validate_cpf, paginate_query
)
from app.utils.constants import ITEMS_PER_PAGE
from app.views.auth import login_required
from datetime import date, timedelta


clientes_bp = Blueprint('clientes', __name__)


@clientes_bp.route('/')
@login_required
def index():
    """Listagem de clientes com busca e filtros"""
    
    # Parâmetros de busca
    termo_busca = request.args.get('q', '').strip()
    filtro = request.args.get('filtro', 'todos')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', ITEMS_PER_PAGE))
    
    # Query base
    query = Cliente.query
    
    # Aplicar filtros
    if filtro == 'ativos':
        query = query.filter(Cliente.ativo == True)
    elif filtro == 'inativos':
        query = query.filter(Cliente.ativo == False)
    elif filtro == 'inadimplentes':
        # Clientes com vendas vencidas
        data_limite = date.today() - timedelta(days=30)
        query = query.join(Venda).filter(
            Cliente.ativo == True,
            Venda.status == 'aberta',
            Venda.data_vencimento < data_limite
        ).distinct()
    elif filtro == 'limite':
        # Clientes próximos do limite (80% ou mais)
        query = query.join(Venda).filter(
            Cliente.ativo == True,
            Venda.status == 'aberta'
        ).group_by(Cliente.id).having(
            func.sum(Venda.total) >= (Cliente.limite_credito * 0.8)
        )
    
    # Busca por termo
    if termo_busca:
        # Remover formatação para busca em CPF e telefone
        termo_limpo = ''.join(filter(str.isalnum, termo_busca))
        
        query = query.filter(
            or_(
                Cliente.nome.ilike(f'%{termo_busca}%'),
                func.replace(func.replace(func.replace(
                    Cliente.cpf, '.', ''), '-', ''), ' ', ''
                ).ilike(f'%{termo_limpo}%'),
                func.replace(func.replace(func.replace(func.replace(
                    Cliente.telefone, '(', ''), ')', ''), '-', ''), ' ', ''
                ).ilike(f'%{termo_limpo}%')
            )
        )
    
    # Ordenação
    ordenacao = request.args.get('ordem', 'nome')
    if ordenacao == 'data_cadastro':
        query = query.order_by(Cliente.data_cadastro.desc())
    elif ordenacao == 'limite_credito':
        query = query.order_by(Cliente.limite_credito.desc())
    elif ordenacao == 'valor_aberto':
        # Ordenar por valor em aberto (requer subquery)
        subquery = db.session.query(
            Venda.cliente_id,
            func.sum(Venda.total).label('total_aberto')
        ).filter(
            Venda.status == 'aberta'
        ).group_by(Venda.cliente_id).subquery()
        
        query = query.outerjoin(
            subquery, Cliente.id == subquery.c.cliente_id
        ).order_by(subquery.c.total_aberto.desc().nullslast())
    else:
        query = query.order_by(Cliente.nome)
    
    # Paginação
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    clientes = pagination.items
    
    # Estatísticas para o header
    stats = {
        'total_clientes': Cliente.query.count(),
        'clientes_ativos': Cliente.query.filter(Cliente.ativo == True).count(),
        'clientes_inadimplentes': Cliente.clientes_inadimplentes().count(),
        'valor_total_aberto': db.session.query(
            func.sum(Venda.total)
        ).filter(Venda.status == 'aberta').scalar() or 0
    }
    
    return render_template(
        'clientes/index.html',
        clientes=clientes,
        pagination=pagination,
        stats=stats,
        termo_busca=termo_busca,
        filtro=filtro,
        ordenacao=ordenacao
    )


@clientes_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def create():
    """Criar novo cliente"""
    
    if request.method == 'POST':
        try:
            # Coletar dados do formulário
            nome = request.form.get('nome', '').strip()
            cpf = request.form.get('cpf', '').strip()
            telefone = request.form.get('telefone', '').strip()
            endereco = request.form.get('endereco', '').strip()
            limite_credito = request.form.get('limite_credito', '500.00')
            observacoes = request.form.get('observacoes', '').strip()
            
            # Validações básicas
            if not nome:
                flash_error('Nome é obrigatório.')
                return render_template('clientes/form.html')
            
            if len(nome) < 2:
                flash_error('Nome deve ter pelo menos 2 caracteres.')
                return render_template('clientes/form.html')
            
            # Validar CPF se informado
            if cpf:
                cpf_limpo = ''.join(filter(str.isdigit, cpf))
                if not validate_cpf(cpf_limpo):
                    flash_error('CPF inválido.')
                    return render_template('clientes/form.html')
                
                # Verificar se CPF já existe
                cpf_existente = Cliente.query.filter(
                    Cliente.cpf == cpf,
                    Cliente.id != None  # Para reuso na edição
                ).first()
                if cpf_existente:
                    flash_error('CPF já cadastrado para outro cliente.')
                    return render_template('clientes/form.html')
            
            # Validar limite de crédito
            try:
                from app.utils.helpers import parse_currency
                limite_credito = parse_currency(limite_credito)
                if limite_credito < 0:
                    flash_error('Limite de crédito não pode ser negativo.')
                    return render_template('clientes/form.html')
            except:
                flash_error('Limite de crédito inválido.')
                return render_template('clientes/form.html')
            
            # Criar cliente
            cliente = Cliente(
                nome=nome,
                cpf=cpf if cpf else None,
                telefone=telefone if telefone else None,
                endereco=endereco if endereco else None,
                limite_credito=limite_credito,
                observacoes=observacoes if observacoes else None
            )
            
            # Validar modelo
            errors = cliente.validate()
            if errors:
                for error in errors:
                    flash_error(error)
                return render_template('clientes/form.html')
            
            # Salvar no banco
            db.session.add(cliente)
            db.session.commit()
            
            flash_success(f'Cliente "{nome}" cadastrado com sucesso!')
            return redirect(url_for('clientes.view', id=cliente.id))
            
        except Exception as e:
            db.session.rollback()
            flash_error(f'Erro ao cadastrar cliente: {str(e)}')
            return render_template('clientes/form.html')
    
    # GET - Mostrar formulário
    return render_template('clientes/form.html')


@clientes_bp.route('/<int:id>')
@login_required
def view(id):
    """Visualizar detalhes do cliente"""
    
    cliente = Cliente.query.get_or_404(id)
    
    # Estatísticas do cliente
    stats = {
        'total_vendas': cliente.vendas.count(),
        'vendas_pagas': cliente.vendas.filter(Venda.status == 'paga').count(),
        'vendas_abertas': cliente.vendas_em_aberto.count(),
        'vendas_vencidas': cliente.vendas_vencidas.count(),
        'valor_total_comprado': db.session.query(
            func.sum(Venda.total)
        ).filter(
            Venda.cliente_id == id
        ).scalar() or 0,
        'valor_total_pago': db.session.query(
            func.sum(Venda.total)
        ).filter(
            Venda.cliente_id == id,
            Venda.status == 'paga'
        ).scalar() or 0
    }
    
    # Histórico de vendas (últimas 10)
    vendas_recentes = cliente.historico_vendas(10).all()
    
    # Vendas em aberto
    vendas_abertas = cliente.vendas_em_aberto.order_by(
        Venda.data_vencimento
    ).all()
    
    # Vendas vencidas
    vendas_vencidas = cliente.vendas_vencidas.order_by(
        Venda.data_vencimento
    ).all()
    
    return render_template(
        'clientes/perfil.html',
        cliente=cliente,
        stats=stats,
        vendas_recentes=vendas_recentes,
        vendas_abertas=vendas_abertas,
        vendas_vencidas=vendas_vencidas
    )


@clientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Editar cliente"""
    
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Coletar dados do formulário
            nome = request.form.get('nome', '').strip()
            cpf = request.form.get('cpf', '').strip()
            telefone = request.form.get('telefone', '').strip()
            endereco = request.form.get('endereco', '').strip()
            limite_credito = request.form.get('limite_credito', '500.00')
            ativo = request.form.get('ativo') == 'on'
            observacoes = request.form.get('observacoes', '').strip()
            
            # Validações básicas
            if not nome:
                flash_error('Nome é obrigatório.')
                return render_template('clientes/form.html', cliente=cliente)
            
            if len(nome) < 2:
                flash_error('Nome deve ter pelo menos 2 caracteres.')
                return render_template('clientes/form.html', cliente=cliente)
            
            # Validar CPF se informado
            if cpf:
                cpf_limpo = ''.join(filter(str.isdigit, cpf))
                if not validate_cpf(cpf_limpo):
                    flash_error('CPF inválido.')
                    return render_template('clientes/form.html', cliente=cliente)
                
                # Verificar se CPF já existe para outro cliente
                cpf_existente = Cliente.query.filter(
                    Cliente.cpf == cpf,
                    Cliente.id != id
                ).first()
                if cpf_existente:
                    flash_error('CPF já cadastrado para outro cliente.')
                    return render_template('clientes/form.html', cliente=cliente)
            
            # Validar limite de crédito
            try:
                from app.utils.helpers import parse_currency
                limite_credito = parse_currency(limite_credito)
                if limite_credito < 0:
                    flash_error('Limite de crédito não pode ser negativo.')
                    return render_template('clientes/form.html', cliente=cliente)
            except:
                flash_error('Limite de crédito inválido.')
                return render_template('clientes/form.html', cliente=cliente)
            
            # Verificar se pode desativar cliente
            if not ativo and cliente.vendas_em_aberto.count() > 0:
                flash_warning('Cliente possui vendas em aberto. Não é possível desativá-lo.')
                ativo = True
            
            # Atualizar dados
            cliente.nome = nome
            cliente.cpf = cpf if cpf else None
            cliente.telefone = telefone if telefone else None
            cliente.endereco = endereco if endereco else None
            cliente.limite_credito = limite_credito
            cliente.ativo = ativo
            cliente.observacoes = observacoes if observacoes else None
            
            # Validar modelo
            errors = cliente.validate()
            if errors:
                for error in errors:
                    flash_error(error)
                return render_template('clientes/form.html', cliente=cliente)
            
            # Salvar alterações
            db.session.commit()
            
            flash_success(f'Cliente "{nome}" atualizado com sucesso!')
            return redirect(url_for('clientes.view', id=cliente.id))
            
        except Exception as e:
            db.session.rollback()
            flash_error(f'Erro ao atualizar cliente: {str(e)}')
            return render_template('clientes/form.html', cliente=cliente)
    
    # GET - Mostrar formulário de edição
    return render_template('clientes/form.html', cliente=cliente)


@clientes_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
def delete(id):
    """Excluir cliente"""
    
    cliente = Cliente.query.get_or_404(id)
    
    try:
        # Verificar se cliente pode ser excluído
        if cliente.vendas.count() > 0:
            flash_error('Não é possível excluir cliente que possui vendas registradas.')
            return redirect(url_for('clientes.view', id=id))
        
        nome_cliente = cliente.nome
        
        # Excluir cliente
        db.session.delete(cliente)
        db.session.commit()
        
        flash_success(f'Cliente "{nome_cliente}" excluído com sucesso!')
        return redirect(url_for('clientes.index'))
        
    except Exception as e:
        db.session.rollback()
        flash_error(f'Erro ao excluir cliente: {str(e)}')
        return redirect(url_for('clientes.view', id=id))


@clientes_bp.route('/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_status(id):
    """Ativar/Desativar cliente"""
    
    cliente = Cliente.query.get_or_404(id)
    
    try:
        if cliente.ativo:
            # Desativar - verificar se tem vendas em aberto
            if cliente.vendas_em_aberto.count() > 0:
                flash_warning('Cliente possui vendas em aberto. Não é possível desativá-lo.')
                return redirect(url_for('clientes.view', id=id))
            
            cliente.ativo = False
            flash_success(f'Cliente "{cliente.nome}" desativado.')
        else:
            # Ativar
            cliente.ativo = True
            flash_success(f'Cliente "{cliente.nome}" ativado.')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash_error(f'Erro ao alterar status do cliente: {str(e)}')
    
    return redirect(url_for('clientes.view', id=id))


# APIs AJAX

@clientes_bp.route('/api/buscar')
@login_required
def api_buscar():
    """API para busca de clientes (AJAX)"""
    
    termo = request.args.get('q', '').strip()
    limite = int(request.args.get('limit', 10))
    apenas_ativos = request.args.get('ativo', 'true').lower() == 'true'
    
    if not termo:
        return jsonify([])
    
    # Buscar clientes
    clientes = Cliente.buscar(termo, apenas_ativos).limit(limite).all()
    
    # Converter para JSON
    resultado = []
    for cliente in clientes:
        resultado.append({
            'id': cliente.id,
            'nome': cliente.nome,
            'cpf': cliente.cpf,
            'telefone': cliente.telefone,
            'limite_credito': float(cliente.limite_credito),
            'valor_aberto': float(cliente.valor_total_em_aberto),
            'credito_disponivel': float(cliente.credito_disponivel),
            'pode_comprar': cliente.pode_comprar,
            'esta_inadimplente': cliente.esta_inadimplente
        })
    
    return jsonify(resultado)


@clientes_bp.route('/api/<int:id>/resumo')
@login_required
def api_resumo(id):
    """API para obter resumo do cliente"""
    
    cliente = Cliente.query.get_or_404(id)
    
    return jsonify({
        'id': cliente.id,
        'nome': cliente.nome,
        'cpf': cliente.cpf,
        'telefone': cliente.telefone,
        'endereco': cliente.endereco,
        'limite_credito': float(cliente.limite_credito),
        'ativo': cliente.ativo,
        'valor_total_em_aberto': float(cliente.valor_total_em_aberto),
        'valor_total_vencido': float(cliente.valor_total_vencido),
        'credito_disponivel': float(cliente.credito_disponivel),
        'pode_comprar': cliente.pode_comprar,
        'esta_inadimplente': cliente.esta_inadimplente,
        'total_vendas': cliente.vendas.count(),
        'vendas_em_aberto': cliente.vendas_em_aberto.count(),
        'vendas_vencidas': cliente.vendas_vencidas.count()
    })


@clientes_bp.route('/api/<int:id>/vendas')
@login_required
def api_vendas(id):
    """API para obter vendas do cliente"""
    
    cliente = Cliente.query.get_or_404(id)
    status = request.args.get('status', 'todas')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Filtrar vendas por status
    query = cliente.vendas
    if status == 'abertas':
        query = cliente.vendas_em_aberto
    elif status == 'pagas':
        query = cliente.vendas.filter(Venda.status == 'paga')
    elif status == 'vencidas':
        query = cliente.vendas_vencidas
    
    # Ordenar por data mais recente
    query = query.order_by(Venda.data_venda.desc())
    
    # Paginar
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Converter para JSON
    vendas = []
    for venda in pagination.items:
        vendas.append(venda.to_dict(include_itens=False))
    
    return jsonify({
        'vendas': vendas,
        'pagination': {
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        }
    })


# Context processor para dados do módulo
@clientes_bp.app_context_processor
def inject_clientes_data():
    """Injetar dados do módulo clientes nos templates"""
    return {
        'filtros_clientes': [
            ('todos', 'Todos'),
            ('ativos', 'Ativos'),
            ('inativos', 'Inativos'),
            ('inadimplentes', 'Inadimplentes'),
            ('limite', 'Próx. do Limite')
        ],
        'ordenacao_clientes': [
            ('nome', 'Nome'),
            ('data_cadastro', 'Data Cadastro'),
            ('limite_credito', 'Limite Crédito'),
            ('valor_aberto', 'Valor em Aberto')
        ]
    }