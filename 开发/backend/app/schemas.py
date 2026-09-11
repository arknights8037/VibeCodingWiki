from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from app.models import Difficulty, PublicationStatus, Role


class Message(BaseModel):
    message: str


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=10, max_length=128)

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


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime


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
    version: int


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title: str
    objective: str
    body_markdown: str
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


class ReviewRequest(BaseModel):
    action: str = Field(pattern=r"^(approve|reject|unpublish)$")
    comment: str | None = Field(default=None, max_length=2000)
    featured: bool = False


class WikiWrite(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    title: str = Field(min_length=2, max_length=180)
    summary: str = Field(min_length=10, max_length=500)
    body_markdown: str = Field(min_length=20, max_length=50000)
    difficulty: Difficulty = Difficulty.beginner
    category: str = Field(min_length=2, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=12)
    status: PublicationStatus = PublicationStatus.draft


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


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


WikiSummary.model_rebuild()
