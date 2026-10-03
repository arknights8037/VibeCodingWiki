from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from app.models import Difficulty, PublicationStatus, Role


class Message(BaseModel):
    message: str


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(
            character.isdigit() for character in value
        ):
            raise ValueError("密码必须同时包含字母和数字")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(character.isdigit() for character in value):
            raise ValueError("密码必须同时包含字母和数字")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime
    github_username: str | None = None
    gitee_username: str | None = None
    real_name: str | None = None
    avatar_url: str | None = None

class SocialAccountsUpdate(BaseModel):
    github_username: str | None = Field(default=None, max_length=120)
    gitee_username: str | None = Field(default=None, max_length=120)

class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    real_name: str | None = Field(default=None, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=500)

class NotificationOut(BaseModel):
    id: str
    title: str
    message: str
    created_at: datetime
    read: bool = False


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class WikiSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title: str
    summary: str
    difficulty: Difficulty
    category: "CategoryOut"
    tags: list[TagOut]
    updated_at: datetime


class WikiDetail(WikiSummary):
    body_markdown: str
    content_json: str = ''
    version: int
    status: PublicationStatus


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    parent_id: int | None = None
    order_index: int = 0


class ContentCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: Literal["project", "skill"]
    slug: str
    name: str
    order_index: int = 0


class ContentCategoryWrite(BaseModel):
    kind: Literal["project", "skill"]
    name: str = Field(min_length=2, max_length=80)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    order_index: int = Field(default=0, ge=0)


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title: str
    objective: str
    body_markdown: str
    content_json: str = ''
    practice: str
    completion_criteria: str
    estimated_minutes: int
    order_index: int


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title: str
    summary: str
    prerequisites: str
    difficulty: Difficulty
    order_index: int
    is_standalone: bool = False
    directory_collapsible: bool = True
    lessons: list[LessonOut] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    summary: str = Field(min_length=10, max_length=500)
    description_markdown: str = Field(min_length=20, max_length=30000)
    repository_url: HttpUrl
    demo_url: HttpUrl | None = None
    license_name: str = Field(default="MIT", max_length=80)
    tech_stack: list[str] = Field(default_factory=list, max_length=20)
    content_category_id: int | None = Field(default=None, gt=0)


class ProjectOut(BaseModel):
    id: int
    name: str
    slug: str
    summary: str
    description_markdown: str
    repository_url: str
    demo_url: str | None
    license_name: str
    tech_stack: list[str]
    status: PublicationStatus
    is_featured: bool
    review_note: str | None
    submitted_at: datetime | None
    published_at: datetime | None
    content_category_id: int | None = None
    content_category: ContentCategoryOut | None = None


class ReviewRequest(BaseModel):
    action: str = Field(pattern=r"^(approve|reject|unpublish)$")
    comment: str | None = Field(default=None, max_length=2000)
    featured: bool = False


