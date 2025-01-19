from typing import Dict, List
import numpy as np
import logging

class ActionCalibrator:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        self.reference_frames: Dict[str, List[Dict]] = {}
        
    def set_reference(self, action_name: str, frames: List[Dict]):
        """设置参考动作序列"""
        self.reference_frames[action_name] = frames
        
    def calibrate(self, action_name: str, frames: List[Dict],
                  max_angle_diff: float = 5.0) -> List[Dict]:
        """校准动作序列
        
        Args:
            action_name: 动作组名称
            frames: 待校准的动作序列
            max_angle_diff: 最大角度差异
            
        Returns:
            校准后的动作序列
        """
        if action_name not in self.reference_frames:
            if self.logger:
                self.logger.error(f"参考动作不存在: {action_name}")
            return frames
            
        reference = self.reference_frames[action_name]
        if len(frames) != len(reference):
            if self.logger:
                self.logger.warning(f"动作帧数不匹配: {len(frames)} vs {len(reference)}")
            return frames
            
        calibrated = []
        for frame, ref_frame in zip(frames, reference):
            # 校准每一帧
            cal_frame = {}
            for servo_id in frame:
                if servo_id not in ref_frame:
                    cal_frame[servo_id] = frame[servo_id]
                    continue
                    
                angle_diff = frame[servo_id] - ref_frame[servo_id]
                if abs(angle_diff) > max_angle_diff:
                    # 角度差异过大，进行校准
                    cal_frame[servo_id] = ref_frame[servo_id]
                    if self.logger:
                        self.logger.warning(
                            f"角度校准: {servo_id} {frame[servo_id]} -> {ref_frame[servo_id]}")
                else:
                    cal_frame[servo_id] = frame[servo_id]
                    
            # 保持原始延时
            if 'delay' in frame:
                cal_frame['delay'] = frame['delay']
                
            calibrated.append(cal_frame)
            
        return calibrated
        
    def analyze_difference(self, action_name: str, 
                          frames: List[Dict]) -> Dict[str, float]:
        """分析动作差异
        
        Returns:
            各舵机的平均角度差异
        """
        if action_name not in self.reference_frames:
            return {}
            
        reference = self.reference_frames[action_name]
        if len(frames) != len(reference):
            return {}
            
        differences = {}
        for frame, ref_frame in zip(frames, reference):
            for servo_id in frame:
                if servo_id not in ref_frame:
                    continue
                    
                diff = abs(frame[servo_id] - ref_frame[servo_id])
                if servo_id not in differences:
                    differences[servo_id] = []
                differences[servo_id].append(diff)
                
        # 计算平均差异
        return {
            servo_id: np.mean(diffs)
            for servo_id, diffs in differences.items()
        } 