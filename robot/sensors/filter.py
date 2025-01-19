from typing import List, Deque
from collections import deque
import numpy as np
import logging

class SensorFilter:
    def __init__(self, window_size: int = 10, logger: logging.Logger = None):
        self.window_size = window_size
        self.logger = logger
        self.data_buffer: Deque = deque(maxlen=window_size)
        
    def update(self, value: float) -> float:
        """更新并过滤数据
        
        Args:
            value: 新的传感器数据
            
        Returns:
            过滤后的数据
        """
        self.data_buffer.append(value)
        return self.get_filtered_value()
        
    def get_filtered_value(self) -> float:
        """获取过滤后的值"""
        if not self.data_buffer:
            return 0.0
            
        # 中值滤波
        return float(np.median(self.data_buffer))
        
    def reset(self):
        """重置过滤器"""
        self.data_buffer.clear()
        
class KalmanFilter:
    def __init__(self, process_variance: float = 1e-4,
                 measurement_variance: float = 1e-2,
                 logger: logging.Logger = None):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.logger = logger
        
        self.posteri_estimate = 0.0
        self.posteri_error_estimate = 1.0
        
    def update(self, measurement: float) -> float:
        """更新卡尔曼滤波
        
        Args:
            measurement: 测量值
            
        Returns:
            滤波后的估计值
        """
        # 预测
        priori_estimate = self.posteri_estimate
        priori_error_estimate = (self.posteri_error_estimate + 
                               self.process_variance)
        
        # 更新
        blending_factor = (priori_error_estimate / 
                         (priori_error_estimate + self.measurement_variance))
        self.posteri_estimate = (priori_estimate + 
                               blending_factor * (measurement - priori_estimate))
        self.posteri_error_estimate = ((1 - blending_factor) * 
                                     priori_error_estimate)
        
        return self.posteri_estimate
        
    def reset(self):
        """重置滤波器"""
        self.posteri_estimate = 0.0
        self.posteri_error_estimate = 1.0 