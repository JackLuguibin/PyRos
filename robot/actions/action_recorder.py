import time
from typing import List, Dict
import yaml
import os
from ..servos.servo_manager import ServoManager
import logging

class ActionRecorder:
    def __init__(self, servo_manager: ServoManager, logger: logging.Logger):
        self.servo_manager = servo_manager
        self.logger = logger
        self.recording = False
        self.actions: List[Dict] = []
        self.start_time = 0
        
    def start_recording(self):
        """开始录制动作"""
        self.recording = True
        self.actions = []
        self.start_time = time.time()
        self.logger.info("开始录制动作")
        
    def stop_recording(self) -> List[Dict]:
        """停止录制动作"""
        self.recording = False
        self.logger.info(f"动作录制完成，共 {len(self.actions)} 个动作")
        return self.actions
        
    def record_action(self, servo_id: str, angle: float):
        """记录一个动作"""
        if self.recording:
            current_time = time.time()
            delay = current_time - self.start_time
            self.start_time = current_time
            
            action = {
                'servo_id': servo_id,
                'angle': angle,
                'delay': round(delay, 3)
            }
            self.actions.append(action)
            self.logger.debug(f"记录动作: {action}")
            
    def save_action_group(self, group_name: str, actions: List[Dict], file_path: str = "actions"):
        """保存动作组到文件"""
        try:
            os.makedirs(file_path, exist_ok=True)
            file_name = os.path.join(file_path, f"{group_name}.yaml")
            
            with open(file_name, 'w') as f:
                yaml.dump({group_name: actions}, f)
                
            self.logger.info(f"动作组已保存到: {file_name}")
            return True
        except Exception as e:
            self.logger.error(f"保存动作组失败: {e}")
            return False 