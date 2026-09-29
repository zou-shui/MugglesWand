#include "ServoDriver.h"

void ServoDriver::begin()
{
    xTaskCreate(
        taskFunc,
        "servo_task",
        2048,
        this,
        1,
        &taskHandle);
}

void ServoDriver::triggerOpen()
{
    if (taskHandle)
    {
        pendingAction = ACTION_OPEN;
        xTaskNotifyGive(taskHandle);
    }
}

void ServoDriver::triggerClose()
{
    if (taskHandle)
    {
        pendingAction = ACTION_CLOSE;
        xTaskNotifyGive(taskHandle);
    }
}

void ServoDriver::setRestAngle(uint8_t angle)
{
    restAngle = angle;
}

void ServoDriver::setOpenAngle(uint8_t angle)
{
    openAngle = angle;
}

void ServoDriver::setCloseAngle(uint8_t angle)
{
    closeAngle = angle;
}

void ServoDriver::setHoldTime(uint32_t ms)
{
    holdTimeMs = ms;
}

void ServoDriver::taskFunc(void *param)
{
    ServoDriver *driver = static_cast<ServoDriver *>(param);
    driver->taskLoop();
}

void ServoDriver::taskLoop()
{
    while (true)
    {
        // 阻塞等待 triggerOpen() / triggerClose() 通知
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        uint8_t targetAngle = (pendingAction == ACTION_OPEN) ? openAngle : closeAngle;

        servo.attach(SERVO_PIN);
        servo.write(restAngle);
        // 执行触发动作
        servo.write(targetAngle);
        vTaskDelay(pdMS_TO_TICKS(holdTimeMs));
        servo.write(restAngle);
        servo.detach();
    }
}
