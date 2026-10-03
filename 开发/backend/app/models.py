from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Role(str, enum.Enum):
    user = "user"
    reviewer = "reviewer"
    admin = "admin"


class PublicationStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    published = "published"
    rejected = "rejected"
    archived = "archived"


class Difficulty(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


article_tags = Table(
    "article_tags",
    Base.metadata,
    Column("article_id", ForeignKey("wiki_articles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    real_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mcp_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.user, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    github_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    gitee_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text)
    prerequisites: Mapped[str] = mapped_column(Text, default="无")
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty), default=Difficulty.beginner)
    order_index: Mapped[int] = mapped_column(Integer, default=0, index=True)
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus), default=PublicationStatus.draft
    )
    is_standalone: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    directory_collapsible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    lessons: Mapped[list[Lesson]] = relationship(
        back_populates="course", order_by="Lesson.order_index"
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("course_id", "slug"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    objective: Mapped[str] = mapped_column(Text)
    body_markdown: Mapped[str] = mapped_column(Text)
    content_json: Mapped[str] = mapped_column(Text, default='')
    practice: Mapped[str] = mapped_column(Text)
    completion_criteria: Mapped[str] = mapped_column(Text)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus), default=PublicationStatus.draft
    )
    course: Mapped[Course] = relationship(back_populates="lessons")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, index=True)
    parent: Mapped[Category | None] = relationship(back_populates="children", remote_side="Category.id")
    children: Mapped[list[Category]] = relationship(back_populates="parent", order_by="Category.order_index")
    articles: Mapped[list[WikiArticle]] = relationship(back_populates="category", order_by="WikiArticle.order_index")


class ContentCategory(Base):
    __tablename__ = "content_categories"
    __table_args__ = (UniqueConstraint("kind", "slug"), UniqueConstraint("kind", "name"))
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    slug: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(80))
    order_index: Mapped[int] = mapped_column(Integer, default=0, index=True)


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    articles: Mapped[list[WikiArticle]] = relationship(
        secondary=article_tags, back_populates="tags"
    )


class WikiArticle(Base):
    __tablename__ = "wiki_articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    summary: Mapped[str] = mapped_column(Text)
    body_markdown: Mapped[str] = mapped_column(Text)
    content_json: Mapped[str] = mapped_column(Text, default='')
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty), default=Difficulty.beginner, index=True
    )
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, index=True)
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus), default=PublicationStatus.draft, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    category: Mapped[Category] = relationship(back_populates="articles")
    tags: Mapped[list[Tag]] = relationship(secondary=article_tags, back_populates="articles")


class ProjectSubmission(Base):
    __tablename__ = "project_submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True, nullable=True)
    content_category_id: Mapped[int | None] = mapped_column(ForeignKey("content_categories.id", ondelete="SET NULL"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    summary: Mapped[str] = mapped_column(Text)
    description_markdown: Mapped[str] = mapped_column(Text)
    repository_url: Mapped[str] = mapped_column(String(500))
    demo_url: Mapped[str | None] = mapped_column(String(500))
    license_name: Mapped[str] = mapped_column(String(80), default="MIT")
    tech_stack: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus), default=PublicationStatus.draft, index=True
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_note: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    owner: Mapped[User] = relationship()
    category: Mapped[Category | None] = relationship()
    content_category: Mapped[ContentCategory | None] = relationship()


class SkillPackage(Base):
    __tablename__ = "skill_packages"
    review_note: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True, nullable=True)
    content_category_id: Mapped[int | None] = mapped_column(ForeignKey("content_categories.id", ondelete="SET NULL"), index=True, nullable=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    __table_args__ = (UniqueConstraint("slug", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(100))
    summary: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(40))
    license_name: Mapped[str | None] = mapped_column(String(100))
    compatibility: Mapped[str | None] = mapped_column(String(500))
    skill_md: Mapped[str] = mapped_column(Text)
    files_json: Mapped[str] = mapped_column(Text, default="{}")
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus), default=PublicationStatus.draft, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    category: Mapped[Category | None] = relationship()
    content_category: Mapped[ContentCategory | None] = relationship()


class MCPSettings(Base):
    __tablename__ = "mcp_settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    auth_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    auth_token_hash: Mapped[str | None] = mapped_column(String(128))
    github_client_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    github_client_secret: Mapped[str | None] = mapped_column(String(300), nullable=True)
    gitee_client_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gitee_client_secret: Mapped[str | None] = mapped_column(String(300), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MCPToolSetting(Base):
    __tablename__ = "mcp_tool_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class ReviewEvent(Base):
    __tablename__ = "review_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(40))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
