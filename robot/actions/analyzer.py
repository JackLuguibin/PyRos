from typing import List, Dict, Tuple
import numpy as np
import logging
from collections import defaultdict

class ActionAnalyzer:
    def __init__(self, logger: logging.Logger = None):
        """动作组分析器"""
        self.logger = logger
        
    def analyze_complexity(self, frames: List[Dict]) -> Dict:
        """分析动作复杂度
        
        Returns:
            复杂度指标
        """
        metrics = {
            'frame_count': len(frames),
            'servo_count': len(self._get_servo_ids(frames)),
            'total_duration': sum(frame.get('delay', 0) for frame in frames),
            'angle_changes': self._analyze_angle_changes(frames),
            'timing_stats': self._analyze_timing(frames),
            'movement_stats': self._analyze_movement(frames)
        }
        
        return metrics
        
    def find_critical_points(self, frames: List[Dict],
                           threshold: float = 10.0) -> List[int]:
        """查找关键帧
        
        Args:
            frames: 动作序列
            threshold: 角度变化阈值
            
        Returns:
            关键帧索引列表
        """
        critical_points = [0]  # 第一帧总是关键帧
        
        for i in range(1, len(frames)-1):
            # 计算角度变化
            max_change = 0
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                prev_angle = frames[i-1].get(servo_id, frames[i][servo_id])
                next_angle = frames[i+1].get(servo_id, frames[i][servo_id])
                
                change = abs(next_angle - prev_angle)
                max_change = max(max_change, change)
                
            if max_change > threshold:
                critical_points.append(i)
                
        critical_points.append(len(frames)-1)  # 最后一帧也是关键帧
        return critical_points
        
    def detect_anomalies(self, frames: List[Dict],
                        velocity_threshold: float = 300.0,
                        accel_threshold: float = 200.0) -> List[Dict]:
        """检测异常
        
        Returns:
            异常列表
        """
        anomalies = []
        
        for i in range(len(frames)):
            frame_anomalies = {}
            
            # 检查速度异常
            if i > 0:
                dt = frames[i-1].get('delay', 0.02)
                for servo_id in frames[i]:
                    if servo_id == 'delay':
                        continue
                        
                    prev_angle = frames[i-1].get(servo_id, frames[i][servo_id])
                    velocity = abs(frames[i][servo_id] - prev_angle) / dt
                    
                    if velocity > velocity_threshold:
                        frame_anomalies[f"{servo_id}_velocity"] = velocity
                        
            # 检查加速度异常
            if i >= 2:
                dt = frames[i-1].get('delay', 0.02)
                for servo_id in frames[i]:
                    if servo_id == 'delay':
                        continue
                        
                    prev_angles = [
                        frames[i-2].get(servo_id, frames[i][servo_id]),
                        frames[i-1].get(servo_id, frames[i][servo_id])
                    ]
                    
                    accel = abs(frames[i][servo_id] - 2*prev_angles[1] +
                              prev_angles[0]) / (dt * dt)
                    
                    if accel > accel_threshold:
                        frame_anomalies[f"{servo_id}_acceleration"] = accel
                        
            if frame_anomalies:
                anomalies.append({
                    'frame_index': i,
                    'anomalies': frame_anomalies
                })
                
        return anomalies
        
    def _get_servo_ids(self, frames: List[Dict]) -> List[str]:
        """获取所有舵机ID"""
        servo_ids = set()
        for frame in frames:
            for servo_id in frame:
                if servo_id != 'delay':
                    servo_ids.add(servo_id)
        return sorted(list(servo_ids))
        
    def _analyze_angle_changes(self, frames: List[Dict]) -> Dict:
        """分析角度变化"""
        changes = defaultdict(list)
        
        for i in range(1, len(frames)):
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                prev_angle = frames[i-1].get(servo_id, frames[i][servo_id])
                change = abs(frames[i][servo_id] - prev_angle)
                changes[servo_id].append(change)
                
        return {
            servo_id: {
                'max': max(changes),
                'mean': np.mean(changes),
                'std': np.std(changes)
            }
            for servo_id, changes in changes.items()
        }
        
    def _analyze_timing(self, frames: List[Dict]) -> Dict:
        """分析时序"""
        delays = [frame.get('delay', 0) for frame in frames]
        return {
            'min_delay': min(delays),
            'max_delay': max(delays),
            'mean_delay': np.mean(delays),
            'std_delay': np.std(delays)
        }
        
    def _analyze_movement(self, frames: List[Dict]) -> Dict:
        """分析运动特征"""
        servo_ranges = defaultdict(lambda: {'min': float('inf'),
                                          'max': float('-inf')})
        
        for frame in frames:
            for servo_id, angle in frame.items():
                if servo_id == 'delay':
                    continue
                    
                servo_ranges[servo_id]['min'] = min(
                    servo_ranges[servo_id]['min'], angle)
                servo_ranges[servo_id]['max'] = max(
                    servo_ranges[servo_id]['max'], angle)
                
        return {
            servo_id: {
                'range': ranges['max'] - ranges['min'],
                'center': (ranges['max'] + ranges['min']) / 2
            }
            for servo_id, ranges in servo_ranges.items()
        } 