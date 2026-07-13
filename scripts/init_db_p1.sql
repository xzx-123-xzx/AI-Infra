-- P1 增量迁移（已有数据库执行此脚本）
-- mysql -u aiinfra -p aiinfra < scripts/init_db_p1.sql

CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO tenants (id, name) VALUES ('default', 'Default Tenant');

CREATE TABLE IF NOT EXISTS tenant_quotas (
    tenant_id VARCHAR(64) PRIMARY KEY,
    monthly_token_limit BIGINT NOT NULL DEFAULT 0,
    monthly_request_limit INT NOT NULL DEFAULT 0,
    kb_limit INT NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_tenant_quotas_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO tenant_quotas (tenant_id) VALUES ('default');

CREATE TABLE IF NOT EXISTS prompt_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    prompt_type VARCHAR(32) NOT NULL DEFAULT 'rag',
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    ab_enabled TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_prompt_templates_tenant (tenant_id),
    UNIQUE KEY uk_prompt_name_tenant (name, tenant_id, prompt_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS prompt_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_id INT NOT NULL,
    version INT NOT NULL,
    content TEXT NOT NULL,
    variables JSON,
    variant_label VARCHAR(32),
    ab_weight INT NOT NULL DEFAULT 100,
    is_active TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_prompt_versions_template (template_id),
    UNIQUE KEY uk_prompt_template_version (template_id, version),
    CONSTRAINT fk_prompt_versions_template FOREIGN KEY (template_id) REFERENCES prompt_templates (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- usage_logs 增加 tenant_id（若列已存在会报错，可忽略）
ALTER TABLE usage_logs ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT 'default' AFTER api_key_id;
ALTER TABLE usage_logs ADD INDEX idx_usage_logs_tenant_id (tenant_id);
