from tools.context_extraction import extract_context
from tools.metadata_filter import filter_by_metadata
from tools.region_resolution import resolve_region
from utils.location_resolver import location_resolver
from tools import cultural_search

def test_context_and_city_region_tools():
    context = extract_context("I am a student attending a wedding dinner dish")
    assert context["user_role"] == "Student"
    assert context["category"] == "Food"
    assert resolve_region("I will be in Jeddah") == "West"

def test_metadata_filter_prefers_general_records_without_requested_region():
    records = [{"region": "East", "category": "Food"}, {"region": "General", "category": "Food"}]
    assert filter_by_metadata(records, None) == records


def test_location_resolver_detects_city_and_planning_region(): 
    location = location_resolver.find_in_query( "What are the traditions in Dammam?" ) 
    assert location is not None 
    assert location["city"] == "Dammam" 
    assert location["administrative_region"] == "Eastern Province" 
    assert location["planning_region"] == "Eastern"



def test_cultural_search_resolves_dammam_to_eastern(monkeypatch):
    captured = {}

    def fake_search(query, region=None, limit=5):
        captured["query"] = query
        captured["region"] = region
        return []

    monkeypatch.setattr(
        cultural_search.store,
        "search",
        fake_search,
    )

    cultural_search.search_cultural_knowledge.invoke(
        "What are the traditions in Dammam?"
    )

    assert captured["query"] == "What are the traditions in Dammam?"
    assert captured["region"] == "Eastern"