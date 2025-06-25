-- ============================================
-- Script de Criação do Banco de Dados
-- Sistema de Crediário para Açougue
-- ============================================

-- Criar banco de dados se não existir
CREATE DATABASE IF NOT EXISTS acougue_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE acougue_db;

-- ============================================
-- Tabela: clientes
-- ============================================
CREATE TABLE IF NOT EXISTS clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cpf VARCHAR(14) UNIQUE DEFAULT NULL,
    telefone VARCHAR(15) DEFAULT NULL,
    endereco TEXT DEFAULT NULL,
    limite_credito DECIMAL(10,2) NOT NULL DEFAULT 500.00,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    observacoes TEXT DEFAULT NULL,
    
    -- Índices
    INDEX idx_clientes_nome (nome),
    INDEX idx_clientes_cpf (cpf),
    INDEX idx_clientes_ativo (ativo),
    INDEX idx_clientes_data_cadastro (data_cadastro)
) ENGINE=InnoDB;

-- ============================================
-- Tabela: vendas
-- ============================================
CREATE TABLE IF NOT EXISTS vendas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    data_venda DATE NOT NULL,
    data_vencimento DATE NOT NULL,
    data_pagamento DATE DEFAULT NULL,
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'aberta',
    eh_restante BOOLEAN NOT NULL DEFAULT FALSE,
    pagamento_multiplo_id INT DEFAULT NULL,
    data_criacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    observacoes TEXT DEFAULT NULL,
    
    -- Chaves estrangeiras
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT,
    
    -- Índices
    INDEX idx_vendas_cliente (cliente_id),
    INDEX idx_vendas_data_venda (data_venda),
    INDEX idx_vendas_data_vencimento (data_vencimento),
    INDEX idx_vendas_data_pagamento (data_pagamento),
    INDEX idx_vendas_status (status),
    INDEX idx_vendas_total (total),
    INDEX idx_vendas_eh_restante (eh_restante),
    INDEX idx_vendas_pagamento_multiplo (pagamento_multiplo_id)
) ENGINE=InnoDB;

-- ============================================
-- Tabela: itens_venda
-- ============================================
CREATE TABLE IF NOT EXISTS itens_venda (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venda_id INT NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    quantidade DECIMAL(10,3) NOT NULL DEFAULT 1.000,
    valor_unitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    ordem INT NOT NULL DEFAULT 1,
    
    -- Chaves estrangeiras
    FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE,
    
    -- Índices
    INDEX idx_itens_venda_venda (venda_id),
    INDEX idx_itens_venda_descricao (descricao)
) ENGINE=InnoDB;

-- ============================================
-- Tabela: pagamentos_multiplos
-- ============================================
CREATE TABLE IF NOT EXISTS pagamentos_multiplos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    valor_total_notas DECIMAL(10,2) NOT NULL,
    valor_pago DECIMAL(10,2) NOT NULL,
    valor_restante DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    forma_pagamento VARCHAR(20) NOT NULL DEFAULT 'dinheiro',
    valor_recebido DECIMAL(10,2) DEFAULT NULL,
    troco DECIMAL(10,2) DEFAULT NULL,
    data_pagamento DATE NOT NULL,
    data_criacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observacoes TEXT DEFAULT NULL,
    
    -- Chaves estrangeiras
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT,
    
    -- Índices
    INDEX idx_pagamentos_multiplos_cliente (cliente_id),
    INDEX idx_pagamentos_multiplos_data (data_pagamento),
    INDEX idx_pagamentos_multiplos_forma (forma_pagamento)
) ENGINE=InnoDB;

-- ============================================
-- Tabela: pagamentos_multiplos_detalhes
-- ============================================
CREATE TABLE IF NOT EXISTS pagamentos_multiplos_detalhes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pagamento_multiplo_id INT NOT NULL,
    venda_id INT NOT NULL,
    valor_original DECIMAL(10,2) NOT NULL,
    valor_pago DECIMAL(10,2) NOT NULL,
    
    -- Chaves estrangeiras
    FOREIGN KEY (pagamento_multiplo_id) REFERENCES pagamentos_multiplos(id) ON DELETE CASCADE,
    FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE,
    
    -- Índices
    INDEX idx_pagamentos_detalhes_multiplo (pagamento_multiplo_id),
    INDEX idx_pagamentos_detalhes_venda (venda_id)
) ENGINE=InnoDB;

-- ============================================
-- Tabela: pagamentos
-- ============================================
CREATE TABLE IF NOT EXISTS pagamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venda_id INT NOT NULL,
    valor DECIMAL(10,2) NOT NULL,
    forma_pagamento VARCHAR(20) NOT NULL DEFAULT 'dinheiro',
    valor_recebido DECIMAL(10,2) DEFAULT NULL,
    troco DECIMAL(10,2) DEFAULT NULL,
    data_pagamento DATE NOT NULL,
    data_criacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observacoes TEXT DEFAULT NULL,
    
    -- Chaves estrangeiras
    FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE,
    
    -- Índices
    INDEX idx_pagamentos_venda (venda_id),
    INDEX idx_pagamentos_data (data_pagamento),
    INDEX idx_pagamentos_forma (forma_pagamento)
) ENGINE=InnoDB;

-- ============================================
-- Adicionar chave estrangeira para pagamento_multiplo_id em vendas
-- (deve ser adicionada após criar a tabela pagamentos_multiplos)
-- ============================================
ALTER TABLE vendas 
ADD CONSTRAINT fk_vendas_pagamento_multiplo 
FOREIGN KEY (pagamento_multiplo_id) REFERENCES pagamentos_multiplos(id) ON DELETE SET NULL;

