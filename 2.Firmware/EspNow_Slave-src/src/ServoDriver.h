#ifndef SERVO_DRIVER_H
#define SERVO_DRIVER_H

#include <Arduino.h>
#include <ESP32Servo.h>

#define SERVO_PIN 1 // GPIO pin for the servo

class ServoDriver
{
public:
    void begin();
    void triggerOpen();
    void triggerClose();

    void setRestAngle(uint8_t angle);
    void setOpenAngle(uint8_t angle);
    void setCloseAngle(uint8_t angle);
    void setHoldTime(uint32_t ms);

private:
    enum Action
    {
        ACTION_OPEN,
        ACTION_CLOSE
    };

    static void taskFunc(void *param);
    void taskLoop();

    Servo servo;
    TaskHandle_t taskHandle = nullptr;

    uint8_t restAngle = 0;
    uint8_t openAngle = 90;
    uint8_t closeAngle = 90;
    uint32_t holdTimeMs = 500;
    Action pendingAction = ACTION_OPEN;
};

#endif
