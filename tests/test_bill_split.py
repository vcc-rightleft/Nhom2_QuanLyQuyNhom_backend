import pytest
from app.crud.bill import calculate_equal_split


def test_split_100k_for_3_participants():
    shares = calculate_equal_split(total_amount=100000, participant_ids=[1, 2, 3], payer_id=1)
    assert shares[1] == 34000
    assert shares[2] == 33000
    assert shares[3] == 33000
    assert sum(shares.values()) == 100000


def test_split_for_1_participant():
    shares = calculate_equal_split(total_amount=100000, participant_ids=[1], payer_id=1)
    assert shares == {1: 100000}


def test_split_even_amount():
    shares = calculate_equal_split(total_amount=90000, participant_ids=[1, 2, 3], payer_id=2)
    assert shares == {1: 30000, 2: 30000, 3: 30000}