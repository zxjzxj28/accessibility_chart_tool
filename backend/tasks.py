from __future__ import annotations
import queue
import threading
from dataclasses import dataclass
from typing import Optional

from flask import Flask

from .extensions import db
from .models import ChartTask, CodeTemplate
from .utils.chart_processing import process_chart
from .utils.template_engine import render_template_for_task


@dataclass
class TaskPayload:
    task_id: int
    image_path: str
    public_image_url: str


class ChartProcessingWorker:
    def __init__(self) -> None:
        self._queue: "queue.Queue[TaskPayload]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None

    def start(self, app: Flask) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run, args=(app,), daemon=True)
        self._thread.start()

    def enqueue(self, payload: TaskPayload) -> None:
        self._queue.put(payload)

    def _run(self, app: Flask) -> None:
        with app.app_context():
            while True:
                payload = self._queue.get()
                try:
                    task = ChartTask.query.get(payload.task_id)
                    if not task:
                        continue
                    if task.status == "cancelled":
                        continue

                    task.status = "processing"
                    db.session.commit()

                    result = process_chart(payload.image_path, payload.public_image_url)

                    task.summary = result.get("summary")
                    task.description = result.get("description")
                    task.data_points = result.get("data_points")
                    task.table_data = result.get("table_data")
                    task.generated_code = result.get("generated_code")
                    task.java_code = result.get("java_code")
                    task.kotlin_code = result.get("kotlin_code")
                    task.integration_doc = result.get("integration_doc")
                    if task.template_id:
                        template = CodeTemplate.query.get(task.template_id)
                        if template:
                            try:
                                task.generated_code = render_template_for_task(template, task)
                                task.language = template.language
                            except ValueError:
                                pass
                    elif task.language == "java" and task.java_code:
                        task.generated_code = task.java_code
                    elif task.language == "kotlin" and task.kotlin_code:
                        task.generated_code = task.kotlin_code
                    task.status = "completed"
                    db.session.commit()
                except Exception as exc:  # pragma: no cover - defensive logging
                    task = ChartTask.query.get(payload.task_id)
                    if task:
                        task.status = "failed"
                        task.error_message = str(exc)
                        db.session.commit()
                finally:
                    self._queue.task_done()


worker = ChartProcessingWorker()
