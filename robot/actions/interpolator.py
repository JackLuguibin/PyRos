from typing import List, Dict, Optional
import numpy as np
import logging
from scipy.interpolate import CubicSpline

class ActionInterpolator:
    def __init__(self, logger: logging.Logger = None):
        """动作插值器"""
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
        
    def interpolate_cubic(self, frames: List[Dict],
                         num_points: int) -> List[Dict]:
        """三次样条插值
        
        Args:
            frames: 关键帧序列
            num_points: 插值点数
            
        Returns:
            插值后的帧序列
        """
        if len(frames) < 2:
            return frames
            
        # 获取所有舵机ID
        servo_ids = set()
        for frame in frames:
            servo_ids.update(k for k in frame.keys() if k != 'delay')
            
        # 构建时间序列
        times = np.zeros(len(frames))
        for i in range(1, len(frames)):
            times[i] = times[i-1] + frames[i-1].get('delay', 0.02)
            
        # 对每个舵机进行插值
        interpolated = []
        new_times = np.linspace(times[0], times[-1], num_points)
        
        for t in new_times:
            frame = {'delay': (times[-1] - times[0]) / (num_points - 1)}
            
            for servo_id in servo_ids:
                # 收集角度数据
                angles = []
                for f in frames:
                    if servo_id in f:
                        angles.append(f[servo_id])
                    else:
                        # 使用最近的有效角度
                        angles.append(angles[-1] if angles else 0)
                        
                # 创建样条插值器
                cs = CubicSpline(times, angles)
                frame[servo_id] = float(cs(t))
                
            interpolated.append(frame)
            
        return interpolated
        
    def interpolate_bezier(self, frames: List[Dict],
                          num_points: int) -> List[Dict]:
        """贝塞尔曲线插值
        
        Args:
            frames: 关键帧序列
            num_points: 插值点数
            
        Returns:
            插值后的帧序列
        """
        def _bezier_curve(points: np.ndarray, t: float) -> float:
            n = len(points) - 1
            result = 0
            for i in range(n + 1):
                coef = np.math.comb(n, i)
                result += coef * (1 - t)**(n - i) * t**i * points[i]
            return result
            
        if len(frames) < 2:
            return frames
            
        # 获取所有舵机ID
        servo_ids = set()
        for frame in frames:
            servo_ids.update(k for k in frame.keys() if k != 'delay')
            
        # 生成插值点
        interpolated = []
        t_values = np.linspace(0, 1, num_points)
        total_time = sum(frame.get('delay', 0.02) for frame in frames[:-1])
        
        for t in t_values:
            frame = {'delay': total_time / (num_points - 1)}
            
            for servo_id in servo_ids:
                # 收集控制点
                control_points = []
                for f in frames:
                    if servo_id in f:
                        control_points.append(f[servo_id])
                    else:
                        control_points.append(control_points[-1] if control_points else 0)
                        
                # 计算贝塞尔曲线点
                frame[servo_id] = _bezier_curve(np.array(control_points), t)
                
            interpolated.append(frame)
            
        return interpolated
        
    def interpolate_slerp(self, frames: List[Dict],
                         num_points: int) -> List[Dict]:
        """球面线性插值（适用于旋转动作）
        
        Args:
            frames: 关键帧序列
            num_points: 插值点数
            
        Returns:
            插值后的帧序列
        """
        def _slerp(start: float, end: float, t: float) -> float:
            """球面线性插值"""
            # 将角度转换为弧度
            start_rad = np.radians(start)
            end_rad = np.radians(end)
            
            # 计算最短路径
            diff = end_rad - start_rad
            if abs(diff) > np.pi:
                if diff > 0:
                    end_rad -= 2 * np.pi
                else:
                    end_rad += 2 * np.pi
                    
            # 执行插值
            result = start_rad + (end_rad - start_rad) * t
            return np.degrees(result)
            
        if len(frames) < 2:
            return frames
            
        # 获取所有舵机ID
        servo_ids = set()
        for frame in frames:
            servo_ids.update(k for k in frame.keys() if k != 'delay')
            
        # 生成插值序列
        interpolated = []
        total_time = sum(frame.get('delay', 0.02) for frame in frames[:-1])
        
        for i in range(num_points):
            t = i / (num_points - 1)
            frame = {'delay': total_time / (num_points - 1)}
            
            # 找到对应的关键帧段
            segment_t = t * (len(frames) - 1)
            idx = int(segment_t)
            if idx >= len(frames) - 1:
                idx = len(frames) - 2
            local_t = segment_t - idx
            
            # 对每个舵机进行插值
            for servo_id in servo_ids:
                start = frames[idx].get(servo_id, 0)
                end = frames[idx + 1].get(servo_id, start)
                frame[servo_id] = _slerp(start, end, local_t)
                
            interpolated.append(frame)
            
        return interpolated
        
    def optimize_trajectory(self, frames: List[Dict],
                          smoothing_factor: float = 0.1) -> List[Dict]:
        """优化轨迹，减少抖动
        
        Args:
            frames: 动作序列
            smoothing_factor: 平滑因子 (0-1)
            
        Returns:
            优化后的序列
        """
        if len(frames) < 3:
            return frames
            
        # 获取所有舵机ID
        servo_ids = set()
        for frame in frames:
            servo_ids.update(k for k in frame.keys() if k != 'delay')
            
        # 对每个舵机的轨迹进行优化
        optimized = []
        for i in range(len(frames)):
            frame = {'delay': frames[i].get('delay', 0.02)}
            
            for servo_id in servo_ids:
                if i == 0 or i == len(frames) - 1:
                    # 保持首尾帧不变
                    frame[servo_id] = frames[i].get(servo_id, 0)
                    continue
                    
                # 获取前后帧的角度
                prev_angle = frames[i-1].get(servo_id, 0)
                curr_angle = frames[i].get(servo_id, 0)
                next_angle = frames[i+1].get(servo_id, 0)
                
                # 计算平滑后的角度
                predicted = prev_angle + (next_angle - prev_angle) / 2
                frame[servo_id] = curr_angle * (1 - smoothing_factor) + \
                                predicted * smoothing_factor
                
            optimized.append(frame)
            
        return optimized 