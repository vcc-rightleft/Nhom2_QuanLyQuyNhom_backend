CREATE DATABASE IF NOT EXISTS app_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE app_db;

CREATE TABLE IF NOT EXISTS items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    price BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL DEFAULT 1,
    full_name VARCHAR(255) NOT NULL,
    student_code VARCHAR(50) NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'MEMBER'
);

CREATE TABLE IF NOT EXISTS collection_campaigns (
    collection_id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL DEFAULT 1,
    name VARCHAR(255) NOT NULL,
    amount_per_member DOUBLE NOT NULL,
    due_date VARCHAR(50) NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_by INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS member_debts (
    debt_id INT AUTO_INCREMENT PRIMARY KEY,
    collection_id INT NOT NULL,
    user_id INT NOT NULL,
    member_name VARCHAR(255) NULL,
    role VARCHAR(50) DEFAULT 'MEMBER',
    amount_due DOUBLE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'UNPAID',
    paid_at DATETIME NULL,
    FOREIGN KEY (collection_id) REFERENCES collection_campaigns(collection_id) ON DELETE CASCADE
);

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
    created_by BIGINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO items (name, description, price) 
VALUES 
    ('Khoản thu mẫu', 'Tiền quỹ tháng 11', 100000),
    ('Khoản chi mẫu', 'Tiền nước ngọt Circle K', 35000);

INSERT INTO users (group_id, full_name, student_code, role)
VALUES
    (1, 'Lê Nguyễn Hữu Quốc', 'B25DTCN256', 'HOST'),
    (1, 'Phạm Đức Anh', 'B25DTCN102', 'MEMBER'),
    (1, 'Lê Minh Thắng', 'B25DTCN188', 'MEMBER'),
    (1, 'Nguyễn Văn An', 'B25DTCN205', 'MEMBER'),
    (1, 'Trần Thị Bình', 'B25DTCN219', 'MEMBER');