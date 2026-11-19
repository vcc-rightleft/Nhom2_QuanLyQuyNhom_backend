CREATE DATABASE IF NOT EXISTS app_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE app_db;

CREATE TABLE IF NOT EXISTS items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    price BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO items (name, description, price)
VALUES
    ('Khoản thu mẫu', 'Tiền quỹ tháng 11', 100000),
    ('Khoản chi mẫu', 'Tiền nước ngọt Circle K', 35000);

-- =====================
-- MODULE NHÓM QUỸ
-- T3CC911
-- =====================
CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS fund_groups (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    image_url VARCHAR(255),
    invite_code CHAR(8) NOT NULL UNIQUE,
    status ENUM('ACTIVE','ARCHIVED') DEFAULT 'ACTIVE',
    creator_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (creator_id)
    REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS group_members (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role ENUM('HOST','MEMBER') DEFAULT 'MEMBER',
    status ENUM('ACTIVE','LEFT','REMOVED') DEFAULT 'ACTIVE',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_group_user UNIQUE(group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES fund_groups(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- =====================
-- MODULE GIAO DỊCH QUỸ & SAO KÊ (T3CCFEE)
-- =====================
CREATE TABLE IF NOT EXISTS fund_transactions (
    transaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    group_id BIGINT NOT NULL,
    type VARCHAR(20) NOT NULL,
    amount BIGINT NOT NULL,
    category VARCHAR(100) NULL,
    payer_id BIGINT NULL,
    description TEXT NULL,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    proof_image_url VARCHAR(500) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_by BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ft_group_occurred (group_id, occurred_at)
);

-- =====================
-- MODULE HOÁ ĐƠN & CÔNG NỢ (T3CDE9A)
-- =====================
CREATE TABLE IF NOT EXISTS bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    bill_date DATETIME NOT NULL,
    total_amount DECIMAL(15, 0) NOT NULL,
    paid_by INT NOT NULL,
    split_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    note TEXT NULL,
    image_url VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_bills_group_date (group_id, bill_date),
    INDEX idx_bills_paid_by (paid_by)
);

CREATE TABLE IF NOT EXISTS bill_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    unit_price DECIMAL(15, 0) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    consumer_user_ids VARCHAR(255) NULL,
    INDEX idx_bill_items_bill_id (bill_id)
);

CREATE TABLE IF NOT EXISTS bill_shares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    member_id INT NOT NULL,
    amount DECIMAL(15, 0) NOT NULL,
    debt_id INT NULL,
    INDEX idx_bill_shares_bill_id (bill_id),
    INDEX idx_bill_shares_debt_id (debt_id)
);

CREATE TABLE IF NOT EXISTS debts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL,
    source_type ENUM('INVOICE', 'COLLECTION_PERIOD') NOT NULL,
    source_id INT NULL,
    debtor_id INT NOT NULL,
    payee_id INT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    paid_amount DECIMAL(12, 2) DEFAULT 0.00,
    status ENUM('UNPAID', 'PARTIAL', 'PAID') DEFAULT 'UNPAID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_debts_source (source_type, source_id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    debt_id INT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    proof_image VARCHAR(255),
    status ENUM('PENDING', 'CONFIRMED', 'REJECTED') DEFAULT 'PENDING',
    confirmed_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (debt_id) REFERENCES debts(id) ON DELETE CASCADE
);

INSERT INTO users(username)
VALUES
('user1'),
('user2'),
('user3');

INSERT INTO fund_groups
(name, description, invite_code, status, creator_id)
VALUES
('Nhom Du Lich','Chi phi du lich','ABCD1234','ACTIVE',1),
('Phong Tro A1','Chi phi sinh hoat','EFGH5678','ACTIVE',2),
('Capstone Project','Chi phi do an','IJKL9012','ACTIVE',3);

INSERT INTO group_members
(group_id,user_id,role)
VALUES
(1,1,'HOST'),
(2,2,'HOST'),
(3,3,'HOST');