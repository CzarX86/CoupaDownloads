"""Add jobs table for async job tracking."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_add_jobs_table"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

job_status_enum = sa.Enum("PENDING", "RUNNING", "SUCCEEDED", "FAILED", name="job_status")
job_type_enum = sa.Enum("ANALYSIS", "ANNOTATION", "TRAINING", name="job_type")


def upgrade() -> None:
    bind = op.get_bind()
    job_status_enum.create(bind, checkfirst=True)
    job_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_type", job_type_enum, nullable=False),
        sa.Column("status", job_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("detail", sa.Text()),
        sa.Column("payload", sa.JSON()),
        sa.Column("resource_type", sa.String(length=255)),
        sa.Column("resource_id", sa.String(length=36)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_resource_id", "jobs", ["resource_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_resource_id", table_name="jobs")
    op.drop_table("jobs")
    bind = op.get_bind()
    job_type_enum.drop(bind, checkfirst=True)
    job_status_enum.drop(bind, checkfirst=True)
