from __future__ import annotations

import json
from typing import List

from flask import url_for

from ..models import ChartTask, CodeTemplate

REQUIRED_TEMPLATE_PLACEHOLDERS = {"{title}", "{summary}", "{generated_code}"}


class _SafeTemplateContext(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return ""


def validate_template_content(content: str) -> List[str]:
    return [placeholder for placeholder in REQUIRED_TEMPLATE_PLACEHOLDERS if placeholder not in content]


def render_template_for_task(template: CodeTemplate, task: ChartTask) -> str:
    base_code = task.java_code if template.language == "java" else task.kotlin_code
    if not base_code:
        if task.language == template.language and task.generated_code:
            base_code = task.generated_code
    if not base_code:
        raise ValueError("Task does not have generated code for the requested template language.")

    try:
        image_url = (
            url_for("charts.serve_upload", filename=task.image_path, _external=True)
            if task.image_path
            else ""
        )
    except RuntimeError:  # pragma: no cover - fallback when outside request context
        image_url = ""

    context = _SafeTemplateContext(
        title=task.title,
        summary=task.summary or "",
        description=task.description or "",
        generated_code=base_code,
        data_points_json=json.dumps(task.data_points or []),
        table_data_json=json.dumps(task.table_data or []),
        image_url=image_url,
    )
    try:
        return template.content.format_map(context)
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Template is missing placeholder: {exc}") from exc
