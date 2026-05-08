import random
import math
import time
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from typing import Optional


# ============================================================
# 1. 数据模型
# ============================================================

@dataclass(frozen=True)
class Point:
    x: float
    y: float
    idx: int


@dataclass
class ClosestPairResult:
    d2: float
    p1: Optional[Point]
    p2: Optional[Point]
    distance_count: int = 0

    @property
    def distance(self) -> float:
        if self.d2 == float("inf"):
            return float("inf")
        return math.sqrt(self.d2)


# ============================================================
# 2. 点集生成器
# ============================================================

class PointGenerator:
    def __init__(self, max_coord: int = 1_000_000):
        self.max_coord = max_coord

    def generate(self, n: int, seed: int = 42) -> list[Point]:
        random.seed(seed)
        return [
            Point(
                x=random.uniform(0, self.max_coord),
                y=random.uniform(0, self.max_coord),
                idx=i
            )
            for i in range(n)
        ]


# ============================================================
# 3. 距离计算器
# ============================================================

class DistanceCounter:
    def __init__(self):
        self.count = 0

    def reset(self):
        self.count = 0

    def dist2(self, a: Point, b: Point) -> float:
        self.count += 1
        dx = a.x - b.x
        dy = a.y - b.y
        return dx * dx + dy * dy


# ============================================================
# 4. 蛮力法求解器
# ============================================================

class BruteForceSolver:
    def __init__(self):
        self.counter = DistanceCounter()

    def solve(self, points: list[Point]) -> ClosestPairResult:
        self.counter.reset()

        n = len(points)
        best = ClosestPairResult(float("inf"), None, None, 0)

        for i in range(n):
            for j in range(i + 1, n):
                d2 = self.counter.dist2(points[i], points[j])

                if d2 < best.d2:
                    best.d2 = d2
                    best.p1 = points[i]
                    best.p2 = points[j]

        best.distance_count = self.counter.count
        return best


# ============================================================
# 5. 分治法求解器
# ============================================================

