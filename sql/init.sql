CREATE TABLE IF NOT EXISTS bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    payer_id INT NOT NULL,
    split_type VARCHAR(50) NOT NULL,
    fee_split_mode VARCHAR(50) DEFAULT 'EQUAL',
    items_subtotal DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    service_ship_fee DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(12, 2) NOT NULL,
    created_by INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bill_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(12, 2) NOT NULL,
    total_price DECIMAL(12, 2) NOT NULL,
    participant_ids VARCHAR(500) NOT NULL,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bill_shares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    user_id INT NOT NULL,
    items_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    fee_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total_share_amount DECIMAL(12, 2) NOT NULL,
    debt_id INT NULL,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
);