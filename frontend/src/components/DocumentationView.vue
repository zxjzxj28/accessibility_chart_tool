<template>
  <div class="doc-page">
    <header class="doc-header">
      <div>
        <p class="eyebrow">ChartAccessibleView · Android 无障碍接入模板</p>
        <h1>快速接入指南</h1>
        <p class="muted">直接复制粘贴即可在 Android App 中完成自定义图表的无障碍支持，同时附带最小接入示例。</p>
      </div>
      <router-link class="ghost" to="/">返回任务面板</router-link>
    </header>

    <section class="card">
      <h2>依赖（Gradle）</h2>
      <pre class="code-block"><code>{{ gradleSnippet }}</code></pre>
    </section>

    <section class="card">
      <h2>核心代码（Java）</h2>
      <p class="muted">直接将 <code>ChartAccessibleView.java</code> 放入项目，替换包名为你的应用包名。</p>
      <pre class="code-block"><code>{{ javaSnippet }}</code></pre>
    </section>

    <section class="card">
      <h2>最小接入示例</h2>
      <div class="example">
        <h3>布局</h3>
        <pre class="code-block"><code>{{ layoutSnippet }}</code></pre>
        <h3>Activity（Java）</h3>
        <pre class="code-block"><code>{{ activitySnippet }}</code></pre>
      </div>
    </section>
  </div>
</template>

<script setup>
const gradleSnippet = `dependencies {
    implementation "androidx.core:core-ktx:1.13.1"
    implementation "androidx.customview:customview:1.2.0"
}`;

