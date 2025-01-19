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