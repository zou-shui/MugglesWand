# train.py 简介

`train.py` 用于训练手势识别模型，主要特点：

- **自动识别数据集**：自动读取同目录下所有 `N.csv` 文件（`N` 为从 0 开始连续的整数），文件名即手势类别编号，支持自定义任意数量的手势类别。
- **数据格式**：每行一个样本，格式为 `label, x0, y0, x1, y1, …, x99, y99`，即 100 个时刻的 2 轴数据；脚本会校验行内标签与文件名一致，不符则终止。
- **网络结构**：轻量 1D-CNN（2 层卷积 + 批归一化 + 池化 + 全连接），配合 EarlyStopping 防止过拟合，PC 上即可快速训练。
- **自动量化**：训练完成后自动转为 INT8 全整数量化模型 `gesture_model.tflite`，并在终端输出归一化参数 `mean` / `std`，供固件端推理使用。

## 运行脚本

TensorFlow需要python3.9，需先安装该版本的Python。

用python3.9创建虚拟环境：

```bash
py -3.9 -m venv tf_env
```

激活虚拟环境：

```bash
tf_env\Scripts\activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

运行脚本（运行之前请先将训练数据放在train.py同级目录）：

```bash
python train.py
```

模型训练好后会输出归一化参数`mean`和`std`到终端、生成模型文件`gesture_model.tflite`到根目录。后者需要在git bash中使用以下命令将其转换为字节数组：

```bash
xxd -i gesture_model.tflite > gesture_model.h
```

之后即可替换原固件中的模型，需要替换的地方有：

`src/Model/gesture_inference.cpp`中的**归一化参数**和**输出类别数量**

`src/Model/gesture_model.h`整个文件替换为新的`gesture_model.h`


