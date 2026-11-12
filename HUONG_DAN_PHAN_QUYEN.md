# Hướng dẫn gắn Phân quyền (RBAC) vào API - Task T3CC6B8

Import các dependency dùng chung từ `app.core.deps`:

```python
from fastapi import APIRouter, Depends
from app.models.user import User
from app.core.deps import (
    get_current_user,
    require_admin,
    require_group_member,
    require_group_host,
)
```

## 1. API yêu cầu đăng nhập
Tự động xác thực JWT và chặn ngay nếu tài khoản bị khóa (`LOCKED` -> trả lỗi `403`):

```python
@router.get("/profile")
def my_profile(current_user: User = Depends(get_current_user)):
    return current_user
```

## 2. API chỉ dành cho Admin hệ thống
Chỉ cho phép user có `role = ADMIN` truy cập (nếu là `USER` -> trả lỗi `403`):

```python
@router.get("/admin/users")
def list_users(admin: User = Depends(require_admin)):
    return {"admin": admin.email}
```

## 3. API yêu cầu là Thành viên của nhóm quỹ
Đường dẫn URL bắt buộc phải chứa biến `{group_id}` để dependency tự động lấy và kiểm tra:

```python
@router.get("/groups/{group_id}/bills")
def get_bills(group_id: int, current_user: User = Depends(require_group_member)):
    return {"group_id": group_id, "user_id": current_user.id}
```

## 4. API chỉ dành cho Trưởng nhóm (Host) của nhóm quỹ
Đường dẫn URL bắt buộc phải chứa biến `{group_id}` để kiểm tra quyền `HOST`:

```python
@router.post("/groups/{group_id}/bills")
def create_bill(group_id: int, host_user: User = Depends(require_group_host)):
    return {"group_id": group_id, "host_id": host_user.id}
```