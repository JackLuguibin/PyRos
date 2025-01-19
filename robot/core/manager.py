from typing import Dict, List
from ..servos.servo_manager import ServoManager
from ..sensors.sensor_manager import SensorManager
from ..actions.action_manager import ActionGroupManager
from ..config.config_manager import ConfigManager

class RobotManager:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.servo_manager = ServoManager()
        self.sensor_manager = SensorManager()
        self.action_manager = ActionGroupManager()
        
    def initialize(self):
        """初始化所有管理器"""
        self.config_manager.load_config()
        self.servo_manager.initialize(self.config_manager.get_servo_config())
        self.sensor_manager.initialize(self.config_manager.get_sensor_config())
        self.action_manager.initialize(self.servo_manager)
        
    def shutdown(self):
        """关闭系统"""
        self.servo_manager.shutdown()
        self.sensor_manager.shutdown() 