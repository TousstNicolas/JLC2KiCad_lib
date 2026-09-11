"""
Unit tests for datasheet link extraction in JLC2KiCadLib.
"""

from JLC2KiCadLib.symbol.symbol import extract_datasheet_link


def test_extract_datasheet_link_with_szlcsc_id():
    data = {
        "result": {
            "title": "CH334P",
            "szlcsc": {
                "id": 6226077,
                "number": "C5373042",
            },
        }
    }
    assert (
        extract_datasheet_link(data)
        == "https://item.szlcsc.com/datasheet/CH334P/6226077.html"
    )


def test_extract_datasheet_link_with_lcsc_id_fallback():
    data = {
        "result": {
            "title": "STM32L431CCU6",
            "lcsc": {
                "id": 1427537,
                "number": "C1337258",
            },
        }
    }
    assert (
        extract_datasheet_link(data)
        == "https://item.szlcsc.com/datasheet/STM32L431CCU6/1427537.html"
    )


def test_extract_datasheet_link_with_special_characters_in_title():
    data = {
        "result": {
            "title": "ESP32-WROOM-32D (4MB)",
            "szlcsc": {
                "id": 12345,
            },
        }
    }
    assert (
        extract_datasheet_link(data)
        == "https://item.szlcsc.com/datasheet/ESP32-WROOM-32D%20%284MB%29/12345.html"
    )


def test_extract_datasheet_link_from_c_para_chinese_key():
    data = {
        "result": {
            "title": "CustomPart",
            "dataStr": {
                "head": {
                    "c_para": {
                        "链接": "https://www.example.com/datasheet.pdf",
                    }
                }
            },
        }
    }
    assert (
        extract_datasheet_link(data)
        == "https://www.example.com/datasheet.pdf"
    )


def test_extract_datasheet_link_from_c_para_english_key():
    data = {
        "result": {
            "title": "CustomPart",
            "dataStr": {
                "head": {
                    "c_para": {
                        "Datasheet": "https://www.example.com/doc.pdf",
                    }
                }
            },
        }
    }
    assert (
        extract_datasheet_link(data)
        == "https://www.example.com/doc.pdf"
    )


def test_extract_datasheet_link_from_szlcsc_url():
    data = {
        "result": {
            "title": "CustomPart",
            "szlcsc": {
                "url": "https://www.szlcsc.com/product/details_123.html",
            },
        }
    }
    assert (
        extract_datasheet_link(data)
        == "https://www.szlcsc.com/product/details_123.html"
    )


def test_extract_datasheet_link_fallback():
    data = {"result": {}}
    assert extract_datasheet_link(data, fallback="http://fallback.com") == "http://fallback.com"
    assert extract_datasheet_link({}, fallback="http://fallback.com") == "http://fallback.com"
    assert extract_datasheet_link(None, fallback="http://fallback.com") == "http://fallback.com"
