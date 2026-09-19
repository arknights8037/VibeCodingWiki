import re


def with_legacy_cards(body: str, objective: str, practice: str, criteria: str) -> str:
    parts = [body.rstrip()]
    for title, content in [("学习目标", objective), ("实践任务", practice), ("完成标准", criteria)]:
        if not content.strip():
            continue
        # A longer outer fence safely contains code examples in migrated content.
        fence = "`" * max(3, max((len(run) + 1 for run in re.findall(r"`+", content)), default=3))
        parts.append(f"{fence}card\n## {title}\n\n{content.strip()}\n{fence}")
    return "\n\n".join(part for part in parts if part)
