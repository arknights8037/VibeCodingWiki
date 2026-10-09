import re

_PLACEHOLDER_PREFIX = "Vibe Coding Wiki 词条："


def display_wiki_summary(summary: str | None, body_markdown: str | None) -> str:
    """Return a useful short definition for cards and lightweight indexes."""
    value = (summary or "").strip()
    if value and not value.startswith(_PLACEHOLDER_PREFIX):
        return value

    for block in re.split(r"\n\s*\n", body_markdown or ""):
        candidate = re.sub(r"\s+", " ", block.strip())
        if not candidate or candidate.startswith(("#", ">", "```")):
            continue
        return candidate[:500]
    return value
