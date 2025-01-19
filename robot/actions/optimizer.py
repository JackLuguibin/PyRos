from typing import List, Dict
import numpy as np
import logging

class ActionOptimizer:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        
    def optimize_timing(self, sequence: List[Dict], 
                       max_speed: float = 300.0) -> List[Dict]:
        """优化动作时序
        
        Args:
            sequence: 动作序列
            max_speed: 最大角速度 (度/秒)
            
        Returns:
            优化后的动作序列
        """
        if len(sequence) < 2:
            return sequence
            
        result = []
        for i in range(len(sequence) - 1):
            current = sequence[i]
            next_frame = sequence[i + 1]
            
            # 计算最大角度变化
            max_angle_change = 0
            for servo_id in current:
                angle_change = abs(next_frame[servo_id] - current[servo_id])
                max_angle_change = max(max_angle_change, angle_change)
                
            # 计算所需时间
            min_time = max_angle_change / max_speed
            
            # 更新延时
            optimized_frame = current.copy()
            optimized_frame['delay'] = max(min_time, 
                                         current.get('delay', 0.0))
            result.append(optimized_frame)
            
        # 添加最后一帧
        result.append(sequence[-1])
        return result
        
    def reduce_jerk(self, sequence: List[Dict], 
                   smoothing_factor: float = 0.5) -> List[Dict]:
        """减少动作抖动
        
        Args:
            sequence: 动作序列
            smoothing_factor: 平滑因子 (0-1)
            
        Returns:
            优化后的动作序列
        """
        if len(sequence) < 3:
            return sequence
            
        result = [sequence[0]]  # 保持第一帧不变
        
        for i in range(1, len(sequence)-1):
            prev_frame = sequence[i-1]
            current = sequence[i]
            next_frame = sequence[i+1]
            
            smoothed_frame = {}
            for servo_id in current:
                # 计算平滑角度
                prev_angle = prev_frame[servo_id]
                current_angle = current[servo_id]
                next_angle = next_frame[servo_id]
                
                # 使用加权平均
                smoothed_angle = (current_angle + 
                                smoothing_factor * 
                                (0.5 * (prev_angle + next_angle) - current_angle))
                
                smoothed_frame[servo_id] = smoothed_angle
                
            # 保持原始延时
            if 'delay' in current:
                smoothed_frame['delay'] = current['delay']
                
            result.append(smoothed_frame)
            
        result.append(sequence[-1])  # 保持最后一帧不变
        return result 