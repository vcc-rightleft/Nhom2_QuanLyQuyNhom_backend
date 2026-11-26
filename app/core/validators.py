def validate_password(password: str) -> str:
    if any(c.isspace() for c in password):
        raise ValueError("Mat khau khong duoc chua khoang trang")

    if not 6 <= len(password) <= 64:
        raise ValueError("Mat khau phai tu 6 den 64 ky tu")

    if len(password.encode("utf-8")) > 72:
        raise ValueError("Mat khau khong duoc vuot qua 72 byte")

    if not any(c.isalpha() for c in password):
        raise ValueError("Mat khau phai co it nhat mot chu cai")

    if not any(c.isdigit() for c in password):
        raise ValueError("Mat khau phai co it nhat mot chu so")

    return password