class DivideConquerSolver:
    def __init__(self, record_steps: bool = False):
        self.record_steps = record_steps
        self.steps = []
        self.counter = DistanceCounter()

    def solve(self, points: list[Point]) -> tuple[ClosestPairResult, list[dict]]:
        self.steps = []
        self.counter.reset()

        if len(points) < 2:
            return ClosestPairResult(float("inf"), None, None, 0), []

        px = sorted(points, key=lambda p: (p.x, p.y))
        py = sorted(points, key=lambda p: (p.y, p.x))

        result, _ = self._divide(px, py, depth=0)
        result.distance_count = self.counter.count

        return result, self.steps

    def _divide(
        self,
        px: list[Point],
        py: list[Point],
        depth: int
    ) -> tuple[ClosestPairResult, list[Point]]:

        n = len(px)

        if n <= 3:
            result = self._solve_small(px)
            y_sorted = sorted(px, key=lambda p: (p.y, p.x))

            if self.record_steps and result.p1 and result.p2:
                self._record_step({
                    "type": "brute",
                    "depth": depth,
                    "points": px[:],
                    "pair": (result.p1, result.p2),
                    "distance": result.distance
                })

            return result, y_sorted

        mid = n // 2
        mid_x = px[mid].x

        left_px = px[:mid]
        right_px = px[mid:]

        left_ids = {p.idx for p in left_px}
        left_py = []
        right_py = []

        for p in py:
            if p.idx in left_ids:
                left_py.append(p)
            else:
                right_py.append(p)

        if self.record_steps:
            self._record_step({
                "type": "split",
                "depth": depth,
                "mid_x": mid_x,
                "points": px[:]
            })

        left_result, left_y = self._divide(left_px, left_py, depth + 1)
        right_result, right_y = self._divide(right_px, right_py, depth + 1)

        best = self._better(left_result, right_result)

        merged_y = self._merge_by_y(left_y, right_y)
        strip = self._build_strip(merged_y, mid_x, best.d2)

        if self.record_steps:
            self._record_step({
                "type": "strip",
                "depth": depth,
                "mid_x": mid_x,
                "strip": strip[:],
                "pair": (best.p1, best.p2) if best.p1 and best.p2 else None,
                "distance": best.distance
            })

        best = self._scan_strip(strip, best, depth)

        return best, merged_y

    def _solve_small(self, points: list[Point]) -> ClosestPairResult:
        best = ClosestPairResult(float("inf"), None, None, 0)

        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                d2 = self.counter.dist2(points[i], points[j])

                if d2 < best.d2:
                    best.d2 = d2
                    best.p1 = points[i]
                    best.p2 = points[j]

        return best

    def _better(
        self,
        a: ClosestPairResult,
        b: ClosestPairResult
    ) -> ClosestPairResult:
        return a if a.d2 <= b.d2 else b

    def _merge_by_y(
        self,
        left: list[Point],
        right: list[Point]
    ) -> list[Point]:
        merged = []
        i = 0
        j = 0

        while i < len(left) and j < len(right):
            if left[i].y <= right[j].y:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1

        merged.extend(left[i:])
        merged.extend(right[j:])

        return merged

    def _build_strip(
        self,
        points_by_y: list[Point],
        mid_x: float,
        best_d2: float
    ) -> list[Point]:
        return [
            p for p in points_by_y
            if (p.x - mid_x) * (p.x - mid_x) < best_d2
        ]

    def _scan_strip(
        self,
        strip: list[Point],
        best: ClosestPairResult,
        depth: int
    ) -> ClosestPairResult:

        for i in range(len(strip)):
            # 经典分治最近点对算法中，候选带每个点最多检查后面 7 个点
            upper = min(i + 8, len(strip))

            for j in range(i + 1, upper):
                dy = strip[j].y - strip[i].y

                if dy * dy >= best.d2:
                    break

                d2 = self.counter.dist2(strip[i], strip[j])

                if d2 < best.d2:
                    best = ClosestPairResult(
                        d2=d2,
                        p1=strip[i],
                        p2=strip[j],
                        distance_count=self.counter.count
                    )

                    if self.record_steps:
                        self._record_step({
                            "type": "best",
                            "depth": depth,
                            "pair": (best.p1, best.p2),
                            "distance": best.distance
                        })

        return best

    def _record_step(self, step: dict):
        self.steps.append(step)


# ============================================================
# 6. 运行时间统计工具
# ============================================================

class BenchmarkRunner:
    def __init__(self):
        self.brute_solver = BruteForceSolver()

    def run_divide(self, points: list[Point]) -> tuple[ClosestPairResult, float]:
        solver = DivideConquerSolver(record_steps=False)

        start = time.perf_counter()
        result, _ = solver.solve(points)
        elapsed_ms = (time.perf_counter() - start) * 1000

        return result, elapsed_ms

    def run_brute(self, points: list[Point]) -> tuple[ClosestPairResult, float]:
        start = time.perf_counter()
        result = self.brute_solver.solve(points)
        elapsed_ms = (time.perf_counter() - start) * 1000

        return result, elapsed_ms


# ============================================================
# 7. 可视化绘图类
# ============================================================

