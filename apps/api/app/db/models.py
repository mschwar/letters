from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, Enum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"


class SourceKind(str, Enum):
    watch_folder = "watch_folder"
    eml_import = "eml_import"
    manual_upload = "manual_upload"


class DocumentStatus(str, Enum):
    ingested = "ingested"
    indexed = "indexed"
    needs_review = "needs_review"
    archived = "archived"
    failed = "failed"


class FileKind(str, Enum):
    original = "original"
    pdf = "pdf"
    txt = "txt"
    md = "md"
    docx = "docx"


class LinkType(str, Enum):
    references = "references"
    clarifies = "clarifies"
    supersedes = "supersedes"
    related = "related"


class LinkState(str, Enum):
    suggested = "suggested"
    confirmed = "confirmed"
    rejected = "rejected"


class LinkCreatedBy(str, Enum):
    system = "system"
    user = "user"


class TagAssignedBy(str, Enum):
    system = "system"
    user = "user"


class IngestionTrigger(str, Enum):
    file_watch = "file_watch"
    eml_import = "eml_import"
    manual_upload = "manual_upload"
    retry = "retry"


class IngestionStatus(str, Enum):
    received = "received"
    processed = "processed"
    failed = "failed"


class RunStatus(str, Enum):
    running = "running"
    success = "success"
    partial_failed = "partial_failed"
    failed = "failed"


class StepStatus(str, Enum):
    running = "running"
    success = "success"
    failed = "failed"
    skipped = "skipped"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(
        String,
        CheckConstraint("role IN ('owner','editor','viewer')"),
        nullable=False,
    )
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(
        String,
        CheckConstraint("kind IN ('watch_folder','eml_import','manual_upload')"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("sha256", name="uq_documents_sha256"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    canonical_title: Mapped[str | None] = mapped_column(String)
    source_name: Mapped[str | None] = mapped_column(String)
    audience: Mapped[str | None] = mapped_column(String)
    document_date: Mapped[str | None] = mapped_column(String)
    document_type: Mapped[str | None] = mapped_column(String)
    summary_one_sentence: Mapped[str | None] = mapped_column(Text)
    confidence_overall: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("0")
    )
    status: Mapped[str] = mapped_column(
        String,
        CheckConstraint(
            "status IN ('ingested','indexed','needs_review','archived','failed')"
        ),
        nullable=False,
    )
    archive_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class DocumentFile(Base):
    __tablename__ = "document_files"
    __table_args__ = (
        UniqueConstraint("document_id", "file_kind", name="uq_document_files_doc_kind"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    file_kind: Mapped[str] = mapped_column(
        String,
        CheckConstraint("file_kind IN ('original','pdf','txt','md','docx')"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String)
    bytes: Mapped[int | None] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class DocumentMetadataVersion(Base):
    __tablename__ = "document_metadata_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_metadata_version"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    edited_by_user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id")
    )
    edit_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    parent_tag_id: Mapped[str | None] = mapped_column(String, ForeignKey("tags.id"))
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class TagAlias(Base):
    __tablename__ = "tag_aliases"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tag_id: Mapped[str] = mapped_column(
        String, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class DocumentTag(Base):
    __tablename__ = "document_tags"
    __table_args__ = (
        CheckConstraint("assigned_by IN ('system','user')"),
    )

    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[str] = mapped_column(
        String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("1"))
    assigned_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class DocumentLink(Base):
    __tablename__ = "document_links"
    __table_args__ = (
        UniqueConstraint("from_document_id", "to_document_id", "link_type", name="uq_document_links"),
        CheckConstraint("link_type IN ('references','clarifies','supersedes','related')"),
        CheckConstraint("state IN ('suggested','confirmed','rejected')"),
        CheckConstraint("created_by IN ('system','user')"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    from_document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    to_document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    link_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("1"))
    state: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class IngestionEvent(Base):
    __tablename__ = "ingestion_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str | None] = mapped_column(String, ForeignKey("sources.id"))
    trigger_type: Mapped[str] = mapped_column(
        String,
        CheckConstraint("trigger_type IN ('file_watch','eml_import','manual_upload','retry')"),
        nullable=False,
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    event_time: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        CheckConstraint("status IN ('received','processed','failed')"),
        nullable=False,
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ingestion_event_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("ingestion_events.id")
    )
    document_id: Mapped[str | None] = mapped_column(String, ForeignKey("documents.id"))
    status: Mapped[str] = mapped_column(
        String,
        CheckConstraint("status IN ('running','success','partial_failed','failed')"),
        nullable=False,
    )
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    ended_at: Mapped[str | None] = mapped_column(Text)
    error_summary: Mapped[str | None] = mapped_column(Text)


class PipelineStep(Base):
    __tablename__ = "pipeline_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    step_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        CheckConstraint("status IN ('running','success','failed','skipped')"),
        nullable=False,
    )
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    ended_at: Mapped[str | None] = mapped_column(Text)
    logs: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    actor_user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id")
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    object_type: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    before_json: Mapped[str | None] = mapped_column(Text)
    after_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(
        Text, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
