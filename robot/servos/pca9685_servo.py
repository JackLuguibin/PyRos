from typing import Dict, Optional
import logging
import time
import Adafruit_PCA9685
from .base_servo import BaseServo, ServoConfig

class PCA9685Servo(BaseServo):
    """PCA9685舵机"""
    
    def __init__(self, channel: int, config: Dict,
                 pca: Optional[Adafruit_PCA9685.PCA9685] = None,
                 logger: Optional[logging.Logger] = None):
        """初始化舵机
        
        Args:
            channel: 通道号
            config: 舵机配置
            pca: PCA9685实例
            logger: 日志记录器
        """
        super().__init__(config, logger)
        self.channel = channel
        
        # 创建或使用PCA9685实例
        if pca is None:
            self.pca = Adafruit_PCA9685.PCA9685()
            self.pca.set_pwm_freq(50)  # 50Hz
        else:
            self.pca = pca
            
        self.enabled = False
        
    def enable(self):
        """使能舵机"""
        if not self.enabled:
            self.enabled = True
            self._write_angle(self.current_angle)
            self.logger.info(f"舵机{self.channel}已使能")
            
    def disable(self):
        """失能舵机"""
        if self.enabled:
            self.pca.set_pwm(self.channel, 0, 0)
            self.enabled = False
            self.logger.info(f"舵机{self.channel}已失能")
            
    def _write_angle(self, angle: float):
        """写入角度"""
        if not self.enabled:
            return
            
        try:
            # 计算脉宽
            pulse = self.angle_to_pulse(angle)
            
            # 转换为PCA9685的值(12位,4096分辨率)
            value = int(pulse * 4096 / (1000000 / 50))  # 50Hz
            
            # 写入PWM
            self.pca.set_pwm(self.channel, 0, value)
            
            # 更新状态
            self.current_angle = angle
            self.is_moving = (abs(angle - self.target_angle) > 0.1)
            
        except Exception as e:
            self.logger.error(f"写入角度失败: {str(e)}") 