class AlgorithmVisualizer:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.margin = 48

        self.bg = "#f7fbff"
        self.grid_color = "#e6edf5"
        self.border_color = "#9eb1c7"

        self.point_color = "#4ca3ff"
        self.strip_color = "#ffb347"
        self.split_color = "#555555"
        self.best_color = "#ff4d4d"

    def draw(
        self,
        points: list[Point],
        highlight_pair: Optional[tuple[Point, Point]] = None,
        mid_x: Optional[float] = None,
        strip: Optional[list[Point]] = None,
        message: Optional[str] = None
    ):
        self.canvas.delete("all")

        if not points:
            return

        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 560)

        self._draw_grid(width, height)
        self._draw_border(width, height)

        if message:
            self._draw_message(message)

        if strip:
            self._draw_strip(points, strip)

        if mid_x is not None:
            self._draw_split_line(points, mid_x)

        self._draw_points(points)

        if highlight_pair:
            self._draw_pair(points, highlight_pair)

        self._draw_axis_text(width, height)

    def _bounds(self, points: list[Point]) -> tuple[float, float, float, float]:
        xs = [p.x for p in points]
        ys = [p.y for p in points]

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)

        if max_x == min_x:
            max_x += 1

        if max_y == min_y:
            max_y += 1

        return min_x, max_x, min_y, max_y

    def _to_canvas(self, points: list[Point], p: Point) -> tuple[float, float]:
        min_x, max_x, min_y, max_y = self._bounds(points)
        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 560)

        x = self.margin + (p.x - min_x) / (max_x - min_x) * (width - 2 * self.margin)
        y = height - self.margin - (p.y - min_y) / (max_y - min_y) * (height - 2 * self.margin)

        return x, y

    def _x_to_canvas(self, points: list[Point], x_value: float) -> float:
        min_x, max_x, _, _ = self._bounds(points)
        width = max(self.canvas.winfo_width(), 800)

        return self.margin + (x_value - min_x) / (max_x - min_x) * (width - 2 * self.margin)

    def _draw_grid(self, width: int, height: int):
        for i in range(10):
            x = self.margin + i * (width - 2 * self.margin) / 9
            self.canvas.create_line(
                x,
                self.margin,
                x,
                height - self.margin,
                fill=self.grid_color
            )

        for i in range(8):
            y = self.margin + i * (height - 2 * self.margin) / 7
            self.canvas.create_line(
                self.margin,
                y,
                width - self.margin,
                y,
                fill=self.grid_color
            )

    def _draw_border(self, width: int, height: int):
        self.canvas.create_rectangle(
            self.margin,
            self.margin,
            width - self.margin,
            height - self.margin,
            outline=self.border_color,
            width=2
        )

    def _draw_message(self, message: str):
        self.canvas.create_text(
            self.margin,
            24,
            text=message,
            anchor=tk.W,
            fill="#1a2a36",
            font=("Microsoft YaHei", 12, "bold")
        )

    def _draw_points(self, points: list[Point]):
        radius = self._point_radius(len(points))

        for p in points:
            x, y = self._to_canvas(points, p)
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=self.point_color,
                outline=""
            )

    def _draw_strip(self, points: list[Point], strip: list[Point]):
        for p in strip:
            x, y = self._to_canvas(points, p)
            self.canvas.create_oval(
                x - 6,
                y - 6,
                x + 6,
                y + 6,
                fill=self.strip_color,
                outline="#8a5200",
                width=1
            )

    def _draw_split_line(self, points: list[Point], mid_x: float):
        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 560)

        x = self._x_to_canvas(points, mid_x)

        self.canvas.create_line(
            x,
            self.margin,
            x,
            height - self.margin,
            fill=self.split_color,
            dash=(6, 6),
            width=2
        )

        self.canvas.create_text(
            x + 8,
            self.margin + 18,
            text="分割线 L",
            anchor=tk.W,
            fill="#333333",
            font=("Microsoft YaHei", 10, "bold")
        )

    def _draw_pair(self, points: list[Point], pair: tuple[Point, Point]):
        p1, p2 = pair

        if not p1 or not p2:
            return

        x1, y1 = self._to_canvas(points, p1)
        x2, y2 = self._to_canvas(points, p2)

        self.canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            fill=self.best_color,
            width=4
        )

        for x, y in [(x1, y1), (x2, y2)]:
            self.canvas.create_oval(
                x - 9,
                y - 9,
                x + 9,
                y + 9,
                outline=self.best_color,
                width=3
            )
            self.canvas.create_oval(
                x - 4,
                y - 4,
                x + 4,
                y + 4,
                fill=self.best_color,
                outline=""
            )

    def _draw_axis_text(self, width: int, height: int):
        self.canvas.create_text(
            width / 2,
            height - 16,
            text="x 坐标",
            fill="#334455",
            font=("Microsoft YaHei", 10)
        )

        self.canvas.create_text(
            18,
            height / 2,
            text="y",
            fill="#334455",
            font=("Microsoft YaHei", 10, "bold")
        )

    def _point_radius(self, n: int) -> int:
        if n <= 300:
            return 4
        if n <= 1000:
            return 3
        return 2


