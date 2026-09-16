from utils.location_resolver import location_resolver


def test_dammam_resolves_to_eastern():
    location = location_resolver.find_in_query(
        "What are the traditions in Dammam?"
    )

    assert location is not None
    assert location["city"] == "Dammam"
    assert location["administrative_region"] == "Eastern Province"
    assert location["planning_region"] == "Eastern"


def test_jeddah_resolves_to_western():
    location = location_resolver.find_in_query(
        "What are the traditions in Jeddah?"
    )

    assert location is not None
    assert location["city"] == "Jeddah"
    assert location["administrative_region"] == "Makkah"
    assert location["planning_region"] == "Western"


def test_faifa_resolves_to_southern():
    location = location_resolver.find_in_query(
        "Tell me about Faifa."
    )

    assert location is not None
    assert location["city"] == "Faifa"
    assert location["administrative_region"] == "Jazan"
    assert location["planning_region"] == "Southern"


def test_tabuk_resolves_to_northern():
    location = location_resolver.find_in_query(
        "What is special about Tabuk?"
    )

    assert location is not None
    assert location["city"] == "Tabuk"
    assert location["administrative_region"] == "Tabuk"
    assert location["planning_region"] == "Northern"


def test_riyadh_alias_resolves():
    location = location_resolver.find_in_query(
        "Tell me about Riyadh."
    )

    assert location is not None
    assert location["city"] == "Riyadh City"
    assert location["administrative_region"] == "Riyadh"
    assert location["planning_region"] == "Central"


def test_unknown_city_returns_none():
    location = location_resolver.find_in_query(
        "Tell me about an unknown city."
    )

    assert location is None

