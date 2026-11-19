from typing import Optional
from pydantic import BaseModel, field_validator


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Tên nhóm không được để trống")

        if len(value) > 255:
            raise ValueError("Tên nhóm tối đa 255 ký tự")

        return value


class JoinGroupRequest(BaseModel):
    invite_code: str


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    invite_code: str
    status: str

    class Config:
        from_attributes = True