"""Initial schema for AI Builder DB workflow."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


annotation_status = sa.Enum(
    "PENDING", "IN_REVIEW", "COMPLETED", name="annotation_status"
)
training_run_status = sa.Enum(
    "PENDING", "RUNNING", "SUCCEEDED", "FAILED", name="training_run_status"
)


def upgrade() -> None:
    annotation_status.create(op.get_bind(), checkfirst=True)
    training_run_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=255)),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("checksum", sa.String(length=128)),
        sa.Column("extra_metadata", sa.JSON()),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_storage_path", sa.String(length=1024), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "extractions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_version_id", sa.String(length=36), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extractor_name", sa.String(length=255), nullable=False),
        sa.Column("predictions", sa.JSON(), nullable=False),
        sa.Column("confidence_summary", sa.JSON()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "annotations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_extraction_id", sa.String(length=36), sa.ForeignKey("extractions.id", ondelete="SET NULL")),
        sa.Column("status", annotation_status, nullable=False, server_default="PENDING"),
        sa.Column("reviewer", sa.String(length=255)),
        sa.Column("notes", sa.Text()),
        sa.Column("latest_payload", sa.JSON()),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_annotations_document_id", "annotations", ["document_id"])

    op.create_table(
        "annotation_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("annotation_id", sa.String(length=36), sa.ForeignKey("annotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("actor", sa.String(length=255)),
        sa.Column("payload", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "training_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("status", training_run_status, nullable=False, server_default="PENDING"),
        sa.Column("triggered_by", sa.String(length=255)),
        sa.Column("parameters", sa.JSON()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("training_run_id", sa.String(length=36), sa.ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_name", sa.String(length=255)),
        sa.Column("version_tag", sa.String(length=255)),
        sa.Column("artifact_path", sa.String(length=1024), nullable=False),
        sa.Column("config_payload", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "metrics",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("training_run_id", sa.String(length=36), sa.ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Float()),
        sa.Column("payload", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "training_run_documents",
        sa.Column("training_run_id", sa.String(length=36), sa.ForeignKey("training_runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("training_run_documents")
    op.drop_table("metrics")
    op.drop_table("model_versions")
    op.drop_table("training_runs")
    op.drop_table("annotation_events")
    op.drop_index("ix_annotations_document_id", table_name="annotations")
    op.drop_table("annotations")
    op.drop_table("extractions")
    op.drop_table("document_versions")
    op.drop_table("documents")

    training_run_status.drop(op.get_bind(), checkfirst=True)
    annotation_status.drop(op.get_bind(), checkfirst=True)
