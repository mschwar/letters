"""Initial schema

Revision ID: 0001_initial
Revises: None
Create Date: 2026-02-08 00:10:00
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("PRAGMA foreign_keys=ON")

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.String(),
            sa.CheckConstraint("role IN ('owner','editor','viewer')"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "kind",
            sa.String(),
            sa.CheckConstraint("kind IN ('watch_folder','eml_import','manual_upload')"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("canonical_title", sa.String()),
        sa.Column("source_name", sa.String()),
        sa.Column("audience", sa.String()),
        sa.Column("document_date", sa.String()),
        sa.Column("document_type", sa.String()),
        sa.Column("summary_one_sentence", sa.Text()),
        sa.Column("confidence_overall", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            sa.CheckConstraint(
                "status IN ('ingested','indexed','needs_review','archived','failed')"
            ),
            nullable=False,
        ),
        sa.Column("archive_path", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.UniqueConstraint("sha256", name="uq_documents_sha256"),
    )

    op.create_table(
        "document_files",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_kind",
            sa.String(),
            sa.CheckConstraint("file_kind IN ('original','pdf','txt','md','docx')"),
            nullable=False,
        ),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String()),
        sa.Column("bytes", sa.Integer()),
        sa.Column("checksum_sha256", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.UniqueConstraint("document_id", "file_kind", name="uq_document_files_doc_kind"),
    )

    op.create_table(
        "document_metadata_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("edited_by_user_id", sa.String(), sa.ForeignKey("users.id")),
        sa.Column("edit_reason", sa.Text()),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.UniqueConstraint("document_id", "version_no", name="uq_metadata_version"),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("key", sa.String(), nullable=False, unique=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("parent_tag_id", sa.String(), sa.ForeignKey("tags.id")),
        sa.Column("is_active", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )

    op.create_table(
        "tag_aliases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "tag_id",
            sa.String(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )

    op.create_table(
        "document_tags",
        sa.Column(
            "document_id",
            sa.String(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.String(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("confidence", sa.Float(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "assigned_by",
            sa.String(),
            sa.CheckConstraint("assigned_by IN ('system','user')"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )

    op.create_table(
        "document_links",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "from_document_id",
            sa.String(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_document_id",
            sa.String(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "link_type",
            sa.String(),
            sa.CheckConstraint("link_type IN ('references','clarifies','supersedes','related')"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "state",
            sa.String(),
            sa.CheckConstraint("state IN ('suggested','confirmed','rejected')"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.String(),
            sa.CheckConstraint("created_by IN ('system','user')"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.UniqueConstraint("from_document_id", "to_document_id", "link_type", name="uq_document_links"),
    )

    op.create_table(
        "ingestion_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), sa.ForeignKey("sources.id")),
        sa.Column(
            "trigger_type",
            sa.String(),
            sa.CheckConstraint(
                "trigger_type IN ('file_watch','eml_import','manual_upload','retry')"
            ),
            nullable=False,
        ),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("event_time", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            sa.CheckConstraint("status IN ('received','processed','failed')"),
            nullable=False,
        ),
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("ingestion_event_id", sa.String(), sa.ForeignKey("ingestion_events.id")),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.id")),
        sa.Column(
            "status",
            sa.String(),
            sa.CheckConstraint("status IN ('running','success','partial_failed','failed')"),
            nullable=False,
        ),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("ended_at", sa.Text()),
        sa.Column("error_summary", sa.Text()),
    )

    op.create_table(
        "pipeline_steps",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(),
            sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            sa.CheckConstraint("status IN ('running','success','failed','skipped')"),
            nullable=False,
        ),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("ended_at", sa.Text()),
        sa.Column("logs", sa.Text()),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("actor_user_id", sa.String(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("object_type", sa.String(), nullable=False),
        sa.Column("object_id", sa.String(), nullable=False),
        sa.Column("before_json", sa.Text()),
        sa.Column("after_json", sa.Text()),
        sa.Column(
            "created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )

    op.execute(
        "CREATE VIRTUAL TABLE document_fts USING fts5("
        "document_id UNINDEXED, title, summary, full_text, source_name, tags)"
    )

    op.create_index("idx_documents_date", "documents", ["document_date"])
    op.create_index("idx_documents_source", "documents", ["source_name"])
    op.create_index("idx_documents_status", "documents", ["status"])
    op.create_index("idx_document_links_from", "document_links", ["from_document_id"])
    op.create_index("idx_document_links_to", "document_links", ["to_document_id"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_fts")

    op.drop_index("idx_document_links_to", table_name="document_links")
    op.drop_index("idx_document_links_from", table_name="document_links")
    op.drop_index("idx_documents_status", table_name="documents")
    op.drop_index("idx_documents_source", table_name="documents")
    op.drop_index("idx_documents_date", table_name="documents")

    op.drop_table("audit_events")
    op.drop_table("pipeline_steps")
    op.drop_table("pipeline_runs")
    op.drop_table("ingestion_events")
    op.drop_table("document_links")
    op.drop_table("document_tags")
    op.drop_table("tag_aliases")
    op.drop_table("tags")
    op.drop_table("document_metadata_versions")
    op.drop_table("document_files")
    op.drop_table("documents")
    op.drop_table("sources")
    op.drop_table("users")
