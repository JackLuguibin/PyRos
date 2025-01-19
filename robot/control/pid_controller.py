from typing import Optional
import numpy as np
import logging

class PIDController:
    def __init__(self, kp: float = 1.0, ki: float = 0.0, kd: float = 0.0,
                 min_output: float = -float('inf'),
                 max_output: float = float('inf'),
                 deadband: float = 0.0,
                 logger: Optional[logging.Logger] = None):
        """PID控制器
        
        Args:
            kp: 比例系数
            ki: 积分系数
            kd: 微分系数
            min_output: 输出下限
            max_output: 输出上限
            deadband: 死区范围
            logger: 日志记录器
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.min_output = min_output
        self.max_output = max_output
        self.deadband = deadband
        self.logger = logger or logging.getLogger('PIDController')
        
        # 控制状态
        self.last_error = 0.0
        self.integral = 0.0
        self.last_output = 0.0
        
        # 积分限幅
        self.integral_min = min_output / ki if ki != 0 else -float('inf')
        self.integral_max = max_output / ki if ki != 0 else float('inf')
        
        # 性能统计
        self.stats = {
            'max_error': 0.0,
            'min_error': 0.0,
            'total_error': 0.0,
            'samples': 0,
            'overshoots': 0
        }
        
    def compute(self, target: float, current: float, dt: float) -> float:
        """计算控制输出
        
        Args:
            target: 目标值
            current: 当前值
            dt: 时间间隔
            
        Returns:
            控制输出
        """
        # 计算误差
        error = target - current
        
        # 更新统计
        self._update_stats(error)
        
        # 死区处理
        if abs(error) < self.deadband:
            self.integral = 0
            self.last_error = 0
            return 0.0
            
        # 计算积分项
        self.integral += error * dt
        
        # 积分限幅
        self.integral = np.clip(
            self.integral,
            self.integral_min,
            self.integral_max
        )
        
        # 计算微分项
        derivative = (error - self.last_error) / dt if dt > 0 else 0
        
        # 计算输出
        output = (
            self.kp * error +
            self.ki * self.integral +
            self.kd * derivative
        )
        
        # 输出限幅
        output = np.clip(output, self.min_output, self.max_output)
        
        # 检测过冲
        if self._check_overshoot(error, self.last_error):
            self.stats['overshoots'] += 1
            
        # 更新状态
        self.last_error = error
        self.last_output = output
        
        return output
        
    def reset(self):
        """重置控制器状态"""
        self.last_error = 0.0
        self.integral = 0.0
        self.last_output = 0.0
        self.stats = {
            'max_error': 0.0,
            'min_error': 0.0,
            'total_error': 0.0,
            'samples': 0,
            'overshoots': 0
        }
        
    def get_stats(self) -> dict:
        """获取性能统计
        
        Returns:
            统计数据字典
        """
        if self.stats['samples'] > 0:
            avg_error = self.stats['total_error'] / self.stats['samples']
        else:
            avg_error = 0.0
            
        return {
            'max_error': self.stats['max_error'],
            'min_error': self.stats['min_error'],
            'avg_error': avg_error,
            'samples': self.stats['samples'],
            'overshoots': self.stats['overshoots']
        }
        
    def _update_stats(self, error: float):
        """更新统计数据"""
        self.stats['samples'] += 1
        self.stats['total_error'] += abs(error)
        self.stats['max_error'] = max(self.stats['max_error'], error)
        self.stats['min_error'] = min(self.stats['min_error'], error)
        
    def _check_overshoot(self, error: float, last_error: float) -> bool:
        """检测过冲
        
        当误差变号且幅值增大时认为发生过冲
        """
        return (error * last_error < 0 and 
                abs(error) > abs(last_error))
                
    def tune(self, kp: Optional[float] = None,
            ki: Optional[float] = None,
            kd: Optional[float] = None):
        """调整PID参数
        
        Args:
            kp: 新的比例系数
            ki: 新的积分系数
            kd: 新的微分系数
        """
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
            # 更新积分限幅
            self.integral_min = self.min_output / ki if ki != 0 else -float('inf')
            self.integral_max = self.max_output / ki if ki != 0 else float('inf')
        if kd is not None:
            self.kd = kd
            
        # 重置状态
        self.reset()
        
    def set_output_limits(self, min_output: float, max_output: float):
        """设置输出限幅
        
        Args:
            min_output: 输出下限
            max_output: 输出上限
        """
        self.min_output = min_output
        self.max_output = max_output
        
        # 更新积分限幅
        if self.ki != 0:
            self.integral_min = min_output / self.ki
            self.integral_max = max_output / self.ki
            
    def set_deadband(self, deadband: float):
        """设置死区范围
        
        Args:
            deadband: 新的死区范围
        """
        self.deadband = deadband
        
    def get_parameters(self) -> dict:
        """获取控制器参数
        
        Returns:
            参数字典
        """
        return {
            'kp': self.kp,
            'ki': self.ki,
            'kd': self.kd,
            'min_output': self.min_output,
            'max_output': self.max_output,
            'deadband': self.deadband
        }