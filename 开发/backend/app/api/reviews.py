from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.projects import project_out
from app.database import get_session
from app.dependencies import require_roles, verify_csrf
from app.models import AuditLog, ProjectSubmission, PublicationStatus, ReviewEvent, Role, User
from app.schemas import FeaturedUpdate, Message, ProjectOut, ReviewRequest

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/projects", response_model=list[ProjectOut])
async def review_queue(
    status: Literal["pending_review", "published", "rejected", "draft"] = "pending_review",
    _reviewer: User = Depends(require_roles(Role.reviewer, Role.admin)),
    session: AsyncSession = Depends(get_session),
) -> list[ProjectOut]:
    items = await session.scalars(
        select(ProjectSubmission)
        .where(ProjectSubmission.status == PublicationStatus(status))
        .order_by(ProjectSubmission.submitted_at)
    )
    return [project_out(item) for item in items]


@router.patch("/projects/{project_id}/featured", response_model=Message, dependencies=[Depends(verify_csrf)])
async def feature_project(
    project_id: int, payload: FeaturedUpdate,
    reviewer: User = Depends(require_roles(Role.reviewer, Role.admin)),
    session: AsyncSession = Depends(get_session),
) -> Message:
    project = await session.get(ProjectSubmission, project_id)
    if not project:
        raise HTTPException(404, "投稿不存在")
    if project.owner_id == reviewer.id:
        raise HTTPException(403, "不能审核自己的投稿")
    if project.status != PublicationStatus.published:
        raise HTTPException(409, "只有已发布项目可以推荐")
    project.is_featured = payload.featured
    session.add(AuditLog(actor_id=reviewer.id, action="project.featured.update",
                        target_type="project", target_id=str(project.id), detail=payload.model_dump_json()))
    await session.commit()
    return Message(message="推荐状态已更新")


@router.post("/projects/{project_id}", response_model=Message, dependencies=[Depends(verify_csrf)])
async def review_project(
    project_id: int,
    payload: ReviewRequest,
    reviewer: User = Depends(require_roles(Role.reviewer, Role.admin)),
    session: AsyncSession = Depends(get_session),
) -> Message:
    project = await session.get(ProjectSubmission, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="投稿不存在")
    if project.owner_id == reviewer.id:
        raise HTTPException(status_code=403, detail="不能审核自己的投稿")
    if (
        payload.action in {"approve", "reject"}
        and project.status != PublicationStatus.pending_review
    ):
        raise HTTPException(status_code=409, detail="投稿不在待审核状态")
    if payload.action == "reject" and not (payload.comment or "").strip():
        raise HTTPException(status_code=422, detail="驳回时必须填写原因")
    now = datetime.now(UTC)
    if payload.action == "approve":
        project.status = PublicationStatus.published
        project.published_at = now
        project.is_featured = payload.featured
        project.review_note = None
        message = "投稿已发布"
    elif payload.action == "reject":
        project.status = PublicationStatus.rejected
        project.review_note = payload.comment
        project.is_featured = False
        message = "投稿已驳回"
    else:
        if project.status != PublicationStatus.published:
            raise HTTPException(status_code=409, detail="只有已发布项目可以撤下")
        project.status = PublicationStatus.draft
        project.published_at = None
        project.is_featured = False
        message = "项目已撤下"
    session.add(
        ReviewEvent(
            entity_type="project",
            entity_id=project.id,
            action=payload.action,
            reviewer_id=reviewer.id,
            comment=payload.comment,
        )
    )
    session.add(
        AuditLog(
            actor_id=reviewer.id,
            action=f"project.{payload.action}",
            target_type="project",
            target_id=str(project.id),
            detail=payload.model_dump_json(),
        )
    )
    await session.commit()
    return Message(message=message)
