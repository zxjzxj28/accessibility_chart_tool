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
    result = task.result
    if not result:
        raise ValueError("任务结果尚未准备好，无法渲染模板。")
    if not result.is_success:
        raise ValueError("任务生成失败，无法渲染模板。")

    base_code = result.java_code if template.language == "java" else result.kotlin_code
    if not base_code and task.language == template.language and result.generated_code:
        base_code = result.generated_code
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
        summary=(result.summary or "") if result else "",
        description=(result.description or "") if result else "",
        generated_code=base_code,
        data_points_json=json.dumps((result.data_points or []) if result else []),
        table_data_json=json.dumps((result.table_data or []) if result else []),
        image_url=image_url,
    )
    try:
        return template.content.format_map(context)
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Template is missing placeholder: {exc}") from exc
