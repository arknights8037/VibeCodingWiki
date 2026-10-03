import io
import zipfile

import pytest

from app.services.skills import SkillValidationError, validate_skill_archive


def make_zip(name: str, content: str) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(name, content)
    return stream.getvalue()


def test_rejects_path_traversal():
    data = make_zip("../SKILL.md", "---\nname: sample\ndescription: sample skill\n---\n")
    with pytest.raises(SkillValidationError, match="不安全路径"):
        validate_skill_archive(data)


def test_accepts_minimal_skill():
    data = make_zip(
        "SKILL.md", "---\nname: sample-skill\ndescription: A useful sample skill.\n---\n# Steps\n"
    )
    result = validate_skill_archive(data)
    assert result["name"] == "sample-skill"
    assert len(result["sha256"]) == 64


@pytest.mark.parametrize('metadata', [
    'name: sample\ndescription: null',
    'name: sample\ndescription: 123',
    'name: sample\ndescription: "   "',
    'name: sample\ndescription: useful\nmetadata: {version: 2}',
    'name: sample\ndescription: useful\nallowed-tools: [Read]',
])
def test_rejects_invalid_standard_metadata(metadata):
    with pytest.raises(SkillValidationError):
        validate_skill_archive(make_zip('SKILL.md', f'---\n{metadata}\n---\n# Steps\n'))


def test_frontmatter_delimiter_inside_description():
    result = validate_skill_archive(make_zip('SKILL.md', '---\nname: sample\ndescription: a --- b\n---\n# Steps'))
    assert result['description'] == 'a --- b'
