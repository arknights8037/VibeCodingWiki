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
    try:
        return _validate_skill_archive(data)
    except (UnicodeDecodeError, yaml.YAMLError, zipfile.BadZipFile, RuntimeError,
            NotImplementedError, OSError, ValueError) as exc:
        if isinstance(exc, SkillValidationError):
            raise
        raise SkillValidationError("压缩包或 SKILL.md 内容无效，请检查 UTF-8 编码和 YAML 格式") from exc


def _validate_skill_archive(data: bytes) -> dict:
    if len(data) > MAX_ARCHIVE_BYTES:
        raise SkillValidationError("压缩包不能超过 5 MB")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise SkillValidationError("文件不是有效 ZIP") from exc
    entries = [item for item in archive.infolist() if not item.is_dir()]
    if not entries or len(entries) > MAX_FILES:
        raise SkillValidationError("压缩包文件数量无效")
    if sum(item.file_size for item in entries) > MAX_ARCHIVE_BYTES:
        raise SkillValidationError("解压后的文件总量不能超过 5 MB")
    names: set[str] = set()
    for item in entries:
        normalized = item.filename.replace("\\", "/")
        if (normalized.startswith("/") or ":" in normalized
                or any(part in {"..", ".", ""} for part in normalized.split("/"))):
            raise SkillValidationError("压缩包包含不安全路径")
        if normalized in names or (item.external_attr >> 16) & 0o170000 == 0o120000:
            raise SkillValidationError("压缩包包含重复路径或符号链接")
        names.add(normalized)
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
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", skill_md, re.DOTALL)
    if not frontmatter:
        raise SkillValidationError("SKILL.md frontmatter 未闭合")
    metadata = yaml.safe_load(frontmatter.group(1)) or {}
    if not isinstance(metadata, dict):
        raise SkillValidationError("frontmatter 必须是包含 name 和 description 的对象")
    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name) or len(name) > 64:
        raise SkillValidationError("skill name 不符合规范")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise SkillValidationError("skill description 不符合规范")
    for field in ("license", "compatibility"):
        if metadata.get(field) is not None and not isinstance(metadata[field], str):
            raise SkillValidationError(f"{field} 必须是文本")
    if "compatibility" in metadata and not 1 <= len(metadata["compatibility"] or "") <= 500:
        raise SkillValidationError("compatibility 长度必须为 1–500")
    if "metadata" in metadata and (not isinstance(metadata["metadata"], dict) or
            any(not isinstance(k, str) or not isinstance(v, str) for k, v in metadata["metadata"].items())):
        raise SkillValidationError("metadata 必须是文本键值对")
    if "allowed-tools" in metadata and not isinstance(metadata["allowed-tools"], str):
        raise SkillValidationError("allowed-tools 必须是文本")
    # Strip a single enclosing directory consistently, preserving relative links.
    root = skill_entries[0].filename.replace("\\", "/").removesuffix("SKILL.md")
    if root and any(not item.filename.replace("\\", "/").startswith(root) for item in entries):
        raise SkillValidationError("所有文件必须位于 SKILL.md 所在目录内")
    files = {
        item.filename.replace("\\", "/").removeprefix(root): base64.b64encode(archive.read(item)).decode("ascii")
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
