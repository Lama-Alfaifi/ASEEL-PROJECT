from pathlib import Path
from retrieval.ingestion import load_csv

def test_load_csv_normalizes_optional_schema(tmp_path: Path):
    source = tmp_path / "EAST.csv"
    source.write_text("Question,Choices,Answer,Question Type,Domain,Category\nWhat food?,–,Example dish,Open-ended,Common,Food\n", encoding="utf-8")
    rows = load_csv(source)
    assert len(rows) == 1
    assert rows[0].region == "East"
    assert rows[0].answer == "Example dish"