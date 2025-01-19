from typing import List, Dict, Optional, Tuple
import numpy as np
import logging

class ActionValidator:
    def __init__(self, logger: logging.Logger = None):
        """动作验证器"""
        self.logger = logger
        self.joint_limits: Dict[str, Tuple[float, float]] = {}
        self.max_velocity = 300.0  # 度/秒
        self.max_acceleration = 200.0  # 度/秒²
        
    def set_joint_limits(self, limits: Dict[str, Tuple[float, float]]):
        """设置关节限位"""
        self.joint_limits = limits
        
    def validate_sequence(self, frames: List[Dict]) -> List[Dict]:
        """验证完整的动作序列
        
        Returns:
            验证问题列表
        """
        issues = []
        
        # 验证角度限位
        angle_issues = self._check_angle_limits(frames)
        if angle_issues:
            issues.extend(angle_issues)
            
        # 验证速度限制
        velocity_issues = self._check_velocity_limits(frames)
        if velocity_issues:
            issues.extend(velocity_issues)
            
        # 验证加速度限制
        accel_issues = self._check_acceleration_limits(frames)
        if accel_issues:
            issues.extend(accel_issues)
            
        # 验证时序合理性
        timing_issues = self._check_timing(frames)
        if timing_issues:
            issues.extend(timing_issues)
            
        return issues
        
    def _check_angle_limits(self, frames: List[Dict]) -> List[Dict]:
        """检查角度限位"""
        issues = []
        
        for i, frame in enumerate(frames):
            frame_issues = {}
            
            for servo_id, angle in frame.items():
                if servo_id == 'delay':
                    continue
                    
                if servo_id in self.joint_limits:
                    min_angle, max_angle = self.joint_limits[servo_id]
                    if angle < min_angle or angle > max_angle:
                        frame_issues[servo_id] = {
                            'type': 'angle_limit',
                            'value': angle,
                            'limit': (min_angle, max_angle)
                        }
                        
            if frame_issues:
                issues.append({
                    'frame_index': i,
                    'issues': frame_issues
                })
                
        return issues
        
    def _check_velocity_limits(self, frames: List[Dict]) -> List[Dict]:
        """检查速度限制"""
        issues = []
        
        for i in range(1, len(frames)):
            frame_issues = {}
            dt = frames[i-1].get('delay', 0.02)
            
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                if servo_id in frames[i-1]:
                    velocity = abs(frames[i][servo_id] - 
                                 frames[i-1][servo_id]) / dt
                    
                    if velocity > self.max_velocity:
                        frame_issues[servo_id] = {
                            'type': 'velocity_limit',
                            'value': velocity,
                            'limit': self.max_velocity
                        }
                        
            if frame_issues:
                issues.append({
                    'frame_index': i,
                    'issues': frame_issues
                })
                
        return issues
        
    def _check_acceleration_limits(self, frames: List[Dict]) -> List[Dict]:
        """检查加速度限制"""
        issues = []
        
        for i in range(2, len(frames)):
            frame_issues = {}
            dt = frames[i-1].get('delay', 0.02)
            
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                if servo_id in frames[i-1] and servo_id in frames[i-2]:
                    accel = abs(frames[i][servo_id] - 2*frames[i-1][servo_id] +
                              frames[i-2][servo_id]) / (dt * dt)
                    
                    if accel > self.max_acceleration:
                        frame_issues[servo_id] = {
                            'type': 'acceleration_limit',
                            'value': accel,
                            'limit': self.max_acceleration
                        }
                        
            if frame_issues:
                issues.append({
                    'frame_index': i,
                    'issues': frame_issues
                })
                
        return issues
        
    def _check_timing(self, frames: List[Dict]) -> List[Dict]:
        """检查时序合理性"""
        issues = []
        
        for i, frame in enumerate(frames):
            frame_issues = {}
            
            # 检查延时是否合理
            if 'delay' in frame:
                delay = frame['delay']
                if delay < 0.01:  # 最小延时
                    frame_issues['delay'] = {
                        'type': 'timing_too_short',
                        'value': delay,
                        'limit': 0.01
                    }
                elif delay > 5.0:  # 最大延时
                    frame_issues['delay'] = {
                        'type': 'timing_too_long',
                        'value': delay,
                        'limit': 5.0
                    }
                    
            if frame_issues:
                issues.append({
                    'frame_index': i,
                    'issues': frame_issues
                })
                
        return issues
        
    def validate_continuity(self, frames: List[Dict],
                           max_gap: float = 10.0) -> List[Dict]:
        """验证动作连续性
        
        Args:
            frames: 动作序列
            max_gap: 最大允许的角度间隔
            
        Returns:
            连续性问题列表
        """
        issues = []
        
        for i in range(1, len(frames)):
            frame_issues = {}
            
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                if servo_id in frames[i-1]:
                    gap = abs(frames[i][servo_id] - frames[i-1][servo_id])
                    if gap > max_gap:
                        frame_issues[servo_id] = {
                            'type': 'continuity_gap',
                            'value': gap,
                            'limit': max_gap
                        }
                        
            if frame_issues:
                issues.append({
                    'frame_index': i,
                    'issues': frame_issues
                })
                
        return issues
        
    def validate_symmetry(self, frames: List[Dict],
                         servo_pairs: Dict[str, str],
                         max_diff: float = 5.0) -> List[Dict]:
        """验证动作对称性
        
        Args:
            frames: 动作序列
            servo_pairs: 对称舵机对，如 {'left_arm': 'right_arm'}
            max_diff: 最大允许的不对称差异
            
        Returns:
            对称性问题列表
        """
        issues = []
        
        for i, frame in enumerate(frames):
            frame_issues = {}
            
            for servo1, servo2 in servo_pairs.items():
                if servo1 in frame and servo2 in frame:
                    # 计算对称差异
                    diff = abs(frame[servo1] - frame[servo2])
                    if diff > max_diff:
                        frame_issues[f"{servo1}_{servo2}"] = {
                            'type': 'symmetry_violation',
                            'value': diff,
                            'limit': max_diff
                        }
                        
            if frame_issues:
                issues.append({
                    'frame_index': i,
                    'issues': frame_issues
                })
                
        return issues
        
    def validate_energy(self, frames: List[Dict],
                       max_power: float = 100.0) -> List[Dict]:
        """验证动作能量消耗
        
        Args:
            frames: 动作序列
            max_power: 最大允许功率（单位：瓦特）
            
        Returns:
            能量问题列表
        """
        issues = []
        
        for i in range(1, len(frames)):
            frame_issues = {}
            dt = frames[i-1].get('delay', 0.02)
            
            total_power = 0
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                if servo_id in frames[i-1]:
                    # 计算角速度
                    velocity = abs(frames[i][servo_id] - 
                                 frames[i-1][servo_id]) / dt
                    # 简化的功率模型
                    power = velocity * velocity * 0.1  # 假设系数
                    total_power += power
                    
            if total_power > max_power:
                frame_issues['total'] = {
                    'type': 'power_limit',
                    'value': total_power,
                    'limit': max_power
                }
                
            if frame_issues:
                issues.append({
                    'frame_index': i,
                    'issues': frame_issues
                })
                
        return issues
        
    def suggest_improvements(self, frames: List[Dict]) -> List[Dict]:
        """提供动作改进建议
        
        Returns:
            改进建议列表
        """
        suggestions = []
        
        # 检查速度分布
        velocities = self._analyze_velocities(frames)
        if velocities['std'] > velocities['mean'] * 0.5:
            suggestions.append({
                'type': 'velocity_distribution',
                'message': '速度分布不均匀，建议平滑加速度',
                'data': velocities
            })
            
        # 检查能量效率
        energy = self._analyze_energy(frames)
        if energy['peaks'] > len(frames) * 0.1:
            suggestions.append({
                'type': 'energy_efficiency',
                'message': '存在能量峰值过多，建议优化动作',
                'data': energy
            })
            
        # 检查动作复杂度
        complexity = self._analyze_complexity(frames)
        if complexity['changes'] > len(frames) * 0.3:
            suggestions.append({
                'type': 'motion_complexity',
                'message': '动作变化过于频繁，建议简化',
                'data': complexity
            })
            
        return suggestions
        
    def _analyze_velocities(self, frames: List[Dict]) -> Dict:
        """分析速度分布"""
        velocities = []
        
        for i in range(1, len(frames)):
            dt = frames[i-1].get('delay', 0.02)
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                if servo_id in frames[i-1]:
                    velocity = abs(frames[i][servo_id] - 
                                 frames[i-1][servo_id]) / dt
                    velocities.append(velocity)
                    
        return {
            'mean': np.mean(velocities),
            'std': np.std(velocities),
            'max': max(velocities),
            'distribution': np.histogram(velocities)[0].tolist()
        }
        
    def _analyze_energy(self, frames: List[Dict]) -> Dict:
        """分析能量消耗"""
        energy_peaks = 0
        total_energy = 0
        
        for i in range(1, len(frames)):
            dt = frames[i-1].get('delay', 0.02)
            frame_energy = 0
            
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                if servo_id in frames[i-1]:
                    velocity = abs(frames[i][servo_id] - 
                                 frames[i-1][servo_id]) / dt
                    energy = velocity * velocity * dt
                    frame_energy += energy
                    
            total_energy += frame_energy
            if frame_energy > total_energy / len(frames) * 2:
                energy_peaks += 1
                
        return {
            'total': total_energy,
            'peaks': energy_peaks,
            'average': total_energy / len(frames)
        }
        
    def _analyze_complexity(self, frames: List[Dict]) -> Dict:
        """分析动作复杂度"""
        changes = 0
        directions = {}
        
        for i in range(1, len(frames)):
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                if servo_id in frames[i-1]:
                    curr_dir = np.sign(frames[i][servo_id] - 
                                     frames[i-1][servo_id])
                    if servo_id in directions:
                        if curr_dir != directions[servo_id]:
                            changes += 1
                    directions[servo_id] = curr_dir
                    
        return {
            'changes': changes,
            'change_rate': changes / len(frames)
        } 