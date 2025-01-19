from typing import List, Dict, Optional
import numpy as np
import logging

class ActionComposer:
    def __init__(self, logger: logging.Logger = None):
        """动作组合成器"""
        self.logger = logger
        
    def merge_actions(self, action1: List[Dict], action2: List[Dict],
                     blend_frames: int = 5) -> List[Dict]:
        """合并两个动作序列，并在连接处进行平滑过渡
        
        Args:
            action1: 第一个动作序列
            action2: 第二个动作序列
            blend_frames: 过渡帧数
            
        Returns:
            合并后的动作序列
        """
        if not action1 or not action2:
            return action1 or action2
            
        # 获取所有舵机ID
        servo_ids = set()
        for frame in action1 + action2:
            servo_ids.update(k for k in frame.keys() if k != 'delay')
            
        # 创建过渡帧
        transition = []
        start_angles = {
            servo_id: action1[-1].get(servo_id, action2[0].get(servo_id, 0))
            for servo_id in servo_ids
        }
        end_angles = {
            servo_id: action2[0].get(servo_id, action1[-1].get(servo_id, 0))
            for servo_id in servo_ids
        }
        
        for i in range(blend_frames):
            t = i / (blend_frames - 1)
            frame = {}
            
            for servo_id in servo_ids:
                # 使用余弦插值实现平滑过渡
                frame[servo_id] = start_angles[servo_id] + \
                    (end_angles[servo_id] - start_angles[servo_id]) * \
                    (1 - np.cos(t * np.pi)) / 2
                    
            frame['delay'] = action1[-1].get('delay', 0.02)
            transition.append(frame)
            
        # 合并序列
        return action1[:-1] + transition + action2[1:]
        
    def extract_subsequence(self, frames: List[Dict],
                          start_idx: int, end_idx: int,
                          servo_ids: Optional[List[str]] = None) -> List[Dict]:
        """提取动作子序列
        
        Args:
            frames: 原动作序列
            start_idx: 起始帧索引
            end_idx: 结束帧索引
            servo_ids: 要提取的舵机ID列表，None表示所有舵机
            
        Returns:
            提取的子序列
        """
        if not frames or start_idx < 0 or end_idx >= len(frames):
            return []
            
        subsequence = []
        for i in range(start_idx, end_idx + 1):
            frame = {}
            
            for servo_id, angle in frames[i].items():
                if servo_id == 'delay' or \
                   (servo_ids is None or servo_id in servo_ids):
                    frame[servo_id] = angle
                    
            subsequence.append(frame)
            
        return subsequence
        
    def mirror_action(self, frames: List[Dict],
                     servo_pairs: Dict[str, str]) -> List[Dict]:
        """镜像动作序列
        
        Args:
            frames: 原动作序列
            servo_pairs: 对称舵机ID映射，如 {'left_arm': 'right_arm'}
            
        Returns:
            镜像后的动作序列
        """
        mirrored = []
        
        for frame in frames:
            new_frame = {'delay': frame.get('delay', 0.02)}
            
            # 处理配对舵机
            for servo1, servo2 in servo_pairs.items():
                if servo1 in frame:
                    new_frame[servo2] = frame[servo1]
                if servo2 in frame:
                    new_frame[servo1] = frame[servo2]
                    
            # 处理未配对舵机
            for servo_id, angle in frame.items():
                if servo_id not in servo_pairs and \
                   servo_id not in servo_pairs.values() and \
                   servo_id != 'delay':
                    new_frame[servo_id] = angle
                    
            mirrored.append(new_frame)
            
        return mirrored
        
    def scale_timing(self, frames: List[Dict],
                    scale_factor: float) -> List[Dict]:
        """缩放动作时序
        
        Args:
            frames: 动作序列
            scale_factor: 时间缩放因子，>1 变慢，<1 变快
            
        Returns:
            缩放后的动作序列
        """
        if scale_factor <= 0:
            raise ValueError("缩放因子必须大于0")
            
        scaled = []
        for frame in frames:
            new_frame = frame.copy()
            if 'delay' in new_frame:
                new_frame['delay'] = new_frame['delay'] * scale_factor
            scaled.append(new_frame)
            
        return scaled
        
    def reverse_action(self, frames: List[Dict]) -> List[Dict]:
        """反转动作序列"""
        reversed_frames = []
        
        for i in range(len(frames) - 1, -1, -1):
            frame = frames[i].copy()
            
            # 使用前一帧的延时
            if i > 0:
                frame['delay'] = frames[i-1].get('delay', 0.02)
            
            reversed_frames.append(frame)
            
        return reversed_frames 