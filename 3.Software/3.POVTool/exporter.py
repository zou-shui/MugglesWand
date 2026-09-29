# -*- coding: utf-8 -*-
"""
POV 图案 C 代码生成与固件头文件插入。

生成的代码与 src/APP/APP_POVPatterns.h 现有排版风格一致：
  - 每行 10 个 CRGB 字面量、行块独立成段（仿 kPovHeart 的写法）
  - 注册行与 kPovPatterns[] 注册表格式一致
"""

from __future__ import annotations

import re
from pathlib import Path

from core import POVPattern, sanitize_name

# 固件头文件默认位置：本工具位于 MugglesWand/3.Software/POVTool，
# 向上两级到仓库根，再进 2.Firmware/MugglesWand-src 固件根
DEFAULT_FIRMWARE_HEADER = (
    Path(__file__).resolve().parents[2]
    / "2.Firmware" / "MugglesWand-src" / "src" / "APP" / "APP_POVPatterns.h"
)


def array_ident(name: str) -> str:
    """图案数组标识符：kPov + 首字母大写的名字（同固件 kPovHeart 约定）。"""
    ident = sanitize_name(name)
    return "kPov" + ident[:1].upper() + ident[1:]


def _pattern_rows(p: POVPattern) -> list[str]:
    """生成图案数组的每个行块（每行一个 CRGB，与固件头文件当前排版一致）。"""
    lines: list[str] = []
    for i in range(p.rows):
        lines.append("    {")
        for (r, g, b) in p.data[i]:
            lines.append(f"        CRGB({r}, {g}, {b}),")
        lines.append("    },")
    return lines


def generate_pattern_block(p: POVPattern, ident: str, with_doc: bool = True) -> str:
    """生成 `static const CRGB <ident>[rows][cols] = {...};` 完整块。"""
    body = "\n".join(_pattern_rows(p))
    doc = (
        f"// POV 图案（上位机工具生成）: {p.rows} 行 x {p.cols} 列, "
        f"播放 {p.duration_ms}ms, 占用约 {p.flash_bytes / 1024:.1f}KB flash\n"
        if with_doc
        else ""
    )
    return (
        f"{doc}static const CRGB {ident}[{p.rows}][{p.cols}] = {{\n"
        f"{body}\n"
        f"}};"
    )


def generate_registry_line(p: POVPattern, ident: str) -> str:
    return f'    {{ "{p.name}", &{ident}[0][0], {p.rows}, {p.cols} }},'


def generate_snippet(p: POVPattern) -> str:
    """生成可粘贴进 APP_POVPatterns.h 的代码段（图案块 + 注册行）。"""
    ident = array_ident(p.name)
    return f"{generate_pattern_block(p, ident)}\n\n{generate_registry_line(p, ident)}"


def generate_standalone_header(p: POVPattern) -> str:
    """生成可直接编译的完整头文件（含 POVPatternInfo 与注册表）。"""
    ident = array_ident(p.name)
    return (
        f"#pragma once\n"
        f'#include <FastLED.h>\n'
        f'#include "HAL/WS2812_Animation/AnimPOV.hpp"\n\n'
        f"{generate_pattern_block(p, ident)}\n\n"
        f"static const POVPatternInfo kPovPatterns[] = {{\n"
        f"{generate_registry_line(p, ident)}\n"
        f"}};\n"
        f"#define POV_PATTERN_COUNT (sizeof(kPovPatterns) / sizeof(kPovPatterns[0]))"
    )


# ---------------------------------------------------------------------------
# 插入固件头文件
# ---------------------------------------------------------------------------

_REG_DECL_RE = re.compile(
    r"static\s+const\s+POVPatternInfo\s+kPovPatterns\s*\[\]\s*=\s*\{"
)


def _find_registry(text: str) -> tuple[int, int]:
    """返回注册表声明行起始与数组体结束位置 (decl_start, body_end)。"""
    m = _REG_DECL_RE.search(text)
    if not m:
        raise ValueError("未找到 kPovPatterns[] 注册表声明")
    body_start = text.find("{", m.end())
    close = text.find("};", body_start)
    if close < 0:
        raise ValueError("注册表声明缺少 '};'")
    return m.start(), close  # close 指向 '}' 的位置


def _find_pattern_block(text: str, ident: str) -> tuple[int, int] | None:
    """若同名图案已存在，返回其 [start, end)（含结尾 '};'）。"""
    m = re.search(
        rf"static\s+const\s+CRGB\s+{re.escape(ident)}\s*\[[^\]]*\]\[[^\]]*\]\s*=",
        text,
    )
    if not m:
        return None
    end = text.find("};", m.end())
    if end < 0:
        return None
    return m.start(), end + 2


def _find_registry_line(text: str, body_start: int, body_end: int, name: str):
    """在注册表体内查找同名注册行，返回其 [start, end)。"""
    m = re.search(
        rf"\{{[ \t]*\"{re.escape(name)}\"[ \t]*,[^}}]*\}},", text[body_start:body_end]
    )
    if not m:
        return None
    return body_start + m.start(), body_start + m.end()


def insert_into_header(header_path: str | Path, p: POVPattern) -> bool:
    """
    把图案块与注册行写入固件头文件（自动备份 .bak 后写回）。
    同名图案已存在则原地替换；返回是否发生了替换。
    """
    header_path = Path(header_path)
    text = header_path.read_text(encoding="utf-8")

    ident = array_ident(p.name)
    block = generate_pattern_block(p, ident)
    reg = generate_registry_line(p, ident)

    reg_decl, reg_body_end = _find_registry(text)

    # 1) 图案块：存在则替换，否则插在注册表声明之前
    found = _find_pattern_block(text, ident)
    replaced = found is not None
    if found:
        start, end = found
        text = text[:start] + block + text[end:]
        delta = len(block) - (end - start)
        if reg_decl > start:
            reg_decl += delta
        reg_body_end += delta
    else:
        text = text[:reg_decl] + block + "\n\n" + text[reg_decl:]
        reg_decl += len(block) + 2
        reg_body_end += len(block) + 2

    # 2) 注册行：同名则替换，否则追加到 '};' 之前
    body_start = _REG_DECL_RE.search(text).end()
    line = _find_registry_line(text, body_start, reg_body_end, p.name)
    if line:
        ls, le = line
        text = text[:ls] + reg + text[le:]
    else:
        text = text[:reg_body_end] + "\n" + reg + text[reg_body_end:]

    _write_with_backup(header_path, text)
    return replaced


def _write_with_backup(header_path: Path, text: str) -> None:
    backup = header_path.with_suffix(header_path.suffix + ".bak")
    backup.write_text(header_path.read_text(encoding="utf-8"), encoding="utf-8")
    header_path.write_text(text, encoding="utf-8")
