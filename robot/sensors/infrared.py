import RPi.GPIO as GPIO
from .sensor_base import SensorBase
import logging

class InfraredSensor(SensorBase):
    def __init__(self, pin: int, logger: logging.Logger):
        self.logger = logger
        super().__init__(pin)
        
    def _setup(self):
        """初始化红外传感器"""
        GPIO.setup(self.pin, GPIO.IN)
        self.logger.debug(f"红外传感器初始化完成，引脚: {self.pin}")
        
    def read(self) -> bool:
        """读取传感器状态
        返回: True 表示检测到障碍物，False 表示未检测到
        """
        return GPIO.input(self.pin) == GPIO.LOW
        
    def cleanup(self):
        """清理资源"""
        pass 