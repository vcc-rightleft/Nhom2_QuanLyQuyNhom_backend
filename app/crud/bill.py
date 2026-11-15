from fastapi import HTTPException


def preview_bill(data):

    if data.split_type == "EQUAL":

        count = len(data.participants)

        if count == 0:
            raise HTTPException(
                status_code=400,
                detail="Participants cannot be empty"
            )

        amount_per_user = data.total_amount // count

        return [
            {
                "member_id": member,
                "amount": amount_per_user
            }
            for member in data.participants
        ]

    elif data.split_type == "CUSTOM":

        total_share = sum(
            share.amount
            for share in data.shares
        )

        if total_share != data.total_amount:
            raise HTTPException(
                status_code=400,
                detail="Total share amount does not match bill total amount"
            )

        return [
            {
                "member_id": share.member_id,
                "amount": share.amount
            }
            for share in data.shares
        ]

    elif data.split_type == "BY_ITEM":

        amounts = {}

        for item in data.items:

            item_total = item.unit_price * item.quantity

            split_amount = item_total // len(item.consumers)

            for consumer in item.consumers:
                amounts[consumer] = (
                    amounts.get(consumer, 0)
                    + split_amount
                )

        return [
            {
                "member_id": member_id,
                "amount": amount
            }
            for member_id, amount in amounts.items()
        ]

    raise HTTPException(
        status_code=400,
        detail="Invalid split type"
    )