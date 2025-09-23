import typer
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import glob
import uuid
from datetime import datetime

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from src.server.db.config import resolve_sync_database_url
from src.server.db.models import Base, Document, Annotation, TrainingRun, AnnotationStatus # Added AnnotationStatus
from tools.feedback_utils import read_review_csv # Assuming this returns a pandas DataFrame

# --- Database Setup (Synchronous) ---
SYNC_DATABASE_URL = resolve_sync_database_url()
engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure tables are created (for standalone script, useful for initial setup)
# In a migration context, tables should already exist.
# Base.metadata.create_all(engine)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(help="Migrate legacy review CSV data to the database.")

def get_db():
    """Dependency for getting a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def map_csv_row_to_db_objects(
    row: pd.Series,
    training_run: TrainingRun,
    csv_filename: str
) -> Optional[Dict[str, Any]]:
    """
    Maps a single CSV row to Document and Annotation objects.
    This is a placeholder and needs to be adapted to the actual CSV structure
    and database model requirements.
    """
    try:
        # Example mapping - adjust based on your actual CSV columns and DB schema
        # You'll need to infer or generate document_id if not present in CSV
        document_id = row.get('document_id', str(uuid.uuid4()))
        filename = row.get('document_name', f"Migrated from {csv_filename}")
        storage_path = f"migrated_documents/{document_id}.pdf" # Placeholder for storage_path

        document = Document(
            id=document_id,
            filename=filename,
            storage_path=storage_path,
            # Add other document fields as necessary
        )

        annotations = []
        # Iterate through columns to find field_name, pred_value, gold_value, status
        # This part is highly dependent on how your CSV stores annotations
        # Example: 'contract_name_pred', 'contract_name_gold', 'contract_name_status'
        for col in row.index:
            if col.endswith('_pred'):
                field_name = col.replace('_pred', '')
                pred_value = row[col]
                gold_value = row.get(f'{field_name}_gold', None)
                status = row.get(f'{field_name}_status', 'PENDING') # Default status

                if pd.isna(pred_value) and pd.isna(gold_value):
                    continue # Skip if no prediction or gold value

                # Construct the payload for the annotation
                payload = {
                    "field_name": field_name,
                    "predicted_value": str(pred_value) if pd.notna(pred_value) else None,
                    "gold_value": str(gold_value) if pd.notna(gold_value) else None,
                }

                # Map status string to AnnotationStatus enum
                annotation_status = AnnotationStatus.pending # Default
                if status.upper() in [s.value for s in AnnotationStatus]:
                    annotation_status = AnnotationStatus(status.upper())
                else:
                    logger.warning(f"Unknown annotation status '{status}'. Defaulting to PENDING.")


                annotation = Annotation(
                    id=str(uuid.uuid4()),
                    document_id=document.id,
                    status=annotation_status,
                    latest_payload=payload,
                    # Add other annotation fields as necessary
                )
                annotations.append(annotation)

        return {"document": document, "annotations": annotations}
    except Exception as e:
        logger.error(f"Error mapping CSV row to DB objects for row: {row.to_dict()}. Error: {e}")
        return None

@app.command()
def migrate(
    csv_glob_pattern: str = typer.Argument(..., help="Glob pattern to find review CSV files (e.g., 'reports/feedback/*.csv')."),
    training_run_name: str = typer.Option(..., "--training-run-name", "-t", help="Name for the new training run to associate migrated documents."),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Run without committing changes to the database."),
    report_dir: Optional[Path] = typer.Option(None, "--report-dir", "-r", help="Directory to save the migration report."),
):
    """
    Migrates legacy review CSV data to the database.
    """
    logger.info(f"Starting migration with CSV glob: '{csv_glob_pattern}', training run name: '{training_run_name}', dry run: {dry_run}")

    if report_dir and not report_dir.exists():
        report_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created report directory: {report_dir}")

    csv_files = glob.glob(csv_glob_pattern)
    if not csv_files:
        logger.warning(f"No CSV files found matching pattern: {csv_glob_pattern}")
        typer.echo(f"No CSV files found matching pattern: {csv_glob_pattern}")
        raise typer.Exit(code=1)

    total_documents_migrated = 0
    total_annotations_migrated = 0
    total_errors = 0
    migration_reports: List[Dict[str, Any]] = []

    with next(get_db()) as db:
        # Create a new TrainingRun for this migration
        training_run = TrainingRun(
            id=str(uuid.uuid4()),
            notes=training_run_name,
            created_at=datetime.utcnow(),
            # Add other training run fields as necessary
        )
        if not dry_run:
            db.add(training_run)
            try:
                db.commit()
                db.refresh(training_run)
                logger.info(f"Created new TrainingRun: {training_run.notes} (ID: {training_run.id})")
            except IntegrityError:
                db.rollback()
                logger.error(f"TrainingRun with notes '{training_run_name}' already exists. Please choose a unique name.")
                raise typer.Exit(code=1)
        else:
            logger.info(f"Dry run: Would create TrainingRun: {training_run_name} (ID: {training_run.id})")

        for csv_file_path_str in csv_files:
            csv_file_path = Path(csv_file_path_str)
            logger.info(f"Processing CSV file: {csv_file_path}")
            file_documents_migrated = 0
            file_annotations_migrated = 0
            file_errors = 0
            file_report: Dict[str, Any] = {
                "csv_file": str(csv_file_path),
                "status": "SUCCESS",
                "documents_migrated": 0,
                "annotations_migrated": 0,
                "errors": [],
            }

            try:
                df = read_review_csv(csv_file_path)
                if df.empty:
                    logger.warning(f"CSV file {csv_file_path} is empty. Skipping.")
                    file_report["status"] = "SKIPPED_EMPTY"
                    migration_reports.append(file_report)
                    continue

                for index, row in df.iterrows():
                    mapped_objects = map_csv_row_to_db_objects(row, training_run, csv_file_path.name)
                    if mapped_objects:
                        document = mapped_objects["document"]
                        annotations = mapped_objects["annotations"]

                        if not dry_run:
                            db.add(document)
                            db.add_all(annotations)
                            training_run.documents.append(document) # Establish relationship
                            try:
                                db.commit()
                                db.refresh(document)
                                file_documents_migrated += 1
                                file_annotations_migrated += len(annotations)
                            except IntegrityError as e:
                                db.rollback()
                                file_errors += 1
                                error_msg = f"Integrity error for document {document.id} from row {index}: {e}"
                                logger.error(error_msg)
                                file_report["errors"].append(error_msg)
                            except Exception as e:
                                db.rollback()
                                file_errors += 1
                                error_msg = f"Unexpected error for document {document.id} from row {index}: {e}"
                                logger.error(error_msg)
                                file_report["errors"].append(error_msg)
                        else:
                            logger.info(f"Dry run: Would migrate document {document.id} with {len(annotations)} annotations from row {index}")
                            file_documents_migrated += 1
                            file_annotations_migrated += len(annotations)
                    else:
                        file_errors += 1
                        error_msg = f"Failed to map row {index} from {csv_file_path} to DB objects."
                        logger.error(error_msg)
                        file_report["errors"].append(error_msg)

            except Exception as e:
                file_errors += 1
                error_msg = f"Error processing CSV file {csv_file_path}: {e}"
                logger.error(error_msg)
                file_report["status"] = "FAILED"
                file_report["errors"].append(error_msg)

            file_report["documents_migrated"] = file_documents_migrated
            file_report["annotations_migrated"] = file_annotations_migrated
            if file_errors > 0:
                file_report["status"] = "FAILED_PARTIAL" if file_documents_migrated > 0 else "FAILED"
            migration_reports.append(file_report)

            total_documents_migrated += file_documents_migrated
            total_annotations_migrated += file_annotations_migrated
            total_errors += file_errors

    # --- Final Report ---
    typer.echo("""
--- Migration Summary ---""")
    typer.echo(f"Total CSV files processed: {len(csv_files)}")
    typer.echo(f"Total documents migrated: {total_documents_migrated}")
    typer.echo(f"Total annotations migrated: {total_annotations_migrated}")
    typer.echo(f"Total errors encountered: {total_errors}")

    if report_dir:
        report_filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        full_report_path = report_dir / report_filename
        import json
        with open(full_report_path, 'w') as f:
            json.dump(migration_reports, f, indent=2)
        typer.echo(f"Detailed report saved to: {full_report_path}")

    if total_errors > 0:
        typer.echo("Migration completed with errors. Please check the logs and detailed report.")
        raise typer.Exit(code=1)
    else:
        typer.echo("Migration completed successfully.")

if __name__ == "__main__":
    app()
