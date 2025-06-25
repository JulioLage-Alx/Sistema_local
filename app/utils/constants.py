"""
Constantes utilizadas em todo o sistema
"""

# Status das vendas
STATUS_VENDA = {
    'ABERTA': 'aberta',
    'PAGA': 'paga',
    'VENCIDA': 'vencida'
}

# Formas de pagamento
FORMAS_PAGAMENTO = {
    'DINHEIRO': 'dinheiro',
    'CARTAO': 'cartao', 
    'PIX': 'pix'
}

# Labels para exibição
FORMAS_PAGAMENTO_LABELS = {
    'dinheiro': 'Dinheiro',
    'cartao': 'Cartão',
    'pix': 'PIX'
}

STATUS_VENDA_LABELS = {
    'aberta': 'Em Aberto',
    'paga': 'Paga',
    'vencida': 'Vencida'
}

# Cores para status (Bootstrap classes)
STATUS_VENDA_COLORS = {
    'aberta': 'warning',
    'paga': 'success',
    'vencida': 'danger'
}

# Configurações de paginação
ITEMS_PER_PAGE = 20
MAX_ITEMS_PER_PAGE = 100

# Configurações de validação
MIN_PASSWORD_LENGTH = 6
MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 255
MAX_OBSERVATION_LENGTH = 500

# Configurações de negócio
LIMITE_CREDITO_PADRAO = 500.00
DIAS_VENCIMENTO_PADRAO = 30
DIAS_INADIMPLENCIA = 30
VALOR_MINIMO_VENDA = 0.01

# Configurações de arquivo
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Configurações de exportação
EXPORT_FORMATS = ['csv', 'xlsx']
MAX_EXPORT_ROWS = 10000

# Configurações de impressão
IMPRESSORA_LARGURA_PAPEL = 48  # caracteres por linha
IMPRESSORA_TIMEOUT = 30  # segundos

# Mensagens de flash
FLASH_MESSAGES = {
    'SUCCESS': {
        'CLIENTE_CRIADO': 'Cliente cadastrado com sucesso!',
        'CLIENTE_ATUALIZADO': 'Cliente atualizado com sucesso!',
        'CLIENTE_REMOVIDO': 'Cliente removido com sucesso!',
        'VENDA_CRIADA': 'Venda registrada com sucesso!',
        'VENDA_ATUALIZADA': 'Venda atualizada com sucesso!',
        'PAGAMENTO_REGISTRADO': 'Pagamento registrado com sucesso!',
        'COMPROVANTE_IMPRESSO': 'Comprovante impresso com sucesso!',
        'BACKUP_CRIADO': 'Backup criado com sucesso!',
        'DADOS_EXPORTADOS': 'Dados exportados com sucesso!'
    },
    'ERROR': {
        'CLIENTE_NAO_ENCONTRADO': 'Cliente não encontrado!',
        'VENDA_NAO_ENCONTRADA': 'Venda não encontrada!',
        'ERRO_BANCO_DADOS': 'Erro ao acessar banco de dados!',
        'ERRO_IMPRESSORA': 'Erro ao imprimir comprovante!',
        'ERRO_BACKUP': 'Erro ao criar backup!',
        'ERRO_EXPORTACAO': 'Erro ao exportar dados!',
        'VALOR_INVALIDO': 'Valor inválido informado!',
        'LIMITE_CREDITO_EXCEDIDO': 'Limite de crédito excedido!',
        'PAGAMENTO_MAIOR_DIVIDA': 'Valor do pagamento maior que a dívida!'
    },
    'WARNING': {
        'CLIENTE_COM_PENDENCIAS': 'Cliente possui pendências em aberto!',
        'VENDA_JA_PAGA': 'Esta venda já foi paga!',
        'IMPRESSORA_DESCONECTADA': 'Impressora não conectada!',
        'BACKUP_DESATUALIZADO': 'Último backup realizado há mais de 7 dias!'
    },
    'INFO': {
        'NENHUM_RESULTADO': 'Nenhum resultado encontrado!',
        'FILTROS_APLICADOS': 'Filtros aplicados na pesquisa!',
        'DADOS_ATUALIZADOS': 'Dados atualizados automaticamente!'
    }
}

# Configurações de dashboard
DASHBOARD_STATS = {
    'VENDAS_HOJE': 'vendas_hoje',
    'VENDAS_MES': 'vendas_mes',
    'CLIENTES_ATIVOS': 'clientes_ativos',
    'VENDAS_VENCIDAS': 'vendas_vencidas',
    'VALOR_TOTAL_ABERTO': 'valor_total_aberto'
}

# Configurações de relatórios
RELATORIO_TIPOS = {
    'VENDAS': 'vendas',
    'CLIENTES': 'clientes', 
    'INADIMPLENTES': 'inadimplentes',
    'FINANCEIRO': 'financeiro'
}

# Configurações de gráficos
CHART_COLORS = [
    '#007bff',  # primary
    '#28a745',  # success
    '#ffc107',  # warning
    '#dc3545',  # danger
    '#17a2b8',  # info
    '#6f42c1',  # purple
    '#e83e8c',  # pink
    '#fd7e14'   # orange
]

# Períodos para relatórios
PERIODOS_RELATORIO = {
    'HOJE': 'hoje',
    'ONTEM': 'ontem',
    'ULTIMOS_7_DIAS': 'ultimos_7_dias',
    'ULTIMOS_30_DIAS': 'ultimos_30_dias',
    'MES_ATUAL': 'mes_atual',
    'MES_ANTERIOR': 'mes_anterior',
    'PERSONALIZADO': 'personalizado'
}

# Máscaras para formatação
MASCARAS = {
    'CPF': '000.000.000-00',
    'TELEFONE': '(00) 00000-0000',
    'CEP': '00000-000',
    'VALOR': 'R$ 0.000,00'
}

# Configurações de log
LOG_ACTIONS = {
    'CREATE': 'create',
    'UPDATE': 'update', 
    'DELETE': 'delete',
    'LOGIN': 'login',
    'LOGOUT': 'logout',
    'BACKUP': 'backup',
    'EXPORT': 'export',
    'PRINT': 'print'
}

# Configurações de sistema
SISTEMA_INFO = {
    'NOME': 'Sistema Crediário Açougue',
    'VERSAO': '1.0.0',
    'AUTOR': 'Desenvolvedor',
    'EMAIL': 'suporte@exemplo.com',
    'SITE': 'https://exemplo.com'
}