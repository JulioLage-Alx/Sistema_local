"""
Configurações da aplicação Flask
"""

import os
from datetime import timedelta


class Config:
    """Configuração base da aplicação"""
    
    # Configurações básicas do Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Configurações da aplicação
    APP_NAME = 'Sistema Crediário Açougue'
    APP_VERSION = '1.0.0'
    APP_AUTHOR = 'Sistema Crediário'
    APP_EMAIL = 'suporte@exemplo.com'
    
    # Configurações de banco de dados
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://acougue_user:senha123@localhost/acougue_db?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 120,
        'pool_pre_ping': True,
        'pool_timeout': 20,
        'max_overflow': 30
    }
    
    # Configurações de sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 8 horas
    SESSION_COOKIE_SECURE = False  # True em produção com HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configurações de segurança
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hora
    
    # Configurações de upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
    
    # Configurações de paginação
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100
    
    # Configurações de negócio
    LIMITE_CREDITO_PADRAO = 500.00
    DIAS_VENCIMENTO_PADRAO = 30
    DIAS_INADIMPLENCIA = 30
    VALOR_MINIMO_VENDA = 0.01
    
    # Configurações de log
    LOG_FOLDER = os.path.join(os.getcwd(), 'logs')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # Configurações de backup
    BACKUP_FOLDER = os.path.join(os.getcwd(), 'backups')
    BACKUP_RETENTION_DAYS = 30
    AUTO_BACKUP_ENABLED = True
    AUTO_BACKUP_TIME = '02:00'  # 2:00 AM
    
    # Configurações de exportação
    EXPORT_FOLDER = os.path.join(os.getcwd(), 'exports')
    EXPORT_MAX_ROWS = 10000
    
    # Configurações de impressora
    IMPRESSORA_ENABLED = True
    IMPRESSORA_VENDOR_ID = 0x0dd4  # Elgin
    IMPRESSORA_PRODUCT_ID = 0x0205  # i9
    IMPRESSORA_TIMEOUT = 30
    IMPRESSORA_LARGURA_PAPEL = 48  # caracteres
    
    # Configurações de email (para futuras implementações)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Configurações de timezone
    TIMEZONE = 'America/Sao_Paulo'
    
    # Configurações de cache (para futuras implementações)
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Configurações de API
    API_RATE_LIMIT = '100 per hour'
    
    # Configurações específicas para sistema local
    SYSTEM_USERNAME = os.environ.get('SYSTEM_USERNAME') or 'admin'
    SYSTEM_PASSWORD = os.environ.get('SYSTEM_PASSWORD') or 'admin123'
    
    @staticmethod
    def init_app(app):
        """Inicializar configurações específicas da aplicação"""
        pass


class DevelopmentConfig(Config):
    """Configuração para ambiente de desenvolvimento"""
    
    DEBUG = True
    TESTING = False
    
    # Configurações de banco para desenvolvimento
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'mysql+pymysql://acougue_user:senha123@localhost/acougue_dev_db?charset=utf8mb4'
    
    # Configurações de log mais verbosas
    LOG_LEVEL = 'DEBUG'
    SQLALCHEMY_ECHO = False  # True para ver queries SQL
    
    # Configurações de sessão mais relaxadas
    SESSION_COOKIE_SECURE = False
    
    # Configurações de desenvolvimento
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Não cachear arquivos estáticos
    
    @staticmethod
    def init_app(app):
        """Inicializar configurações de desenvolvimento"""
        Config.init_app(app)
        
        # Configurar logging para desenvolvimento
        import logging
        logging.basicConfig(level=logging.DEBUG)


