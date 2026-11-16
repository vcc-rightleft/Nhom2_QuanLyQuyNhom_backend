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
CREATE DATABASE IF NOT EXISTS app_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE app_db;

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

    role ENUM('HOST','MEMBER')
    DEFAULT 'MEMBER',

    status ENUM('ACTIVE','LEFT','REMOVED')
    DEFAULT 'ACTIVE',

    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_group_user
    UNIQUE(group_id,user_id),

    FOREIGN KEY (group_id)
    REFERENCES fund_groups(id),

    FOREIGN KEY (user_id)
    REFERENCES users(id)
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