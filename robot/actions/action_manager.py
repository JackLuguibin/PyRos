from typing import Dict, List
from ..servos.servo_manager import ServoManager
import time
import logging

class ActionGroup:
    def __init__(self, name: str, actions: List[dict]):
        self.name = name
        self.actions = actions

class ActionGroupManager:
    def __init__(self, logger: logging.Logger):
        self.action_groups: Dict[str, ActionGroup] = {}
        self.servo_manager = None
        self.logger = logger
        
    def initialize(self, servo_manager: ServoManager):
        """初始化动作组管理器"""
        self.servo_manager = servo_manager
        
    def load_action_groups(self, config: dict):
        """从配置加载动作组"""
        try:
            action_groups = config.get('action_groups', {})
            for group_name, actions in action_groups.items():
                self.register_action_group(group_name, actions)
                self.logger.info(f"已加载动作组: {group_name}")
        except Exception as e:
            self.logger.error(f"加载动作组失败: {e}")
            raise
        
    def register_action_group(self, group_name: str, actions: List[dict]):
        """注册新的动作组"""
        self.action_groups[group_name] = ActionGroup(group_name, actions)
        self.logger.debug(f"注册动作组: {group_name}")
        
    def execute_action_group(self, group_name: str):
        """执行动作组"""
        if group_name in self.action_groups:
            group = self.action_groups[group_name]
            self.logger.info(f"开始执行动作组: {group_name}")
            try:
                for action in group.actions:
                    servo_id = action['servo_id']
                    angle = action['angle']
                    delay = action.get('delay', 0)
                    self.servo_manager.set_angle(servo_id, angle)
                    if delay > 0:
                        time.sleep(delay)
                self.logger.info(f"动作组 {group_name} 执行完成")
            except Exception as e:
                self.logger.error(f"执行动作组 {group_name} 失败: {e}")
                raise 