class WikiWrite(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    title: str = Field(min_length=2, max_length=180)
    summary: str = Field(min_length=10, max_length=500)
    body_markdown: str = Field(min_length=20, max_length=50000)
    content_json: str | None = Field(default=None, max_length=1000000)
    difficulty: Difficulty = Difficulty.beginner
    category: str = Field(min_length=2, max_length=80)
    category_id: int | None = None
    order_index: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list, max_length=12)
    status: Literal["draft", "published"] = "draft"

    @field_validator("category")
    @classmethod
    def clean_category(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("分类至少两个字符")
        return value

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        result = list(dict.fromkeys(value.strip().lower().replace(" ", "-") for value in values))
        if any(not value or len(value) > 80 for value in result):
            raise ValueError("标签须为 1–80 个字符")
        return result


class CategoryWrite(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    name: str = Field(min_length=2, max_length=80)
    parent_id: int | None = None
    order_index: int = Field(default=0, ge=0)


class AdminCategoryOut(CategoryOut):
    id: int
    children: list["AdminCategoryOut"] = Field(default_factory=list)
    article_count: int = 0


class WikiMove(BaseModel):
    offset: Literal[-1, 1]


AdminCategoryOut.model_rebuild()


class UserStatusUpdate(BaseModel):
    is_active: bool


class ContentStatusUpdate(BaseModel):
    status: Literal["draft", "published"]


class FeaturedUpdate(BaseModel):
    featured: bool


class RoleUpdate(BaseModel):
    role: Role


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    summary: str
    version: str
    license_name: str | None
    compatibility: str | None
    sha256: str
    content_category_id: int | None = None
    content_category: ContentCategoryOut | None = None


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


class AdminSkillOut(SkillOut):
    review_note: str | None = None
    id: int
    status: PublicationStatus


class SkillIntroUpdate(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)

    @field_validator("summary")
    @classmethod
    def nonblank_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请填写简要说明")
        return value.strip()


class SkillCreate(SkillIntroUpdate):
    name: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
    description: str = Field(min_length=1, max_length=1024)
    instructions: str = Field(min_length=1, max_length=100000)
    version: str = Field(default="1.0.0", pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}$")
    publish: bool = False
    content_category_id: int | None = Field(default=None, gt=0)

    @field_validator("description", "instructions")
    @classmethod
    def nonblank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("内容不能为空")
        return value.strip()


class SkillStatusUpdate(BaseModel):
    status: Literal["draft", "pending_review", "published"]


class SkillReviewUpdate(BaseModel):
    status: Literal["draft", "published", "rejected"]
    review_note: str = Field(default="", max_length=2000)


class MCPSettingsOut(BaseModel):
    enabled: bool
    auth_enabled: bool
    has_token: bool


class MCPSettingsWrite(BaseModel):
    enabled: bool | None = None
    auth_enabled: bool | None = None
    token: str | None = Field(default=None, min_length=16, max_length=256)

class OAuthSettingsOut(BaseModel):
    github_client_id: str | None = None
    github_configured: bool = False
    gitee_client_id: str | None = None
    gitee_configured: bool = False

class OAuthSettingsWrite(BaseModel):
    github_client_id: str | None = Field(default=None, max_length=200)
    github_client_secret: str | None = Field(default=None, max_length=300)
    gitee_client_id: str | None = Field(default=None, max_length=200)
    gitee_client_secret: str | None = Field(default=None, max_length=300)


class MCPToolOut(BaseModel):
    id: int
    name: str
    description: str
    enabled: bool


class MCPToolUpdate(BaseModel):
    enabled: bool


WikiSummary.model_rebuild()


class LessonWrite(BaseModel):
    id: int | None = None
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    title: str = Field(min_length=1, max_length=180)
    objective: str = Field(default="", max_length=10000)
    body_markdown: str = Field(default="", max_length=200000)
    content_json: str | None = Field(default=None, max_length=1000000)
    practice: str = Field(default="", max_length=20000)
    completion_criteria: str = Field(default="", max_length=20000)
    estimated_minutes: int = Field(default=30, ge=0, le=10000)
    order_index: int = Field(default=0, ge=0)
    status: Literal["draft", "published", "archived"] = "draft"


class CourseWrite(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=10000)
    prerequisites: str = Field(default="无", max_length=10000)
    difficulty: Difficulty = Difficulty.beginner
    order_index: int = Field(default=0, ge=0)
    status: Literal["draft", "published", "archived"] = "draft"
    is_standalone: bool = False
    directory_collapsible: bool = True
    lessons: list[LessonWrite] = Field(default_factory=list, max_length=200)


class AdminLessonOut(LessonOut):
    status: PublicationStatus


class AdminCourseOut(CourseOut):
    status: PublicationStatus
    lessons: list[AdminLessonOut] = Field(default_factory=list)


class DirectoryMove(BaseModel):
    offset: Literal[-1, 1]
