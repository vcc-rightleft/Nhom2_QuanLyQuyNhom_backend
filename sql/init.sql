CREATE TABLE IF NOT EXISTS fund_transactions (
    transaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    group_id BIGINT NOT NULL DEFAULT 1,
    type VARCHAR(20) NOT NULL,
    amount BIGINT NOT NULL,
    category VARCHAR(100) NULL,
    payer_id BIGINT NULL,
    description TEXT NULL,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    proof_image_url VARCHAR(500) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_by BIGINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fund_transaction_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id BIGINT NOT NULL,
    group_id BIGINT NOT NULL DEFAULT 1,
    action VARCHAR(20) NOT NULL,
    changed_by BIGINT NOT NULL,
    reason TEXT NOT NULL,
    old_data TEXT NULL,
    new_data TEXT NULL,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES fund_transactions(transaction_id) ON DELETE CASCADE
);
