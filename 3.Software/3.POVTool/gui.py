# -*- coding: utf-8 -*-
"""
MugglesWand POV 图案生成器 —— PySide6 图形界面。

布局：
  ┌────────────────────────────────────────────────┐
  │ 标题                                        … │
  ├───────────────┬────────────────────────────────┤
  │ 控制面板        │  QTabWidget                   │
  │ (固定宽度)     │  [挥舞动画] [点阵预览]          │
  └───────────────┴────────────────────────────────┘

核心交互：
  - 选择/拖入图片 -> 实时转换为彩色点阵（列数=LED 数、行数=播放帧数）
  - 横扫/竖扫 4 种方向 -> 生成不同行列映射的图案数组
  - 「挥舞动画」页用魔杖线稿渲染真实挥舞路径，所见即所得
  - 导出为固件风格 CRGB 数组，可一键插入 src/APP/APP_POVPatterns.h
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, QSettings, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core import (
    DIRECTION_OPTIONS,
    POVConfig,
    POVPattern,
    auto_rows,
    c_identifier_ok,
    convert,
    sanitize_name,
)
from exporter import (
    DEFAULT_FIRMWARE_HEADER,
    generate_snippet,
    generate_standalone_header,
    insert_into_header,
)

def resource_path(name: str) -> Path:
    """资源文件路径：源码运行取项目根目录下文件；PyInstaller 打包后从解压目录读取。"""
    if getattr(sys, "frozen", False):  # PyInstaller 冻结运行（exe）
        return Path(sys._MEIPASS) / name
    return Path(__file__).resolve().parent / name


# 魔杖线稿（灯带区域横向 x=30~1310，长度 1280px）
WAND_ART_PATH = resource_path("wand_lineart.png")
STRIP_X0, STRIP_LEN = 30, 1280

# 主题色
C_BG = QColor("#15161a")
C_LED_OFF = QColor("#262830")
C_ACCENT = QColor("#4f8cff")
C_TEXT_DIM = QColor("#8a8f9c")

QSS = """
QWidget { background: #1c1d22; color: #dfe1e6; font-family: "Microsoft YaHei UI"; font-size: 9pt; }
QMainWindow { background: #1c1d22; }
QLabel#title { font-size: 14pt; font-weight: 600; color: #ffffff; }
QLabel#dim { color: #8a8f9c; }
QLabel#ok { color: #67c23a; }
QLabel#warn { color: #e6a23c; }
QPushButton { background: #2a2d36; border: 1px solid #3a3e4a; border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { background: #343847; border-color: #4f8cff; }
QPushButton:pressed { background: #242731; }
QPushButton:disabled { color: #5a5e6a; border-color: #2e313b; background: #24262c; }
QPushButton#primary { background: #2f6feb; border: none; color: #fff; font-weight: 600; }
QPushButton#primary:hover { background: #3b7cf5; }
QPushButton#primary:pressed { background: #2560d6; }
QPushButton#primary:disabled { background: #2c3550; color: #7d8296; }
QLineEdit, QSpinBox, QComboBox { background: #17181c; border: 1px solid #3a3e4a; border-radius: 6px; padding: 4px 8px; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #4f8cff; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background: #23242a; border: 1px solid #3a3e4a; selection-background-color: #2f6feb; }
QSlider { background: transparent; min-height: 22px; }
QSlider::groove:horizontal { height: 6px; background: #2a2e3d; border-radius: 3px; }
QSlider::sub-page:horizontal { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #2f6feb, stop: 1 #6d9cf5); border-radius: 3px; }
QSlider::handle:horizontal { width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; background: #f4f6fa; border: 2px solid #3b7cf5; }
QSlider::handle:horizontal:hover { background: #ffffff; border-color: #6d9cf5; }
QSlider::handle:horizontal:pressed { background: #dbe4f5; border-color: #2f6feb; }
QLabel, QCheckBox { background: transparent; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 15px; height: 15px; border-radius: 4px; border: 1px solid #4a4e5c; background: #17181c; }
QCheckBox::indicator:hover { border-color: #4f8cff; }
QCheckBox::indicator:checked { background: #2f6feb; border-color: #2f6feb; }
QTabWidget::pane { border: 1px solid #2e313b; border-radius: 8px; background: #15161a; top: -1px; }
QTabBar::tab { background: transparent; padding: 8px 20px; color: #9aa0ae; }
QTabBar::tab:selected { color: #fff; border-bottom: 2px solid #4f8cff; }
QGroupBox { background: #20222b; border: 1px solid #2e313b; border-radius: 10px; margin-top: 12px; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; background: transparent; color: #c8ccd6; font-weight: 600; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #3a3e4a; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QStatusBar { background: #17181c; color: #8a8f9c; border-top: 1px solid #2e313b; }
QToolTip { background: #2a2d36; color: #dfe1e6; border: 1px solid #4a4e5c; }
"""


# ===========================================================================
# 通用：可缩放画布基类（滚轮缩放、双击适应、fit 模式）
# ===========================================================================

class WheelSlider(QSlider):
    """悬停即可滚轮调节（无需先点击获得焦点）。"""

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = max(1, self.singleStep())
        self.setValue(self.value() + (delta // 120) * step)
        event.accept()


class ZoomCanvas(QWidget):
    """逻辑坐标系画布：paintEvent 内 painter.scale(zoom) 后按逻辑尺寸绘制。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._fit = True
        self._hint = ""

    # --- 子类实现 ---
    def logical_size(self) -> tuple[float, float]:
        raise NotImplementedError

    def paint_content(self, p: QPainter) -> None:
        raise NotImplementedError

    # --- 缩放 ---
    def _fit_to_view(self):
        w, h = self.logical_size()
        if w <= 0 or h <= 0:
            return
        self._zoom = min(self.width() / w, self.height() / h)
        self._fit = True
        self.update()

    def set_hint(self, text: str):
        self._hint = text
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit:
            self._fit_to_view()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        self._fit = False
        factor = 1.2 if delta > 0 else 1 / 1.2
        self._zoom = min(max(self._zoom * factor, 0.05), 8.0)
        self.update()

    def mouseDoubleClickEvent(self, event):
        self._fit_to_view()

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), C_BG)
        p.save()
        p.scale(self._zoom, self._zoom)
        try:
            self.paint_content(p)
        finally:
            p.restore()
        if self._hint:
            p.setPen(C_TEXT_DIM)
            f = QFont(self.font())
            f.setPointSize(11)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, self._hint)
        p.end()


# ===========================================================================
# 点阵预览
# ===========================================================================

class DotMatrixView(ZoomCanvas):
    CELL = 26  # 逻辑像素/格

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pattern: POVPattern | None = None
        self._direction = "h_top_down"
        self._mirror = False

    def set_pattern(self, pattern: POVPattern | None, direction: str,
                    mirror: bool, reset_fit: bool = True):
        self._pattern = pattern
        self._direction = direction
        self._mirror = mirror
        if reset_fit:
            self._fit_to_view()
        self.update()

    def logical_size(self) -> tuple[float, float]:
        if not self._pattern:
            return 400, 300
        if self._direction == "h_top_down":
            return self._pattern.cols * self.CELL, self._pattern.rows * self.CELL
        # 竖扫转置显示（与挥舞动画空间一致）：宽 = 播放序，高 = LED 数
        return self._pattern.rows * self.CELL, self._pattern.cols * self.CELL

    def paint_content(self, p: QPainter):
        pat = self._pattern
        if not pat:
            return
        cell = self.CELL
        h_sweep = self._direction == "h_top_down"

        if h_sweep:
            # 显示坐标: x=LED(LED 0 在右端握柄, 与固件一致), y=播放序(0 在顶)
            n_cols, n_rows = pat.cols, pat.rows
            color_at = ((lambda px, py: pat.data[py][n_cols - 1 - px])
                        if not self._mirror else
                        (lambda px, py: pat.data[py][px]))
        else:
            # 竖扫转置显示: x=播放序(0 在左), y=LED(LED 0 在底=握柄端)
            n_cols, n_rows = pat.rows, pat.cols
            color_at = lambda px, py: pat.data[px][n_rows - 1 - py]

        # 首行（先播放）指示
        f8 = QFont(self.font()); f8.setPointSize(8)
        p.setFont(f8)
        if h_sweep:
            p.fillRect(QRectF(-4, -1, n_cols * cell + 8, 2), C_ACCENT)
            p.setPen(C_ACCENT)
            p.drawText(QRectF(n_cols * cell + 6, 0, 90, cell), Qt.AlignVCenter, "先播放 ▶")
        else:
            p.fillRect(QRectF(-1, -4, 2, n_rows * cell + 8), C_ACCENT)
            p.setPen(C_ACCENT)
            p.drawText(QRectF(2, -16, 90, 14), Qt.AlignLeft, "先播放 ▶")

        # 点
        dense = n_cols * n_rows > 5000
        for y in range(n_rows):
            for x in range(n_cols):
                r, g, b = color_at(x, y)
                cx = (x + 0.5) * cell
                cy = (y + 0.5) * cell
                if r or g or b:
                    p.setBrush(QColor(r, g, b))
                    p.setPen(Qt.NoPen)
                    if dense:
                        p.drawRect(int(cx - cell * 0.45), int(cy - cell * 0.45),
                                   int(cell * 0.9), int(cell * 0.9))
                    else:
                        p.drawEllipse(QPointF(cx, cy), cell * 0.40, cell * 0.40)
                else:
                    p.setPen(QPen(QColor(255, 255, 255, 26), 1))
                    p.setBrush(Qt.NoBrush)
                    p.drawEllipse(QPointF(cx, cy), cell * 0.40, cell * 0.40)

        # 方向状态提示
        p.setPen(C_TEXT_DIM)
        f7 = QFont(self.font()); f7.setPointSize(7)
        p.setFont(f7)
        if h_sweep:
            label = "LED 0 在左端（杖尖，已镜像）" if self._mirror else "LED 0 在右端（握柄）"
        else:
            label = "从右往左挥（已镜像）" if self._mirror else "从左往右挥 · LED 0 在底端（握柄）"
        p.drawText(QRectF(0, n_rows * cell + 4, n_cols * cell, 14), Qt.AlignCenter, label)


# ===========================================================================
# 挥舞动画预览（魔杖线稿渲染）
# ===========================================================================

class WandAnimationView(ZoomCanvas):
    """用魔杖线稿 + 灯带 LED 渲染挥舞路径，拖尾为已扫过的行。"""

    _TICK_MS = 16
    _ROWS_PER_SEC = 100  # 固件节奏：100 行/秒

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pattern: POVPattern | None = None
        self._direction = "h_top_down"
        self._mirror = False
        self._playing = False
        self._loop = True
        self._speed = 1.0  # 100% = 固件节奏（10ms/帧，100 行/秒）
        self._progress = 0.0
        self._hold_timer = 0.0
        self._fade = 1.0
        self._phase = "idle"  # idle | playing | holding | fading

        self._art: QPixmap | None = None
        self._art_key: tuple | None = None  # (是否水平, 是否镜像)
        self._load_art_if_needed()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._TICK_MS)

    # ---------------- 状态 ----------------

    def set_pattern(self, pattern: POVPattern | None, direction: str, mirror: bool):
        self._pattern = pattern
        self._direction = direction
        self._mirror = mirror
        self._load_art_if_needed()
        self.reset()
        if pattern:
            self._fit_to_view()

    def reset(self):
        self._progress = 0.0
        self._hold_timer = 0.0
        self._fade = 1.0
        self._phase = "playing" if self._playing else "idle"
        self.update()

    def play(self):
        self._playing = True
        if self._phase == "idle":
            self._phase = "playing"
        self.update()

    def pause(self):
        self._playing = False
        self.update()

    def toggle(self):
        if self._playing:
            self.pause()
        else:
            self.play()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def set_speed(self, v: float):
        self._speed = v

    def set_loop(self, on: bool):
        self._loop = on

    # ---------------- 素材加载（PIL 裁剪 + 旋转，灯带坐标同步变换） ----------------

    def _load_art_if_needed(self):
        key = (self._direction == "h_top_down", self._mirror)
        if self._art is not None and key == self._art_key:
            return
        self._art_key = key
        if not WAND_ART_PATH.exists():
            self._art = None
            return
        pil = Image.open(WAND_ART_PATH).convert("RGBA")
        alpha = np.asarray(pil)[..., 3] > 10
        ys, xs = np.where(alpha)
        if len(xs) == 0:
            self._art = None
            return
        m = 14
        x0, y0 = max(xs.min() - m, 0), max(ys.min() - m, 0)
        x1 = min(xs.max() + m, pil.width - 1)
        y1 = min(ys.max() + m, pil.height - 1)
        crop = pil.crop((x0, y0, x1 + 1, y1 + 1))
        self._strip_axis0 = STRIP_X0 - x0  # 灯带 0 号 LED 在裁剪图中的灯带轴坐标

        # 线稿为黑色描边，重染为浅色以便在深色画布上可见
        arr = np.asarray(crop.convert("RGBA")).copy()
        arr[arr[..., 3] > 10, :3] = (222, 225, 231)
        crop = Image.fromarray(arr, "RGBA")

        h_sweep, mirror = key
        if h_sweep:
            if mirror:
                # 杖水平 + 左右镜像：杖身水平翻转（LED 0 端换到右侧）
                crop = crop.transpose(Image.FLIP_LEFT_RIGHT)
        else:
            # 杖竖直：固定逆时针 90°（杖尖朝上、手柄朝下）。
            # 镜像不翻转魔杖，而是改变挥动方向（见 _layout 的 step_pos）
            crop = crop.rotate(-90, expand=True)
        self._art = QPixmap.fromImage(_pil_to_qimage(crop))

    # ---------------- 布局计算 ----------------

    def _layout(self) -> dict | None:
        pat = self._pattern
        if pat is None or self._art is None:
            return None
        pitch = STRIP_LEN / pat.cols
        h_sweep = self._direction == "h_top_down"
        aw, ah = self._art.width(), self._art.height()
        strip_axis0 = self._strip_axis0
        margin = max(pitch * 1.5, 20.0)
        trail_len = pat.rows * pitch
        mirror = self._mirror

        if h_sweep:
            # 杖水平（灯带沿 x），从上往下挥（镜像不改挥动方向）。
            # LED 0 在握柄端（右端），与固件灯带方向一致；镜像时杖身水平翻转
            fwd = True
            canvas = (aw, trail_len + ah + 2 * margin)
            sweep0 = margin + ah / 2 - pitch / 2  # 轨迹起点（y）
            led_pos = lambda j: ((strip_axis0 + (pat.cols - 1 - j + 0.5) * pitch)
                                 if not mirror
                                 else aw - (strip_axis0 + (pat.cols - 1 - j + 0.5) * pitch))

            cell_rect = lambda k, j: QRectF(led_pos(j) - pitch / 2, step_pos(k) - pitch / 2,
                                            pitch, pitch)
            band_rect = lambda k: QRectF(strip_axis0, step_pos(k) - pitch / 2, STRIP_LEN, pitch)
            trail_rect = QRectF(strip_axis0, sweep0, STRIP_LEN, trail_len)
            wand_center = lambda k: (aw / 2, step_pos(k))
            led_dx = lambda j: led_pos(j) - aw / 2
            led_dy = 0.0
        else:
            # 杖竖直（灯带沿 y）：线稿固定杖尖朝上（rotate(-90)）。
            # LED 0 在握柄端 = 底端（杖尖朝上时），与固件灯带方向一致。
            # 镜像不翻转魔杖，而是改为从右往左挥（播放行反序）
            fwd = not mirror
            canvas = (trail_len + aw + 2 * margin, ah)
            sweep0 = margin + aw / 2 - pitch / 2  # 轨迹起点（x）
            led_pos = lambda j: strip_axis0 + (pat.cols - 1 - j + 0.5) * pitch

            cell_rect = lambda k, j: QRectF(step_pos(k) - pitch / 2, led_pos(j) - pitch / 2,
                                            pitch, pitch)
            band_rect = lambda k: QRectF(step_pos(k) - pitch / 2, strip_axis0, pitch, STRIP_LEN)
            trail_rect = QRectF(sweep0, strip_axis0, trail_len, STRIP_LEN)
            wand_center = lambda k: (step_pos(k), ah / 2)
            led_dx = 0.0
            led_dy = lambda j: led_pos(j) - ah / 2

        # 杖从起始位置（上/左）挥动，每次推进一行；竖扫镜像时从右往左
        def step_pos(k: float) -> float:
            base = sweep0 + (k + 0.5) * pitch
            return base if fwd else sweep0 + trail_len - (k + 0.5) * pitch

        return {
            "pitch": pitch, "h_sweep": h_sweep, "trail_len": trail_len,
            "canvas": canvas, "margin": margin, "sweep0": sweep0,
            "strip_axis0": strip_axis0, "trail_rect": trail_rect,
            "step_pos": step_pos, "led_pos": led_pos,
            "cell_rect": cell_rect, "band_rect": band_rect,
            "wand_center": wand_center, "led_dx": led_dx, "led_dy": led_dy,
        }

    # ---------------- 动画 ----------------

    def _tick(self):
        pat = self._pattern
        if pat is None or not self._playing or self._phase not in ("playing", "holding", "fading"):
            return
        dt = self._TICK_MS / 1000.0
        if self._phase == "playing":
            self._progress += dt * self._ROWS_PER_SEC * self._speed
            if self._progress >= pat.rows:
                self._progress = float(pat.rows)
                self._phase = "holding"
                self._hold_timer = 0.6
        elif self._phase == "holding":
            self._hold_timer -= dt
            if self._hold_timer <= 0:
                self._phase = "fading"
        else:  # fading
            self._fade -= dt * 2.0
            if self._fade <= 0.0:
                self._fade = 1.0
                if self._loop:
                    self.reset()
                else:
                    self._phase = "idle"
                    self._playing = False
        self.update()

    # ---------------- 绘制 ----------------

    def logical_size(self) -> tuple[float, float]:
        lay = self._layout()
        return lay["canvas"] if lay else (640, 360)

    def paint_content(self, p: QPainter):
        pat = self._pattern
        lay = self._layout()
        if pat is None or lay is None:
            return
        pitch, h_sweep = lay["pitch"], lay["h_sweep"]
        rows = pat.rows
        step_pos, led_pos = lay["step_pos"], lay["led_pos"]
        k = int(self._progress)

        # 1) 轨迹（磷光式拖尾：先播放的行更暗）
        dense = rows * pat.cols > 4000
        if dense:
            p.setPen(Qt.NoPen)
            for kk in range(k):
                p.setBrush(QColor(255, 255, 255, int(22 * self._fade)))
                p.drawRect(lay["band_rect"](kk))
        else:
            for kk in range(k):
                age = k - kk
                alpha = 255.0 * (0.25 + 0.75 * (rows - age) / max(rows, 1)) * self._fade
                for j in range(pat.cols):
                    r, g, b = pat.data[kk][j]
                    if not (r or g or b):
                        continue
                    p.setBrush(QColor(r, g, b, int(alpha * 0.85)))
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(lay["cell_rect"](kk, j), pitch * 0.18, pitch * 0.18)

        # 2) 挥舞区域边界
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(lay["trail_rect"])

        # 3) 魔杖本体 + 灯带
        done = self._progress >= rows
        if self._art is not None and not (done and self._phase == "idle"):
            art = self._art
            # 杖身位置 = 当前播放行（step_pos 已返回坐标，不可再套一层）
            step = (self._progress if (self._phase in ("playing", "idle") and not done)
                    else float(rows - 1))
            cx, cy = lay["wand_center"](step)
            row = pat.data[min(k, rows - 1)]

            p.save()
            p.translate(cx, cy)
            p.setOpacity(0.92)
            p.drawPixmap(-art.width() / 2, -art.height() / 2, art)
            p.setOpacity(1.0)
            for j in range(pat.cols):
                dx = lay["led_dx"](j) if callable(lay["led_dx"]) else lay["led_dx"]
                dy = lay["led_dy"](j) if callable(lay["led_dy"]) else lay["led_dy"]
                r, g, b = row[j]
                radius = pitch * 0.34
                if r or g or b:
                    # 光晕 + 灯珠
                    p.setBrush(QColor(r, g, b, 90))
                    p.setPen(Qt.NoPen)
                    p.drawEllipse(QPointF(dx, dy), radius + 3.5, radius + 3.5)
                    p.setBrush(QColor(r, g, b))
                    p.setPen(QPen(QColor(255, 255, 255, 70), 1))
                    p.drawEllipse(QPointF(dx, dy), radius + 1.0, radius + 1.0)
                    p.setPen(Qt.NoPen)
                    p.drawEllipse(QPointF(dx, dy), radius * 0.72, radius * 0.72)
                else:
                    p.setBrush(C_LED_OFF)
                    p.setPen(Qt.NoPen)
                    p.drawEllipse(QPointF(dx, dy), radius * 0.55, radius * 0.55)
            p.restore()

        # 4) 首行（先播放）指示
        if self._phase in ("idle", "playing") and not done:
            pos0 = step_pos(0.0)
            p.setPen(C_ACCENT)
            f8 = QFont(self.font()); f8.setPointSize(8)
            p.setFont(f8)
            if h_sweep:
                mx, my = lay["strip_axis0"] - 8, pos0
                p.drawText(QPointF(mx - 62, my + 4), "先播放 ▶")
                tri = [QPointF(mx - 8, my - 4), QPointF(mx - 8, my + 9), QPointF(mx, my + 2.5)]
            else:
                mx, my = pos0, lay["strip_axis0"] - 8
                p.drawText(QPointF(mx - 24, my - 5), "先播放 ▶")
                tri = [QPointF(mx - 4, my - 8), QPointF(mx + 9, my - 8), QPointF(mx + 2.5, my)]
            p.setBrush(C_ACCENT)
            p.setPen(Qt.NoPen)
            p.drawPolygon(tri)


# ===========================================================================
# 主窗口
# ===========================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MugglesWand POV 图案生成器")
        self.resize(1400, 820)
        self.setAcceptDrops(True)
        self._image_path: Path | None = None
        self._pattern: POVPattern | None = None
        self._prev_cols = 41  # 列数联动行数时的旧值基准

        # 固件头文件路径：默认空（用户自选），用 QSettings 记忆上次选择
        self._settings = QSettings("MugglesWand", "POVConverter")
        saved = self._settings.value("header_path", "")
        self._header_path = Path(saved) if saved and Path(saved).exists() else None

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._regen)

        self._build_ui()
        self.setStyleSheet(QSS)
        self._update_state()

    # ---------------- UI 构建 ----------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 10, 14, 6)
        root.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("MugglesWand · POV 光绘图案生成器")
        title.setObjectName("title")
        sub = QLabel("图片 → 彩色点阵 → 固件 CRGB 图案数组（41 LED 灯带）")
        sub.setObjectName("dim")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(sub)
        root.addLayout(title_row)

        # 先创建预览视图（面板构建时可能引用它们）
        self._anim_view = WandAnimationView()
        self._dot_view = DotMatrixView()

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)
        splitter.addWidget(self._build_panel())
        tabs = QTabWidget()
        tabs.addTab(self._anim_view, "挥舞动画")
        tabs.addTab(self._dot_view, "点阵预览")
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 1046])

        self.statusBar().showMessage("就绪：选择一张图片开始")

    def _slider_row(self, label: str, lo: int, hi: int, val: int,
                    step: int = 1, suffix: str = "") -> tuple[QSlider, QSpinBox, QHBoxLayout]:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        slider = WheelSlider(Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(val)
        slider.setSingleStep(step)
        spin = QSpinBox()
        spin.setRange(lo, hi)
        spin.setValue(val)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        spin.valueChanged.connect(self._on_param_change)
        row.addWidget(slider, 1)
        row.addWidget(spin)
        return slider, spin, row

    def _panel_section(self, title: str) -> tuple[QGroupBox, QVBoxLayout]:
        """板块卡片：QGroupBox + 内部布局。"""
        gb = QGroupBox(title)
        gl = QVBoxLayout(gb)
        gl.setContentsMargins(10, 16, 10, 10)
        gl.setSpacing(8)
        return gb, gl

    def _build_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(340)
        v = QVBoxLayout(panel)
        v.setContentsMargins(4, 4, 8, 8)
        v.setSpacing(12)

        # ---- ① 图片 ----
        gb, v1 = self._panel_section("① 图片")
        self.btn_pick = QPushButton("＋ 选择图片")
        self.btn_pick.setObjectName("primary")
        self.btn_pick.setMinimumHeight(36)
        self.btn_pick.clicked.connect(self._pick_image)
        v1.addWidget(self.btn_pick)
        self.lbl_image = QLabel("未选择（可拖拽图片到窗口）")
        self.lbl_image.setObjectName("dim")
        self.lbl_image.setWordWrap(True)
        v1.addWidget(self.lbl_image)
        v.addWidget(gb)

        # ---- ② 图案参数 ----
        gb, v2 = self._panel_section("② 图案参数")
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("图案名"))
        self.ed_name = QLineEdit("custom")
        self.ed_name.setPlaceholderText("仅限英文/数字/下划线，如 my_heart")
        self.ed_name.textChanged.connect(self._on_name_changed)
        name_row.addWidget(self.ed_name, 1)
        v2.addLayout(name_row)
        self.lbl_name_warn = QLabel("")
        self.lbl_name_warn.setObjectName("warn")
        self.lbl_name_warn.setWordWrap(True)
        self.lbl_name_warn.setVisible(False)  # 默认隐藏，避免空行占位
        v2.addWidget(self.lbl_name_warn)

        self.sl_cols, self.sp_cols, r = self._slider_row("列数(LED)", 4, 128, 41, suffix=" 颗")
        v2.addLayout(r)
        self.sp_cols.valueChanged.connect(self._on_cols_change)
        self.sl_rows, self.sp_rows, r = self._slider_row("行数(帧)", 2, 128, 20, suffix=" 帧")
        v2.addLayout(r)

        v2.addWidget(QLabel("扫描方向"))
        self.cb_dir = QComboBox()
        for key, desc in DIRECTION_OPTIONS:
            self.cb_dir.addItem(desc, key)
        self.cb_dir.currentIndexChanged.connect(self._on_dir_change)
        v2.addWidget(self.cb_dir)
        self.chk_mirror = QCheckBox("画面左右镜像")
        self.chk_mirror.toggled.connect(self._on_param_change)
        v2.addWidget(self.chk_mirror)
        v.addWidget(gb)

        # ---- ③ 图像处理 ----
        gb, v3 = self._panel_section("③ 图像处理")
        self.chk_bg = QCheckBox("去除背景（取四角平均色）")
        self.chk_bg.toggled.connect(self._on_param_change)
        v3.addWidget(self.chk_bg)
        self.sl_bg, self.sp_bg, r = self._slider_row("背景容差", 0, 120, 40)
        v3.addLayout(r)
        self.sl_bg.valueChanged.connect(self._on_param_change)
        v.addWidget(gb)

        # ---- ④ 导出 ----
        gb, v4 = self._panel_section("④ 导出固件代码")
        self.btn_copy = QPushButton("复制 CRGB 代码")
        self.btn_copy.clicked.connect(self._copy_code)
        v4.addWidget(self.btn_copy)
        self.btn_save = QPushButton("保存为完整头文件 (.h)")
        self.btn_save.clicked.connect(self._save_header)
        v4.addWidget(self.btn_save)
        header_group = QGroupBox("插入固件头文件")
        hg = QVBoxLayout(header_group)
        self.lbl_header = QLabel()
        self.lbl_header.setObjectName("dim")
        self.lbl_header.setWordWrap(True)
        hg.addWidget(self.lbl_header)
        hb = QHBoxLayout()
        self.btn_browse = QPushButton("更改…")
        self.btn_browse.clicked.connect(self._browse_header)
        self.btn_insert = QPushButton("插入 / 替换")
        self.btn_insert.setObjectName("primary")
        self.btn_insert.clicked.connect(self._insert_header)
        hb.addWidget(self.btn_browse)
        hb.addWidget(self.btn_insert)
        hg.addLayout(hb)
        v4.addWidget(header_group)

        self.lbl_stats = QLabel()
        self.lbl_stats.setObjectName("dim")
        self.lbl_stats.setWordWrap(True)
        v4.addWidget(self.lbl_stats)
        v.addWidget(gb)
        v.addStretch()
        return panel

    # ---------------- 事件 ----------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.exists() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"):
                self._load_image(p)
                return

    # ---------------- 动作 ----------------

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;所有文件 (*)")
        if path:
            self._load_image(Path(path))

    def _load_image(self, path: Path):
        self._image_path = path
        self.lbl_image.setText(f"已加载：{path.name}")
        self.lbl_image.setObjectName("ok")
        self.lbl_image.style().unpolish(self.lbl_image)
        self.lbl_image.style().polish(self.lbl_image)
        if self.ed_name.text().strip() in ("", "custom"):
            self.ed_name.setText(sanitize_name(path.stem))
        # 按图片宽高比自动调整行数，保持图片原比例（用户可再手动微调）
        self.sp_rows.setValue(auto_rows(path, self.sp_cols.value(), self.cb_dir.currentData()))
        self._regen()
        # 默认开始播放预览（100% 速度 = 固件 10ms/帧节奏）
        self._anim_view.play()

    def _on_param_change(self, *_):
        self._debounce.start(80)

    def _on_name_changed(self, text: str):
        """图案名实时校验：含中文/非法字符时警告（固件会编译失败）。"""
        name = text.strip()
        if not name:
            self.lbl_name_warn.setText("图案名为空，将使用 custom")
            self.lbl_name_warn.setVisible(True)
        elif any(ord(ch) >= 128 for ch in name):
            self.lbl_name_warn.setText("⚠ 图案名含中文/非 ASCII 字符，固件编译会报错")
            self.lbl_name_warn.setVisible(True)
        elif not all(ch.isalnum() or ch == "_" for ch in name) or name[0].isdigit():
            self.lbl_name_warn.setText("⚠ 仅限字母/数字/下划线，且不能以数字开头")
            self.lbl_name_warn.setVisible(True)
        else:
            self.lbl_name_warn.setVisible(False)
        self._on_param_change()

    def _on_dir_change(self, index: int):
        """切换扫描方向：按图片比例动态调整行数。"""
        if self._image_path:
            self.sp_rows.setValue(
                auto_rows(self._image_path, self.sp_cols.value(), self.cb_dir.currentData()))
        self._on_param_change()

    def _on_cols_change(self, value: int):
        """改变列数：行数按比例联动（保持行/列比例），调整行数不联动列数。"""
        old = self._prev_cols
        self._prev_cols = value
        if self._image_path and old > 0 and value != old:
            rows = self.sp_rows.value()
            new_rows = max(2, min(128, round(rows * value / old)))
            self.sp_rows.setValue(new_rows)

    def _read_config(self) -> POVConfig:
        return POVConfig(
            name=sanitize_name(self.ed_name.text()),
            cols=self.sp_cols.value(),
            rows=self.sp_rows.value(),
            direction=self.cb_dir.currentData(),
            mirror=self.chk_mirror.isChecked(),
            remove_bg=self.chk_bg.isChecked(),
            bg_tolerance=self.sp_bg.value(),
        )

    def _regen(self):
        if not self._image_path:
            return
        cfg = self._read_config()
        try:
            self._pattern = convert(self._image_path, cfg)
        except Exception as e:  # noqa: BLE001
            self.statusBar().showMessage(f"转换失败：{e}")
            return
        self._dot_view.set_pattern(self._pattern, cfg.direction, cfg.mirror)
        self._anim_view.set_pattern(self._pattern, cfg.direction, cfg.mirror)
        self._update_state()

    def _update_state(self):
        cfg = self._read_config()
        h_sweep = cfg.direction == "h_top_down"
        self.btn_copy.setEnabled(self._pattern is not None)
        self.btn_save.setEnabled(self._pattern is not None)
        self.btn_insert.setEnabled(self._pattern is not None)

        if self._pattern:
            p = self._pattern
            warn = ""
            if p.cols != 41:
                warn = ("　⚠ 列数 ≠ 41：固件灯带按 41 颗 LED 播放，"
                        "多余 LED 会被截断、不足部分留空。")
            self.lbl_stats.setText(
                f"{p.rows} 行 × {p.cols} 列 ｜ 播放 {p.duration_ms}ms ｜ "
                f"flash ≈ {p.flash_bytes / 1024:.1f} KB{warn}")
        else:
            self.lbl_stats.setText("")
        if self._header_path:
            self.lbl_header.setText(f"目标文件：\n{self._header_path}")
        else:
            self.lbl_header.setText("未选择目标文件（可点「更改…」或直接「插入 / 替换」选择）")

    # ---------------- 导出 ----------------

    def _copy_code(self):
        if not self._pattern:
            return
        QApplication.clipboard().setText(generate_snippet(self._pattern))
        self.statusBar().showMessage("已复制 CRGB 代码到剪贴板", 4000)

    def _save_header(self):
        if not self._pattern:
            return
        default = f"kPov{sanitize_name(self._pattern.name).capitalize()}.h"
        path, _ = QFileDialog.getSaveFileName(self, "保存头文件", default, "C 头文件 (*.h)")
        if not path:
            return
        Path(path).write_text(generate_standalone_header(self._pattern), encoding="utf-8")
        self.statusBar().showMessage(f"已保存：{path}", 4000)

    def _browse_header(self):
        if self._header_path and self._header_path.exists():
            start = str(self._header_path)
        elif DEFAULT_FIRMWARE_HEADER.exists():  # 源码运行：固件默认位置
            start = str(DEFAULT_FIRMWARE_HEADER)
        else:  # exe 环境没有固件目录时，从用户目录开始
            start = str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "选择固件头文件", start, "C 头文件 (*.h)")
        if path:
            self._header_path = Path(path)
            self._settings.setValue("header_path", str(path))  # 记忆，下次启动恢复
            self._update_state()

    def _insert_header(self):
        if not self._pattern:
            return
        if self._header_path is None or not self._header_path.exists():
            # 未选择或文件已不存在：引导用户选择（复用浏览对话框）
            self._browse_header()
            if self._header_path is None or not self._header_path.exists():
                QMessageBox.warning(
                    self, "未选择目标文件",
                    "请选择固件头文件 APP_POVPatterns.h。\n"
                    "（路径会被记忆，下次打开自动恢复）")
                return
        name = self.ed_name.text().strip()
        if not c_identifier_ok(name):
            QMessageBox.warning(
                self, "图案名非法",
                "图案名必须是合法的 C 标识符（仅英文/数字/下划线，不以数字开头）。"
                "中文或其它非 ASCII 字符会导致固件编译错误。")
            return
        ret = QMessageBox.question(
            self, "插入固件头文件",
            f"将把图案「{name}」写入：\n{self._header_path}\n\n"
            f"（写入前自动备份为同目录 .bak 文件；同名图案会整体替换。）\n继续？",
            QMessageBox.Yes | QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        try:
            replaced = insert_into_header(self._header_path, self._pattern)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "写入失败", str(e))
            return
        msg = "已替换同名图案" if replaced else "已插入新图案"
        self.statusBar().showMessage(f"{msg} → {self._header_path}", 6000)
        QMessageBox.information(
            self, "完成",
            f"{msg}：\n{self._header_path}\n\n重新编译固件后即可使用。")



def _pil_to_qimage(pil: Image.Image) -> QImage:
    """PIL RGBA -> QImage（拷贝数据，生命周期安全）。"""
    arr = np.asarray(pil.convert("RGBA"))
    h, w, _ = arr.shape
    qimg = QImage(arr.data, w, h, arr.strides[0], QImage.Format_RGBA8888).copy()
    return qimg
