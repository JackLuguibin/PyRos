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
        
    def analyze_patterns(self, frames: List[Dict]) -> Dict:
        """分析动作模式
        
        Returns:
            动作模式分析结果
        """
        patterns = {
            'repetitive': self._find_repetitive_patterns(frames),
            'synchronized': self._analyze_synchronization(frames),
            'sequential': self._analyze_sequence_patterns(frames)
        }
        return patterns
        
    def _find_repetitive_patterns(self, frames: List[Dict]) -> List[Dict]:
        """查找重复动作模式"""
        patterns = []
        min_pattern_length = 3
        max_pattern_length = len(frames) // 2
        
        for length in range(min_pattern_length, max_pattern_length + 1):
            for start in range(len(frames) - length * 2):
                pattern = frames[start:start + length]
                next_segment = frames[start + length:start + length * 2]
                
                if self._is_similar_sequence(pattern, next_segment):
                    patterns.append({
                        'start_index': start,
                        'length': length,
                        'repetitions': self._count_repetitions(frames, pattern, start)
                    })
                    
        return patterns
        
    def _is_similar_sequence(self, seq1: List[Dict],
                            seq2: List[Dict],
                            threshold: float = 5.0) -> bool:
        """判断两个序列是否相似"""
        if len(seq1) != len(seq2):
            return False
            
        for f1, f2 in zip(seq1, seq2):
            for servo_id in f1:
                if servo_id == 'delay':
                    continue
                if servo_id not in f2:
                    return False
                if abs(f1[servo_id] - f2[servo_id]) > threshold:
                    return False
                    
        return True
        
    def _count_repetitions(self, frames: List[Dict],
                          pattern: List[Dict],
                          start: int) -> int:
        """计算模式重复次数"""
        count = 0
        length = len(pattern)
        pos = start
        
        while pos + length <= len(frames):
            if self._is_similar_sequence(pattern,
                                       frames[pos:pos + length]):
                count += 1
                pos += length
            else:
                break
                
        return count
        
    def _analyze_synchronization(self, frames: List[Dict]) -> Dict:
        """分析舵机同步性"""
        sync_info = {}
        
        for i in range(1, len(frames)):
            active_servos = set()
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                if servo_id in frames[i-1]:
                    if abs(frames[i][servo_id] - frames[i-1][servo_id]) > 1.0:
                        active_servos.add(servo_id)
                        
            if len(active_servos) > 1:
                key = tuple(sorted(active_servos))
                sync_info[key] = sync_info.get(key, 0) + 1
                
        return {
            'groups': [{
                'servos': list(group),
                'count': count
            } for group, count in sync_info.items()]
        }
        
    def _analyze_sequence_patterns(self, frames: List[Dict]) -> Dict:
        """分析顺序模式"""
        sequences = []
        current_sequence = []
        
        for i in range(1, len(frames)):
            active_servos = []
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                if servo_id in frames[i-1]:
                    if abs(frames[i][servo_id] - frames[i-1][servo_id]) > 1.0:
                        active_servos.append(servo_id)
                        
            if active_servos:
                if not current_sequence or \
                   set(active_servos).isdisjoint(current_sequence[-1]):
                    current_sequence.append(active_servos)
                else:
                    if len(current_sequence) > 1:
                        sequences.append(current_sequence)
                    current_sequence = [active_servos]
                    
        return {
            'sequences': sequences,
            'count': len(sequences)
        } 