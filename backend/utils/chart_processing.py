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


def build_accessible_code(
    image_url: str, summary: str, data_points: list[dict[str, Any]]
) -> dict[str, Any]:
    html_points = []
    for point in data_points:
        html_points.append(
            f'    <button class="chart-point" style="left: {point["x_percent"]}%; top: {point["y_percent"]}%;" '
            f'aria-label="{point["description"]}" tabindex="0"></button>'
        )

    html_markup = "\n".join(html_points)
    web_snippet = f"""
<div class=\"chart-wrapper\" role=\"img\" aria-label=\"{summary}\" tabindex=\"0\">
  <img src=\"{image_url}\" alt=\"{summary}\" class=\"chart-image\" />
{html_markup}
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

    def _android_code(language: str) -> str:
        class_decl = (
            "public class AccessibleChartActivity extends AppCompatActivity {"
            if language == "java"
            else "class AccessibleChartActivity : AppCompatActivity() {"
        )
        on_create = (
            "    @Override\n    protected void onCreate(Bundle savedInstanceState) {"
            if language == "java"
            else "    override fun onCreate(savedInstanceState: Bundle?) {"
        )
        super_call = (
            "        super.onCreate(savedInstanceState);\n        setContentView(R.layout.activity_accessible_chart);"
            if language == "java"
            else "        super.onCreate(savedInstanceState)\n        setContentView(R.layout.activity_accessible_chart)"
        )
        summary_line = (
            f"        String chartSummary = \"{summary}\";"
            if language == "java"
            else f"        val chartSummary = \"{summary}\""
        )

        points_lines = []
        for point in data_points:
            label = point["label"]
            value = point["value"]
            if language == "java":
                points_lines.append(
                    f'                new ChartPoint("{label}", {value})'
                )
            else:
                points_lines.append(f'                ChartPoint("{label}", {value})')

        if language == "java":
            points_block = "List<ChartPoint> points = Arrays.asList(\n" + ",\n".join(points_lines) + "\n        );"
        else:
            points_block = "val points = listOf(\n" + ",\n".join(points_lines) + "\n        )"

        register_block = (
            "        chartView.render(points, chartSummary);"
            if language == "java"
            else "        chartView.render(points, chartSummary)"
        )

        class_end = "}" if language == "java" else "}"

        code = [
            "// 自动生成的可访问图表集成示例",
            "package com.example.chart;",
            "",
            "import android.os.Bundle;",
            "import androidx.appcompat.app.AppCompatActivity;",
            "",
            class_decl,
            on_create,
            super_call,
            "        AccessibleChartView chartView = findViewById(R.id.chartView);"
            if language == "java"
            else "        val chartView: AccessibleChartView = findViewById(R.id.chartView)",
            summary_line,
            points_block,
            register_block,
            "    }",
            class_end,
        ]

        if language == "java":
            code.insert(
                -2,
                "        ChartPointAdapter adapter = new ChartPointAdapter(points);\n        chartView.setAdapter(adapter);",
            )
        else:
            code.insert(
                -2,
                "        val adapter = ChartPointAdapter(points)\n        chartView.adapter = adapter",
            )

        return "\n".join(code)

    integration_steps = {
        "java": [
            "1. 在模块的 build.gradle 中启用 viewBinding 并确保 minSdk ≥ 21。",
            "2. 将生成的 `AccessibleChartActivity.java` 放入 `app/src/main/java/com/example/chart/` 目录。",
            "3. 在布局文件中引用自定义的 `AccessibleChartView`，并为其分配 `@+id/chartView`。",
            "4. 通过无障碍检查（TalkBack）验证每个数据点的朗读内容。",
        ],
        "kotlin": [
            "1. 在模块的 build.gradle.kts 中启用 viewBinding。",
            "2. 将 `AccessibleChartActivity.kt` 放入 `app/src/main/java/com/example/chart/`。",
            "3. 在布局文件内引用 `AccessibleChartView` 并保持 id 为 `chartView`。",
            "4. 编译并运行，使用无障碍服务验证焦点移动顺序。",
        ],
    }

    return {
        "web": web_snippet,
        "java": _android_code("java"),
        "kotlin": _android_code("kotlin"),
        "integration": integration_steps,
    }


def process_chart(image_path: str, public_image_url: str) -> dict[str, Any]:
    result = simulate_cloud_processing(image_path)
    bundle = build_accessible_code(public_image_url, result["summary"], result["data_points"])
    result["generated_code"] = bundle.get("web")
    result["java_code"] = bundle.get("java")
    result["kotlin_code"] = bundle.get("kotlin")
    result["integration_doc"] = bundle.get("integration")
    return result
