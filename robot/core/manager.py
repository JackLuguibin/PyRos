from typing import Dict, List
from ..servos.servo_manager import ServoManager
from ..sensors.sensor_manager import SensorManager
from ..actions.action_manager import ActionGroupManager
from ..config.config_manager import ConfigManager
from ..utils.logger import RobotLogger
import logging

class RobotManager:
    def __init__(self):
        # 初始化日志系统
        self.logger_manager = RobotLogger()
        self.logger = self.logger_manager.get_logger()
        
        # 初始化其他管理器
        self.config_manager = ConfigManager()
        self.servo_manager = ServoManager(self.logger)
        self.sensor_manager = SensorManager(self.logger)
        self.action_manager = ActionGroupManager(self.logger)
        
        self.logger.info("机器人管理器已创建")
        
    def initialize(self):
        """初始化所有管理器"""
        try:
            self.logger.info("开始初始化系统...")
            self.config_manager.load_config()
            self.servo_manager.initialize(self.config_manager.get_servo_config())
            self.sensor_manager.initialize(self.config_manager.get_sensor_config())
            self.action_manager.initialize(self.servo_manager)
            self.logger.info("系统初始化完成")
        except Exception as e:
            self.logger.error(f"系统初始化失败: {e}")
            raise
        
    def shutdown(self):
        """关闭系统"""
        try:
            self.logger.info("开始关闭系统...")
            self.servo_manager.shutdown()
            self.sensor_manager.shutdown()
            self.logger.info("系统已关闭")
        except Exception as e:
            self.logger.error(f"系统关闭出错: {e}")
            raise 