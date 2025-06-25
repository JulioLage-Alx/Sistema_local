"""
Script para inserir dados iniciais no banco de dados
Usado para desenvolvimento e testes
"""

import sys
import os
from datetime import date, timedelta
from decimal import Decimal

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import (
    Cliente, Venda, ItemVenda, Pagamento, 
    PagamentoMultiplo, PagamentoMultiploDetalhe
)


def create_clientes():
    """Criar clientes de exemplo"""
    clientes_data = [
        {
            'nome': 'João Silva Santos',
            'cpf': '123.456.789-01',
            'telefone': '(31) 99999-1234',
            'endereco': 'Rua das Flores, 123 - Centro',
            'limite_credito': Decimal('1000.00'),
            'observacoes': 'Cliente antigo, sempre paga em dia'
        },
        {
            'nome': 'Maria Oliveira Costa',
            'cpf': '987.654.321-00',
            'telefone': '(31) 88888-5678',
            'endereco': 'Av. Brasil, 456 - Savassi',
            'limite_credito': Decimal('800.00'),
            'observacoes': 'Prefere carne de primeira'
        },
        {
            'nome': 'Pedro Souza Lima',
            'cpf': '456.789.123-45',
            'telefone': '(31) 77777-9012',
            'endereco': 'Rua do Açougue, 789 - Bairro Novo',
            'limite_credito': Decimal('500.00'),
            'observacoes': None
        },
        {
            'nome': 'Ana Carolina Ferreira',
            'cpf': '321.654.987-89',
            'telefone': '(31) 66666-3456',
            'endereco': 'Rua das Palmeiras, 321 - Vila Rica',
            'limite_credito': Decimal('1200.00'),
            'observacoes': 'Compra sempre aos sábados'
        },
        {
            'nome': 'Carlos Eduardo Alves',
            'cpf': None,  # Cliente sem CPF
            'telefone': '(31) 55555-7890',
            'endereco': 'Rua do Comércio, 654',
            'limite_credito': Decimal('300.00'),
            'observacoes': 'Cliente eventual'
        },
        {
            'nome': 'Fernanda Santos Ribeiro',
            'cpf': '789.123.456-78',
            'telefone': '(31) 44444-2345',
            'endereco': 'Av. dos Estados, 987 - Centro',
            'limite_credito': Decimal('700.00'),
            'observacoes': 'Gosta de linguiça artesanal'
        }
    ]
    
    clientes = []
    for data in clientes_data:
        cliente = Cliente(**data)
        db.session.add(cliente)
        clientes.append(cliente)
    
    db.session.commit()
    print(f"✓ {len(clientes)} clientes criados")
    return clientes


def create_vendas_abertas(clientes):
    """Criar vendas em aberto para testes"""
    vendas_data = [
        {
            'cliente': clientes[0],  # João Silva
            'data_venda': date.today() - timedelta(days=15),
            'itens': [
                {'descricao': 'Picanha', 'quantidade': 1.5, 'valor_unitario': 45.00},
                {'descricao': 'Linguiça Toscana', 'quantidade': 1.0, 'valor_unitario': 18.00}
            ]
        },
        {
            'cliente': clientes[1],  # Maria Oliveira
            'data_venda': date.today() - timedelta(days=10),
            'itens': [
                {'descricao': 'Carne Moída', 'quantidade': 2.0, 'valor_unitario': 12.00},
                {'descricao': 'Coxa de Frango', 'quantidade': 1.8, 'valor_unitario': 8.50}
            ]
        },
        {
            'cliente': clientes[2],  # Pedro Souza
            'data_venda': date.today() - timedelta(days=25),
            'itens': [
                {'descricao': 'Costela', 'quantidade': 2.5, 'valor_unitario': 22.00}
            ]
        },
        {
            'cliente': clientes[3],  # Ana Carolina
            'data_venda': date.today() - timedelta(days=5),
            'itens': [
                {'descricao': 'Alcatra', 'quantidade': 1.2, 'valor_unitario': 38.00},
                {'descricao': 'Frango Inteiro', 'quantidade': 2.0, 'valor_unitario': 15.00},
                {'descricao': 'Bacon', 'quantidade': 0.5, 'valor_unitario': 24.00}
            ]
        },
        {
            'cliente': clientes[4],  # Carlos Eduardo
            'data_venda': date.today() - timedelta(days=35),  # Vencida
            'itens': [
                {'descricao': 'Carne de Sol', 'quantidade': 1.0, 'valor_unitario': 32.00}
            ]
        }
    ]
    
    vendas = []
    for venda_data in vendas_data:
        venda = Venda(
            cliente_id=venda_data['cliente'].id,
            data_venda=venda_data['data_venda']
        )
        venda.gerar_data_vencimento()
        
        db.session.add(venda)
        db.session.flush()  # Para obter o ID
        
        # Adicionar itens
        for item_data in venda_data['itens']:
            item = ItemVenda(
                venda_id=venda.id,
                descricao=item_data['descricao'],
                quantidade=Decimal(str(item_data['quantidade'])),
                valor_unitario=Decimal(str(item_data['valor_unitario']))
            )
            item.calcular_subtotal()
            db.session.add(item)
        
        vendas.append(venda)
    
    db.session.commit()
    
    # Recalcular totais
    for venda in vendas:
        venda.calcular_totais()
        venda.atualizar_status()
    
    db.session.commit()
    print(f"✓ {len(vendas)} vendas em aberto criadas")
    return vendas


