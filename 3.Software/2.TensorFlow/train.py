import os
# 屏蔽 TensorFlow 的 INFO 和 WARNING 日志 (0 = 全部显示, 1 = 屏蔽 INFO, 2 = 屏蔽 INFO 和 WARNING, 3 = 屏蔽所有)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0' # 关闭 oneDNN 提示

from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, BatchNormalization
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.model_selection import train_test_split
import numpy as np
import tensorflow as tf
import csv
import glob  # 导入用于自动匹配文件名的库
import sys   # 用于安全退出程序

# ==================== 自动检测与规范检查逻辑 ====================

# 1. 自动检测同目录下的所有 CSV 文件
csv_files = glob.glob("*.csv")

if not csv_files:
    print("错误：未在当前目录下检测到任何 CSV 文件！")
    sys.exit(1)

# 2. 解析文件名中的数字标签
detected_labels = []
file_to_label = {}

for file in csv_files:
    base_name = os.path.splitext(file)[0]
    try:
        label_val = int(base_name)
        detected_labels.append(label_val)
        file_to_label[file] = label_val
    except ValueError:
        print(f"错误：文件名称 '{file}' 不符合规范（文件名必须是纯整数，如 '0.csv'）。")
        sys.exit(1)

# 排序以便进行连续性检查
detected_labels.sort()

# 3. 检查是否从 0 开始且为连续整数
if detected_labels[0] != 0:
    print(f"错误：检测到的文件标签不是从 0 开始。当前检测到的最小标签是: {detected_labels[0]}")
    sys.exit(1)

for i in range(len(detected_labels)):
    if detected_labels[i] != i:
        print(
            f"错误：文件标签整数不连续！期望的标签序列为 {list(range(len(detected_labels)))}, 但实际检测到的排序后序列为 {detected_labels}")
        sys.exit(1)

# 动态配置原有的全局变量
# 按照 0, 1, 2... 的顺序安全排序文件列表
LABEL_MAP = sorted(csv_files, key=lambda x: file_to_label[x])
CLASS = len(detected_labels)

print(f"识别到共 {CLASS} 个手势类别。")
print(f"将要处理的文件列表 (LABEL_MAP): {LABEL_MAP}")

# ==================== 数据处理与模型核心逻辑 ====================


def load_gesture_csv(filename):
    x_list = []
    y_list = []

    # 获取该文件对应的期望标签
    expected_label = file_to_label[filename]

    with open(filename, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            # 1. label
            label = int(row[0])

            # 4. 检查表格内部数据标签是否与文件名一致
            if label != expected_label:
                print(
                    f"错误：文件 '{filename}' 内部包含不一致的数据标签 '{label}'（期望标签应全为 '{expected_label}'）。程序已终止。")
                sys.exit(1)

            # 2. 后面 200 个数据
            data = np.array(row[1:], dtype=float)

            # 3. reshape 成 (100, 2)
            data = data.reshape(100, 2)
            x_list.append(data)
            y_list.append(label)

    return x_list, y_list


x_all = []
y_all = []


# 读取多个CSV到 x_all 和 y_all
for file in LABEL_MAP:
    X, y = load_gesture_csv(file)
    x_all.extend(X)
    y_all.extend(y)

x_all = np.array(x_all)
y_all = np.array(y_all)

print("x_all shape:", x_all.shape)
print("y_all shape:", y_all.shape)


# 划分训练集和测试集
x_train, x_test, y_train, y_test = train_test_split(
    x_all, y_all,
    test_size=0.3,
    random_state=42,
    stratify=y_all
)

# 再用训练集算 mean/std
mean = np.mean(x_train, axis=(0, 1), keepdims=True)
std = np.std(x_train, axis=(0, 1), keepdims=True) + 1e-6

x_train = (x_train - mean) / std
x_test = (x_test - mean) / std


print("训练集:", x_train.shape)
print("测试集:", x_test.shape)


# 建立模型
model = Sequential([
    Input(shape=(100, 2)),

    Conv1D(8, 5, activation='relu'),
    BatchNormalization(),
    MaxPooling1D(2),

    Conv1D(16, 3, activation='relu'),
    BatchNormalization(),
    MaxPooling1D(2),

    Flatten(),
    Dense(16, activation='relu'),
    Dense(CLASS, activation='softmax')
])


# 编译模型
model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

early_stop = EarlyStopping(
    monitor="val_loss",
    patience=8,
    restore_best_weights=True
)

# 训练模型
model.fit(
    x_train,
    y_train,
    epochs=60,
    batch_size=8,
    validation_split=0.2,
    callbacks=[early_stop]
)


# 测试预测
loss, acc = model.evaluate(x_test, y_test)
print("测试准确率:", acc)


# 创建转换器
converter = tf.lite.TFLiteConverter.from_keras_model(model)

# 启用量化
converter.optimizations = [tf.lite.Optimize.DEFAULT]


# 添加代表性数据集
def representative_dataset():
    # 使用确定性的样本，覆盖各类别
    indices = np.linspace(0, len(x_train)-1, 500, dtype=int)
    for idx in indices:
        yield [x_train[idx:idx+1].astype(np.float32)]


# 设置代表性数据集
converter.representative_dataset = representative_dataset

# 使用纯整数模型（包括输入/输出也是INT8）
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]

# 设置输入和输出张量为 INT8
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

# 转换模型
tflite_model = converter.convert()

# 保存模型
with open('gesture_model.tflite', 'wb') as f:
    f.write(tflite_model)

print("===== 模型已保存为 gesture_model.tflite =====")
print("mean:", mean)
print("std:", std)
