from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from PIL import Image


def simulate_cloud_processing(image_path: str) -> dict[str, Any]:
    """Simulate calling a remote service to analyse the chart image."""
    with Image.open(image_path) as image:
        width, height = image.size
    random.seed(Path(image_path).name)

    summary = "Auto-generated accessible chart summary."
    description = "This chart visualises key data points extracted from the uploaded image."

    point_count = 5
    data_points = []
    table_data = []
    for index in range(point_count):
        value = random.randint(10, 100)
        x_percent = round((index / (point_count - 1)) * 100, 2)
        y_percent = round(100 - (value / 100) * 100, 2)
        point_description = f"Data point {index + 1} has a value of {value}."
        x_pixel = round((x_percent / 100) * width, 2)
        y_pixel = round((y_percent / 100) * height, 2)

        data_points.append(
            {
                "id": index + 1,
                "label": f"Point {index + 1}",
                "value": value,
                "x_percent": x_percent,
                "y_percent": y_percent,
                "x_pixel": x_pixel,
                "y_pixel": y_pixel,
                "description": point_description,
            }
        )
        table_data.append({"label": f"Point {index + 1}", "value": value})

    return {
        "summary": summary,
        "description": description,
        "data_points": data_points,
        "table_data": table_data,
    }


def build_accessible_code(image_url: str, summary: str, data_points: list[dict[str, Any]]) -> str:
    focusables = []
    for point in data_points:
        focusables.append(
            f'    <button class="chart-point" style="left: {point["x_percent"]}%; top: {point["y_percent"]}%;" '
            f'aria-label="{point["description"]}" tabindex="0"></button>'
        )

    points_markup = "\n".join(focusables)

    code = f"""
<div class=\"chart-wrapper\" role=\"img\" aria-label=\"{summary}\" tabindex=\"0\">
  <img src=\"{image_url}\" alt=\"{summary}\" class=\"chart-image\" />
{points_markup}
</div>
<style>
.chart-wrapper {{
  position: relative;
  display: inline-block;
  outline: none;
}}
.chart-wrapper:focus {{
  box-shadow: 0 0 0 3px #2684ff;
}}
.chart-image {{
  display: block;
  width: 100%;
  height: auto;
}}
.chart-point {{
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}}
.chart-point:focus {{
  opacity: 1;
  width: 16px;
  height: 16px;
  margin-left: -8px;
  margin-top: -8px;
  border-radius: 50%;
  border: 2px solid #2684ff;
  background: rgba(38, 132, 255, 0.2);
}}
</style>
""".strip()

    return code


def process_chart(image_path: str, public_image_url: str) -> dict[str, Any]:
    result = simulate_cloud_processing(image_path)
    code = build_accessible_code(public_image_url, result["summary"], result["data_points"])
    result["generated_code"] = code
    return result
