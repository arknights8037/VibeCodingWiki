from app.course_content import COURSES


def test_public_curriculum_has_nine_modules_and_twenty_seven_lessons():
    assert [item["slug"] for item in COURSES] == [
        "vibe-coding-basics",
        "requirements-breakdown",
        "prompt-and-context",
        "environment-git",
        "testing-security-review",
        "ai-tools-and-models",
        "software-design-with-ai",
        "production-delivery",
        "team-governance-and-career",
    ]
    lessons = [lesson for course in COURSES for lesson in course["lessons"]]
    assert len(lessons) == 27
    assert len({lesson["slug"] for lesson in lessons}) == 27

    for course in COURSES:
        assert course["title"].strip()
        assert course["summary"].strip()
        assert course["prerequisites"].strip()
        assert course["difficulty"] in {"beginner", "intermediate", "advanced"}
        assert len(course["lessons"]) == 3
        for lesson in course["lessons"]:
            assert lesson["body"].startswith("# ")
            assert "> 本篇导读：" in lesson["body"]
            assert "## 先从一个场景开始" in lesson["body"]
            assert "## 核心概念" in lesson["body"]
            assert "## 跟做任务" in lesson["body"]
            assert "## 课后检查" in lesson["body"]
            assert lesson["objective"].strip()
            assert lesson["practice"].strip()
            assert lesson["criteria"].strip()
