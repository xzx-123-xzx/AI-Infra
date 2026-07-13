-- P2 增量迁移
ALTER TABLE documents ADD COLUMN progress INT NOT NULL DEFAULT 0 AFTER chunk_count;
ALTER TABLE documents ADD COLUMN content_hash VARCHAR(64) AFTER progress;

CREATE TABLE IF NOT EXISTS document_chunks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    doc_id INT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_hash VARCHAR(64) NOT NULL,
    chunk_id VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_doc_chunk_index (doc_id, chunk_index),
    INDEX idx_document_chunks_doc_id (doc_id),
    CONSTRAINT fk_document_chunks_doc FOREIGN KEY (doc_id) REFERENCES documents (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sync_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kb_id INT NOT NULL,
    name VARCHAR(128) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    config JSON NOT NULL,
    cron_minutes INT NOT NULL DEFAULT 0,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    last_sync_at DATETIME,
    last_status VARCHAR(32),
    last_error TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sync_sources_kb_id (kb_id),
    CONSTRAINT fk_sync_sources_kb FOREIGN KEY (kb_id) REFERENCES knowledge_bases (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