-- ============================================
-- Views úteis para relatórios
-- ============================================

-- View: Vendas com informações do cliente
CREATE OR REPLACE VIEW vw_vendas_completas AS
SELECT 
    v.id,
    v.data_venda,
    v.data_vencimento,
    v.data_pagamento,
    v.total,
    v.status,
    v.eh_restante,
    c.id as cliente_id,
    c.nome as cliente_nome,
    c.cpf as cliente_cpf,
    c.telefone as cliente_telefone,
    COALESCE(SUM(p.valor), 0) as valor_pago,
    (v.total - COALESCE(SUM(p.valor), 0)) as valor_restante,
    CASE 
        WHEN v.status = 'paga' THEN 0
        WHEN v.data_vencimento < CURDATE() THEN DATEDIFF(CURDATE(), v.data_vencimento)
        ELSE 0 
    END as dias_atraso
FROM vendas v
INNER JOIN clientes c ON v.cliente_id = c.id
LEFT JOIN pagamentos p ON v.id = p.venda_id
GROUP BY v.id, c.id;

-- View: Clientes com resumo financeiro
CREATE OR REPLACE VIEW vw_clientes_resumo AS
SELECT 
    c.id,
    c.nome,
    c.cpf,
    c.telefone,
    c.limite_credito,
    c.ativo,
    c.data_cadastro,
    COUNT(DISTINCT v.id) as total_vendas,
    COALESCE(SUM(CASE WHEN v.status = 'aberta' THEN v.total ELSE 0 END), 0) as valor_em_aberto,
    COALESCE(SUM(CASE WHEN v.status = 'paga' THEN v.total ELSE 0 END), 0) as valor_pago_total,
    (c.limite_credito - COALESCE(SUM(CASE WHEN v.status = 'aberta' THEN v.total ELSE 0 END), 0)) as credito_disponivel,
    COUNT(CASE WHEN v.status = 'aberta' AND v.data_vencimento < CURDATE() THEN 1 END) as vendas_vencidas
FROM clientes c
LEFT JOIN vendas v ON c.id = v.cliente_id
WHERE c.ativo = TRUE
GROUP BY c.id;

-- ============================================
-- Triggers para manter consistência
-- ============================================

-- Trigger: Atualizar total da venda quando item é modificado
DELIMITER $$
CREATE TRIGGER tr_atualizar_total_venda_insert
AFTER INSERT ON itens_venda
FOR EACH ROW
BEGIN
    UPDATE vendas 
    SET subtotal = (
        SELECT COALESCE(SUM(subtotal), 0) 
        FROM itens_venda 
        WHERE venda_id = NEW.venda_id
    ),
    total = (
        SELECT COALESCE(SUM(subtotal), 0) 
        FROM itens_venda 
        WHERE venda_id = NEW.venda_id
    )
    WHERE id = NEW.venda_id;
END$$

CREATE TRIGGER tr_atualizar_total_venda_update
AFTER UPDATE ON itens_venda
FOR EACH ROW
BEGIN
    UPDATE vendas 
    SET subtotal = (
        SELECT COALESCE(SUM(subtotal), 0) 
        FROM itens_venda 
        WHERE venda_id = NEW.venda_id
    ),
    total = (
        SELECT COALESCE(SUM(subtotal), 0) 
        FROM itens_venda 
        WHERE venda_id = NEW.venda_id
    )
    WHERE id = NEW.venda_id;
END$$

CREATE TRIGGER tr_atualizar_total_venda_delete
AFTER DELETE ON itens_venda
FOR EACH ROW
BEGIN
    UPDATE vendas 
    SET subtotal = (
        SELECT COALESCE(SUM(subtotal), 0) 
        FROM itens_venda 
        WHERE venda_id = OLD.venda_id
    ),
    total = (
        SELECT COALESCE(SUM(subtotal), 0) 
        FROM itens_venda 
        WHERE venda_id = OLD.venda_id
    )
    WHERE id = OLD.venda_id;
END$$

-- Trigger: Atualizar status da venda após pagamento
CREATE TRIGGER tr_atualizar_status_venda_pagamento
AFTER INSERT ON pagamentos
FOR EACH ROW
BEGIN
    DECLARE valor_total DECIMAL(10,2);
    DECLARE valor_pago_total DECIMAL(10,2);
    
    SELECT total INTO valor_total 
    FROM vendas 
    WHERE id = NEW.venda_id;
    
    SELECT COALESCE(SUM(valor), 0) INTO valor_pago_total
    FROM pagamentos 
    WHERE venda_id = NEW.venda_id;
    
    IF valor_pago_total >= valor_total THEN
        UPDATE vendas 
        SET status = 'paga', data_pagamento = NEW.data_pagamento
        WHERE id = NEW.venda_id;
    END IF;
END$$

DELIMITER ;

-- ============================================
-- Inserir dados iniciais de configuração
-- ============================================

-- Configurações do sistema (se necessário criar tabela própria)
-- Por enquanto, usar variáveis da aplicação

-- ============================================
-- Comentários sobre performance
-- ============================================

-- Para melhor performance com grandes volumes:
-- 1. Manter estatísticas atualizadas: ANALYZE TABLE nome_tabela;
-- 2. Considerar particionamento por data nas vendas
-- 3. Arquivar dados antigos periodicamente
-- 4. Monitorar queries lentas: SET GLOBAL slow_query_log = ON;

-- ============================================
-- Fim do script
-- ============================================