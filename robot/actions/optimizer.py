from typing import List, Dict, Optional
import numpy as np
import logging

class ActionOptimizer:
    def __init__(self, logger: logging.Logger = None):
        """动作组优化器"""
        self.logger = logger
        
    def optimize_timing(self, frames: List[Dict],
                       min_delay: float = 0.02,
                       max_velocity: float = 300.0) -> List[Dict]:
        """优化动作时序
        
        Args:
            frames: 动作序列
            min_delay: 最小延时
            max_velocity: 最大角速度(度/秒)
        """
        optimized = []
        prev_frame = None
        
        for frame in frames:
            if prev_frame is None:
                optimized.append(frame.copy())
                prev_frame = frame
                continue
                
            # 计算最大角度变化
            max_angle_change = 0
            for servo_id, angle in frame.items():
                if servo_id == 'delay':
                    continue
                prev_angle = prev_frame.get(servo_id, angle)
                angle_change = abs(angle - prev_angle)
                max_angle_change = max(max_angle_change, angle_change)
                
            # 计算所需最小延时
            required_delay = max_angle_change / max_velocity
            
            # 更新延时
            new_frame = frame.copy()
            new_frame['delay'] = max(required_delay, min_delay)
            optimized.append(new_frame)
            
            prev_frame = frame
            
        return optimized
        
    def smooth_trajectory(self, frames: List[Dict],
                         window_size: int = 3) -> List[Dict]:
        """平滑动作轨迹
        
        Args:
            frames: 动作序列
            window_size: 平滑窗口大小
        """
        if len(frames) < window_size:
            return frames
            
        smoothed = []
        half_window = window_size // 2
        
        for i in range(len(frames)):
            new_frame = {'delay': frames[i].get('delay', 0)}
            
            # 对每个舵机进行平滑
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                # 收集窗口内的角度值
                angles = []
                for j in range(max(0, i-half_window),
                             min(len(frames), i+half_window+1)):
                    if servo_id in frames[j]:
                        angles.append(frames[j][servo_id])
                        
                # 计算加权平均
                if angles:
                    weights = np.exp(-0.5 * np.square(
                        np.linspace(-1, 1, len(angles))))
                    new_frame[servo_id] = np.average(angles, weights=weights)
                    
            smoothed.append(new_frame)
            
        return smoothed
        
    def reduce_jerk(self, frames: List[Dict],
                    max_accel: float = 200.0) -> List[Dict]:
        """减少加加速度
        
        Args:
            frames: 动作序列
            max_accel: 最大加速度(度/秒²)
        """
        optimized = []
        
        for i in range(len(frames)):
            new_frame = frames[i].copy()
            
            if i >= 2:
                for servo_id in new_frame:
                    if servo_id == 'delay':
                        continue
                        
                    # 获取前两帧的角度
                    prev_angles = [
                        frames[i-2].get(servo_id, new_frame[servo_id]),
                        frames[i-1].get(servo_id, new_frame[servo_id])
                    ]
                    
                    # 计算加速度
                    dt = frames[i-1].get('delay', 0.02)
                    accel = (new_frame[servo_id] - 2*prev_angles[1] +
                            prev_angles[0]) / (dt * dt)
                    
                    # 限制加速度
                    if abs(accel) > max_accel:
                        # 调整当前角度以限制加速度
                        direction = 1 if accel > 0 else -1
                        max_angle = (2*prev_angles[1] - prev_angles[0] +
                                   direction * max_accel * dt * dt)
                        new_frame[servo_id] = max_angle
                        
            optimized.append(new_frame)
            
        return optimized 