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
        
    def optimize_energy(self, frames: List[Dict],
                       max_power: float = 100.0) -> List[Dict]:
        """优化动作能量消耗
        
        Args:
            frames: 动作序列
            max_power: 最大功率限制
            
        Returns:
            优化后的动作序列
        """
        optimized = []
        
        for i in range(len(frames)):
            frame = frames[i].copy()
            
            if i > 0:
                dt = frames[i-1].get('delay', 0.02)
                total_power = 0
                
                # 计算当前功率
                for servo_id in frame:
                    if servo_id == 'delay':
                        continue
                        
                    if servo_id in frames[i-1]:
                        velocity = abs(frame[servo_id] - 
                                     frames[i-1][servo_id]) / dt
                        power = velocity * velocity * 0.1
                        total_power += power
                        
                # 如果超过功率限制，调整延时
                if total_power > max_power:
                    scale_factor = np.sqrt(max_power / total_power)
                    frame['delay'] = dt / scale_factor
                    
            optimized.append(frame)
            
        return optimized
        
    def optimize_symmetry(self, frames: List[Dict],
                         servo_pairs: Dict[str, str]) -> List[Dict]:
        """优化动作对称性
        
        Args:
            frames: 动作序列
            servo_pairs: 对称舵机对
            
        Returns:
            优化后的动作序列
        """
        optimized = []
        
        for frame in frames:
            new_frame = frame.copy()
            
            for servo1, servo2 in servo_pairs.items():
                if servo1 in frame and servo2 in frame:
                    # 计算对称角度
                    angle1 = frame[servo1]
                    angle2 = frame[servo2]
                    avg_angle = (angle1 + angle2) / 2
                    
                    # 调整到对称位置
                    new_frame[servo1] = avg_angle
                    new_frame[servo2] = avg_angle
                    
            optimized.append(new_frame)
            
        return optimized
        
    def optimize_continuity(self, frames: List[Dict],
                           max_gap: float = 10.0) -> List[Dict]:
        """优化动作连续性
        
        Args:
            frames: 动作序列
            max_gap: 最大角度间隔
            
        Returns:
            优化后的动作序列
        """
        optimized = []
        
        for i in range(len(frames)):
            frame = frames[i].copy()
            
            if i > 0:
                prev_frame = optimized[-1]
                
                for servo_id in frame:
                    if servo_id == 'delay':
                        continue
                        
                    if servo_id in prev_frame:
                        gap = abs(frame[servo_id] - prev_frame[servo_id])
                        if gap > max_gap:
                            # 插入过渡帧
                            steps = int(np.ceil(gap / max_gap))
                            for j in range(1, steps):
                                t = j / steps
                                transition_frame = prev_frame.copy()
                                transition_frame[servo_id] = prev_frame[servo_id] + \
                                    t * (frame[servo_id] - prev_frame[servo_id])
                                transition_frame['delay'] = frame.get('delay', 0.02) / steps
                                optimized.append(transition_frame)
                                
            optimized.append(frame)
            
        return optimized
        
    def optimize_complexity(self, frames: List[Dict],
                           threshold: float = 5.0) -> List[Dict]:
        """优化动作复杂度
        
        Args:
            frames: 动作序列
            threshold: 变化阈值
            
        Returns:
            优化后的动作序列
        """
        optimized = []
        directions = {}
        
        for i in range(len(frames)):
            frame = frames[i].copy()
            
            if i > 0:
                prev_frame = optimized[-1]
                
                for servo_id in frame:
                    if servo_id == 'delay':
                        continue
                        
                    if servo_id in prev_frame:
                        change = frame[servo_id] - prev_frame[servo_id]
                        curr_dir = np.sign(change)
                        
                        # 检查方向变化
                        if servo_id in directions:
                            if curr_dir != directions[servo_id] and \
                               abs(change) < threshold:
                                # 保持原方向
                                frame[servo_id] = prev_frame[servo_id]
                                curr_dir = directions[servo_id]
                                
                        directions[servo_id] = curr_dir
                        
            optimized.append(frame)
            
        return optimized
        
    def optimize_all(self, frames: List[Dict],
                    config: Dict = None) -> List[Dict]:
        """应用所有优化
        
        Args:
            frames: 动作序列
            config: 优化配置
            
        Returns:
            优化后的动作序列
        """
        if config is None:
            config = {
                'max_power': 100.0,
                'servo_pairs': {},
                'max_gap': 10.0,
                'complexity_threshold': 5.0,
                'smoothing_factor': 0.1
            }
            
        # 应用各种优化
        optimized = frames
        optimized = self.optimize_energy(optimized, config['max_power'])
        optimized = self.optimize_symmetry(optimized, config['servo_pairs'])
        optimized = self.optimize_continuity(optimized, config['max_gap'])
        optimized = self.optimize_complexity(optimized, config['complexity_threshold'])
        optimized = self.optimize_trajectory(optimized, config['smoothing_factor'])
        
        return optimized 