import json
import re

TEACHING_TITLES = {"学习目标", "实践任务", "完成标准"}


def teaching_cards(body: str):
    """Yield top-level teaching fences; ignore examples inside other code fences."""
    opening = None
    offset = 0
    for line in body.splitlines(keepends=True):
        if opening is None:
            match = re.match(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)", line)
            if match:
                opening = (offset, offset + len(line), match[1], match[2].strip())
        else:
            start, content_start, fence, language = opening
            if re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*", line.rstrip("\r\n")):
                content = body[content_start:offset].strip()
                if language == "card" and content.split("\n", 1)[0].strip() in {f"## {title}" for title in TEACHING_TITLES}:
                    yield start, offset + len(line), content
                opening = None
        offset += len(line)


def deduplicate_teaching_cards(body: str) -> str:
    seen = set()
    parts = []
    position = 0
    for start, end, content in teaching_cards(body):
        key = content.replace("\r\n", "\n")
        if key in seen:
            parts.append(body[position:start])
            position = end
        else:
            seen.add(key)
    if not parts:
        return body
    parts.append(body[position:])
    return "".join(parts).rstrip()


def deduplicate_teaching_content(value: str | None) -> str | None:
    """Keep the first identical teaching card, including its existing editor IDs."""
    if not value:
        return value
    try:
        document = json.loads(value)
    except (ValueError, TypeError):
        return value
    if not isinstance(document, dict) or not isinstance(document.get("content"), list):
        return value

    def without_ids(node):
        if isinstance(node, dict):
            return {key: without_ids(item) for key, item in node.items() if key != "id"}
        if isinstance(node, list):
            return [without_ids(item) for item in node]
        return node

    seen = set()
    retained = []
    for node in document["content"]:
        children = node.get("content", []) if isinstance(node, dict) else []
        heading = children[0] if children and isinstance(children[0], dict) else {}
        title = "".join(item.get("text", "") for item in heading.get("content", []) if isinstance(item, dict))
        if isinstance(node, dict) and node.get("type") == "cardBlock" and heading.get("type") == "heading" and title in TEACHING_TITLES:
            key = json.dumps(without_ids(node), ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
        retained.append(node)
    if len(retained) == len(document["content"]):
        return value
    document["content"] = retained
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"))


def with_legacy_cards(body: str, objective: str, practice: str, criteria: str) -> str:
    body = deduplicate_teaching_cards(body)
    existing = {content.replace("\r\n", "\n") for _, _, content in teaching_cards(body)}
    parts = [body.rstrip()]
    for title, content in [("学习目标", objective), ("实践任务", practice), ("完成标准", criteria)]:
        if not content.strip():
            continue
        if f"## {title}\n\n{content.strip()}".replace("\r\n", "\n") in existing:
            continue
        # A longer outer fence safely contains code examples in migrated content.
        fence = "`" * max(3, max((len(run) + 1 for run in re.findall(r"`+", content)), default=3))
        parts.append(f"{fence}card\n## {title}\n\n{content.strip()}\n{fence}")
    return "\n\n".join(part for part in parts if part)
