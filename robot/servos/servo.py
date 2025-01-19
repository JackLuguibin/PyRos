import RPi.GPIO as GPIO
import time

class Servo:
    def __init__(self, pin: int, min_pulse: int = 500, max_pulse: int = 2500, 
                 min_angle: float = 0, max_angle: float = 180):
        self.pin = pin
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.current_angle = 0
        self._setup()
        
    def _setup(self):
        """初始化舵机"""
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, 50)  # 50Hz PWM
        self.pwm.start(0)
        
    def set_angle(self, angle: float):
        """设置舵机角度"""
        # 限制角度范围
        angle = max(self.min_angle, min(self.max_angle, angle))
        
        # 将角度转换为占空比
        pulse = self._angle_to_pulse(angle)
        duty = pulse / 20000 * 100  # 转换为占空比
        
        self.pwm.ChangeDutyCycle(duty)
        self.current_angle = angle
        time.sleep(0.1)  # 等待舵机转动
        
    def _angle_to_pulse(self, angle: float) -> float:
        """将角度转换为脉冲宽度"""
        pulse_range = self.max_pulse - self.min_pulse
        angle_range = self.max_angle - self.min_angle
        return self.min_pulse + (angle - self.min_angle) * pulse_range / angle_range
        
    def cleanup(self):
        """清理资源"""
        self.pwm.stop() 