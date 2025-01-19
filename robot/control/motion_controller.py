from typing import Dict, List, Optional, Protocol, Tuple
import numpy as np
import logging
from abc import ABC, abstractmethod

class MotionController(ABC):
    """运动控制器基类"""
    
    @abstractmethod
    def update(self, state: Dict, dt: float) -> Dict:
        """更新控制"""
        pass
        
    @abstractmethod
    def reset(self):
        """重置控制器"""
        pass
        
    @abstractmethod
    def get_state(self) -> Dict:
        """获取状态"""
        pass

class TrajectoryGenerator(Protocol):
    """轨迹生成器协议"""
    
    def generate(self, start: Dict, end: Dict, duration: float) -> List[Dict]:
        """生成轨迹"""
        pass
        
    def interpolate(self, waypoints: List[Dict], durations: List[float]) -> List[Dict]:
        """插值轨迹"""
        pass

class MotionProfile:
    """运动规划"""
    
    def __init__(self, max_velocity: float, max_acceleration: float):
        self.max_velocity = max_velocity
        self.max_acceleration = max_acceleration
        
    def plan(self, distance: float) -> Tuple[float, List[float]]:
        """规划运动参数
        
        Args:
            distance: 运动距离
            
        Returns:
            (总时间, [加速时间, 匀速时间, 减速时间])
        """
        # 计算最小运动时间
        t_min = np.sqrt(abs(distance) / self.max_acceleration)
        
        if t_min * self.max_acceleration <= self.max_velocity:
            # 三角形速度曲线
            t_acc = t_min
            t_dec = t_min
            t_const = 0
        else:
            # 梯形速度曲线
            t_acc = self.max_velocity / self.max_acceleration
            t_dec = t_acc
            d_acc = 0.5 * self.max_acceleration * t_acc * t_acc
            d_dec = d_acc
            d_const = abs(distance) - d_acc - d_dec
            t_const = d_const / self.max_velocity
            
        total_time = t_acc + t_const + t_dec
        return total_time, [t_acc, t_const, t_dec] 