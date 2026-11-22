-- SQUAD.CASH: đối chiếu SQL dump 22/11/2026 với models SQLAlchemy.
-- IMPORTANT: Chọn đúng database bằng USE quan_ly_quy_nhom; hoặc chọn schema trước khi chạy.
-- SAO LƯU database trước khi chạy. Không DROP, DELETE, TRUNCATE.
-- Dùng INFORMATION_SCHEMA để chạy lại không lỗi khi cột đã tồn tại.

DELIMITER $$
DROP PROCEDURE IF EXISTS squad_ensure_column $$
CREATE PROCEDURE squad_ensure_column(IN t VARCHAR(128), IN c VARCHAR(128), IN definition TEXT)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = t AND COLUMN_NAME = c
    ) THEN
        SET @sql = CONCAT('ALTER TABLE `', t, '` ADD COLUMN `', c, '` ', definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END $$
DELIMITER ;

CALL squad_ensure_column('bills', 'status', 'VARCHAR(20) NOT NULL DEFAULT ''ACTIVE''');
CALL squad_ensure_column('bills', 'updated_at', 'DATETIME NULL DEFAULT NULL');
CALL squad_ensure_column('bill_shares', 'debt_id', 'INT NULL DEFAULT NULL');
CALL squad_ensure_column('debts', 'source_id', 'INT NULL DEFAULT NULL');
CALL squad_ensure_column('member_debts', 'amount_paid', 'BIGINT NOT NULL DEFAULT 0');
CALL squad_ensure_column('users', 'token_version', 'INT NOT NULL DEFAULT 0');
DROP PROCEDURE IF EXISTS squad_ensure_column;

-- Khoản nợ cũ có source_id=NULL sẽ không được suy đoán tự động;
-- cần đối soát thủ công nếu cần liên kết với hóa đơn trước đây.
