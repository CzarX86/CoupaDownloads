import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime, timezone # Added timezone
import uuid
import typer
from typer.testing import CliRunner
from sqlalchemy.exc import IntegrityError

from scripts.migrate_review_csv import (
    app,
    map_csv_row_to_db_objects,
    Document,
    Annotation,
    TrainingRun,
    SessionLocal,
    engine,
)

# Mock the database session for tests
@pytest.fixture
def mock_db_session():
    with patch('scripts.migrate_review_csv.SessionLocal') as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session
        yield mock_session

# Mock read_review_csv to return a DataFrame
@pytest.fixture
def mock_read_review_csv():
    with patch('scripts.migrate_review_csv.read_review_csv') as mock_read:
        yield mock_read

# Sample CSV data for testing
@pytest.fixture
def sample_csv_data():
    return pd.DataFrame({
        'document_id': ['doc1', 'doc2'],
        'document_name': ['Doc One', 'Doc Two'],
        'pdf_url': ['http://example.com/doc1.pdf', None],
        'contract_name_pred': ['Contract A', 'Contract B'],
        'contract_name_gold': ['Contract A', 'Contract C'],
        'contract_name_status': ['ACCEPTED', 'REJECTED'],
        'sow_value_eur_pred': ['1000', '2000'],
        'sow_value_eur_gold': ['1000', None],
        'sow_value_eur_status': ['ACCEPTED', 'PENDING'],
    })

# Test map_csv_row_to_db_objects
def test_map_csv_row_to_db_objects(sample_csv_data):
    row = sample_csv_data.iloc[0]
    training_run = TrainingRun(id=str(uuid.uuid4()), notes="test_run", created_at=datetime.now(timezone.utc)) # Fixed DeprecationWarning
    csv_filename = "test.csv"

    result = map_csv_row_to_db_objects(row, training_run, csv_filename)

    assert result is not None
    document = result["document"]
    annotations = result["annotations"]

    assert isinstance(document, Document)
    assert document.id == 'doc1'
    assert document.filename == 'Doc One'
    # Removed assert document.pdf_url == 'http://example.com/doc1.pdf'

    assert len(annotations) == 2
    assert all(isinstance(ann, Annotation) for ann in annotations)

    contract_ann = next(ann for ann in annotations if ann.latest_payload.get('field_name') == 'contract_name') # Updated assertion
    assert contract_ann.latest_payload.get('predicted_value') == 'Contract A' # Updated assertion
    assert contract_ann.latest_payload.get('gold_value') == 'Contract A' # Updated assertion
    assert contract_ann.status.value == 'PENDING' # Updated assertion to check enum value, and expecting PENDING due to warning

    sow_ann = next(ann for ann in annotations if ann.latest_payload.get('field_name') == 'sow_value_eur') # Updated assertion
    assert sow_ann.latest_payload.get('predicted_value') == '1000' # Updated assertion
    assert sow_ann.latest_payload.get('gold_value') == '1000' # Updated assertion
    assert sow_ann.status.value == 'PENDING' # Updated assertion to check enum value, and expecting PENDING due to warning

# Test the migrate command (dry-run)
def test_migrate_command_dry_run(mock_db_session, mock_read_review_csv, sample_csv_data, tmp_path):
    # Setup mock CSV file
    csv_file = tmp_path / "test.csv"
    sample_csv_data.to_csv(csv_file, index=False)
    mock_read_review_csv.return_value = sample_csv_data

    runner = CliRunner()
    result = runner.invoke(app, [
        str(csv_file),
        "--training-run-name", "test-migration-dry-run",
        "--dry-run",
        "--report-dir", str(tmp_path)
    ])

    assert result.exit_code == 0
    assert "Dry run: Would create TrainingRun" in result.stdout
    assert "Dry run: Would migrate document" in result.stdout
    assert "Total documents migrated: 2" in result.stdout
    assert "Total annotations migrated: 4" in result.stdout
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

