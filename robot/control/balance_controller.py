import time
from typing import Tuple
import logging

class BalanceController:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        
        # PID参数
        self.kp = 20.0
        self.ki = 0.1
        self.kd = 0.4
        
        # 控制相关变量
        self.target_angle = 0.0
        self.last_error = 0.0
        self.error_sum = 0.0
        self.last_time = time.time()
        
    def update(self, current_angle: float) -> float:
        """更新平衡控制
        
        Args:
            current_angle: 当前角度
            
        Returns:
            控制输出值
        """
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # 计算误差
        error = self.target_angle - current_angle
        self.error_sum += error * dt
        error_rate = (error - self.last_error) / dt
        
        # PID控制
        output = (self.kp * error + 
                 self.ki * self.error_sum + 
                 self.kd * error_rate)
        
        # 更新状态
        self.last_error = error
        
        if self.logger:
            self.logger.debug(f"平衡控制: 误差={error:.2f}, 输出={output:.2f}")
            
        return output
        
    def set_target(self, angle: float):
        """设置目标角度"""
        self.target_angle = angle
        self.error_sum = 0.0  # 重置积分项
        
    def set_pid(self, kp: float, ki: float, kd: float):
        """设置PID参数"""
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.error_sum = 0.0  # 重置积分项 