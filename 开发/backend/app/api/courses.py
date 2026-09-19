from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import require_user, verify_csrf
from app.models import Course, Lesson, LessonProgress, PublicationStatus, User
from app.schemas import CourseOut, Message

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseOut])
async def list_courses(session: AsyncSession = Depends(get_session)) -> list[Course]:
    statement = (
        select(Course)
        .where(Course.status == PublicationStatus.published)
        .options(selectinload(Course.lessons.and_(Lesson.status == PublicationStatus.published)))
        .order_by(Course.order_index, Course.id)
    )
    return list(await session.scalars(statement))


@router.get("/{slug}", response_model=CourseOut)
async def get_course(slug: str, session: AsyncSession = Depends(get_session)) -> Course:
    course = await session.scalar(
        select(Course)
        .where(Course.slug == slug, Course.status == PublicationStatus.published)
        .options(selectinload(Course.lessons.and_(Lesson.status == PublicationStatus.published)))
    )
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


@router.post(
    "/lessons/{slug}/complete", response_model=Message, dependencies=[Depends(verify_csrf)]
)
async def complete_lesson(
    slug: str,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> Message:
    lesson = await session.scalar(
        select(Lesson).where(Lesson.slug == slug, Lesson.status == PublicationStatus.published)
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="课文不存在")
    progress = await session.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson.id
        )
    )
    if not progress:
        session.add(LessonProgress(user_id=user.id, lesson_id=lesson.id))
        await session.commit()
    return Message(message="学习进度已保存")
