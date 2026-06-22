import re
from datetime import datetime
from pathlib import Path

from . import config


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣\-]+", "-", title.strip()).strip("-").lower()
    return slug or "skill"


def save_skill(title: str, summary: str, steps_markdown: str) -> str:
    """성공적으로 끝난 작업을 재사용 가능한 마크다운 스킬 문서로 저장한다."""
    skills_dir = Path(config.SKILLS_DIR)
    skills_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(title)
    path = skills_dir / f"{slug}.md"
    body = (
        f"# {title}\n\n"
        f"- 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"## 요약\n{summary}\n\n"
        f"## 단계\n{steps_markdown}\n"
    )
    path.write_text(body, encoding="utf-8")
    return str(path)


def list_skills() -> list[dict]:
    """등록된 스킬 목록을 (이름, 요약 첫 줄)으로 반환한다. 시스템 프롬프트에 주입할 때 사용."""
    skills_dir = Path(config.SKILLS_DIR)
    if not skills_dir.exists():
        return []

    skills = []
    for path in sorted(skills_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        summary_match = re.search(r"^##\s+요약\s*\n(.+)$", text, re.MULTILINE)
        skills.append(
            {
                "file": path.name,
                "title": title_match.group(1) if title_match else path.stem,
                "summary": summary_match.group(1) if summary_match else "",
            }
        )
    return skills


def read_skill(file_name: str) -> str:
    path = Path(config.SKILLS_DIR) / file_name
    if not path.exists():
        raise FileNotFoundError(file_name)
    return path.read_text(encoding="utf-8")