const javaSnippet = `package your.pkg;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.PointF;
import android.graphics.Rect;
import android.graphics.RectF;
import android.os.Bundle;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;
import android.view.accessibility.AccessibilityEvent;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.view.ViewCompat;
import androidx.core.view.accessibility.AccessibilityNodeInfoCompat;
import androidx.customview.widget.ExploreByTouchHelper;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/**
 * ChartAccessibleView（Java）
 * - 初次聚焦播报摘要，高亮框覆盖整图；
 * - 右移/下一项：依次聚焦每个数据点并播报点描述；
 * - 坐标系支持：NORMALIZED[0,1] / BITMAP(原图像素) / VIEW(视图像素)。
 */
public class ChartAccessibleView extends View {

    // ======== 公共数据模型 ========
    public static class DataPoint {
        public final int id;           // 1..N，0 保留给摘要
        public final float x;          // 与 coordSpace 对应
        public final float y;
        public final String description;

        public DataPoint(int id, float x, float y, @NonNull String description) {
            this.id = id;
            this.x = x;
            this.y = y;
            this.description = description;
        }
    }

    public enum CoordSpace { NORMALIZED, BITMAP, VIEW }

    public static class Spec {
        public final Bitmap image;
        public final String summary;
        public final List<DataPoint> points;
        public final CoordSpace coordSpace;

        public Spec(@NonNull Bitmap image,
                    @NonNull String summary,
                    @NonNull List<DataPoint> points,
                    @NonNull CoordSpace coordSpace) {
            this.image = image;
            this.summary = summary;
            this.points = points;
            this.coordSpace = coordSpace;
        }
    }

    // ======== 内部状态 ========
    private Spec spec;

    private final Matrix drawMatrix = new Matrix();
    private final RectF contentRect = new RectF();

    private final Paint imagePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint highlightPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint pointPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

    private static final int SUMMARY_ID = 0;
    private static final int INVALID_ID = Integer.MIN_VALUE;
    private int a11yFocusedVirtualId = INVALID_ID;

    private float dp(float v) { return v * getResources().getDisplayMetrics().density; }
    private float targetSizePx() { return dp(44f); } // TalkBack 命中更稳定

    public ChartAccessibleView(Context context) {
        this(context, null);
    }

    public ChartAccessibleView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        initView();
    }

    private void initView() {
        setFocusable(true);
        setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_YES);

        highlightPaint.setStyle(Paint.Style.STROKE);
        highlightPaint.setStrokeWidth(dp(2f));
        highlightPaint.setColor(Color.MAGENTA);
        highlightPaint.setAlpha(200);

        pointPaint.setStyle(Paint.Style.FILL);
        pointPaint.setColor(Color.MAGENTA);
        pointPaint.setAlpha(200);

        ViewCompat.setAccessibilityDelegate(this, a11yHelper);
    }

    // ======== 对外 API ========
    public void setData(@NonNull Spec spec) {
        this.spec = spec;
        requestLayout();
        invalidate();
        a11yHelper.invalidateRoot();
    }

    /** 页面展示后，如需默认把焦点放到“摘要” */
    public void requestInitialAccessibilityFocus() {
        a11yHelper.requestKeyboardFocusForVirtualView(SUMMARY_ID);
        a11yFocusedVirtualId = SUMMARY_ID;
        invalidate();
    }

    // ======== 布局与绘制 ========
    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        updateImageMatrixAndContentRect();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (spec == null) return;

        // 1) 绘制图表位图：等比居中
        canvas.drawBitmap(spec.image, drawMatrix, imagePaint);

        // 2) 高亮：摘要=外框；数据点=圆圈+小圆点
        if (a11yFocusedVirtualId == SUMMARY_ID) {
            canvas.drawRect(contentRect, highlightPaint);
        } else if (a11yFocusedVirtualId != INVALID_ID) {
            DataPoint dp = findPointById(a11yFocusedVirtualId);
            if (dp != null) {
                PointF p = pointToView(dp);
                float r = Math.max(targetSizePx() / 2f, dp(8f));
                canvas.drawCircle(p.x, p.y, r, highlightPaint);
                canvas.drawCircle(p.x, p.y, dp(3f), pointPaint);
            }
        }
    }

    @Override
    public boolean dispatchHoverEvent(MotionEvent event) {
        return a11yHelper.dispatchHoverEvent(event) || super.dispatchHoverEvent(event);
    }

    // ======== ExploreByTouchHelper（虚拟节点） ========
    private final ExploreByTouchHelper a11yHelper = new ExploreByTouchHelper(this) {
        @Override
        protected int getVirtualViewAt(float x, float y) {
            if (spec == null) return INVALID_ID;
            if (!contentRect.contains(x, y)) return INVALID_ID;

            Integer hit = nearestPointWithin(x, y, targetSizePx() / 2f);
            return hit != null ? hit : SUMMARY_ID;
        }

        @Override
        protected void getVisibleVirtualViews(@NonNull List<Integer> virtualViewIds) {
            virtualViewIds.add(SUMMARY_ID);
            if (spec == null || spec.points.isEmpty()) return;

            // 按“映射到视图坐标后的 x” 升序
            List<DataPoint> pts = new ArrayList<>(spec.points);
            Collections.sort(pts, new Comparator<DataPoint>() {
                @Override
                public int compare(DataPoint a, DataPoint b) {
                    float ax = pointToView(a).x;
                    float bx = pointToView(b).x;
                    return Float.compare(ax, bx);
                }
            });
            for (DataPoint p : pts) virtualViewIds.add(p.id);
        }

        @Override
        protected void onPopulateNodeForVirtualView(int virtualViewId,
                                                    @NonNull AccessibilityNodeInfoCompat node) {
            if (spec == null) return;
            node.setClassName("android.view.View");
            node.setEnabled(true);
            node.setFocusable(true);

            if (virtualViewId == SUMMARY_ID) {
                node.setContentDescription(spec.summary);
                Rect r = new Rect();
                contentRect.round(r);
                node.setBoundsInParent(r);
            } else {
                DataPoint dp = findPointById(virtualViewId);
                if (dp == null) return;
                node.setContentDescription(dp.description);
                Rect br = boundsForPoint(dp);
                node.setBoundsInParent(br);
            }
        }

        @Override
        protected void onPopulateEventForVirtualView(int virtualViewId,
                                                     @NonNull AccessibilityEvent event) {
            if (spec == null) return;
            event.setClassName("android.view.View");
            if (virtualViewId == SUMMARY_ID) {
                event.getText().add(spec.summary);
            } else {
                DataPoint dp = findPointById(virtualViewId);
                if (dp != null) event.getText().add(dp.description);
            }
        }

        @Override
        protected boolean onPerformActionForVirtualView(int virtualViewId, int action,
                                                        @Nullable Bundle arguments) {
            if (action == AccessibilityNodeInfoCompat.ACTION_ACCESSIBILITY_FOCUS) {
                a11yFocusedVirtualId = virtualViewId;
                invalidate();
                sendEventForVirtualView(virtualViewId,
                        AccessibilityEvent.TYPE_VIEW_ACCESSIBILITY_FOCUSED);
                return true;
            } else if (action == AccessibilityNodeInfoCompat.ACTION_CLEAR_ACCESSIBILITY_FOCUS) {
                a11yFocusedVirtualId = INVALID_ID;
                invalidate();
                return true;
            } else if (action == AccessibilityNodeInfoCompat.ACTION_CLICK) {
                // 需要“点按触发更多信息”可在此扩展
                return true;
            }
            return false;
        }
    };

    // ======== 矩阵与坐标映射 ========
    private void updateImageMatrixAndContentRect() {
        if (spec == null || spec.image == null) return;

        float vw = Math.max(1f, getWidth());
        float vh = Math.max(1f, getHeight());
        float bw = spec.image.getWidth();
        float bh = spec.image.getHeight();

        float scale = Math.min(vw / bw, vh / bh);
        float dx = (vw - bw * scale) / 2f;
        float dy = (vh - bh * scale) / 2f;

        drawMatrix.reset();
        drawMatrix.postScale(scale, scale);
        drawMatrix.postTranslate(dx, dy);

        RectF r = new RectF(0f, 0f, bw, bh);
        drawMatrix.mapRect(r);
        contentRect.set(r);
    }

    private PointF pointToView(@NonNull DataPoint dp) {
        if (spec == null) return new PointF(0, 0);
        switch (spec.coordSpace) {
            case NORMALIZED: {
                float x = contentRect.left + clamp01(dp.x) * contentRect.width();
                float y = contentRect.top + clamp01(dp.y) * contentRect.height();
                return new PointF(x, y);
            }
            case BITMAP: {
                float[] pts = new float[]{dp.x, dp.y};
                drawMatrix.mapPoints(pts);
                return new PointF(pts[0], pts[1]);
            }
            case VIEW:
            default:
                return new PointF(dp.x, dp.y);
        }
    }

    private Rect boundsForPoint(@NonNull DataPoint dp) {
        PointF p = pointToView(dp);
        float half = targetSizePx() / 2f;

        float l = clamp(p.x - half, contentRect.left, contentRect.right);
        float t = clamp(p.y - half, contentRect.top, contentRect.bottom);
        float r = clamp(p.x + half, contentRect.left, contentRect.right);
        float b = clamp(p.y + half, contentRect.top, contentRect.bottom);

        return new Rect((int) l, (int) t, (int) r, (int) b);
    }

    private Integer nearestPointWithin(float x, float y, float radius) {
        if (spec == null || spec.points == null) return null;
        float best = Float.MAX_VALUE;
        Integer bestId = null;
        float r2 = radius * radius;

        for (DataPoint dp : spec.points) {
            PointF p = pointToView(dp);
            float dx = p.x - x, dy = p.y - y;
            float d2 = dx * dx + dy * dy;
            if (d2 <= r2 && d2 < best) {
                best = d2;
                bestId = dp.id;
            }
        }
        return bestId;
    }

    @Nullable
    private DataPoint findPointById(int id) {
        if (spec == null || spec.points == null) return null;
        for (DataPoint dp : spec.points) if (dp.id == id) return dp;
        return null;
    }

    private float clamp01(float v) { return Math.max(0f, Math.min(1f, v)); }
    private float clamp(float v, float a, float b) { return Math.max(a, Math.min(b, v)); }
}
`;

