import RPi.GPIO as GPIO
import time
from .sensor_base import SensorBase

class UltrasonicSensor(SensorBase):
    def __init__(self, trigger_pin: int, echo_pin: int):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        super().__init__(trigger_pin)  # 使用trigger_pin作为主pin
        
    def _setup(self):
        """初始化超声波传感器"""
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
    def read(self) -> float:
        """读取距离（厘米）"""
        # 发送触发信号
        GPIO.output(self.trigger_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trigger_pin, False)
        
        # 等待回响
        start_time = time.time()
        while GPIO.input(self.echo_pin) == 0:
            if time.time() - start_time > 0.1:  # 超时保护
                return -1
        pulse_start = time.time()
        
        while GPIO.input(self.echo_pin) == 1:
            if time.time() - start_time > 0.1:  # 超时保护
                return -1
        pulse_end = time.time()
        
        # 计算距离
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # 声速 * 时间 / 2
        return round(distance, 2)
        
    def cleanup(self):
        """清理资源"""
        pass  # GPIO cleanup将由GPIO管理器统一处理 