# ============================================================
# 8. 主应用程序类
# ============================================================

class ClosestPairApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("分治法求最近点对问题 - 面向对象可视化版")
        self.root.geometry("1180x760")
        self.root.minsize(1000, 680)

        self.colors = {
            "bg": "#101820",
            "panel": "#17212b",
            "panel2": "#1f2d3a",
            "fg": "#f2f6fa",
            "sub": "#aab7c4",
            "accent": "#00bcd4",
            "green": "#6dd47e"
        }

        self.generator = PointGenerator()
        self.benchmark_runner = BenchmarkRunner()

        self.points: list[Point] = []
        self.result: Optional[ClosestPairResult] = None
        self.steps: list[dict] = []
        self.step_index = 0
        self.animating = False
        self.paused = False

        self._setup_style()
        self._build_ui()

        self.visualizer = AlgorithmVisualizer(self.canvas)

        self.generate_points()

    # ------------------------------------------------------------
    # UI 初始化
    # ------------------------------------------------------------

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "TFrame",
            background=self.colors["bg"]
        )

        style.configure(
            "Panel.TFrame",
            background=self.colors["panel"]
        )

        style.configure(
            "TLabel",
            background=self.colors["bg"],
            foreground=self.colors["fg"],
            font=("Microsoft YaHei", 10)
        )

        style.configure(
            "Title.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["fg"],
            font=("Microsoft YaHei", 18, "bold")
        )

        style.configure(
            "Sub.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["sub"],
            font=("Microsoft YaHei", 10)
        )

        style.configure(
            "Panel.TLabel",
            background=self.colors["panel"],
            foreground=self.colors["fg"],
            font=("Microsoft YaHei", 10)
        )

        style.configure(
            "TButton",
            font=("Microsoft YaHei", 10),
            padding=7,
            background=self.colors["panel2"],
            foreground=self.colors["fg"]
        )

        style.map(
            "TButton",
            background=[("active", "#26384a")]
        )

        style.configure(
            "Accent.TButton",
            font=("Microsoft YaHei", 10, "bold"),
            padding=7,
            background=self.colors["accent"],
            foreground="#061018"
        )

        style.map(
            "Accent.TButton",
            background=[("active", "#18d4ec")]
        )

        style.configure(
            "TEntry",
            fieldbackground="#0f1720",
            foreground=self.colors["fg"],
            insertcolor=self.colors["fg"],
            bordercolor=self.colors["panel2"]
        )

    def _build_ui(self):
        self.root.configure(bg=self.colors["bg"])

        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)

        self._build_header(outer)

        body = ttk.Frame(outer)
        body.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(body, style="Panel.TFrame", padding=12)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

        right_panel = ttk.Frame(body, style="Panel.TFrame", padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_left_panel(left_panel)
        self._build_right_panel(right_panel)

    def _build_header(self, parent):
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(
            header,
            text="分治法求最近点对问题",
            style="Title.TLabel"
        ).pack(side=tk.LEFT)

        ttk.Label(
            header,
            text="面向对象封装 · 蛮力法验证 · 分治法动画 · 性能对比",
            style="Sub.TLabel"
        ).pack(side=tk.LEFT, padx=18)

    def _build_left_panel(self, parent):
        ttk.Label(
            parent,
            text="参数设置",
            style="Panel.TLabel",
            font=("Microsoft YaHei", 13, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))

        form = ttk.Frame(parent, style="Panel.TFrame")
        form.pack(fill=tk.X)

        ttk.Label(form, text="点数 N", style="Panel.TLabel").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.n_var = tk.StringVar(value="120")
        ttk.Entry(form, textvariable=self.n_var, width=14).grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(form, text="随机种子", style="Panel.TLabel").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.seed_var = tk.StringVar(value="42")
        ttk.Entry(form, textvariable=self.seed_var, width=14).grid(row=1, column=1, padx=8, pady=6)

        ttk.Label(form, text="动画速度", style="Panel.TLabel").grid(row=2, column=0, sticky=tk.W, pady=6)
        self.speed_var = tk.IntVar(value=320)
        ttk.Scale(
            form,
            from_=80,
            to=900,
            variable=self.speed_var,
            orient=tk.HORIZONTAL,
            length=115
        ).grid(row=2, column=1, padx=8, pady=6)

        ttk.Separator(parent).pack(fill=tk.X, pady=12)

        ttk.Button(parent, text="生成随机点", style="Accent.TButton", command=self.generate_points).pack(fill=tk.X, pady=4)
        ttk.Button(parent, text="蛮力法求解", command=self.run_brute_force).pack(fill=tk.X, pady=4)
        ttk.Button(parent, text="分治法求解", command=self.run_divide_conquer).pack(fill=tk.X, pady=4)
        ttk.Button(parent, text="开始动画演示", style="Accent.TButton", command=self.start_animation).pack(fill=tk.X, pady=4)

        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill=tk.X, pady=4)

        ttk.Button(row, text="单步", command=self.next_step).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ttk.Button(row, text="暂停/继续", command=self.toggle_pause).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        ttk.Button(parent, text="性能对比", command=self.run_benchmark).pack(fill=tk.X, pady=4)
        ttk.Button(parent, text="清空高亮", command=self.redraw_plain_points).pack(fill=tk.X, pady=4)

        ttk.Separator(parent).pack(fill=tk.X, pady=12)

        ttk.Label(
            parent,
            text="运行结果",
            style="Panel.TLabel",
            font=("Microsoft YaHei", 13, "bold")
        ).pack(anchor=tk.W, pady=(0, 8))

        self.result_text = tk.Text(
            parent,
            width=36,
            height=14,
            bg="#0f1720",
            fg=self.colors["fg"],
            insertbackground=self.colors["fg"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 10)
        )
        self.result_text.pack(fill=tk.X)

        ttk.Separator(parent).pack(fill=tk.X, pady=12)

        ttk.Label(
            parent,
            text="图例",
            style="Panel.TLabel",
            font=("Microsoft YaHei", 13, "bold")
        ).pack(anchor=tk.W, pady=(0, 6))

        legends = [
            "蓝色点：随机生成的平面点",
            "灰色虚线：分治递归分割线",
            "橙色点：合并阶段候选带点",
            "红色线：当前或最终最近点对"
        ]

        for item in legends:
            ttk.Label(parent, text=item, style="Panel.TLabel").pack(anchor=tk.W, pady=2)

    def _build_right_panel(self, parent):
        self.status_var = tk.StringVar(value="等待生成点集。")

        ttk.Label(
            parent,
            textvariable=self.status_var,
            style="Panel.TLabel",
            font=("Microsoft YaHei", 11, "bold")
        ).pack(anchor=tk.W, pady=(0, 8))

        self.canvas = tk.Canvas(
            parent,
            width=820,
            height=600,
            bg="#f7fbff",
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------

    def _write_result(self, text: str):
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)

    def _read_parameters(self) -> tuple[int, int]:
        try:
            n = int(self.n_var.get())
            seed = int(self.seed_var.get())

            if n < 2:
                raise ValueError

            return n, seed

        except ValueError:
            raise ValueError("点数 N 和随机种子必须是整数，并且 N >= 2。")

    def _format_result(self, title: str, result: ClosestPairResult, elapsed_ms: float) -> str:
        if not result.p1 or not result.p2:
            return f"{title}\n没有找到有效点对。"

        return (
            f"【{title}】\n"
            f"最短距离：{result.distance:.8f}\n"
            f"最近点对：#{result.p1.idx} 与 #{result.p2.idx}\n"
            f"点 1：({result.p1.x:.2f}, {result.p1.y:.2f})\n"
            f"点 2：({result.p2.x:.2f}, {result.p2.y:.2f})\n"
            f"距离计算次数：{result.distance_count}\n"
            f"运行时间：{elapsed_ms:.3f} ms\n"
        )

    # ------------------------------------------------------------
    # 按钮功能
    # ------------------------------------------------------------

    def generate_points(self):
        try:
            n, seed = self._read_parameters()
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))
            return

        self.points = self.generator.generate(n, seed)
        self.result = None
        self.steps = []
        self.step_index = 0
        self.animating = False
        self.paused = False

        self.status_var.set(f"已生成 {n} 个随机点。")
        self._write_result(
            f"点集生成完成\n"
            f"点数 N：{n}\n"
            f"随机种子：{seed}\n\n"
            f"建议：\n"
            f"1. N <= 300 适合动画演示\n"
            f"2. N <= 6000 适合蛮力法验证\n"
            f"3. N 较大时建议只运行分治法\n"
        )

        self.visualizer.draw(
            self.points,
            message=f"已生成 {n} 个随机点"
        )

    def run_brute_force(self):
        if not self.points:
            return

        if len(self.points) > 6000:
            messagebox.showwarning(
                "规模过大",
                "蛮力法时间复杂度为 O(N²)，N 太大时会非常慢。请将 N 调小到 6000 以内。"
            )
            return

        start = time.perf_counter()
        solver = BruteForceSolver()
        result = solver.solve(self.points)
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.result = result

        self.status_var.set("蛮力法求解完成。")
        self._write_result(
            self._format_result("蛮力法结果", result, elapsed_ms)
            + "\n复杂度分析：\n蛮力法枚举所有点对，时间复杂度为 O(N²)。"
        )

        self.visualizer.draw(
            self.points,
            highlight_pair=(result.p1, result.p2),
            message=f"蛮力法完成：最短距离 = {result.distance:.6f}"
        )

    def run_divide_conquer(self):
        if not self.points:
            return

        start = time.perf_counter()
        solver = DivideConquerSolver(record_steps=False)
        result, _ = solver.solve(self.points)
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.result = result

        self.status_var.set("分治法求解完成。")
        self._write_result(
            self._format_result("分治法结果", result, elapsed_ms)
            + "\n复杂度分析：\n"
            + "分治法先按 x 坐标排序，然后递归二分点集，"
            + "合并时只检查分割线附近的候选带，整体复杂度为 O(N log N)。"
        )

        self.visualizer.draw(
            self.points,
            highlight_pair=(result.p1, result.p2),
            message=f"分治法完成：最短距离 = {result.distance:.6f}"
        )

    def start_animation(self):
        if not self.points:
            return

        if len(self.points) > 300:
            messagebox.showwarning(
                "点数过多",
                "动画演示建议 N <= 300。点太多时分割线和候选带会过于密集。"
            )
            return

        solver = DivideConquerSolver(record_steps=True)
        self.result, self.steps = solver.solve(self.points)

        self.step_index = 0
        self.animating = True
        self.paused = False

        self.status_var.set("动画演示中：灰色虚线为分割线，橙色点为候选带，红色线为最近点对。")

        self._write_result(
            f"【动画演示】\n"
            f"共记录步骤：{len(self.steps)}\n\n"
            f"展示内容：\n"
            f"1. 递归划分点集\n"
            f"2. 小规模子问题蛮力求解\n"
            f"3. 合并阶段构造候选带\n"
            f"4. 候选带中更新最近点对\n"
        )

        self._animate()

    def toggle_pause(self):
        if not self.animating:
            return

        self.paused = not self.paused

        if self.paused:
            self.status_var.set("动画已暂停。")
        else:
            self.status_var.set("动画继续播放。")
            self._animate()

    def next_step(self):
        if not self.points:
            return

        if not self.steps:
            solver = DivideConquerSolver(record_steps=True)
            self.result, self.steps = solver.solve(self.points)
            self.step_index = 0

        self.animating = True
        self.paused = True
        self._draw_next_step()

    def run_benchmark(self):
        if not self.points:
            return

        n = len(self.points)

        divide_result, divide_ms = self.benchmark_runner.run_divide(self.points)

        lines = [
            "【性能对比】",
            f"点数 N：{n}",
            "",
            f"{'算法':<12}{'时间/ms':>12}{'最短距离':>18}{'距离计算次数':>16}",
            "-" * 62,
            f"{'分治法':<12}{divide_ms:>12.3f}{divide_result.distance:>18.6f}{divide_result.distance_count:>16}"
        ]

        if n <= 6000:
            brute_result, brute_ms = self.benchmark_runner.run_brute(self.points)
            same = abs(brute_result.d2 - divide_result.d2) < 1e-7
            speedup = brute_ms / divide_ms if divide_ms > 0 else float("inf")

            lines.append(
                f"{'蛮力法':<12}{brute_ms:>12.3f}{brute_result.distance:>18.6f}{brute_result.distance_count:>16}"
            )
            lines.append("")
            lines.append(f"结果一致：{'是' if same else '否'}")
            lines.append(f"分治法相对蛮力法加速约：{speedup:.2f} 倍")

        else:
            pair_count = n * (n - 1) // 2
            lines.append("")
            lines.append("蛮力法未运行：N 较大，O(N²) 计算过慢。")
            lines.append(f"若运行蛮力法，需要比较点对数量：{pair_count:,}")

        lines.append("")
        lines.append("分析：")
        lines.append("蛮力法时间复杂度为 O(N²)。")
        lines.append("分治法时间复杂度为 O(N log N)。")
        lines.append("数据规模越大，分治法优势越明显。")

        self.status_var.set("性能对比完成。")
        self._write_result("\n".join(lines))

        self.visualizer.draw(
            self.points,
            highlight_pair=(divide_result.p1, divide_result.p2),
            message=f"性能对比完成：分治法耗时 {divide_ms:.3f} ms"
        )

    def redraw_plain_points(self):
        if self.points:
            self.visualizer.draw(
                self.points,
                message="已清空高亮，仅显示随机点集"
            )

    # ------------------------------------------------------------
    # 动画逻辑
    # ------------------------------------------------------------

    def _animate(self):
        if not self.animating or self.paused:
            return

        if self.step_index >= len(self.steps):
            self._finish_animation()
            return

        self._draw_next_step()

        delay = int(self.speed_var.get())
        self.root.after(delay, self._animate)

    def _draw_next_step(self):
        if self.step_index >= len(self.steps):
            self._finish_animation()
            return

        step = self.steps[self.step_index]
        self.step_index += 1

        prefix = f"步骤 {self.step_index}/{len(self.steps)}"

        if step["type"] == "split":
            self.visualizer.draw(
                self.points,
                mid_x=step["mid_x"],
                message=f"{prefix}：递归划分，深度 {step['depth']}"
            )

        elif step["type"] == "brute":
            self.visualizer.draw(
                self.points,
                highlight_pair=step["pair"],
                message=f"{prefix}：小规模子问题使用蛮力法，深度 {step['depth']}"
            )

        elif step["type"] == "strip":
            self.visualizer.draw(
                self.points,
                highlight_pair=step["pair"],
                mid_x=step["mid_x"],
                strip=step["strip"],
                message=f"{prefix}：合并阶段候选带扫描，当前 d = {step['distance']:.6f}"
            )

        elif step["type"] == "best":
            self.visualizer.draw(
                self.points,
                highlight_pair=step["pair"],
                message=f"{prefix}：发现更近点对，更新 d = {step['distance']:.6f}"
            )

    def _finish_animation(self):
        self.animating = False
        self.paused = False

        if self.result and self.result.p1 and self.result.p2:
            self.status_var.set("动画演示结束。")

            self._write_result(
                f"【动画演示结束】\n"
                f"最终最短距离：{self.result.distance:.8f}\n"
                f"最近点对：#{self.result.p1.idx} 与 #{self.result.p2.idx}\n"
                f"点 1：({self.result.p1.x:.2f}, {self.result.p1.y:.2f})\n"
                f"点 2：({self.result.p2.x:.2f}, {self.result.p2.y:.2f})\n"
                f"距离计算次数：{self.result.distance_count}\n\n"
                f"结论：\n"
                f"分治法通过递归划分缩小问题规模，"
                f"并在合并阶段只扫描候选带，从而避免枚举所有点对。"
            )

            self.visualizer.draw(
                self.points,
                highlight_pair=(self.result.p1, self.result.p2),
                message=f"动画结束：最终最短距离 = {self.result.distance:.6f}"
            )


# ============================================================
# 9. 程序入口
# ============================================================

def main():
    root = tk.Tk()
    ClosestPairApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()