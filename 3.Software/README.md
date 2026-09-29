# Software

本目录存放在PC上运行的Python脚本和tf模型

## 1.OriginalData

内有DataCollector脚本源码以及打包好的可执行文件`DataCollector.exe`，后者可直接运行（无需Python环境）。

另外附有固件中模型的原始数据（csv）。

## 2.TensorFLow

内有利用原始数据对模型进行训练的程序`train.py`。需要自行配置python环境后运行。详细步骤请参阅内部的`README.md`。

## 3.POVTool

该工具是一个带有UI的可视化上位机，用于将任意图片转换成数组，供光绘模块使用。需要自行配置python环境后运行，详细步骤请参阅内部的`README.md`。








