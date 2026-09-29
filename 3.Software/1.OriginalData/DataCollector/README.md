# DataCollector.py 脚本

用于采集魔杖输出的数据，为后续模型训练提供数据支持。

采集前需要连接魔杖热点，脚本会访问8080端口的TCP/IP串口获取IMU输出的数据并缓存，只有在手势状态机输出4时保存最新的100帧数据到csv中。

## 若需要打包成exe，执行以下操作：

### 1.创建虚拟环境并启动（可选）

创建：

```bash
python -m venv .venv
```

启动：

```bash
.venv\Scripts\activate
```

### 2.安装pyinstaller

```bash
pip install pyinstaller
```

### 3.打包DataCollector.py

```bash
pyinstaller -F --clean DataCollector.py
```
