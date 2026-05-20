from datetime import date

from passport_agent.extractor import PassportExtractor


def test_extracts_passport_data_from_mrz_text() -> None:
    payload = b"""
    P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<
    L898902C36UTO7408122F1204159ZE184226B<<<<<10
    """

    data = PassportExtractor().extract(
        payload=payload,
        filename="passport.txt",
        content_type="text/plain",
    )

    assert data.full_name == "ANNA MARIA ERIKSSON"
    assert data.passport_number == "L898902C3"
    assert data.expiry_date == date(2012, 4, 15)
    assert data.confidence == 0.9


def test_extracts_passport_data_from_labelled_text() -> None:
    payload = b"""
    Name: Muzammil Younus
    Passport Number: A1234567
    Date of Expiry: 20 May 2031
    """

    data = PassportExtractor().extract(
        payload=payload,
        filename="passport.txt",
        content_type="text/plain",
    )

    assert data.full_name == "MUZAMMIL YOUNUS"
    assert data.passport_number == "A1234567"
    assert data.expiry_date == date(2031, 5, 20)
