import base64
import hashlib
import io
import json
import re
import zipfile

import yaml

MAX_ARCHIVE_BYTES = 5 * 1024 * 1024
MAX_FILES = 100
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SkillValidationError(ValueError):
    pass


def validate_skill_archive(data: bytes) -> dict:
    if len(data) > MAX_ARCHIVE_BYTES:
        raise SkillValidationError("压缩包不能超过 5 MB")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise SkillValidationError("文件不是有效 ZIP") from exc
    entries = [item for item in archive.infolist() if not item.is_dir()]
    if not entries or len(entries) > MAX_FILES:
        raise SkillValidationError("压缩包文件数量无效")
    for item in entries:
        normalized = item.filename.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise SkillValidationError("压缩包包含不安全路径")
        if item.file_size > MAX_ARCHIVE_BYTES:
            raise SkillValidationError("单个文件过大")
    skill_entries = [
        item
        for item in entries
        if item.filename.replace("\\", "/").endswith("/SKILL.md") or item.filename == "SKILL.md"
    ]
    if len(skill_entries) != 1:
        raise SkillValidationError("压缩包必须且只能包含一个 SKILL.md")
    skill_md = archive.read(skill_entries[0]).decode("utf-8")
    if not skill_md.startswith("---"):
        raise SkillValidationError("SKILL.md 缺少 YAML frontmatter")
    parts = skill_md.split("---", 2)
    if len(parts) < 3:
        raise SkillValidationError("SKILL.md frontmatter 未闭合")
    metadata = yaml.safe_load(parts[1]) or {}
    name = str(metadata.get("name", ""))
    description = str(metadata.get("description", ""))
    if not NAME_RE.fullmatch(name) or len(name) > 64:
        raise SkillValidationError("skill name 不符合规范")
    if not description or len(description) > 1024:
        raise SkillValidationError("skill description 不符合规范")
    files = {
        item.filename.replace("\\", "/"): base64.b64encode(archive.read(item)).decode("ascii")
        for item in entries
        if item != skill_entries[0]
    }
    files_json = json.dumps(files, ensure_ascii=False, sort_keys=True)
    canonical_archive = build_skill_archive(skill_md, files_json)
    return {
        "name": name,
        "description": description,
        "license": metadata.get("license"),
        "compatibility": metadata.get("compatibility"),
        "skill_md": skill_md,
        "files_json": files_json,
        "sha256": hashlib.sha256(canonical_archive).hexdigest(),
    }


def build_skill_archive(skill_md: str, files_json: str) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:

        def write_entry(name: str, payload: bytes) -> None:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)

        write_entry("SKILL.md", skill_md.encode("utf-8"))
        for name, encoded in sorted(json.loads(files_json or "{}").items()):
            normalized = name.replace("\\", "/")
            if normalized.startswith("/") or ".." in normalized.split("/"):
                continue
            write_entry(normalized, base64.b64decode(encoded))
    return stream.getvalue()
