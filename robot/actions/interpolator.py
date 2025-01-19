from typing import List, Dict
import numpy as np
import logging

class ActionInterpolator:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        
    def interpolate(self, keyframes: List[Dict], 
                   num_points: int = 10) -> List[Dict]:
        """在关键帧之间插值
        
        Args:
            keyframes: 关键帧列表
            num_points: 每两个关键帧之间的插值点数
            
        Returns:
            插值后的动作序列
        """
        if len(keyframes) < 2:
            return keyframes
            
        result = []
        for i in range(len(keyframes) - 1):
            start_frame = keyframes[i]
            end_frame = keyframes[i + 1]
            
            # 对每个舵机进行插值
            for j in range(num_points):
                t = j / num_points
                frame = {}
                
                # 线性插值
                for servo_id in start_frame:
                    start_angle = start_frame[servo_id]
                    end_angle = end_frame[servo_id]
                    frame[servo_id] = start_angle + t * (end_angle - start_angle)
                    
                result.append(frame)
                
        # 添加最后一帧
        result.append(keyframes[-1])
        
        if self.logger:
            self.logger.debug(f"插值完成: {len(keyframes)} 帧 -> {len(result)} 帧")
            
        return result
        
    def smooth_trajectory(self, frames: List[Dict], 
                         window_size: int = 3) -> List[Dict]:
        """平滑动作轨迹
        
        Args:
            frames: 动作序列
            window_size: 平滑窗口大小
            
        Returns:
            平滑后的动作序列
        """
        if len(frames) < window_size:
            return frames
            
        result = []
        half_window = window_size // 2
        
        # 对每个舵机分别平滑
        servo_ids = frames[0].keys()
        
        for i in range(len(frames)):
            frame = {}
            
            for servo_id in servo_ids:
                # 提取窗口内的角度值
                start_idx = max(0, i - half_window)
                end_idx = min(len(frames), i + half_window + 1)
                angles = [frames[j][servo_id] for j in range(start_idx, end_idx)]
                
                # 计算加权平均
                weights = np.exp(-0.5 * np.square(np.arange(-half_window, half_window+1)))
                weights = weights[:(end_idx-start_idx)]
                weights /= np.sum(weights)
                
                frame[servo_id] = np.sum(np.array(angles) * weights)
                
            result.append(frame)
            
        return result 