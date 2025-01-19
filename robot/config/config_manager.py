from typing import Dict, Any, Optional
import yaml
import json
import os
import logging
from dataclasses import dataclass

@dataclass
class RobotConfig:
    """机器人配置"""
    # 网络配置
    network: Dict = None
    # 运动学配置
    kinematics: Dict = None
    # 动力学配置
    dynamics: Dict = None
    # 控制器配置
    controller: Dict = None
    # 传感器配置
    sensors: Dict = None
    # 执行器配置
    actuators: Dict = None
    # 日志配置
    logging: Dict = None

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('ConfigManager')
        self.config_path = config_path or 'config/robot_config.yaml'
        self.config = RobotConfig()
        
    def load_config(self) -> bool:
        """加载配置"""
        try:
            # 检查文件是否存在
            if not os.path.exists(self.config_path):
                self.logger.error(f"配置文件不存在: {self.config_path}")
                return False
                
            # 读取配置文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.endswith('.yaml'):
                    config_data = yaml.safe_load(f)
                elif self.config_path.endswith('.json'):
                    config_data = json.load(f)
                else:
                    self.logger.error("不支持的配置文件格式")
                    return False
                    
            # 更新配置
            for key, value in config_data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    
            self.logger.info("配置加载完成")
            return True
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {str(e)}")
            return False
            
    def save_config(self) -> bool:
        """保存配置"""
        try:
            # 转换为字典
            config_data = {
                key: value
                for key, value in self.config.__dict__.items()
                if value is not None
            }
            
            # 保存配置文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if self.config_path.endswith('.yaml'):
                    yaml.safe_dump(config_data, f, allow_unicode=True)
                elif self.config_path.endswith('.json'):
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                    
            self.logger.info("配置保存完成")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {str(e)}")
            return False
            
    def get_config(self, section: str = None) -> Dict:
        """获取配置
        
        Args:
            section: 配置段名称
            
        Returns:
            配置字典
        """
        if section:
            return getattr(self.config, section, {}) or {}
        return self.config.__dict__
        
    def update_config(self, section: str, config: Dict) -> bool:
        """更新配置
        
        Args:
            section: 配置段名称
            config: 新的配置
            
        Returns:
            是否更新成功
        """
        try:
            if not hasattr(self.config, section):
                self.logger.error(f"配置段不存在: {section}")
                return False
                
            current = getattr(self.config, section) or {}
            current.update(config)
            setattr(self.config, section, current)
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新配置失败: {str(e)}")
            return False

    def get_servo_config(self) -> dict:
        """获取舵机配置"""
        return self.config.get('servos', {})
        
    def get_sensor_config(self) -> dict:
        """获取传感器配置"""
        return self.config.get('sensors', {}) 