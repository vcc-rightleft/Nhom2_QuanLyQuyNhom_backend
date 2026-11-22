-- Chạy MỘT LẦN trên cơ sở dữ liệu đã có bảng notifications.
-- Sao lưu DB trước khi chạy. Nếu cột đã tồn tại, bỏ qua câu lệnh này.
ALTER TABLE notifications ADD COLUMN target_path VARCHAR(255) NULL;
