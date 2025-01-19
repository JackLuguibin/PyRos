import yaml
import os

class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = {}
        
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                
    def get_servo_config(self) -> dict:
        """获取舵机配置"""
        return self.config.get('servos', {})
        
    def get_sensor_config(self) -> dict:
        """获取传感器配置"""
        return self.config.get('sensors', {}) 