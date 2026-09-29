# -*- coding: utf-8 -*-
"""
POV 图案转换核心（纯逻辑，无 GUI 依赖）。

把任意图片转换成固件使用的 POV 图案数组（POVPattern）：
  - pattern[i][j] = RGB 颜色, i = 播放顺序行号 (row 0 先播放), j = LED 编号

灯带几何约定（与固件一致）：
  - 灯带共 WS2812_LED_COUNT 个 LED，沿魔杖杖身排布
  - 魔杖线稿中灯带区域为横向像素 x=30~1310（1280 px 长）
  - 杖水平（h_top_down）：灯带沿 x，向下挥，扫出一个 cols×rows 的矩形
  - 杖竖直（v_left_right）：灯带沿 y，向右挥，扫出一个 rows×cols 的矩形
    （即图案数组是图像的转置，图案的"列"= 图像的"行"）

上位机只生成正向挥动的数组（row 0 = 先播放 = 起始位置）；反向挥舞由固件
reverse 参数实现（APP_POV_set_params(pattern, reverse)）。

方向映射（保证最终视觉为正立）：
  - h_top_down   杖水平，从上往下挥:  row i → 图像第 i 行
  - v_left_right 杖竖直，从左往右挥:  row i → 图像第 i 列（转置）

灯带物理方向（与固件一致）：LED 0 在握柄端。
  - 杖水平: LED 0 在右端（握柄），LED 40 在左端（杖尖）
  - 杖竖直: LED 0 在底端（握柄，杖尖朝上时），LED 40 在顶端（杖尖）

UI 渲染（挥舞动画/点阵预览）以杖尖为视觉基准（杖水平 LED 0 画在左端杖尖），
与固件 LED 0 的物理方向相反，因此生成数组前先翻转画面，使固件实际效果与 UI 一致：
  - 杖水平: 采样前水平翻转图像（convert 内）
  - 杖竖直: 采样后 LED 行反序（_orient 内）

mirror（画面左右镜像）：
  - 杖水平: LED 列反序（LED 0 从握柄端换到杖尖端），杖身水平翻转
  - 杖竖直: 播放行反序（从左往右挥改为从右往左挥），线稿与 LED 方向不变
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image

RGB = Tuple[int, int, int]

# 魔杖线稿中灯带区域（横向像素范围）
ART_WAND_STRIP_X0 = 30
ART_WAND_STRIP_LEN = 1280  # 1310 - 30

# 扫描方向选项（GUI 下拉框显示名 -> 映射键）
DIRECTION_OPTIONS = [
    ("h_top_down", "杖水平，从上往下挥"),
    ("v_left_right", "杖竖直，从左往右挥"),
]


@dataclass
class POVConfig:
    """转换参数（全部可选，GUI 直接绑定）。"""

    name: str = "custom"  # 图案名（C 标识符）
    cols: int = 41  # 列数 = LED 数量（固件 WS2812_LED_COUNT = 41）
    rows: int = 20  # 行数（播放帧数，播放时长 = rows * 10ms）
    direction: str = "h_top_down"  # 见 DIRECTION_OPTIONS
    mirror: bool = False  # 画面左右镜像（LED 方向反序）
    remove_bg: bool = False  # 去背景（取四角平均色，容差内视为透明）
    bg_tolerance: int = 40  # 去背景容差 0~255


@dataclass
class POVPattern:
    """生成结果：pattern[row][col] = RGB，row 0 = 先播放。"""

    name: str
    data: List[List[RGB]]  # [rows][cols]
    rows: int
    cols: int

    @property
    def duration_ms(self) -> int:
        """播放时长（固件每行 10ms）。"""
        return self.rows * 10

    @property
    def flash_bytes(self) -> int:
        """估算的固件 flash 占用（CRGB 3 字节/点）。"""
        return self.rows * self.cols * 3


# ---------------------------------------------------------------------------
# 图片预处理
# ---------------------------------------------------------------------------

def auto_rows(path: str | Path, cols: int, direction: str) -> int:
    """
    按图片宽高比自动计算行数，使点阵保持图片原比例（clamp 到 2~128）。
      - 杖水平: 点阵宽高比 = cols:rows = 图宽:图高  -> rows = cols * 高/宽
      - 杖竖直: 点阵宽高比 = rows:cols = 图宽:图高  -> rows = cols * 宽/高
    """
    with Image.open(path) as im:
        w, h = im.size
    ratio = (h / w) if direction == "h_top_down" else (w / h)
    # 四舍五入（round() 是银行家舍入，0.5 会舍去）
    return max(2, min(128, int(cols * ratio + 0.5)))


def _corner_bg_color(rgba: np.ndarray) -> np.ndarray:
    """取四角像素平均色作为背景色。"""
    h, w = rgba.shape[:2]
    corners = [rgba[2, 2, :3], rgba[2, -3, :3], rgba[-3, 2, :3], rgba[-3, -3, :3]]
    return np.mean(corners, axis=0).astype(np.float32)


def load_rgba(path: str | Path, cfg: POVConfig) -> np.ndarray:
    """加载图片为 RGBA 数组 (H, W, 4) 0~255，含去背景处理。"""
    img = Image.open(path).convert("RGBA")
    rgba = np.asarray(img).astype(np.float32)

    if cfg.remove_bg:
        bg = _corner_bg_color(rgba)
        dist = np.sqrt(((rgba[:, :, :3] - bg) ** 2).sum(axis=2))
        mask = dist < float(cfg.bg_tolerance)
        rgba[:, :, 3] = np.where(mask, 0.0, rgba[:, :, 3])

    return rgba


def _box_resize(channel: np.ndarray, w: int, h: int) -> np.ndarray:
    """BOX（均值）缩放单个 float32 通道。"""
    img = Image.fromarray(channel, mode="F").resize((w, h), Image.BOX)
    return np.asarray(img)


def to_dot_matrix(rgba: np.ndarray, w: int, h: int) -> np.ndarray:
    """
    alpha 感知的均值缩放：原图 (H, W, 4) -> 点阵 (h, w, 4)（alpha 0~255）。
    （RGB 先预乘 alpha 再平均，避免透明像素的底色污染边缘颜色。）

    杖水平传 w=cols, h=rows；杖竖直传 w=rows(播放步数), h=cols(LED 数)。
    """
    alpha = rgba[:, :, 3] / 255.0
    premul = rgba[:, :, :3] * alpha[..., None]

    a_out = _box_resize(alpha, w, h) * 255.0
    rgb_out = np.stack(
        [_box_resize(premul[..., c], w, h) for c in range(3)], axis=-1
    )

    a_safe = np.where(a_out > 0, a_out, 1.0)
    rgb_out = rgb_out / a_safe[..., None] * 255.0

    out = np.dstack([rgb_out, a_out])
    # 极低 alpha 视为全灭，杜绝残色
    out[np.any(out[:, :, 3:] < 1.0, axis=-1)] = 0.0
    return out


def apply_filters(dots: np.ndarray) -> np.ndarray:
    """颜色取整 + alpha 清理（亮度不压缩，保持 255 最大值）。"""
    rgb, alpha = dots[..., :3], dots[..., 3]

    rgb = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    alpha = np.where(alpha > 8.0, 255.0, 0.0).astype(np.uint8)  # 余量以下的视为灭
    return np.dstack([rgb, alpha])


# ---------------------------------------------------------------------------
# 方向映射 -> POVPattern
# ---------------------------------------------------------------------------

def _orient(dots: np.ndarray, cfg: POVConfig) -> List[List[RGB]]:
    """
    按方向把图像点阵映射为播放序数组，返回 pattern[play_row][led] = (r, g, b)。

    杖水平: dots 形状 (rows, cols)（图像 y × x），led = 图像列, play = 图像行
    杖竖直: dots 形状 (cols, rows)（LED 数 × 播放步数，图像已转置采样），
            led = 图像行, play = 图像列
    mirror: 杖水平 = LED 列反序；杖竖直 = 播放行反序（从左往右挥改为从右往左挥）
    """
    rows, cols = cfg.rows, cfg.cols
    rgb = dots[..., :3]
    on = dots[..., 3] > 0

    def px(r: int, c: int) -> RGB:
        return (int(rgb[r, c, 0]), int(rgb[r, c, 1]), int(rgb[r, c, 2])) if on[r, c] else (0, 0, 0)

    h_sweep = cfg.direction == "h_top_down"
    mirror = cfg.mirror

    def pick(i: int, j: int) -> RGB:
        """i = 播放行, j = LED 编号。"""
        if h_sweep:
            # 杖水平: 播放行 i = 图像行 i，LED j = 图像列 j（镜像则列反序）
            return px(i, cols - 1 - j if mirror else j)
        # 杖竖直: LED 0 在握柄端（底端，杖尖朝上时）=> 图像行反序；
        # 播放步 i 映射图像列（镜像则列反序 = 从右往左挥）
        img_row = cols - 1 - j
        img_col = rows - 1 - i if mirror else i
        return px(img_row, img_col)

    return [[pick(i, j) for j in range(cols)] for i in range(rows)]


def convert(path: str | Path, cfg: POVConfig) -> POVPattern:
    """完整转换管线：加载 -> 预处理 -> 缩放 -> 过滤 -> 方向映射。"""
    cfg = cfg or POVConfig()
    rgba = load_rgba(path, cfg)
    if cfg.direction == "h_top_down":
        # 杖水平: 固件 LED 0 在握柄端（右端），UI 渲染 LED 0 在杖尖（左端）。
        # 生成数组前水平翻转画面，使固件实际效果与 UI 渲染一致。
        rgba = np.ascontiguousarray(rgba[:, ::-1])
        dots = to_dot_matrix(rgba, cfg.cols, cfg.rows)
    else:
        # 杖竖直: 点阵 (cols, rows) = LED 数 × 播放步数（图像转置采样）
        dots = to_dot_matrix(rgba, cfg.rows, cfg.cols)
    dots = apply_filters(dots)
    data = _orient(dots, cfg)
    return POVPattern(name=cfg.name, data=data, rows=cfg.rows, cols=cfg.cols)


def sanitize_name(raw: str) -> str:
    """
    清洗为合法 C 标识符（仅 ASCII，kPov + 名字）。
    中文等非 ASCII 字符会破坏固件编译，一律替换为下划线；
    若结果不含字母（如纯中文文件名），回退为 "custom"。
    """
    name = "".join(
        ch if (ord(ch) < 128 and (ch.isalnum() or ch == "_")) else "_"
        for ch in raw.strip()
    )
    if not any(ch.isalpha() for ch in name):
        name = "custom"
    if name[0].isdigit():
        name = "_" + name
    return name


def c_identifier_ok(name: str) -> bool:
    """图案名是否为合法 C 标识符（仅 ASCII 字母/数字/下划线，不以数字开头）。"""
    return bool(name) and (name[0].isalpha() or name[0] == "_") and all(
        ord(ch) < 128 and (ch.isalnum() or ch == "_") for ch in name
    )
