# SQUAD.CASH — Frontend + FastAPI + MySQL

## Phạm vi bàn giao (22/11/2026)

Đã đối chiếu các file `Dump20261122.zip`, `Backend(1).zip`, `Fontend(1).zip` được cung cấp. Bản này **không chứa dữ liệu người dùng từ SQL dump, mật khẩu MySQL, file `.env` thực, hay script seed với tài khoản/mật khẩu demo**. Chỉ có mã nguồn và script bổ sung schema.

### Đã kết nối với API và có kiểm thử tự động trên SQLite tạm

- Đăng ký/đăng nhập với FastAPI, JWT, xem hồ sơ, đăng xuất thu hồi token cũ.
- Tài khoản mới: danh sách nhóm, hóa đơn, quỹ, công nợ đều trống.
- Tạo nhóm, tham gia nhóm bằng mã mời, xem danh sách nhóm có tham gia và thành viên.
- Chọn nhóm và xem số dư quỹ, lịch sử giao dịch quỹ, hóa đơn, phần tiền phải trả và công nợ từ API.
- Host nhóm được tạo giao dịch quỹ thu/chi và tạo **hóa đơn chia đều**, Backend lưu các phần chia/nợ liên quan.
- API xác định người dùng từ JWT, kiểm tra tư cách thành viên và quyền Host theo nhóm. Không dùng `user_id=1` cố định; không tin quyền do trình duyệt tự gửi.
- Phiên tài khoản lưu trên `sessionStorage`; **không lưu dữ liệu tài chính làm nguồn dữ liệu chính trong `localStorage`**.

### Chưa kết nối hoàn chỉnh / đã khóa thao tác giả

- Chia hóa đơn **theo món (Itemized)**: schema/API cũ chưa khớp, UI không cho lưu giả.
- Xác nhận trả nợ, thanh toán thực tế, gửi nhắc nợ, mời thành viên trực tiếp qua email, thay mã nhóm.
- VietQR: mã mẫu từng chứa **tài khoản nhận tiền được ghi cứng** nên đã tắt chức năng QR thật để không chuyển nhầm tiền. Cần API thông tin người thụ hưởng đã xác minh trước khi bật.
- Quản trị hệ thống: khóa/mở khóa, xóa mềm/khôi phục, lưu trữ 5 năm hiện không có API phù hợp; không thông báo thành công giả. Admin dashboard chưa được nối dữ liệu thực.
- Các router nguồn cũ chưa an toàn hoặc chưa tương thích (`items`, `notification`, `bill_split`, `transaction_history`, `collection`, `expense`) được **ngừng đăng ký trong `app/main.py`**, chưa thể sử dụng.
- Các trang `Fontend/pages/*.html` là cầu nối chuyển hướng vào ứng dụng SPA tại `Fontend/index.html`; code trong `Fontend/js/pages/` là code legacy, không phải luồng tích hợp hiện tại.

## 1. Trước khi chạy

**Sao lưu toàn bộ MySQL trước khi chỉnh sửa schema!** Không chạy script này trên database khác hoặc database production chưa có bản backup.

Mở MySQL Workbench hoặc phpMyAdmin và chọn đúng database đang chạy theo file `.env` (trong dump gốc tên là `quan_ly_quy_nhom`). Thực thi:

`Backend/sql/migrations/20261122_align_dump_with_models.sql`

Script bổ sung cột còn thiếu khi cần, **không `DROP TABLE`, `DELETE` hoặc `TRUNCATE`**. Các script SQL legacy `sql/init.sql` và `sql/debt_payment.sql` không được đóng gói vì có schema mẫu không tương thích; không sử dụng chúng để nâng cấp database thật. Script không nhập lại các bản ghi từ SQL dump. Nó cần quyền `ALTER TABLE` và `CREATE/DROP PROCEDURE`; chọn đúng schema làm database mặc định trước khi chạy. Các nợ cũ không tự gán sang hóa đơn nếu chưa thể đối chiếu.

## 2. Cấu hình Backend

Trong thư mục `Backend/`, sao chép `.env.example` thành `.env` rồi chỉnh `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `SECRET_KEY` và `CORS_ORIGINS`. Đặt `SECRET_KEY` là chuỗi ngẫu nhiên ít nhất 32 ký tự và không đưa lên Git hoặc chat. Với PowerShell:

```powershell
cd Backend
copy .env.example .env
python -c "import secrets;print(secrets.token_urlsafe(48))"
# Chép khóa vừa in vào SECRET_KEY trong .env
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Kiểm tra API tại `http://127.0.0.1:8000/docs`. Backend kết nối MySQL thông qua driver PyMySQL.

## 3. Chạy Frontend

Mở terminal thứ hai, chạy từ thư mục `Fontend/`:

```powershell
cd Fontend
python -m http.server 5500 --bind 127.0.0.1
```

Truy cập **`http://127.0.0.1:5500/`**, không mở bằng `file://`. Tailwind, font, Lucide và ảnh nghệ thuật tải từ CDN, nên cần mạng để hiện giao diện đầy đủ.

## 4. Quy trình kiểm tra thủ công đề xuất

1. Đăng ký tài khoản A → tab User phải hiện **0 nhóm**, số dư/nợ/hóa đơn đều 0.
2. Ở tab Host, tạo nhóm A → người tạo được làm Host, có mã mời.
3. Đăng xuất, đăng ký tài khoản B → không thấy nhóm của A.
4. Nhập mã mời vào form **Nhóm của tôi đang tham gia** → B vào được nhóm A.
5. A ghi một giao dịch thu quỹ và tạo hóa đơn **chia đều** → B xem được số dư/hóa đơn và chỉ công nợ của mình.
6. B thử tạo giao dịch với quyền thành viên → Backend phải trả `403`.
7. A đăng xuất; token cũ không truy cập được `/auth/me`.

## 5. Kiểm thử đã làm và giới hạn

- `python -m compileall Backend/app` và `node --check` các JavaScript mới: đạt.
- Bộ test bằng **SQLite trong bộ nhớ** (mô phỏng bcrypt) dùng FastAPI TestClient: tài khoản mới trống, phân quyền nhóm, xem dữ liệu liên quan, ghi quỹ Host, chia đều, tạo nợ, thu hồi JWT: đạt.
- Test JavaScript kiểm tra dữ liệu không rò qua phiên tài khoản: đạt.
- **Chưa thể chạy thử với MySQL trên máy của bạn, chưa thực hiện E2E bằng trình duyệt thật.** Do đó chưa khẳng định đã vận hành toàn bộ. Sau khi cài trên máy của bạn, chạy theo checklist và kiểm tra bảng MySQL sau từng thao tác.

## Cảnh báo bảo mật

Không công khai SQL dump gốc vì có dữ liệu tài khoản và mật khẩu băm. Backend gốc còn có script tạo Admin demo với mật khẩu cố định; script đó đã được loại khỏi ZIP. Nếu từng chạy seed cũ, **đổi mật khẩu tất cả tài khoản mẫu/Admin hoặc xóa các tài khoản mẫu** trước khi triển khai ra mạng. Backend vẫn cần audit bảo mật toàn diện, đặc biệt trước khi đưa lên Internet với dữ liệu tài chính thật. Không dùng thanh toán thật khi QR/đối soát chưa được triển khai an toàn.
