# Sistema de Crediário para Açougue

Sistema web desenvolvido em Python Flask para gerenciamento de vendas a crediário em açougues, com integração para impressora térmica ESC/POS.

## 🚀 Funcionalidades

- **CRUD de Clientes**: Cadastro completo com histórico de compras
- **Gestão de Vendas**: Criação de vendas com itens livres
- **Controle de Pagamentos**: Pagamentos parciais e múltiplos
- **Alertas de Inadimplência**: Identificação automática de vendas vencidas
- **Relatórios e Exportação**: CSV/Excel com gráficos interativos
- **Impressão ESC/POS**: Comprovantes na impressora térmica Elgin i9
- **Interface Responsiva**: Design moderno com Bootstrap

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.8+, Flask, SQLAlchemy
- **Banco de Dados**: MySQL
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 4.6
- **Impressão**: python-escpos (Elgin i9)
- **Gráficos**: Chart.js
- **Exportação**: pandas, openpyxl

## 📋 Pré-requisitos

### Software Necessário
- Python 3.8 ou superior
- MySQL Server 5.7 ou superior
- Driver da impressora Elgin i9

### Hardware
- Impressora Térmica Elgin i9
- Cabo USB para conexão da impressora

## 🔧 Instalação

### 1. Clonar o repositório
```bash
git clone https://github.com/seu-usuario/sistema-acougue.git
cd sistema-acougue
```

### 2. Criar ambiente virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar banco de dados
```sql
-- Conectar no MySQL como root
CREATE DATABASE acougue_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'acougue_user'@'localhost' IDENTIFIED BY 'sua_senha_aqui';
GRANT ALL PRIVILEGES ON acougue_db.* TO 'acougue_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Configurar variáveis de ambiente
```bash
# Copiar arquivo de exemplo
cp config/env.example .env

# Editar o arquivo .env com suas configurações
```

### 6. Inicializar banco de dados
```bash
python run.py init-db
```

### 7. Executar aplicação
```bash
python run.py
```

A aplicação estará disponível em: `http://localhost:5000`

## 🖨️ Configuração da Impressora

### Driver Elgin i9
1. Baixar driver oficial da Elgin
2. Instalar seguindo instruções do fabricante
3. Verificar conexão USB

### Teste de Impressão
```bash
python run.py test-printer
```

## 👤 Primeiro Acesso

### Criar usuário administrativo
```bash
python run.py create-user
```

**Login padrão:**
- Usuário: `admin`
- Senha: `admin123`

> ⚠️ **Importante**: Altere a senha padrão após o primeiro acesso!

## 📊 Comandos Úteis

### Backup do banco de dados
```bash
python run.py backup
```

### Resetar banco de dados
```bash
python run.py reset-db
```

### Executar testes
```bash
pytest
```

### Gerar executável (PyInstaller)
```bash
python scripts/build.py
```

## 📁 Estrutura do Projeto

```
sistema_acougue/
├── app/                    # Aplicação Flask
│   ├── models/            # Modelos do banco
│   ├── views/             # Controllers/Views
│   ├── services/          # Lógica de negócio
│   ├── templates/         # Templates HTML
│   └── static/           # CSS, JS, imagens
├── migrations/            # Migrações do banco
├── tests/                # Testes automatizados
├── scripts/              # Scripts utilitários
├── docs/                 # Documentação
└── config/               # Configurações
```

## 🔒 Segurança

- Proteção CSRF em formulários
- Sanitização de inputs
- Headers de segurança HTTP
- Logs de auditoria
- Backup automático diário

## 📈 Monitoramento

### Logs do Sistema
- Localização: `logs/app.log`
- Rotação automática (10MB por arquivo)
- Retenção de 10 arquivos

### Alertas Automáticos
- Vendas vencidas há mais de 30 dias
- Clientes acima do limite de crédito
- Verificação diária automática

## 🚨 Solução de Problemas

### Erro de conexão com MySQL
```bash
# Verificar se o MySQL está rodando
sudo systemctl status mysql

# Testar conexão
mysql -u acougue_user -p acougue_db
```

### Impressora não responde
1. Verificar conexão USB
2. Confirmar driver instalado
3. Testar com: `python run.py test-printer`

### Erro de permissão
```bash
# Linux: dar permissão aos diretórios
chmod 755 logs/ backups/ exports/
```

## 📞 Suporte

Para dúvidas e suporte:
- 📧 Email: suporte@exemplo.com
- 📱 WhatsApp: (31) 99999-9999
- 🐛 Issues: GitHub Issues

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🤝 Contribuições

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Changelog

### v1.0.0 (2025-06-25)
- 🎉 Lançamento inicial
- ✅ CRUD de clientes e vendas
- ✅ Sistema de pagamentos múltiplos
- ✅ Integração impressora ESC/POS
- ✅ Relatórios e alertas
- ✅ Exportação CSV/Excel

---

