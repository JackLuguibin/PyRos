from typing import Dict
import RPi.GPIO as GPIO
from .servo import Servo

class ServoManager:
    def __init__(self):
        self.servos: Dict[str, Servo] = {}
        
    def initialize(self, servo_config: dict):
        """初始化所有舵机"""
        GPIO.setmode(GPIO.BCM)
        for servo_id, config in servo_config.items():
            servo = Servo(
                pin=config['pin'],
                min_pulse=config.get('min_pulse', 500),
                max_pulse=config.get('max_pulse', 2500)
            )
            self.servos[servo_id] = servo
            
    def register_servo(self, servo_id: str, servo: Servo):
        """注册新的舵机"""
        self.servos[servo_id] = servo
        
    def set_angle(self, servo_id: str, angle: float):
        """设置舵机角度"""
        if servo_id in self.servos:
            self.servos[servo_id].set_angle(angle)
            
    def shutdown(self):
        """关闭所有舵机"""
        for servo in self.servos.values():
            servo.cleanup()
        GPIO.cleanup() 