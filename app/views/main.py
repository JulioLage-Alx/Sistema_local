"""
Blueprint Principal - Dashboard e rotas base
"""

from datetime import date, timedelta
from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import func
from app import db
from app.models import Cliente, Venda, Pagamento
from app.utils.constants import STATUS_VENDA, DASHBOARD_STATS
from app.views.auth import login_required


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Página inicial - redireciona para dashboard se logado"""
    from flask import redirect, url_for, session
    
    if session.get('user_logged'):
        return redirect(url_for('main.dashboard'))
    else:
        return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal do sistema"""
    
    # Calcular estatísticas do dashboard
    stats = calcular_estatisticas_dashboard()
    
    # Obter alertas
    alertas = obter_alertas()
    
    # Vendas recentes
    vendas_recentes = Venda.query.order_by(
        Venda.data_criacao.desc()
    ).limit(5).all()
    
    # Clientes com maior valor em aberto
    clientes_maior_divida = obter_clientes_maior_divida()
    
    # Dados para gráficos
    dados_graficos = obter_dados_graficos()
    
    return render_template(
        'dashboard.html',
        stats=stats,
        alertas=alertas,
        vendas_recentes=vendas_recentes,
        clientes_maior_divida=clientes_maior_divida,
        dados_graficos=dados_graficos
    )


def calcular_estatisticas_dashboard():
    """Calcular estatísticas para o dashboard"""
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    
    # Vendas de hoje
    vendas_hoje = Venda.query.filter(
        Venda.data_venda == hoje
    ).count()
    
    # Valor vendido hoje
    valor_hoje = db.session.query(
        func.sum(Venda.total)
    ).filter(
        Venda.data_venda == hoje
    ).scalar() or 0
    
    # Vendas do mês
    vendas_mes = Venda.query.filter(
        Venda.data_venda >= inicio_mes
    ).count()
    
    # Valor vendido no mês
    valor_mes = db.session.query(
        func.sum(Venda.total)
    ).filter(
        Venda.data_venda >= inicio_mes
    ).scalar() or 0
    
    # Clientes ativos
    clientes_ativos = Cliente.query.filter(
        Cliente.ativo == True
    ).count()
    
    # Vendas em aberto
    vendas_abertas = Venda.query.filter(
        Venda.status == STATUS_VENDA['ABERTA']
    ).count()
    
    # Valor total em aberto
    valor_aberto = db.session.query(
        func.sum(Venda.total)
    ).filter(
        Venda.status == STATUS_VENDA['ABERTA']
    ).scalar() or 0
    
    # Vendas vencidas
    vendas_vencidas = Venda.query.filter(
        Venda.status == STATUS_VENDA['ABERTA'],
        Venda.data_vencimento < hoje
    ).count()
    
    # Valor vencido
    valor_vencido = db.session.query(
        func.sum(Venda.total)
    ).filter(
        Venda.status == STATUS_VENDA['ABERTA'],
        Venda.data_vencimento < hoje
    ).scalar() or 0
    
    # Pagamentos de hoje
    pagamentos_hoje = Pagamento.query.filter(
        Pagamento.data_pagamento == hoje
    ).count()
    
    # Valor recebido hoje
    valor_recebido_hoje = db.session.query(
        func.sum(Pagamento.valor)
    ).filter(
        Pagamento.data_pagamento == hoje
    ).scalar() or 0
    
    return {
        'vendas_hoje': vendas_hoje,
        'valor_hoje': float(valor_hoje),
        'vendas_mes': vendas_mes,
        'valor_mes': float(valor_mes),
        'clientes_ativos': clientes_ativos,
        'vendas_abertas': vendas_abertas,
        'valor_aberto': float(valor_aberto),
        'vendas_vencidas': vendas_vencidas,
        'valor_vencido': float(valor_vencido),
        'pagamentos_hoje': pagamentos_hoje,
        'valor_recebido_hoje': float(valor_recebido_hoje)
    }


def obter_alertas():
    """Obter alertas para o dashboard"""
    from app.utils.constants import DIAS_INADIMPLENCIA
    
    alertas = []
    hoje = date.today()
    
    # Vendas vencidas há mais de X dias
    data_limite = hoje - timedelta(days=DIAS_INADIMPLENCIA)
    vendas_inadimplentes = Venda.query.filter(
        Venda.status == STATUS_VENDA['ABERTA'],
        Venda.data_vencimento < data_limite
    ).count()
    
    if vendas_inadimplentes > 0:
        alertas.append({
            'tipo': 'danger',
            'icone': 'fas fa-exclamation-triangle',
            'titulo': f'{vendas_inadimplentes} venda(s) inadimplente(s)',
            'descricao': f'Vendas em aberto há mais de {DIAS_INADIMPLENCIA} dias',
            'link': '/vendas?status=vencida',
            'link_texto': 'Ver vendas'
        })
    
    # Vendas que vencem hoje
    vendas_vencem_hoje = Venda.query.filter(
        Venda.status == STATUS_VENDA['ABERTA'],
        Venda.data_vencimento == hoje
    ).count()
    
    if vendas_vencem_hoje > 0:
        alertas.append({
            'tipo': 'warning',
            'icone': 'fas fa-clock',
            'titulo': f'{vendas_vencem_hoje} venda(s) vencem hoje',
            'descricao': 'Acompanhe os pagamentos',
            'link': f'/vendas?data_vencimento={hoje}',
            'link_texto': 'Ver vendas'
        })
    
    # Clientes próximos do limite
    clientes_limite = db.session.query(Cliente).join(Venda).filter(
        Cliente.ativo == True,
        Venda.status == STATUS_VENDA['ABERTA']
    ).group_by(Cliente.id).having(
        func.sum(Venda.total) > (Cliente.limite_credito * 0.8)
    ).count()
    
    if clientes_limite > 0:
        alertas.append({
            'tipo': 'info',
            'icone': 'fas fa-credit-card',
            'titulo': f'{clientes_limite} cliente(s) próximo(s) do limite',
            'descricao': 'Mais de 80% do limite de crédito utilizado',
            'link': '/clientes?filtro=limite',
            'link_texto': 'Ver clientes'
        })
    
    return alertas


