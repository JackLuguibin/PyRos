from typing import Dict, Optional
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
import time

@dataclass
class ServoConfig:
    """舵机配置"""
    min_pulse: int = 500    # 最小脉宽(μs)
    max_pulse: int = 2500   # 最大脉宽(μs)
    min_angle: float = 0.0  # 最小角度(度)
    max_angle: float = 180.0  # 最大角度(度)
    default_speed: int = 100  # 默认速度(度/秒)
    default_acc: int = 100   # 默认加速度(度/秒²)

class BaseServo(ABC):
    """舵机基类"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """初始化舵机
        
        Args:
            config: 舵机配置
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.config = ServoConfig(**config)
        
        self.current_angle = 0.0
        self.target_angle = 0.0
        self.current_speed = self.config.default_speed
        self.is_moving = False
        
    @abstractmethod
    def enable(self):
        """使能舵机"""
        pass
        
    @abstractmethod
    def disable(self):
        """失能舵机"""
        pass
        
    def set_angle(self, angle: float, speed: Optional[int] = None):
        """设置角度
        
        Args:
            angle: 目标角度(度)
            speed: 运动速度(度/秒)
        """
        # 限制角度范围
        angle = max(self.config.min_angle,
                   min(self.config.max_angle, angle))
                   
        self.target_angle = angle
        if speed is not None:
            self.current_speed = speed
            
        self._write_angle(angle)
        
    def get_angle(self) -> float:
        """获取当前角度"""
        return self.current_angle
        
    @abstractmethod
    def _write_angle(self, angle: float):
        """写入角度
        
        Args:
            angle: 目标角度(度)
        """
        pass
        
    def angle_to_pulse(self, angle: float) -> int:
        """角度转脉宽
        
        Args:
            angle: 角度(度)
            
        Returns:
            pulse: 脉宽(μs)
        """
        # 线性映射
        ratio = (angle - self.config.min_angle) / (
            self.config.max_angle - self.config.min_angle
        )
        pulse = int(self.config.min_pulse + ratio * (
            self.config.max_pulse - self.config.min_pulse
        ))
        return pulse
        
    def pulse_to_angle(self, pulse: int) -> float:
        """脉宽转角度
        
        Args:
            pulse: 脉宽(μs)
            
        Returns:
            angle: 角度(度)
        """
        # 线性映射
        ratio = (pulse - self.config.min_pulse) / (
            self.config.max_pulse - self.config.min_pulse
        )
        angle = self.config.min_angle + ratio * (
            self.config.max_angle - self.config.min_angle
        )
        return angle 