def create_vendas_pagas(clientes):
    """Criar vendas já pagas para histórico"""
    vendas_pagas_data = [
        {
            'cliente': clientes[0],  # João Silva
            'data_venda': date.today() - timedelta(days=45),
            'data_pagamento': date.today() - timedelta(days=40),
            'forma_pagamento': 'dinheiro',
            'itens': [
                {'descricao': 'Contrafilé', 'quantidade': 1.8, 'valor_unitario': 42.00}
            ]
        },
        {
            'cliente': clientes[1],  # Maria Oliveira
            'data_venda': date.today() - timedelta(days=60),
            'data_pagamento': date.today() - timedelta(days=55),
            'forma_pagamento': 'pix',
            'itens': [
                {'descricao': 'Filé Mignon', 'quantidade': 0.8, 'valor_unitario': 65.00},
                {'descricao': 'Salmão', 'quantidade': 0.5, 'valor_unitario': 55.00}
            ]
        },
        {
            'cliente': clientes[3],  # Ana Carolina
            'data_venda': date.today() - timedelta(days=30),
            'data_pagamento': date.today() - timedelta(days=25),
            'forma_pagamento': 'cartao',
            'itens': [
                {'descricao': 'Maminha', 'quantidade': 2.0, 'valor_unitario': 28.00},
                {'descricao': 'Linguiça Calabresa', 'quantidade': 1.5, 'valor_unitario': 16.00}
            ]
        }
    ]
    
    vendas = []
    for venda_data in vendas_pagas_data:
        venda = Venda(
            cliente_id=venda_data['cliente'].id,
            data_venda=venda_data['data_venda'],
            status='paga',
            data_pagamento=venda_data['data_pagamento']
        )
        venda.gerar_data_vencimento()
        
        db.session.add(venda)
        db.session.flush()
        
        # Adicionar itens
        for item_data in venda_data['itens']:
            item = ItemVenda(
                venda_id=venda.id,
                descricao=item_data['descricao'],
                quantidade=Decimal(str(item_data['quantidade'])),
                valor_unitario=Decimal(str(item_data['valor_unitario']))
            )
            item.calcular_subtotal()
            db.session.add(item)
        
        db.session.flush()
        venda.calcular_totais()
        
        # Criar pagamento
        pagamento = Pagamento(
            venda_id=venda.id,
            valor=venda.total,
            forma_pagamento=venda_data['forma_pagamento'],
            data_pagamento=venda_data['data_pagamento']
        )
        
        # Se for dinheiro, simular troco
        if venda_data['forma_pagamento'] == 'dinheiro':
            valor_recebido = venda.total + Decimal('5.00')  # Cliente deu um pouco a mais
            pagamento.valor_recebido = valor_recebido
            pagamento.calcular_troco()
        
        db.session.add(pagamento)
        vendas.append(venda)
    
    db.session.commit()
    print(f"✓ {len(vendas)} vendas pagas criadas")
    return vendas