def obter_clientes_maior_divida():
    """Obter clientes com maior valor em aberto"""
    return db.session.query(
        Cliente.id,
        Cliente.nome,
        func.sum(Venda.total).label('total_aberto'),
        func.count(Venda.id).label('num_vendas')
    ).join(Venda).filter(
        Cliente.ativo == True,
        Venda.status == STATUS_VENDA['ABERTA']
    ).group_by(Cliente.id, Cliente.nome).order_by(
        func.sum(Venda.total).desc()
    ).limit(5).all()


def obter_dados_graficos():
    """Obter dados para os gráficos do dashboard"""
    hoje = date.today()
    
    # Vendas dos últimos 7 dias
    vendas_7_dias = []
    for i in range(6, -1, -1):
        data = hoje - timedelta(days=i)
        total = db.session.query(
            func.sum(Venda.total)
        ).filter(
            Venda.data_venda == data
        ).scalar() or 0
        
        vendas_7_dias.append({
            'data': data.strftime('%d/%m'),
            'valor': float(total)
        })
    
    # Pagamentos por forma nos últimos 30 dias
    inicio_mes = hoje - timedelta(days=30)
    pagamentos_forma = db.session.query(
        Pagamento.forma_pagamento,
        func.sum(Pagamento.valor).label('total')
    ).filter(
        Pagamento.data_pagamento >= inicio_mes
    ).group_by(Pagamento.forma_pagamento).all()
    
    # Status das vendas
    status_vendas = db.session.query(
        Venda.status,
        func.count(Venda.id).label('quantidade')
    ).group_by(Venda.status).all()
    
    return {
        'vendas_7_dias': vendas_7_dias,
        'pagamentos_forma': [
            {'forma': p.forma_pagamento, 'total': float(p.total)}
            for p in pagamentos_forma
        ],
        'status_vendas': [
            {'status': s.status, 'quantidade': s.quantidade}
            for s in status_vendas
        ]
    }


@main_bp.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """API para atualizar estatísticas do dashboard"""
    stats = calcular_estatisticas_dashboard()
    return jsonify(stats)


@main_bp.route('/api/dashboard/alertas')
@login_required
def api_dashboard_alertas():
    """API para obter alertas atualizados"""
    alertas = obter_alertas()
    return jsonify(alertas)


@main_bp.route('/search')
@login_required
def search():
    """Busca global no sistema"""
    termo = request.args.get('q', '').strip()
    
    if not termo:
        return render_template('search_results.html', termo='', resultados={})
    
    resultados = {
        'clientes': [],
        'vendas': [],
        'total': 0
    }
    
    # Buscar clientes
    clientes = Cliente.buscar(termo, apenas_ativos=True).limit(10).all()
    resultados['clientes'] = [
        {
            'id': c.id,
            'nome': c.nome,
            'cpf': c.cpf,
            'telefone': c.telefone,
            'valor_aberto': float(c.valor_total_em_aberto)
        }
        for c in clientes
    ]
    
    # Buscar vendas por ID se o termo for numérico
    if termo.isdigit():
        venda = Venda.query.get(int(termo))
        if venda:
            resultados['vendas'].append({
                'id': venda.id,
                'cliente_nome': venda.cliente.nome,
                'data_venda': venda.data_venda.strftime('%d/%m/%Y'),
                'total': float(venda.total),
                'status': venda.status
            })
    
    resultados['total'] = len(resultados['clientes']) + len(resultados['vendas'])
    
    return render_template('search_results.html', termo=termo, resultados=resultados)


@main_bp.route('/about')
def about():
    """Página sobre o sistema"""
    from app.utils.constants import SISTEMA_INFO
    
    return render_template('about.html', sistema_info=SISTEMA_INFO)


# Context processor para dados globais
@main_bp.app_context_processor
def inject_global_data():
    """Injetar dados globais nos templates"""
    return {
        'hoje': date.today(),
        'sistema_nome': 'Sistema Crediário Açougue'
    }