from typing import Dict, List, Optional
import yaml
import os
import logging
from datetime import datetime
from ..config.version_manager import ConfigVersionManager

class ActionVersionManager:
    def __init__(self, base_dir: str = 'action_versions',
                 logger: logging.Logger = None):
        """动作组版本管理器"""
        self.version_manager = ConfigVersionManager(
            base_dir=base_dir,
            logger=logger
        )
        self.logger = logger
        
    def save_action_group(self, name: str, frames: List[Dict],
                         version_name: str = None,
                         comment: str = None) -> str:
        """保存动作组版本"""
        action_data = {
            'name': name,
            'frames': frames,
            'metadata': {
                'frame_count': len(frames),
                'servo_ids': self._get_servo_ids(frames),
                'total_duration': self._calculate_duration(frames)
            }
        }
        
        return self.version_manager.save_version(
            action_data,
            version_name=version_name,
            comment=comment
        )
        
    def load_action_group(self, version_id: str) -> Optional[Dict]:
        """加载动作组版本"""
        return self.version_manager.load_version(version_id)
        
    def _get_servo_ids(self, frames: List[Dict]) -> List[str]:
        """获取所有舵机ID"""
        servo_ids = set()
        for frame in frames:
            for servo_id in frame:
                if servo_id != 'delay':
                    servo_ids.add(servo_id)
        return sorted(list(servo_ids))
        
    def _calculate_duration(self, frames: List[Dict]) -> float:
        """计算总时长"""
        return sum(frame.get('delay', 0) for frame in frames) 