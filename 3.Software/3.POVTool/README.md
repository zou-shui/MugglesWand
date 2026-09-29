# MugglesWand POV 光绘图案生成器（上位机）

把任意图片转换为固件 POV 光绘模块（`src/APP/APP_POVPatterns.h`）所需的
`CRGB[rows][cols]` 图案数组，并实时预览点阵效果与魔杖挥舞路径。

## 目录结构

```
POVTool/
├── main.py              # 入口: python main.py
├── gui.py               # PySide6 界面（点阵预览 + 挥舞动画）
├── core.py              # 转换核心: 加载/去背景/缩放/方向映射/自动比例
├── exporter.py          # CRGB 代码生成 + 固件头文件插入
├── requirements.txt
└── wand_lineart.png     # 挥舞动画素材（灯带区域: 横向像素 x=30~1310）
```

## 运行上位机

**1.（可选）创建虚拟环境**

虚拟环境可隔离本项目依赖，避免污染系统 Python；跳过此步则直接全局安装。

```bash
python -m venv .venv
```

激活虚拟环境（Windows）：

```bash
.venv\Scripts\activate
```

> 激活后命令行提示符前会出现 `(.venv)`；之后步骤的命令均在虚拟环境中执行。

**2. 安装依赖**

```bash
pip install -r requirements.txt
```

**3. 启动上位机**

```bash
python main.py
```

## 上位机使用说明

1. **导入图片**：点击「选择图片…」或直接拖入窗口（支持 PNG/JPG/BMP/WebP/GIF）。
   导入时按图片宽高比自动调整行数，并自动开始播放预览（100% 速度 = 固件 10ms/帧）。
2. **图案参数**：
   - **图案名**：仅限英文/数字/下划线（C 标识符），含中文会实时警告
   - **列数(LED)**：灯带 LED 数量，固件固定为 41；改变列数时行数按比例联动
   - **行数(帧)**：播放帧数，决定图案高度与播放时长（行数 × 10ms）
   - **扫描方向**：杖水平从上往下挥 / 杖竖直从左往右挥，切换时按图片比例动态调整行数
   - **左右镜像**：杖水平时 LED 列反序；杖竖直时改为从右往左挥
   - **去除背景**：取四角平均色，容差内视为透明（白底/纯色底图片常用）
3. **预览**：「挥舞动画」页用 `wand_lineart.png` 渲染真实的挥舞路径与拖尾；「点阵预览」页显示空间效果图案。
4. **导出**：
   - **复制 CRGB 代码**：图案块 + 注册行，格式与 `APP_POVPatterns.h` 一致
   - **保存完整头文件**：可直接编译
   - **插入固件头文件**：一键写入，自动备份 `.bak`，同名图案整体替换

## 打包成 exe（分发到无 Python 的电脑）

**1.（可选）创建虚拟环境**（同上；已创建过可跳过）

```bash
python -m venv .venv
.venv\Scripts\activate
```

**2. 安装 PyInstaller**

```bash
pip install pyinstaller
```

**3. 打包**

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name MugglesWandPOVTool --add-data  "wand_lineart.png;." main.py
```

产物：`dist/MugglesWandPOVTool.exe`（单文件，约 65MB），目标电脑无需安装
Python，双击即用。

要点：

- `--onefile` 单文件模式（首次启动解压稍慢）；若在意启动速度或杀毒误报，
  可换成 `--onedir` 目录模式
- `--windowed` 隐藏控制台窗口
- 挥舞动画素材 `wand_lineart.png` 已通过 `--add-data` 打进 exe，
  代码用 `resource_path()` 读取，源码/打包两种模式通用

## 固件对接要点

- 固件定义：`POVPatternInfo { name, data, rows, width }`，`width` = 41（`WS2812_LED_COUNT`）
- 行序约定：row 0 = 先播放（`AnimPOV` 每 10ms 推进一行，100 行/秒）
- 上位机只生成正向挥动的数组；反向挥舞（如习惯向上/向左挥杖）在固件端用
  `APP_POV_set_params(pattern, reverse)` 播放同一数组即可，无需重新生成
- 插入功能会正则定位 `kPovPatterns[]` 注册表并保持排版一致，文件有 `.bak` 备份可回滚