const layoutSnippet = `<!-- res/layout/activity_chart.xml -->
<your.pkg.ChartAccessibleView
    android:id="@+id/chartA11y"
    android:layout_width="match_parent"
    android:layout_height="240dp"/>`;

const activitySnippet = `import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import java.util.Arrays;
import your.pkg.ChartAccessibleView;
import your.pkg.ChartAccessibleView.*;

public class ChartActivity extends AppCompatActivity {
    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_chart);

        ChartAccessibleView view = findViewById(R.id.chartA11y);

        Bitmap bmp = BitmapFactory.decodeResource(getResources(), R.drawable.sample_chart);

        // 假设坐标是归一化到 [0,1]
        Spec spec = new Spec(
            bmp,
            "2024年一至四月销售趋势总体上升，峰值出现在四月，约五十一万。",
            Arrays.asList(
                new DataPoint(1, 0.10f, 0.72f, "一月 销售额 23.5 万"),
                new DataPoint(2, 0.35f, 0.55f, "二月 销售额 31.2 万"),
                new DataPoint(3, 0.65f, 0.28f, "三月 销售额 46.8 万"),
                new DataPoint(4, 0.90f, 0.20f, "四月 销售额 51.0 万")
            ),
            CoordSpace.NORMALIZED
        );

        view.setData(spec);
        view.requestInitialAccessibilityFocus(); // 可选：初次进来直接播报摘要
    }
}
`;
</script>

