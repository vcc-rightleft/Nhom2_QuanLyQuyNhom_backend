from fastapi import APIRouter

from app.schemas.bill_preview import BillPreviewRequest
from app.crud.bill import preview_bill


router = APIRouter(
    prefix="/bills",
    tags=["Bills"]
)


@router.post("/preview")
def preview(data: BillPreviewRequest):

    shares = preview_bill(data)

    return {
        "total_amount": data.total_amount,
        "shares": shares
    }
