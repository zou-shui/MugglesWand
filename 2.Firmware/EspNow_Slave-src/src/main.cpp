#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <FastLED.h> // 引入 FastLED 库
#include "ServoDriver.h"

ServoDriver wandServo;

#define CHANNEL 1
#define WAKEUP_WINDOW_MS 40       // 闪现探测窗口：只睁眼 40ms（可覆盖发送端 20ms 的心跳周期）
#define SLEEP_DURATION_SEC 1      // 休眠周期：1 秒左右
#define KEEP_AWAKE_TIMEOUT_MS 200 // 暂停休眠状态下，超过 1 秒没收到心跳则重新休眠

// WS2812 配置
#define NUM_LEDS 1
#define DATA_PIN 21
CRGB leds[NUM_LEDS];

enum MsgType
{
  MSG_HEARTBEAT = 0x01,
  MSG_SIGNAL_1 = 0x02,
  MSG_SIGNAL_2 = 0x03
};

// 使用 RTC 内存存储状态，即使 Deep Sleep 也不会丢失
RTC_DATA_ATTR bool keepAwakeMode = false;

volatile bool heartbeatReceived = false;
volatile uint32_t lastHeartbeatTime = 0; // 记录最后一次收到心跳的时间戳

// 接收回调
void OnDataRecv(const uint8_t *mac_addr, const uint8_t *data, int data_len)
{
  if (data_len == 0)
    return;
  uint8_t msgType = data[0];

  if (msgType == MSG_HEARTBEAT)
  {
    heartbeatReceived = true;
    lastHeartbeatTime = millis(); // 更新最后收到心跳的时间
  }
  else if (msgType == MSG_SIGNAL_1)
  {
    Serial.println("[ALERT] signal 1!");
    wandServo.triggerClose();
    lastHeartbeatTime = millis();
  }
  else if (msgType == MSG_SIGNAL_2)
  {
    Serial.println("[ALERT] signal 2!");
    wandServo.triggerOpen();
    lastHeartbeatTime = millis();
  }
}

void initEspNowReceiver()
{
  WiFi.mode(WIFI_STA);
  esp_wifi_set_channel(CHANNEL, WIFI_SECOND_CHAN_NONE);
  WiFi.disconnect();
  if (esp_now_init() == ESP_OK)
  {
    esp_now_register_recv_cb(OnDataRecv);
  }
}

// 封装一个进入深度休眠的函数
void enterDeepSleep()
{
  // 在全黑关闭灯珠后再去睡觉，否则灯珠会一直亮着耗电
  leds[0] = CRGB::Black;
  FastLED.show();

  esp_sleep_enable_timer_wakeup(SLEEP_DURATION_SEC * 1000000ULL);
  Serial.println("Entering Deep Sleep...");
  Serial.flush();
  esp_deep_sleep_start();
}

void setup()
{
  Serial.begin(115200);

  // 初始化 FastLED，配置为 ESP32-S3 的 GPIO21
  FastLED.addLeds<WS2812, DATA_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(50); // 设置适中的亮度（0-255）

  // 初始化网络与 ESP-NOW
  initEspNowReceiver();

  // 状态 A：如果原本就处于“暂停休眠模式”
  if (keepAwakeMode)
  {
    Serial.println("Running in ALWAYS-AWAKE mode. Waiting for signals...");
    // 既然在线，确保灯珠是亮着的（比如绿色）
    leds[0] = CRGB::Green;
    FastLED.show();

    lastHeartbeatTime = millis();
    return;
  }

  // 状态 B：处于“周期唤醒探测”状态
  Serial.println("Woke up. Flashing window check...");
  heartbeatReceived = false;
  uint32_t startTime = millis();

  // 闪现监听 40ms
  while (millis() - startTime < WAKEUP_WINDOW_MS)
  {
    if (heartbeatReceived)
      break;
    delay(1);
  }

  if (heartbeatReceived)
  {
    // 抓到心跳，修改 RTC 变量
    keepAwakeMode = true;
    lastHeartbeatTime = millis();
    Serial.println("Transmitter detected! Switching to Always-Awake mode...");

    // 抓到心跳时点亮灯珠（绿色）
    leds[0] = CRGB::Green;
    FastLED.show();
  }
  else
  {
    // 没抓到心跳，立马调用带有“熄灯逻辑”的休眠函数
    Serial.println("No HB found in window.");
    enterDeepSleep();
  }

  wandServo.setOpenAngle(105); // 开灯角度
  wandServo.setCloseAngle(75); // 关灯角度
  wandServo.setRestAngle(90);  // 静止角度
  wandServo.setHoldTime(300);  // 保持 300ms
  wandServo.begin();
}

void loop()
{
  // 只有当 keepAwakeMode == true 时，程序才会持续运行在这里

  // 超时检测：如果 1 秒钟没收到心跳，则认为断线
  if (millis() - lastHeartbeatTime > KEEP_AWAKE_TIMEOUT_MS)
  {
    Serial.println("\n[TIMEOUT] Transmitter lost heartbeat! Returning to sleep-wake cycle...");
    keepAwakeMode = false;
    enterDeepSleep(); // 内部会自动熄灭灯珠并休眠
  }

  delay(100);
}