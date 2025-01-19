from typing import Dict
from .sensor_base import SensorBase

class SensorManager:
    def __init__(self):
        self.sensors: Dict[str, SensorBase] = {}
        
    def initialize(self, sensor_config: dict):
        """初始化所有传感器"""
        for sensor_id, config in sensor_config.items():
            sensor_type = config['type']
            sensor = self._create_sensor(sensor_type, config)
            self.sensors[sensor_id] = sensor
            
    def register_sensor(self, sensor_id: str, sensor: SensorBase):
        """注册新的传感器"""
        self.sensors[sensor_id] = sensor
        
    def get_sensor_data(self, sensor_id: str):
        """获取传感器数据"""
        if sensor_id in self.sensors:
            return self.sensors[sensor_id].read()
        return None
        
    def shutdown(self):
        """关闭所有传感器"""
        for sensor in self.sensors.values():
            sensor.cleanup() 