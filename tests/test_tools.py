from tools.context_extraction import extract_context
from tools.metadata_filter import filter_by_metadata
from tools.region_resolution import resolve_region

def test_context_and_city_region_tools():
    context = extract_context("I am a student attending a wedding dinner dish")
    assert context["user_role"] == "Student"
    assert context["category"] == "Food"
    assert resolve_region("I will be in Jeddah") == "West"

def test_metadata_filter_prefers_general_records_without_requested_region():
    records = [{"region": "East", "category": "Food"}, {"region": "General", "category": "Food"}]
    assert filter_by_metadata(records, None) == records