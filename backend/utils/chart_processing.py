from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from PIL import Image


def simulate_cloud_processing(image_path: str) -> dict[str, Any]:
    """模拟外部服务对图表图片进行解析。"""
    with Image.open(image_path) as image:
        width, height = image.size
    random.seed(Path(image_path).name)

    summary = "自动生成的图表摘要"
    point_count = 5
    data_points: list[dict[str, Any]] = []
    table_data: list[dict[str, Any]] = []

    for index in range(point_count):
        value = random.randint(10, 100)
        x_percent = round((index / max(point_count - 1, 1)) * 100, 2)
        y_percent = round(100 - (value / 100) * 100, 2)
        point_description = f"第 {index + 1} 个数据点的数值为 {value}。"
        x_pixel = round((x_percent / 100) * width, 2)
        y_pixel = round((y_percent / 100) * height, 2)

        data_points.append(
            {
                "id": index + 1,
                "label": f"数据点 {index + 1}",
                "value": value,
                "x_percent": x_percent,
                "y_percent": y_percent,
                "x_pixel": x_pixel,
                "y_pixel": y_pixel,
                "description": point_description,
            }
        )
        table_data.append({"label": f"数据点 {index + 1}", "value": value})

    return {
        "summary": summary,
        "data_points": data_points,
        "table_data": table_data,
    }


def process_chart(image_path: str, public_image_url: str) -> dict[str, Any]:
    del public_image_url  # 当前实现不依赖公开地址，保留参数以兼容调用
    return simulate_cloud_processing(image_path)
