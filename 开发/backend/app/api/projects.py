import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import require_user, verify_csrf
from app.models import ProjectSubmission, PublicationStatus, User
from app.schemas import Message, ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


def project_out(project: ProjectSubmission) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        slug=project.slug,
        summary=project.summary,
        description_markdown=project.description_markdown,
        repository_url=project.repository_url,
        demo_url=project.demo_url,
        license_name=project.license_name,
        tech_stack=json.loads(project.tech_stack or "[]"),
        status=project.status,
        is_featured=project.is_featured,
        review_note=project.review_note,
        submitted_at=project.submitted_at,
        published_at=project.published_at,
    )


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    featured: bool | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[ProjectOut]:
    statement = select(ProjectSubmission).where(
        ProjectSubmission.status == PublicationStatus.published
    )
    if featured is not None:
        statement = statement.where(ProjectSubmission.is_featured == featured)
    projects = await session.scalars(
        statement.order_by(
            ProjectSubmission.is_featured.desc(), ProjectSubmission.published_at.desc()
        ).limit(limit)
    )
    return [project_out(item) for item in projects]


@router.get("/mine", response_model=list[ProjectOut])
async def my_projects(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProjectOut]:
    projects = await session.scalars(
        select(ProjectSubmission)
        .where(ProjectSubmission.owner_id == user.id)
        .order_by(ProjectSubmission.updated_at.desc())
    )
    return [project_out(item) for item in projects]


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectOut:
    if await session.scalar(
        select(ProjectSubmission).where(ProjectSubmission.slug == payload.slug)
    ):
        raise HTTPException(status_code=409, detail="项目标识已存在")
    project = ProjectSubmission(
        owner_id=user.id,
        name=payload.name.strip(),
        slug=payload.slug,
        summary=payload.summary.strip(),
        description_markdown=payload.description_markdown,
        repository_url=str(payload.repository_url),
        demo_url=str(payload.demo_url) if payload.demo_url else None,
        license_name=payload.license_name,
        tech_stack=json.dumps(payload.tech_stack, ensure_ascii=False),
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project_out(project)


@router.put("/{project_id}", response_model=ProjectOut, dependencies=[Depends(verify_csrf)])
async def update_project(
    project_id: int,
    payload: ProjectCreate,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectOut:
    project = await session.get(ProjectSubmission, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="投稿不存在")
    if project.status not in {PublicationStatus.draft, PublicationStatus.rejected}:
        raise HTTPException(status_code=409, detail="当前状态不可编辑")
    duplicate = await session.scalar(
        select(ProjectSubmission).where(
            ProjectSubmission.slug == payload.slug, ProjectSubmission.id != project_id
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="项目标识已存在")
    for field in ("name", "slug", "summary", "description_markdown", "license_name"):
        setattr(project, field, getattr(payload, field))
    project.repository_url = str(payload.repository_url)
    project.demo_url = str(payload.demo_url) if payload.demo_url else None
    project.tech_stack = json.dumps(payload.tech_stack, ensure_ascii=False)
    project.review_note = None
    project.status = PublicationStatus.draft
    await session.commit()
    await session.refresh(project)
    return project_out(project)


@router.post("/{project_id}/submit", response_model=Message, dependencies=[Depends(verify_csrf)])
async def submit_project(
    project_id: int,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> Message:
    project = await session.get(ProjectSubmission, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="投稿不存在")
    if project.status not in {PublicationStatus.draft, PublicationStatus.rejected}:
        raise HTTPException(status_code=409, detail="当前状态不可提交")
    project.status = PublicationStatus.pending_review
    project.submitted_at = datetime.now(UTC)
    project.review_note = None
    await session.commit()
    return Message(message="投稿已进入审核队列")


@router.get("/{slug}", response_model=ProjectOut)
async def get_project(slug: str, session: AsyncSession = Depends(get_session)) -> ProjectOut:
    project = await session.scalar(
        select(ProjectSubmission).where(
            ProjectSubmission.slug == slug, ProjectSubmission.status == PublicationStatus.published
        )
    )
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project_out(project)
