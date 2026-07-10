import pytest
import csv
from pathlib import Path

from build_your_own_rag.models import SourceDocument, ExtractionStrategy
from build_your_own_rag.parsing.csv_parser import parse_csv

@pytest.fixture
def sample_csv_file(tmp_path):
    file_path = tmp_path / "test.csv"
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Age", "City"])
        writer.writerow(["Alice", "30", "New York"])
        writer.writerow(["Bob", "25", "San Francisco"])
        # Add an empty row
        writer.writerow([])
        writer.writerow(["Charlie", "", "London"])
    return file_path


def test_parse_csv(sample_csv_file):
    source = SourceDocument(
        source_id="test_id_csv",
        source_type="local_csv",
        path=sample_csv_file,
        filename="test.csv",
        extension="csv",
        size_bytes=sample_csv_file.stat().st_size,
        mime_type="text/csv",
    )
    
    parsed = parse_csv(source, strategy=ExtractionStrategy.FAST)
    
    assert parsed.parser_name == "csv_native"
    assert parsed.source == source
    assert parsed.status == "success"
    
    # Check that it prepended headers properly
    assert "Name: Alice | Age: 30 | City: New York" in parsed.text
    assert "Name: Bob | Age: 25 | City: San Francisco" in parsed.text
    
    # Check handling of missing cells
    assert "Name: Charlie | City: London" in parsed.text
    assert "Age" not in parsed.text.split("Charlie")[1]
    
    csv_meta = parsed.metadata.format_specific["csv"]
    assert csv_meta["row_count"] == 4  # 3 data rows + 1 empty row read
    assert csv_meta["column_count"] == 3


@pytest.fixture
def complex_csv_file():
    file_path = Path(__file__).parent.parent / "data" / "test_docs" / "complex_data.csv"
    if not file_path.exists():
        pytest.skip("complex_data.csv not generated. Run generate_dummy.py first.")
    return file_path

def test_parse_complex_csv(complex_csv_file):
    source = SourceDocument(
        source_id="test_complex_csv",
        source_type="local_csv",
        path=complex_csv_file,
        filename="complex_data.csv",
        extension="csv",
        size_bytes=complex_csv_file.stat().st_size,
        mime_type="text/csv",
    )
    
    parsed = parse_csv(source, strategy=ExtractionStrategy.FAST)
    
    assert parsed.parser_name == "csv_native"
    assert parsed.status == "success"
    
    # Check that commas inside quotes were handled correctly
    assert "Description: A widget, with commas, inside." in parsed.text
    
    # Check multiline
    assert "Multiline\nDescription\nHere!" in parsed.text
    
    # Check that missing price is handled (empty cell skipped)
    # The cell is empty in Widget B row, so "Price" shouldn't be extracted for it
    block_b = [b for b in parsed.text.split("\n\n") if "Widget B" in b][0]
    assert "Price" not in block_b
    
    csv_meta = parsed.metadata.format_specific["csv"]
    assert csv_meta["row_count"] == 5 # 1 header, 3 data rows, 1 empty row (the script skipped writing the completely empty fields row since we generated it manually in python script, wait, we used writerow(["","","",""]) which has 4 empty fields).
    assert csv_meta["column_count"] == 4
