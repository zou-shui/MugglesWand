import asyncio
import csv
from collections import deque

# ========================= TCP 默认配置区域 =========================
DEFAULT_IP = "192.168.4.1"
DEFAULT_PORT = 8080

WINDOW_SIZE = 100
DEFAULT_GESTURE_NAME = '0'
# ===================================================================


class TCPDataCollector:
    def __init__(self, gesture_name: str):
        self.gesture_name = gesture_name
        self.csv_file = f"{gesture_name}.csv"
        self.buffer = deque(maxlen=WINDOW_SIZE)
        self.sample_count = 0

        try:
            with open(self.csv_file, 'r') as f:
                self.sample_count = sum(1 for _ in f)
        except FileNotFoundError:
            self.sample_count = 0

    def process_line(self, line: str):
        try:
            line = line.strip()
            if not line:
                return
            values = [float(x) for x in line.split(',')]

            if len(values) != 3:
                return

            arg1, arg2, sta = values

            self.buffer.append((arg1, arg2))

            print(f"\r(arg1:{arg1:7.3f} | arg2:{arg2:7.3f} | sta:{int(sta)}) "
                  f"Buffer: {len(self.buffer):3d}/{WINDOW_SIZE}", end="", flush=True)

            if int(sta) == 4:
                if len(self.buffer) < WINDOW_SIZE:
                    print(f"\n⚠️ 检测到状态4，但缓冲区数据不足 ({len(self.buffer)}/{WINDOW_SIZE})，已忽略")
                    return

                row = [self.gesture_name]
                for a1, a2 in self.buffer:
                    row.extend([a1, a2])

                with open(self.csv_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(row)

                self.sample_count += 1
                print(
                    f"\n✅ 触发并保存手势{self.gesture_name}样本！当前{self.csv_file}总样本数: {self.sample_count}")

                self.buffer.clear()

        except ValueError as ve:
            print(f"\n⚠️ 数据解析跳过: {ve}")
        except Exception as e:
            print(f"\n❌ 处理异常: {e}")


async def main():
    print("=== Muggles' Wand 数据采集程序 ===")
    print(f"将访问默认IP: {DEFAULT_IP}")
    input_port = input(f"请输入端口号 (不填则使用默认值: {DEFAULT_PORT}): ").strip()
    port = int(input_port) if input_port else DEFAULT_PORT

    input_gesture = input(
        f"请输入手势标签 (不填则使用默认值: {DEFAULT_GESTURE_NAME}): ").strip()
    gesture_name = input_gesture if input_gesture else DEFAULT_GESTURE_NAME

    collector = TCPDataCollector(gesture_name)

    print("-" * 30)
    print(f"目标地址: {DEFAULT_IP}:{port}")
    print(f"数据保存文件: {collector.csv_file}")
    print(f"历史已有样本: {collector.sample_count} 条")
    print("-" * 30)

    print(f"🔗 正在连接 {DEFAULT_IP}:{port} ...")

    try:
        reader, writer = await asyncio.open_connection(DEFAULT_IP, port)
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    print(f"✅ 已连接！")

    # 发送使能指令
    print(f"🚀 正在发送使能指令: [imu] ...")
    try:
        writer.write(b"imu")
        await writer.drain()
        print(f"✅ 指令发送成功，设备进入数据输出模式。")
    except Exception as e:
        print(f"❌ 指令发送失败: {e}，程序将尝试继续接收数据...")

    print("✅ TCP 实时采集已就绪。按 Ctrl+C 退出...\n")

    try:
        while True:
            line = await reader.readline()
            if not line:
                print("\n⚠️ 连接已断开。")
                break
            collector.process_line(line.decode('utf-8', errors='ignore'))
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 程序已由用户终止")
