from typing import Dict, List
from ..servos.servo_manager import ServoManager
import time

class ActionGroup:
    def __init__(self, name: str, actions: List[dict]):
        self.name = name
        self.actions = actions

class ActionGroupManager:
    def __init__(self):
        self.action_groups: Dict[str, ActionGroup] = {}
        self.servo_manager = None
        
    def initialize(self, servo_manager: ServoManager):
        """初始化动作组管理器"""
        self.servo_manager = servo_manager
        
    def register_action_group(self, group_name: str, actions: List[dict]):
        """注册新的动作组"""
        self.action_groups[group_name] = ActionGroup(group_name, actions)
        
    def execute_action_group(self, group_name: str):
        """执行动作组"""
        if group_name in self.action_groups:
            group = self.action_groups[group_name]
            for action in group.actions:
                servo_id = action['servo_id']
                angle = action['angle']
                delay = action.get('delay', 0)
                self.servo_manager.set_angle(servo_id, angle)
                if delay > 0:
                    time.sleep(delay) 