def create_pagamento_multiplo_exemplo(clientes):
    """Criar exemplo de pagamento múltiplo com restante"""
    # Criar 3 vendas para o mesmo cliente
    cliente = clientes[0]  # João Silva
    vendas = []
    
    vendas_data = [
        {
            'data_venda': date.today() - timedelta(days=20),
            'itens': [
                {'descricao': 'Carne Moída', 'quantidade': 1.0, 'valor_unitario': 15.00}
            ]
        },
        {
            'data_venda': date.today() - timedelta(days=18),
            'itens': [
                {'descricao': 'Frango à Passarinho', 'quantidade': 1.5, 'valor_unitario': 20.00}
            ]
        },
        {
            'data_venda': date.today() - timedelta(days=16),
            'itens': [
                {'descricao': 'Linguiça Artesanal', 'quantidade': 1.0, 'valor_unitario': 25.00}
            ]
        }
    ]
    
    # Criar as vendas
    for venda_data in vendas_data:
        venda = Venda(
            cliente_id=cliente.id,
            data_venda=venda_data['data_venda']
        )
        venda.gerar_data_vencimento()
        
        db.session.add(venda)
        db.session.flush()
        
        # Adicionar itens
        for item_data in venda_data['itens']:
            item = ItemVenda(
                venda_id=venda.id,
                descricao=item_data['descricao'],
                quantidade=Decimal(str(item_data['quantidade'])),
                valor_unitario=Decimal(str(item_data['valor_unitario']))
            )
            item.calcular_subtotal()
            db.session.add(item)
        
        db.session.flush()
        venda.calcular_totais()
        vendas.append(venda)
    
    db.session.commit()
    
    # Calcular total das vendas: 15 + 30 + 25 = 70
    total_vendas = sum(v.total for v in vendas)
    valor_pago = Decimal('50.00')  # Cliente pagou apenas 50, restante: 20
    
    # Criar pagamento múltiplo
    pagamento_multiplo = PagamentoMultiplo(
        cliente_id=cliente.id,
        valor_total_notas=total_vendas,
        valor_pago=valor_pago,
        forma_pagamento='dinheiro',
        valor_recebido=Decimal('50.00'),
        data_pagamento=date.today() - timedelta(days=5)
    )
    
    db.session.add(pagamento_multiplo)
    db.session.flush()
    
    # Adicionar detalhes (distribuir proporcionalmente)
    for venda in vendas:
        proporcao = venda.total / total_vendas
        valor_pago_venda = (valor_pago * proporcao).quantize(Decimal('0.01'))
        
        detalhe = PagamentoMultiploDetalhe(
            pagamento_multiplo_id=pagamento_multiplo.id,
            venda_id=venda.id,
            valor_original=venda.total,
            valor_pago=valor_pago_venda
        )
        db.session.add(detalhe)
        
        # Criar pagamento individual para cada venda
        pagamento = Pagamento(
            venda_id=venda.id,
            valor=valor_pago_venda,
            forma_pagamento='dinheiro',
            data_pagamento=pagamento_multiplo.data_pagamento,
            observacoes=f"Pagamento múltiplo #{pagamento_multiplo.id}"
        )
        db.session.add(pagamento)
    
    db.session.commit()
    
    # Processar o pagamento múltiplo (criar nota de restante)
    venda_restante = pagamento_multiplo.processar_pagamento()
    
    db.session.commit()
    
    print(f"✓ Pagamento múltiplo criado (R$ {valor_pago} de R$ {total_vendas})")
    if venda_restante:
        print(f"✓ Nota de restante criada: #{venda_restante.id} - R$ {venda_restante.total}")
    
    return pagamento_multiplo


def run_seeders():
    """Executar todos os seeders"""
    print("Iniciando inserção de dados de exemplo...")
    print("=" * 50)
    
    try:
        # Criar clientes
        clientes = create_clientes()
        
        # Criar vendas em aberto
        vendas_abertas = create_vendas_abertas(clientes)
        
        # Criar vendas pagas
        vendas_pagas = create_vendas_pagas(clientes)
        
        # Criar exemplo de pagamento múltiplo
        pagamento_multiplo = create_pagamento_multiplo_exemplo(clientes)
        
        print("=" * 50)
        print("✅ Dados de exemplo inseridos com sucesso!")
        print("\nResumo:")
        print(f"• {len(clientes)} clientes")
        print(f"• {len(vendas_abertas)} vendas em aberto")  
        print(f"• {len(vendas_pagas)} vendas pagas")
        print(f"• 1 pagamento múltiplo com restante")
        
    except Exception as e:
        print(f"❌ Erro ao inserir dados: {e}")
        db.session.rollback()
        raise


if __name__ == '__main__':
    # Criar aplicação para executar os seeders
    app = create_app('development')
    
    with app.app_context():
        run_seeders()