<style scoped>
.doc-page {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--spacing-xl, 32px) var(--spacing-md, 16px) var(--spacing-2xl, 48px);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg, 24px);
}

.doc-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md, 16px);
  flex-wrap: wrap;
}

.doc-header h1 {
  margin: 0;
  font-size: var(--text-3xl, 24px);
  font-weight: 600;
  color: var(--color-text-primary, #24292f);
  letter-spacing: -0.02em;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  font-size: var(--text-xs, 12px);
  color: var(--color-primary, #2563eb);
  margin: 0 0 var(--spacing-sm, 8px);
}

.muted {
  color: var(--color-text-secondary, #57606a);
  font-size: var(--text-sm, 13px);
  margin-top: var(--spacing-xs, 4px);
  line-height: var(--leading-relaxed, 1.75);
}

.card {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border, #e1e4e8);
  border-radius: var(--radius-lg, 12px);
  padding: var(--spacing-lg, 24px);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(0, 0, 0, 0.05));
}

.card h2 {
  margin: 0 0 var(--spacing-md, 16px);
  font-size: var(--text-xl, 18px);
  font-weight: 600;
  color: var(--color-text-primary, #24292f);
}

.card h3 {
  margin: var(--spacing-md, 16px) 0 var(--spacing-sm, 8px);
  font-size: var(--text-md, 15px);
  font-weight: 600;
  color: var(--color-text-primary, #24292f);
}

.card h3:first-child {
  margin-top: 0;
}

.card p {
  margin: 0 0 var(--spacing-md, 16px);
  font-size: var(--text-sm, 13px);
  color: var(--color-text-secondary, #57606a);
  line-height: var(--leading-relaxed, 1.75);
}

.card p code {
  background: var(--color-bg, #fafbfc);
  padding: 2px 6px;
  border-radius: var(--radius-sm, 6px);
  font-family: var(--font-mono, 'JetBrains Mono', 'Fira Code', monospace);
  font-size: var(--text-xs, 12px);
  color: var(--color-primary, #2563eb);
  border: 1px solid var(--color-border-light, #eaecef);
}

.code-block {
  background: #1e293b;
  color: #e2e8f0;
  border-radius: var(--radius-md, 8px);
  padding: var(--spacing-md, 16px);
  overflow-x: auto;
  font-family: var(--font-mono, 'JetBrains Mono', 'Fira Code', monospace);
  line-height: var(--leading-relaxed, 1.75);
  font-size: var(--text-sm, 13px);
  border: 1px solid #334155;
}

.code-block code {
  white-space: pre;
  color: inherit;
  background: none;
  padding: 0;
  border: none;
  font-size: inherit;
}

.example {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
}

.ghost {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border, #e1e4e8);
  border-radius: var(--radius-md, 8px);
  padding: 8px 14px;
  color: var(--color-text-primary, #24292f);
  font-weight: 500;
  font-size: var(--text-sm, 13px);
  text-decoration: none;
  transition: background-color 0.15s ease, border-color 0.15s ease;
  white-space: nowrap;
}

.ghost:hover {
  background: var(--color-bg, #fafbfc);
  border-color: var(--color-text-muted, #8b949e);
}

@media (max-width: 640px) {
  .doc-header {
    flex-direction: column;
    align-items: stretch;
  }

  .code-block {
    font-size: var(--text-xs, 12px);
    padding: var(--spacing-sm, 8px);
  }
}
</style>
