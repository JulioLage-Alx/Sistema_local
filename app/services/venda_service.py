"""
VendaService - Lógica de negócio para gestão de vendas
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from sqlalchemy import func, or_, and_, desc, asc
from sqlalchemy.orm import joinedload

from app import db
from app.models import Cliente, Venda, ItemVenda, Pagamento
from app.utils.constants import (
    STATUS_VENDA, DIAS_VENCIMENTO_PADRAO, VALOR_MINIMO_VENDA,
    ITEMS_PER_PAGE
)
from app.utils.helpers import parse_currency, format_currency


class VendaService:
    """Service para operações com vendas"""
    
    def __init__(self):
        self.db = db
    
    def criar_venda(self, cliente_id: int, itens: List[Dict], observacoes: str = None) -> Tuple[bool, str, Optional[Venda]]:
        """
        Criar nova venda
        
        Args:
            cliente_id: ID do cliente
            itens: Lista de itens [{'descricao': str, 'quantidade': float, 'valor_unitario': float}]
            observacoes: Observações da venda
            
        Returns:
            Tuple[sucesso, mensagem, venda]
        """
        try:
            # Validar cliente
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                return False, "Cliente não encontrado", None
            
            if not cliente.ativo:
                return False, "Cliente inativo", None
            
            # Validar itens
            if not itens or len(itens) == 0:
                return False, "Adicione pelo menos um item à venda", None
            
            # Criar venda
            venda = Venda(
                cliente_id=cliente_id,
                observacoes=observacoes
            )
            
            # Gerar data de vencimento
            venda.gerar_data_vencimento()
            
            # Adicionar itens
            total_venda = Decimal('0.00')
            for item_data in itens:
                try:
                    descricao = item_data.get('descricao', '').strip()
                    quantidade = Decimal(str(item_data.get('quantidade', 0)))
                    valor_unitario = Decimal(str(item_data.get('valor_unitario', 0)))
                    
                    # Validações do item
                    if not descricao:
                        return False, "Descrição do item é obrigatória", None
                    
                    if quantidade <= 0:
                        return False, "Quantidade deve ser maior que zero", None
                    
                    if valor_unitario <= 0:
                        return False, "Valor unitário deve ser maior que zero", None
                    
                    # Criar item
                    item = ItemVenda(
                        descricao=descricao,
                        quantidade=quantidade,
                        valor_unitario=valor_unitario
                    )
                    item.calcular_subtotal()
                    
                    venda.itens.append(item)
                    total_venda += item.subtotal
                    
                except (ValueError, TypeError) as e:
                    return False, f"Erro nos dados do item: {str(e)}", None
            
            # Validar valor mínimo
            if total_venda < VALOR_MINIMO_VENDA:
                return False, f"Valor mínimo da venda: R$ {VALOR_MINIMO_VENDA:.2f}", None
            
            # Calcular totais da venda
            venda.calcular_totais()
            
            # Verificar limite de crédito
            if not cliente.verificar_limite_credito(venda.total):
                credito_disponivel = cliente.credito_disponivel
                return False, f"Limite de crédito insuficiente. Disponível: R$ {credito_disponivel:.2f}", None
            
            # Salvar venda
            self.db.session.add(venda)
            self.db.session.commit()
            
            return True, f"Venda #{venda.id} criada com sucesso!", venda
            
        except Exception as e:
            self.db.session.rollback()
            return False, f"Erro ao criar venda: {str(e)}", None
    
    def atualizar_venda(self, venda_id: int, dados: Dict) -> Tuple[bool, str, Optional[Venda]]:
        """
        Atualizar venda existente
        
        Args:
            venda_id: ID da venda
            dados: Dados para atualização
            
        Returns:
            Tuple[sucesso, mensagem, venda]
        """
        try:
            venda = Venda.query.get(venda_id)
            if not venda:
                return False, "Venda não encontrada", None
            
            # Verificar se pode editar
            if venda.status != STATUS_VENDA['ABERTA']:
                return False, "Apenas vendas em aberto podem ser editadas", None
            
            if venda.eh_restante:
                return False, "Vendas de restante não podem ser editadas", None
            
            # Atualizar campos permitidos
            if 'observacoes' in dados:
                venda.observacoes = dados['observacoes']
            
            if 'data_vencimento' in dados:
                try:
                    nova_data = datetime.strptime(dados['data_vencimento'], '%Y-%m-%d').date()
                    if nova_data < date.today():
                        return False, "Data de vencimento não pode ser no passado", None
                    venda.data_vencimento = nova_data
                except ValueError:
                    return False, "Data de vencimento inválida", None
            
            # Atualizar itens se fornecidos
            if 'itens' in dados:
                # Remover itens existentes
                ItemVenda.query.filter_by(venda_id=venda.id).delete()
                
                # Adicionar novos itens
                for item_data in dados['itens']:
                    descricao = item_data.get('descricao', '').strip()
                    quantidade = Decimal(str(item_data.get('quantidade', 0)))
                    valor_unitario = Decimal(str(item_data.get('valor_unitario', 0)))
                    
                    if not descricao or quantidade <= 0 or valor_unitario <= 0:
                        continue
                    
                    item = ItemVenda(
                        venda_id=venda.id,
                        descricao=descricao,
                        quantidade=quantidade,
                        valor_unitario=valor_unitario
                    )
                    item.calcular_subtotal()
                    self.db.session.add(item)
                
                # Recalcular totais
                venda.calcular_totais()
                
                # Verificar limite de crédito novamente
                if not venda.cliente.verificar_limite_credito(venda.total):
                    self.db.session.rollback()
                    credito_disponivel = venda.cliente.credito_disponivel
                    return False, f"Limite de crédito insuficiente. Disponível: R$ {credito_disponivel:.2f}", None
            
            self.db.session.commit()
            return True, "Venda atualizada com sucesso!", venda
            
        except Exception as e:
            self.db.session.rollback()
            return False, f"Erro ao atualizar venda: {str(e)}", None
    
    def excluir_venda(self, venda_id: int) -> Tuple[bool, str]:
        """
        Excluir venda
        
        Args:
            venda_id: ID da venda
            
        Returns:
            Tuple[sucesso, mensagem]
        """
        try:
            venda = Venda.query.get(venda_id)
            if not venda:
                return False, "Venda não encontrada"
            
            # Verificar se pode excluir
            if venda.status != STATUS_VENDA['ABERTA']:
                return False, "Apenas vendas em aberto podem ser excluídas"
            
            if venda.eh_restante:
                return False, "Vendas de restante não podem ser excluídas"
            
            # Verificar se tem pagamentos
            if venda.pagamentos.count() > 0:
                return False, "Não é possível excluir venda que possui pagamentos"
            
            venda_id_str = venda.id
            cliente_nome = venda.cliente.nome
            
            # Excluir venda (cascade vai excluir os itens)
            self.db.session.delete(venda)
            self.db.session.commit()
            
            return True, f"Venda #{venda_id_str} de {cliente_nome} excluída com sucesso!"
            
        except Exception as e:
            self.db.session.rollback()
            return False, f"Erro ao excluir venda: {str(e)}"
    
    def obter_venda(self, venda_id: int, incluir_relacionamentos: bool = True) -> Optional[Venda]:
        """
        Obter venda por ID
        
        Args:
            venda_id: ID da venda
            incluir_relacionamentos: Se deve incluir cliente, itens e pagamentos
            
        Returns:
            Venda ou None
        """
        query = Venda.query
        
        if incluir_relacionamentos:
            query = query.options(
                joinedload(Venda.cliente),
                joinedload(Venda.itens),
                joinedload(Venda.pagamentos)
            )
        
        return query.get(venda_id)
    
    def listar_vendas(self, filtros: Dict = None, page: int = 1, per_page: int = ITEMS_PER_PAGE) -> Dict:
        """
        Listar vendas com filtros e paginação
        
        Args:
            filtros: Dicionário com filtros
            page: Página atual
            per_page: Itens por página
            
        Returns:
            Dict com resultados paginados e estatísticas
        """
        try:
            # Query base
            query = Venda.query.options(
                joinedload(Venda.cliente),
                joinedload(Venda.itens)
            )
            
            # Aplicar filtros
            if filtros:
                # Filtro por cliente
                if filtros.get('cliente_id'):
                    query = query.filter(Venda.cliente_id == filtros['cliente_id'])
                
                # Filtro por status
                status = filtros.get('status')
                if status and status != 'todas':
                    if status == 'abertas':
                        query = query.filter(Venda.status == STATUS_VENDA['ABERTA'])
                    elif status == 'pagas':
                        query = query.filter(Venda.status == STATUS_VENDA['PAGA'])
                    elif status == 'vencidas':
                        query = query.filter(
                            and_(
                                Venda.status == STATUS_VENDA['ABERTA'],
                                Venda.data_vencimento < date.today()
                            )
                        )
                    elif status == 'restantes':
                        query = query.filter(Venda.eh_restante == True)
                
                # Filtro por data
                if filtros.get('data_inicio'):
                    try:
                        data_inicio = datetime.strptime(filtros['data_inicio'], '%Y-%m-%d').date()
                        query = query.filter(Venda.data_venda >= data_inicio)
                    except ValueError:
                        pass
                
                if filtros.get('data_fim'):
                    try:
                        data_fim = datetime.strptime(filtros['data_fim'], '%Y-%m-%d').date()
                        query = query.filter(Venda.data_venda <= data_fim)
                    except ValueError:
                        pass
                
                # Filtro por valor
                if filtros.get('valor_min'):
                    try:
                        valor_min = Decimal(str(filtros['valor_min']))
                        query = query.filter(Venda.total >= valor_min)
                    except (ValueError, TypeError):
                        pass
                
                if filtros.get('valor_max'):
                    try:
                        valor_max = Decimal(str(filtros['valor_max']))
                        query = query.filter(Venda.total <= valor_max)
                    except (ValueError, TypeError):
                        pass
            
            # Ordenação
            ordenacao = filtros.get('ordenacao', 'data_desc') if filtros else 'data_desc'
            
            if ordenacao == 'data_asc':
                query = query.order_by(asc(Venda.data_venda))
            elif ordenacao == 'data_desc':
                query = query.order_by(desc(Venda.data_venda))
            elif ordenacao == 'valor_asc':
                query = query.order_by(asc(Venda.total))
            elif ordenacao == 'valor_desc':
                query = query.order_by(desc(Venda.total))
            elif ordenacao == 'cliente':
                query = query.join(Cliente).order_by(asc(Cliente.nome))
            elif ordenacao == 'vencimento':
                query = query.order_by(asc(Venda.data_vencimento))
            else:
                query = query.order_by(desc(Venda.data_criacao))
            
            # Paginação
            pagination = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            # Estatísticas
            stats = self.calcular_estatisticas_vendas(filtros)
            
            return {
                'vendas': pagination.items,
                'pagination': pagination,
                'stats': stats,
                'total': pagination.total
            }
            
        except Exception as e:
            return {
                'vendas': [],
                'pagination': None,
                'stats': {},
                'total': 0,
                'error': str(e)
            }
    
    def buscar_vendas(self, termo: str, page: int = 1, per_page: int = ITEMS_PER_PAGE) -> Dict:
        """
        Buscar vendas por termo
        
        Args:
            termo: Termo de busca
            page: Página atual
            per_page: Itens por página
            
        Returns:
            Dict com resultados paginados
        """
        if not termo or len(termo.strip()) < 2:
            return self.listar_vendas(page=page, per_page=per_page)
        
        termo = termo.strip()
        
        # Query com busca
        query = Venda.query.options(
            joinedload(Venda.cliente),
            joinedload(Venda.itens)
        ).join(Cliente)
        
        # Buscar por ID da venda, nome do cliente ou observações
        try:
            # Tentar buscar por ID da venda
            venda_id = int(termo)
            query = query.filter(Venda.id == venda_id)
        except ValueError:
            # Buscar por texto
            query = query.filter(
                or_(
                    Cliente.nome.ilike(f'%{termo}%'),
                    Venda.observacoes.ilike(f'%{termo}%'),
                    ItemVenda.descricao.ilike(f'%{termo}%')
                )
            ).join(ItemVenda, isouter=True)
        
        query = query.order_by(desc(Venda.data_criacao))
        
        # Paginação
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return {
            'vendas': pagination.items,
            'pagination': pagination,
            'total': pagination.total,
            'termo_busca': termo
        }
    
    def calcular_estatisticas_vendas(self, filtros: Dict = None) -> Dict:
        """
        Calcular estatísticas das vendas
        
        Args:
            filtros: Filtros aplicados (opcional)
            
        Returns:
            Dict com estatísticas
        """
        try:
            # Query base para estatísticas
            base_query = Venda.query
            
            # Aplicar mesmos filtros da listagem
            if filtros:
                if filtros.get('cliente_id'):
                    base_query = base_query.filter(Venda.cliente_id == filtros['cliente_id'])
                
                if filtros.get('data_inicio'):
                    try:
                        data_inicio = datetime.strptime(filtros['data_inicio'], '%Y-%m-%d').date()
                        base_query = base_query.filter(Venda.data_venda >= data_inicio)
                    except ValueError:
                        pass
                
                if filtros.get('data_fim'):
                    try:
                        data_fim = datetime.strptime(filtros['data_fim'], '%Y-%m-%d').date()
                        base_query = base_query.filter(Venda.data_venda <= data_fim)
                    except ValueError:
                        pass
            
            # Total de vendas
            total_vendas = base_query.count()
            
            # Vendas em aberto
            vendas_abertas = base_query.filter(
                Venda.status == STATUS_VENDA['ABERTA']
            ).count()
            
            # Vendas pagas
            vendas_pagas = base_query.filter(
                Venda.status == STATUS_VENDA['PAGA']
            ).count()
            
            # Vendas vencidas
            vendas_vencidas = base_query.filter(
                and_(
                    Venda.status == STATUS_VENDA['ABERTA'],
                    Venda.data_vencimento < date.today()
                )
            ).count()
            
            # Valor total em aberto
            valor_total_aberto = base_query.filter(
                Venda.status == STATUS_VENDA['ABERTA']
            ).with_entities(func.sum(Venda.total)).scalar() or 0
            
            # Valor total vendido
            valor_total_vendido = base_query.with_entities(
                func.sum(Venda.total)
            ).scalar() or 0
            
            # Ticket médio
            ticket_medio = (valor_total_vendido / total_vendas) if total_vendas > 0 else 0
            
            return {
                'total_vendas': total_vendas,
                'vendas_abertas': vendas_abertas,
                'vendas_pagas': vendas_pagas,
                'vendas_vencidas': vendas_vencidas,
                'valor_total_aberto': float(valor_total_aberto),
                'valor_total_vendido': float(valor_total_vendido),
                'ticket_medio': float(ticket_medio),
                'percentual_abertas': (vendas_abertas / total_vendas * 100) if total_vendas > 0 else 0,
                'percentual_vencidas': (vendas_vencidas / total_vendas * 100) if total_vendas > 0 else 0
            }
            
        except Exception as e:
            return {
                'total_vendas': 0,
                'vendas_abertas': 0,
                'vendas_pagas': 0,
                'vendas_vencidas': 0,
                'valor_total_aberto': 0,
                'valor_total_vendido': 0,
                'ticket_medio': 0,
                'percentual_abertas': 0,
                'percentual_vencidas': 0,
                'error': str(e)
            }
    
    def obter_vendas_vencidas(self, dias_vencimento: int = 30) -> List[Venda]:
        """
        Obter vendas vencidas há mais de X dias
        
        Args:
            dias_vencimento: Número de dias para considerar vencida
            
        Returns:
            Lista de vendas vencidas
        """
        data_limite = date.today() - timedelta(days=dias_vencimento)
        
        return Venda.query.options(
            joinedload(Venda.cliente)
        ).filter(
            and_(
                Venda.status == STATUS_VENDA['ABERTA'],
                Venda.data_vencimento <= data_limite
            )
        ).order_by(asc(Venda.data_vencimento)).all()
    
    def marcar_vendas_vencidas(self) -> int:
        """
        Marcar vendas como vencidas (executar diariamente)
        
        Returns:
            Número de vendas marcadas como vencidas
        """
        try:
            vendas_para_vencer = Venda.query.filter(
                and_(
                    Venda.status == STATUS_VENDA['ABERTA'],
                    Venda.data_vencimento < date.today()
                )
            ).all()
            
            contador = 0
            for venda in vendas_para_vencer:
                # Não alterar o status, apenas marcar como vencida
                # O status continua 'aberta' mas a propriedade esta_vencida retorna True
                contador += 1
            
            self.db.session.commit()
            return contador
            
        except Exception as e:
            self.db.session.rollback()
            return 0
    
    def verificar_limite_cliente(self, cliente_id: int, valor_venda: float) -> Tuple[bool, str, Dict]:
        """
        Verificar se cliente pode fazer uma venda de determinado valor
        
        Args:
            cliente_id: ID do cliente
            valor_venda: Valor da venda
            
        Returns:
            Tuple[pode_comprar, mensagem, dados_cliente]
        """
        try:
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                return False, "Cliente não encontrado", {}
            
            if not cliente.ativo:
                return False, "Cliente inativo", {}
            
            valor_decimal = Decimal(str(valor_venda))
            pode_comprar = cliente.verificar_limite_credito(valor_decimal)
            
            dados_cliente = {
                'nome': cliente.nome,
                'limite_credito': float(cliente.limite_credito),
                'valor_em_aberto': float(cliente.valor_total_em_aberto),
                'credito_disponivel': float(cliente.credito_disponivel),
                'esta_inadimplente': cliente.esta_inadimplente
            }
            
            if not pode_comprar:
                mensagem = f"Limite de crédito insuficiente. Disponível: R$ {cliente.credito_disponivel:.2f}"
                return False, mensagem, dados_cliente
            
            return True, "Cliente pode realizar a compra", dados_cliente
            
        except Exception as e:
            return False, f"Erro ao verificar limite: {str(e)}", {}
    
    def calcular_totais_itens(self, itens: List[Dict]) -> Dict:
        """
        Calcular totais de uma lista de itens
        
        Args:
            itens: Lista de itens com quantidade e valor_unitario
            
        Returns:
            Dict com subtotais e total
        """
        try:
            total = Decimal('0.00')
            itens_calculados = []
            
            for item in itens:
                quantidade = Decimal(str(item.get('quantidade', 0)))
                valor_unitario = Decimal(str(item.get('valor_unitario', 0)))
                subtotal = quantidade * valor_unitario
                
                itens_calculados.append({
                    'descricao': item.get('descricao', ''),
                    'quantidade': float(quantidade),
                    'valor_unitario': float(valor_unitario),
                    'subtotal': float(subtotal),
                    'subtotal_formatado': format_currency(subtotal)
                })
                
                total += subtotal
            
            return {
                'itens': itens_calculados,
                'total': float(total),
                'total_formatado': format_currency(total),
                'quantidade_itens': len(itens_calculados)
            }
            
        except Exception as e:
            return {
                'itens': [],
                'total': 0,
                'total_formatado': 'R$ 0,00',
                'quantidade_itens': 0,
                'error': str(e)
            }