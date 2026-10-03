from app.course_content import COURSES


def test_public_curriculum_has_five_modules_and_fifteen_lessons():
    assert [item["slug"] for item in COURSES] == [
        "vibe-coding-basics",
        "requirements-breakdown",
        "prompt-and-context",
        "environment-git",
        "testing-security-review",
    ]
    lessons = [lesson for course in COURSES for lesson in course["lessons"]]
    assert len(lessons) == 15
    assert len({lesson["slug"] for lesson in lessons}) == 15

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
