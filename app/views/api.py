"""
Blueprint API - Endpoints AJAX para funcionalidades dinâmicas
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import func, or_, and_
from app import db
from app.models import Cliente, Venda, ItemVenda, Pagamento
from app.utils.helpers import parse_currency, format_currency
from app.utils.constants import STATUS_VENDA
from app.views.auth import login_required
from datetime import date, timedelta
from decimal import Decimal


api_bp = Blueprint('api', __name__)


# Endpoints de Clientes

@api_bp.route('/clientes/buscar')
@login_required
def clientes_buscar():
    """Buscar clientes para autocomplete"""
    
    termo = request.args.get('q', '').strip()
    limite = int(request.args.get('limit', 10))
    apenas_ativos = request.args.get('ativo', 'true').lower() == 'true'
    
    if not termo or len(termo) < 2:
        return jsonify([])
    
    try:
        # Buscar clientes
        query = Cliente.query
        
        if apenas_ativos:
            query = query.filter(Cliente.ativo == True)
        
        # Remover formatação para busca em CPF e telefone
        termo_limpo = ''.join(filter(str.isalnum, termo))
        
        query = query.filter(
            or_(
                Cliente.nome.ilike(f'%{termo}%'),
                func.replace(func.replace(func.replace(
                    Cliente.cpf, '.', ''), '-', ''), ' ', ''
                ).ilike(f'%{termo_limpo}%'),
                func.replace(func.replace(func.replace(func.replace(
                    Cliente.telefone, '(', ''), ')', ''), '-', ''), ' ', ''
                ).ilike(f'%{termo_limpo}%')
            )
        ).order_by(Cliente.nome).limit(limite)
        
        clientes = query.all()
        
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
                'esta_inadimplente': cliente.esta_inadimplente,
                'ativo': cliente.ativo
            })
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400


@api_bp.route('/clientes/<int:id>/resumo')
@login_required
def cliente_resumo(id):
    """Obter resumo financeiro do cliente"""
    
    try:
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
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 404


@api_bp.route('/clientes/<int:id>/vendas-abertas')
@login_required
def cliente_vendas_abertas(id):
    """Obter vendas em aberto do cliente"""
    
    try:
        cliente = Cliente.query.get_or_404(id)
        vendas = cliente.vendas_em_aberto.order_by(Venda.data_vencimento).all()
        
        resultado = []
        for venda in vendas:
            resultado.append({
                'id': venda.id,
                'data_venda': venda.data_venda.strftime('%d/%m/%Y'),
                'data_vencimento': venda.data_vencimento.strftime('%d/%m/%Y'),
                'total': float(venda.total),
                'valor_pago': float(venda.valor_pago),
                'valor_restante': float(venda.valor_restante),
                'dias_atraso': venda.dias_atraso,
                'esta_vencida': venda.esta_vencida,
                'eh_restante': venda.eh_restante,
                'status': venda.status,
                'itens_count': venda.itens.count(),
                'descricao_resumo': ', '.join([
                    item.descricao for item in venda.itens.limit(2)
                ]) + ('...' if venda.itens.count() > 2 else '')
            })
        
        return jsonify({
            'vendas': resultado,
            'total_vendas': len(resultado),
            'valor_total': sum(v['valor_restante'] for v in resultado)
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 404


# Endpoints de Vendas

@api_bp.route('/vendas/calcular-total', methods=['POST'])
@login_required
def vendas_calcular_total():
    """Calcular total da venda baseado nos itens"""
    
    try:
        data = request.json
        itens = data.get('itens', [])
        
        total = Decimal('0.00')
        itens_processados = []
        
        for item in itens:
            descricao = item.get('descricao', '').strip()
            if not descricao:
                continue
                
            quantidade = parse_currency(str(item.get('quantidade', 0)))
            valor_unitario = parse_currency(str(item.get('valor_unitario', 0)))
            subtotal = quantidade * valor_unitario
            
            total += subtotal
            
            itens_processados.append({
                'descricao': descricao,
                'quantidade': float(quantidade),
                'valor_unitario': float(valor_unitario),
                'subtotal': float(subtotal),
                'subtotal_formatado': format_currency(subtotal)
            })
        
        return jsonify({
            'success': True,
            'itens': itens_processados,
            'total': float(total),
            'total_formatado': format_currency(total),
            'subtotal': float(total),
            'subtotal_formatado': format_currency(total)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@api_bp.route('/vendas/verificar-limite/<int:cliente_id>/<valor>')
@login_required
def vendas_verificar_limite(cliente_id, valor):
    """Verificar se valor da venda está dentro do limite do cliente"""
    
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
            'valor_em_aberto': float(cliente.valor_total_em_aberto),
            'percentual_usado': float(cliente.valor_total_em_aberto / cliente.limite_credito * 100) if cliente.limite_credito > 0 else 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404


@api_bp.route('/vendas/<int:id>/status')
@login_required
def venda_status(id):
    """Obter status atual da venda"""
    
    try:
        venda = Venda.query.get_or_404(id)
        
        return jsonify({
            'id': venda.id,
            'status': venda.status,
            'status_display': venda.status_display,
            'total': float(venda.total),
            'valor_pago': float(venda.valor_pago),
            'valor_restante': float(venda.valor_restante),
            'esta_paga': venda.esta_paga,
            'esta_vencida': venda.esta_vencida,
            'dias_atraso': venda.dias_atraso,
            'data_pagamento': venda.data_pagamento.isoformat() if venda.data_pagamento else None,
            'pagamentos_count': venda.pagamentos.count()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 404


# Endpoints de Pagamentos

@api_bp.route('/pagamentos/simular-multiplo', methods=['POST'])
@login_required
def pagamentos_simular_multiplo():
    """Simular distribuição de pagamento múltiplo"""
    
    try:
        data = request.json
        vendas_ids = data.get('vendas_ids', [])
        valor_pago = parse_currency(str(data.get('valor_pago', 0)))
        
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
        
        if len(vendas) != len(vendas_ids):
            return jsonify({
                'success': False,
                'error': 'Uma ou mais vendas são inválidas'
            }), 400
        
        valor_total_vendas = sum(v.valor_restante for v in vendas)
        
        # Simular distribuição proporcional
        distribuicao = []
        valor_restante_distribuir = valor_pago
        
        for venda in vendas:
            if valor_restante_distribuir <= 0:
                valor_para_venda = Decimal('0')
            else:
                # Calcular proporção desta venda no total
                proporcao = venda.valor_restante / valor_total_vendas
                valor_para_venda = valor_pago * proporcao
                
                # Limitar ao valor restante da venda e ao valor ainda disponível
                valor_para_venda = min(
                    valor_para_venda,
                    venda.valor_restante,
                    valor_restante_distribuir
                )
                
                # Arredondar para 2 casas decimais
                valor_para_venda = valor_para_venda.quantize(Decimal('0.01'))
                valor_restante_distribuir -= valor_para_venda
            
            nova_situacao_venda = venda.valor_restante - valor_para_venda
            
            distribuicao.append({
                'venda_id': venda.id,
                'data_venda': venda.data_venda.strftime('%d/%m/%Y'),
                'valor_original': float(venda.valor_restante),
                'valor_pago': float(valor_para_venda),
                'valor_restante_apos': float(nova_situacao_venda),
                'percentual_pago': float((valor_para_venda / venda.valor_restante * 100)) if venda.valor_restante > 0 else 0,
                'sera_quitada': nova_situacao_venda <= 0.01,  # Considerar quitada se restar menos de 1 centavo
                'esta_vencida': venda.esta_vencida
            })
        
        valor_restante_total = valor_total_vendas - valor_pago
        gera_restante = valor_restante_total > 0.01
        
        return jsonify({
            'success': True,
            'distribuicao': distribuicao,
            'resumo': {
                'valor_total_vendas': float(valor_total_vendas),
                'valor_pago': float(valor_pago),
                'valor_restante': float(max(valor_restante_total, 0)),
                'gera_restante': gera_restante,
                'vendas_quitadas': sum(1 for d in distribuicao if d['sera_quitada']),
                'total_vendas': len(distribuicao)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# Endpoints de Dashboard

@api_bp.route('/dashboard/stats')
@login_required
def dashboard_stats():
    """Estatísticas atualizadas do dashboard"""
    
    try:
        hoje = date.today()
        inicio_mes = hoje.replace(day=1)
        
        stats = {
            'vendas_hoje': Venda.query.filter(Venda.data_venda == hoje).count(),
            'vendas_mes': Venda.query.filter(Venda.data_venda >= inicio_mes).count(),
            'clientes_ativos': Cliente.query.filter(Cliente.ativo == True).count(),
            'vendas_abertas': Venda.query.filter(Venda.status == STATUS_VENDA['ABERTA']).count(),
            'vendas_vencidas': Venda.vendas_vencidas().count(),
            'valor_aberto': float(db.session.query(
                func.sum(Venda.total)
            ).filter(Venda.status == STATUS_VENDA['ABERTA']).scalar() or 0),
            'valor_recebido_hoje': float(db.session.query(
                func.sum(Pagamento.valor)
            ).filter(Pagamento.data_pagamento == hoje).scalar() or 0)
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@api_bp.route('/dashboard/alertas')
@login_required
def dashboard_alertas():
    """Alertas atualizados do dashboard"""
    
    try:
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
        
        return jsonify(alertas)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


# Endpoints Utilitários

@api_bp.route('/utils/format-currency/<valor>')
@login_required
def utils_format_currency(valor):
    """Formatar valor monetário"""
    
    try:
        valor_decimal = parse_currency(valor)
        return jsonify({
            'valor_original': valor,
            'valor_decimal': float(valor_decimal),
            'valor_formatado': format_currency(valor_decimal)
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400


@api_bp.route('/utils/validate-cpf/<cpf>')
@login_required
def utils_validate_cpf(cpf):
    """Validar CPF"""
    
    try:
        from app.utils.helpers import validate_cpf
        
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        is_valid = validate_cpf(cpf_limpo) if cpf_limpo else False
        
        return jsonify({
            'cpf_original': cpf,
            'cpf_limpo': cpf_limpo,
            'is_valid': is_valid
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400


# Endpoint de busca global

@api_bp.route('/busca-global')
@login_required
def busca_global():
    """Busca global no sistema"""
    
    termo = request.args.get('q', '').strip()
    limite = int(request.args.get('limit', 20))
    
    if not termo or len(termo) < 2:
        return jsonify({
            'results': [],
            'total': 0
        })
    
    try:
        resultados = []
        
        # Buscar clientes
        clientes = Cliente.buscar(termo, apenas_ativos=True).limit(limite // 2).all()
        for cliente in clientes:
            resultados.append({
                'tipo': 'cliente',
                'id': cliente.id,
                'titulo': cliente.nome,
                'subtitulo': cliente.cpf or cliente.telefone or '',
                'descricao': f'Crédito disponível: {format_currency(cliente.credito_disponivel)}',
                'url': f'/clientes/{cliente.id}',
                'icone': 'fas fa-user',
                'status': 'ativo' if cliente.ativo else 'inativo'
            })
        
        # Buscar vendas (por ID se for numérico)
        if termo.isdigit():
            venda = Venda.query.get(int(termo))
            if venda:
                resultados.append({
                    'tipo': 'venda',
                    'id': venda.id,
                    'titulo': f'Venda #{venda.id}',
                    'subtitulo': venda.cliente.nome,
                    'descricao': f'{format_currency(venda.total)} - {venda.status_display}',
                    'url': f'/vendas/{venda.id}',
                    'icone': 'fas fa-shopping-cart',
                    'status': venda.status
                })
        
        return jsonify({
            'results': resultados,
            'total': len(resultados),
            'termo': termo
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


# Middleware para CORS (se necessário)
@api_bp.after_request
def after_request(response):
    """Adicionar headers CORS se necessário"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response