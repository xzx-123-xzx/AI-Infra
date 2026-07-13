-- P3 增量迁移
CREATE TABLE IF NOT EXISTS model_registry (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    version VARCHAR(64) NOT NULL,
    base_model VARCHAR(128) NOT NULL,
    adapter_path VARCHAR(1024),
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    canary_weight INT NOT NULL DEFAULT 0,
    metrics JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_model_name_version (name, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS finetune_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    base_model VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'labeling',
    stage VARCHAR(32) NOT NULL DEFAULT 'labeling',
    config JSON,
    metrics JSON,
    registry_id INT,
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_finetune_jobs_tenant (tenant_id),
    CONSTRAINT fk_finetune_registry FOREIGN KEY (registry_id) REFERENCES model_registry (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS finetune_samples (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    instruction TEXT,
    input_text TEXT,
    output_text TEXT,
    label_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_finetune_samples_job (job_id),
    CONSTRAINT fk_finetune_samples_job FOREIGN KEY (job_id) REFERENCES finetune_jobs (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS eval_datasets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    items JSON NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_eval_datasets_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS eval_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id INT NOT NULL,
    name VARCHAR(128) NOT NULL,
    config JSON NOT NULL,
    results JSON,
    metrics JSON,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_eval_runs_dataset (dataset_id),
    CONSTRAINT fk_eval_runs_dataset FOREIGN KEY (dataset_id) REFERENCES eval_datasets (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_workflows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    definition JSON NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_agent_workflows_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS kb_access (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kb_id INT NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    permission VARCHAR(32) NOT NULL DEFAULT 'read',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_kb_access (kb_id, tenant_id),
    CONSTRAINT fk_kb_access_kb FOREIGN KEY (kb_id) REFERENCES knowledge_bases (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