class ProductionConfig(Config):
    """Configuração para ambiente de produção"""
    
    DEBUG = False
    TESTING = False
    
    # Configurações de segurança para produção
    SESSION_COOKIE_SECURE = True  # Requer HTTPS
    WTF_CSRF_ENABLED = True
    
    # Configurações de banco para produção
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://acougue_user:senha_forte@localhost/acougue_db?charset=utf8mb4'
    
    # Configurações de log para produção
    LOG_LEVEL = 'INFO'
    SQLALCHEMY_ECHO = False
    
    # Configurações de email habilitadas
    MAIL_SUPPRESS_SEND = False
    
    @staticmethod
    def init_app(app):
        """Inicializar configurações de produção"""
        Config.init_app(app)
        
        # Configurar logging para produção
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Criar diretório de logs se não existir
        if not os.path.exists(Config.LOG_FOLDER):
            os.makedirs(Config.LOG_FOLDER)
        
        # Configurar handler de arquivo
        file_handler = RotatingFileHandler(
            os.path.join(Config.LOG_FOLDER, 'app.log'),
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Sistema Crediário Açougue - Iniciando em produção')


class TestingConfig(Config):
    """Configuração para ambiente de testes"""
    
    DEBUG = False
    TESTING = True
    
    # Configurações de banco para testes (em memória)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Desabilitar CSRF para testes
    WTF_CSRF_ENABLED = False
    
    # Configurações específicas para testes
    SERVER_NAME = 'localhost.localdomain'
    
    # Configurações de autenticação para testes
    SYSTEM_USERNAME = 'test'
    SYSTEM_PASSWORD = 'test123'
    
    @staticmethod
    def init_app(app):
        """Inicializar configurações de teste"""
        Config.init_app(app)


class DockerConfig(ProductionConfig):
    """Configuração para ambiente Docker"""
    
    # Configurações específicas para Docker
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:root@db/acougue_db?charset=utf8mb4'
    
    # Configurações de rede para Docker
    HOST = '0.0.0.0'
    PORT = int(os.environ.get('PORT', 5000))
    
    @staticmethod
    def init_app(app):
        """Inicializar configurações Docker"""
        ProductionConfig.init_app(app)
        
        # Log para stdout em Docker
        import logging
        
        # Configurar handler para stdout
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        app.logger.setLevel(logging.INFO)


# Mapeamento de configurações por ambiente
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'docker': DockerConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Obter configuração baseada no nome ou variável de ambiente
    
    Args:
        config_name: Nome da configuração
        
    Returns:
        Classe de configuração
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])


# Configurações específicas para diferentes componentes

class DatabaseConfig:
    """Configurações específicas do banco de dados"""
    
    # Pool de conexões
    POOL_SIZE = 10
    POOL_RECYCLE = 3600
    POOL_PRE_PING = True
    
    # Timeouts
    POOL_TIMEOUT = 30
    MAX_OVERFLOW = 20
    
    # Configurações de charset
    CHARSET = 'utf8mb4'
    COLLATION = 'utf8mb4_unicode_ci'


class SecurityConfig:
    """Configurações de segurança"""
    
    # Headers de segurança
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'"
    }
    
    # Configurações de senha
    PASSWORD_MIN_LENGTH = 6
    PASSWORD_REQUIRE_UPPERCASE = False
    PASSWORD_REQUIRE_LOWERCASE = False
    PASSWORD_REQUIRE_NUMBERS = False
    PASSWORD_REQUIRE_SPECIAL = False


class BusinessConfig:
    """Configurações de regras de negócio"""
    
    # Valores padrão
    LIMITE_CREDITO_MINIMO = 50.00
    LIMITE_CREDITO_MAXIMO = 10000.00
    
    # Prazos
    PRAZO_VENCIMENTO_MINIMO = 1  # dias
    PRAZO_VENCIMENTO_MAXIMO = 90  # dias
    
    # Alertas
    ALERTA_VENCIMENTO_DIAS = 7  # alertar 7 dias antes do vencimento
    ALERTA_LIMITE_PERCENTUAL = 80  # alertar quando usar 80% do limite
    
    # Validações
    VALOR_MINIMO_ITEM = 0.01
    QUANTIDADE_MINIMA_ITEM = 0.01
    QUANTIDADE_MAXIMA_ITEM = 9999.99


class PrinterConfig:
    """Configurações da impressora"""
    
    # Configurações da Elgin i9
    VENDOR_ID = 0x0dd4
    PRODUCT_ID = 0x0205
    
    # Configurações de papel
    PAPER_WIDTH = 48  # caracteres
    FONT_SIZE = 12
    
    # Configurações de impressão
    CUT_PAPER = True
    OPEN_DRAWER = False
    
    # Timeout
    TIMEOUT = 30
    
    # Configurações de layout do comprovante
    HEADER_LINES = 3
    FOOTER_LINES = 2
    ITEM_PADDING = 2