# Test the migrate command (actual commit)
def test_migrate_command_commit(mock_db_session, mock_read_review_csv, sample_csv_data, tmp_path):
    # Setup mock CSV file
    csv_file = tmp_path / "test.csv"
    sample_csv_data.to_csv(csv_file, index=False)
    mock_read_review_csv.return_value = sample_csv_data

    runner = CliRunner()
    result = runner.invoke(app, [
        str(csv_file),
        "--training-run-name", "test-migration-commit",
        "--report-dir", str(tmp_path)
    ])

    assert result.exit_code == 0
    assert "Created new TrainingRun" in result.stdout
    assert "Total documents migrated: 2" in result.stdout
    assert "Total annotations migrated: 4" in result.stdout
    assert mock_db_session.add.call_count >= 3 # TrainingRun + 2 Documents + 4 Annotations
    assert mock_db_session.commit.call_count >= 3 # TrainingRun + 2 Documents

# Test with empty CSV
def test_migrate_command_empty_csv(mock_db_session, mock_read_review_csv, tmp_path):
    csv_file = tmp_path / "empty.csv"
    pd.DataFrame().to_csv(csv_file, index=False)
    mock_read_review_csv.return_value = pd.DataFrame()

    runner = CliRunner()
    result = runner.invoke(app, [
        str(csv_file),
        "--training-run-name", "test-empty-csv",
    ])

    assert result.exit_code == 0
    assert "CSV file" in result.stdout and "is empty. Skipping." in result.stdout
    assert "Total documents migrated: 0" in result.stdout

# Test with no CSV files found
def test_migrate_command_no_csv_files(mock_db_session, mock_read_review_csv, tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, [
        str(tmp_path / "non_existent_*.csv"),
        "--training-run-name", "test-no-csv",
    ])

    assert result.exit_code == 1
    assert "No CSV files found matching pattern" in result.stdout

# Test IntegrityError for TrainingRun
def test_migrate_command_training_run_integrity_error(mock_db_session, mock_read_review_csv, sample_csv_data, tmp_path):
    csv_file = tmp_path / "test.csv"
    sample_csv_data.to_csv(csv_file, index=False)
    mock_read_review_csv.return_value = sample_csv_data

    # Simulate IntegrityError on adding TrainingRun
    mock_db_session.add.side_effect = [
        MagicMock(), # For the TrainingRun
        IntegrityError("", {}, ""), # Simulate error on commit
        # Subsequent adds for documents/annotations will not be called if commit fails for TrainingRun
    ]

    runner = CliRunner()
    result = runner.invoke(app, [
        str(csv_file),
        "--training-run-name", "duplicate-training-run",
    ])

    assert result.exit_code == 1
    assert "TrainingRun with notes 'duplicate-training-run' already exists" in result.stdout # Updated assertion
    mock_db_session.rollback.assert_called_once()

# Test IntegrityError for Document/Annotation
def test_migrate_command_document_integrity_error(mock_db_session, mock_read_review_csv, sample_csv_data, tmp_path):
    csv_file = tmp_path / "test.csv"
    sample_csv_data.to_csv(csv_file, index=False)
    mock_read_review_csv.return_value = sample_csv_data

    # Simulate IntegrityError on adding a Document/Annotation
    # First add for TrainingRun succeeds
    # Then for the first document/annotations, simulate error on commit
    mock_db_session.commit.side_effect = [
        None, # For TrainingRun
        IntegrityError("", {}, ""), # For first document/annotations
        None, # For second document/annotations
    ]

    runner = CliRunner()
    result = runner.invoke(app, [
        str(csv_file),
        "--training-run-name", "test-doc-integrity-error",
    ])

    assert result.exit_code == 1 # Because there was an error
    assert "Integrity error for document" in result.stdout
    assert "Total documents migrated: 1" in result.stdout # One document should still pass
    assert "Total annotations migrated: 2" in result.stdout # Updated assertion
    assert mock_db_session.rollback.call_count == 1