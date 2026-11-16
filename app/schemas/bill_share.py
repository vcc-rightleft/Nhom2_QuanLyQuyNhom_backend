from pydantic import BaseModel


class BillShareBase(BaseModel):
    bill_id: int
    member_id: int
    amount: int


class BillShareCreate(BillShareBase):
    pass


class BillShareResponse(BillShareBase):
    id: int

    class Config:
        from_attributes = True