"""Markdown to the editor's persisted Tiptap document format.

This is intentionally conservative: unsupported inline HTML is stripped and the
original Markdown remains available as the search/API projection.
"""

from __future__ import annotations

import json
import re
from uuid import uuid4

SCHEMA_VERSION = 2


def markdown_to_content(markdown: str | None) -> str:
    lines = (markdown or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    nodes: list[dict] = []
    paragraph: list[str] = []
    list_items: list[tuple[str, bool | None, bool]] = []
    code: list[str] = []
    language: str | None = None
    in_code = False

    def flush_paragraph() -> None:
        if paragraph:
            text = clean_inline(" ".join(paragraph).strip())
            if text:
                nodes.append(text_node("paragraph", text))
            paragraph.clear()

    def flush_list() -> None:
        if not list_items:
            return
        task = any(checked is not None for _, checked, _ in list_items)
        ordered = list_items[0][2]
        nodes.append(
            {
                "type": "taskList" if task else "orderedList" if ordered else "bulletList",
                "content": [
                    {
                        "type": "taskItem" if task else "listItem",
                        **({"attrs": {"checked": checked is True}} if task else {}),
                        "content": [text_node("paragraph", clean_inline(text))],
                    }
                    for text, checked, _ in list_items
                ],
            }
        )
        list_items.clear()

    def flush_code() -> None:
        nonlocal language
        value = "\n".join(code)
        if (language or "").lower() in {"card", "callout"}:
            nested = json.loads(markdown_to_content(value))
            nodes.append(
                {
                    "type": "cardBlock",
                    "attrs": {"variant": "card"},
                    "content": nested.get("content", []),
                }
            )
        elif (language or "").lower() in {"math", "latex", "tex"}:
            nodes.append({"type": "mathBlock", "attrs": {"latex": value.strip()}})
        else:
            node = {"type": "codeBlock", "attrs": {"language": language} if language else {}}
            if value:
                node["content"] = [{"type": "text", "text": value}]
            nodes.append(node)
        code.clear()
        language = None

    for line in lines:
        fence = re.match(r"^```([\w-]+)?\s*$", line)
        if in_code:
            if line.startswith("```"):
                flush_code()
                in_code = False
            else:
                code.append(line)
            continue
        if fence:
            flush_paragraph()
            flush_list()
            in_code = True
            language = fence.group(1)
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            nodes.append(
                text_node(
                    "heading",
                    clean_inline(heading.group(2).strip()),
                    {"level": len(heading.group(1))},
                )
            )
            continue
        task = re.match(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+)$", line)
        unordered = re.match(r"^\s*[-*+]\s+(.+)$", line)
        ordered = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if task or unordered or ordered:
            flush_paragraph()
            checked = task.group(1).lower() == "x" if task else None
            value = task.group(2) if task else unordered.group(1) if unordered else ordered.group(1)
            is_ordered = bool(ordered)
            if list_items and (
                list_items[0][2] != is_ordered or (list_items[0][1] is None) != (checked is None)
            ):
                flush_list()
            list_items.append((value.strip(), checked, is_ordered))
            continue
        flush_list()
        paragraph.append(line.strip())
    if in_code:
        flush_code()
    flush_paragraph()
    flush_list()
    if not nodes:
        nodes = [{"type": "paragraph"}]
    return json.dumps(
        {"type": "doc", "schemaVersion": SCHEMA_VERSION, "content": add_ids(nodes)},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def normalize_content_json(value: str | None, fallback_markdown: str | None = "") -> str:
    if value:
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
            if isinstance(parsed, dict) and parsed.get("type") == "doc":
                parsed.setdefault("schemaVersion", SCHEMA_VERSION)
                parsed.setdefault("content", [{"type": "paragraph"}])
                return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return markdown_to_content(fallback_markdown)


def text_node(kind: str, text: str, attrs: dict | None = None) -> dict:
    node = {"type": kind}
    if attrs:
        node["attrs"] = attrs
    if text:
        node["content"] = inline_nodes(text)
    return node


def inline_nodes(text: str) -> list[dict]:
    nodes: list[dict] = []
    pattern = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))")
    last = 0
    for match in pattern.finditer(text):
        if match.start() > last:
            nodes.append({"type": "text", "text": text[last : match.start()]})
        token = match.group(0)
        if token.startswith("`"):
            nodes.append({"type": "text", "text": token[1:-1], "marks": [{"type": "code"}]})
        elif token.startswith("**"):
            nodes.append({"type": "text", "text": token[2:-2], "marks": [{"type": "bold"}]})
        elif token.startswith("*"):
            nodes.append({"type": "text", "text": token[1:-1], "marks": [{"type": "italic"}]})
        else:
            link = re.match(r"^\[([^\]]+)\]\(([^)]+)\)$", token)
            if link and not link.group(2).lower().startswith(("javascript:", "data:")):
                nodes.append(
                    {
                        "type": "text",
                        "text": link.group(1),
                        "marks": [{"type": "link", "attrs": {"href": link.group(2)}}],
                    }
                )
            else:
                nodes.append({"type": "text", "text": token})
        last = match.end()
    if last < len(text):
        nodes.append({"type": "text", "text": text[last:]})
    return [node for node in nodes if node.get("text")]


def clean_inline(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>[\s\S]*?</script\s*>", "", value, flags=re.I)
    value = re.sub(r"<style\b[^>]*>[\s\S]*?</style\s*>", "", value, flags=re.I)
    return re.sub(r"<[^>]+>", "", value)


def add_ids(nodes: list[dict]) -> list[dict]:
    for node in nodes:
        if node.get("type") != "text":
            node.setdefault("attrs", {})
            node["attrs"].setdefault("id", str(uuid4()))
        if isinstance(node.get("content"), list):
            add_ids(node["content"])
    return nodes
