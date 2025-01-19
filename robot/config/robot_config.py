from typing import Dict, Any, Optional, Callable, List
import yaml
import logging
import os
import shutil
from .version_manager import ConfigVersionManager

class RobotConfig:
    def __init__(self, config_file: str = None, logger: logging.Logger = None):
        self.logger = logger
        self.config: Dict = {}
        self.config_file = config_file
        
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
            
        # 初始化版本管理器
        self.version_manager = ConfigVersionManager(logger=logger)
        
    def load_config(self, config_file: str):
        """加载配置文件"""
        try:
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
                if self.logger:
                    self.logger.info(f"加载配置文件: {config_file}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"加载配置文件失败: {e}")
                
    def save_config(self, config_file: str = None):
        """保存配置"""
        file_path = config_file or self.config_file
        if not file_path:
            if self.logger:
                self.logger.error("未指定配置文件路径")
            return
            
        try:
            with open(file_path, 'w') as f:
                yaml.dump(self.config, f)
                if self.logger:
                    self.logger.info(f"保存配置到: {file_path}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"保存配置失败: {e}")
                
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set(self, key: str, value: Any):
        """设置配置项"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value 

    def merge_config(self, other_config: Dict):
        """合并配置"""
        def _merge_dict(d1: Dict, d2: Dict):
            for k, v in d2.items():
                if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                    _merge_dict(d1[k], v)
                else:
                    d1[k] = v
                
        _merge_dict(self.config, other_config)
        
    def validate_config(self, schema: Dict) -> bool:
        """验证配置是否符合模式"""
        def _validate_dict(config: Dict, schema_dict: Dict) -> bool:
            for key, schema_value in schema_dict.items():
                if key not in config:
                    if self.logger:
                        self.logger.error(f"缺少必需的配置项: {key}")
                    return False
                    
                if isinstance(schema_value, dict):
                    if not isinstance(config[key], dict):
                        if self.logger:
                            self.logger.error(f"配置项类型错误: {key}")
                        return False
                    if not _validate_dict(config[key], schema_value):
                        return False
                else:
                    if not isinstance(config[key], schema_value):
                        if self.logger:
                            self.logger.error(
                                f"配置项类型错误: {key}, 期望 {schema_value}, "
                                f"实际 {type(config[key])}")
                        return False
                        
            return True
            
        return _validate_dict(self.config, schema)
        
    def watch_config(self, key: str, callback: Callable[[Any], None]):
        """监听配置变化"""
        if not hasattr(self, '_watchers'):
            self._watchers = {}
            
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)
        
    def _notify_watchers(self, key: str, value: Any):
        """通知配置变化"""
        if hasattr(self, '_watchers') and key in self._watchers:
            for callback in self._watchers[key]:
                try:
                    callback(value)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"配置变化回调执行失败: {e}")
                        
    def export_config(self, format: str = 'yaml') -> str:
        """导出配置"""
        if format == 'yaml':
            return yaml.dump(self.config)
        elif format == 'json':
            import json
            return json.dumps(self.config, indent=2)
        else:
            raise ValueError(f"不支持的导出格式: {format}") 

    def save_version(self, version_name: str = None, comment: str = None) -> str:
        """保存当前配置为新版本"""
        return self.version_manager.save_version(
            self.config,
            version_name=version_name,
            comment=comment
        )
        
    def load_version(self, version_id: str) -> bool:
        """加载指定版本的配置"""
        config = self.version_manager.load_version(version_id)
        if config:
            self.config = config
            return True
        return False
        
    def list_versions(self) -> List[Dict]:
        """列出所有配置版本"""
        return self.version_manager.list_versions()
        
    def compare_with_version(self, version_id: str) -> Dict:
        """比较当前配置与指定版本的差异"""
        # 保存当前配置为临时版本
        current_version = self.version_manager.save_version(
            self.config,
            version_name='temp_current',
            comment='Temporary version for comparison'
        )
        
        # 比较差异
        differences = self.version_manager.compare_versions(
            current_version,
            version_id
        )
        
        # 清理临时版本
        temp_dir = os.path.join(self.version_manager.base_dir, current_version)
        shutil.rmtree(temp_dir)
        
        return differences
        
    def rollback(self, version_id: str) -> bool:
        """回滚到指定版本"""
        config = self.version_manager.rollback(version_id)
        if config:
            self.config = config
            return True
        return False