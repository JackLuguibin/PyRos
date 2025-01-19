from typing import Dict, List, Optional
import yaml
import os
import shutil
import time
import logging
from datetime import datetime

class ConfigVersionManager:
    def __init__(self, base_dir: str = 'config_versions',
                 max_versions: int = 10,
                 logger: logging.Logger = None):
        """初始化配置版本管理器
        
        Args:
            base_dir: 版本存储目录
            max_versions: 最大保存版本数
            logger: 日志记录器
        """
        self.base_dir = base_dir
        self.max_versions = max_versions
        self.logger = logger
        
        # 创建版本存储目录
        os.makedirs(base_dir, exist_ok=True)
        
    def save_version(self, config: Dict, version_name: str = None,
                    comment: str = None) -> str:
        """保存配置版本
        
        Args:
            config: 配置数据
            version_name: 版本名称，默认使用时间戳
            comment: 版本说明
            
        Returns:
            版本ID
        """
        # 生成版本ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        version_id = version_name or f"v_{timestamp}"
        
        # 创建版本目录
        version_dir = os.path.join(self.base_dir, version_id)
        os.makedirs(version_dir, exist_ok=True)
        
        try:
            # 保存配置文件
            config_path = os.path.join(version_dir, 'config.yaml')
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
                
            # 保存版本信息
            info = {
                'version_id': version_id,
                'timestamp': timestamp,
                'comment': comment,
                'created_at': datetime.now().isoformat()
            }
            
            info_path = os.path.join(version_dir, 'info.yaml')
            with open(info_path, 'w') as f:
                yaml.dump(info, f)
                
            if self.logger:
                self.logger.info(f"保存配置版本: {version_id}")
                
            # 清理旧版本
            self._cleanup_old_versions()
            
            return version_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"保存版本失败: {e}")
            raise
            
    def load_version(self, version_id: str) -> Optional[Dict]:
        """加载指定版本的配置"""
        config_path = os.path.join(self.base_dir, version_id, 'config.yaml')
        
        if not os.path.exists(config_path):
            if self.logger:
                self.logger.error(f"版本不存在: {version_id}")
            return None
            
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if self.logger:
                self.logger.info(f"加载配置版本: {version_id}")
                
            return config
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"加载版本失败: {e}")
            return None
            
    def get_version_info(self, version_id: str) -> Optional[Dict]:
        """获取版本信息"""
        info_path = os.path.join(self.base_dir, version_id, 'info.yaml')
        
        if not os.path.exists(info_path):
            return None
            
        try:
            with open(info_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception:
            return None
            
    def list_versions(self) -> List[Dict]:
        """列出所有版本"""
        versions = []
        
        for version_id in os.listdir(self.base_dir):
            info = self.get_version_info(version_id)
            if info:
                versions.append(info)
                
        # 按时间戳排序
        return sorted(versions, key=lambda x: x['timestamp'], reverse=True)
        
    def compare_versions(self, version1: str, version2: str) -> Dict:
        """比较两个版本的差异"""
        config1 = self.load_version(version1)
        config2 = self.load_version(version2)
        
        if not config1 or not config2:
            return {}
            
        def _compare_dict(d1: Dict, d2: Dict, path: str = '') -> Dict:
            differences = {}
            
            # 检查所有键
            all_keys = set(d1.keys()) | set(d2.keys())
            
            for key in all_keys:
                current_path = f"{path}.{key}" if path else key
                
                # 键只在其中一个字典中存在
                if key not in d1:
                    differences[current_path] = {'type': 'added', 'value': d2[key]}
                elif key not in d2:
                    differences[current_path] = {'type': 'removed', 'value': d1[key]}
                # 两个都是字典，递归比较
                elif isinstance(d1[key], dict) and isinstance(d2[key], dict):
                    nested_diff = _compare_dict(d1[key], d2[key], current_path)
                    differences.update(nested_diff)
                # 值不同
                elif d1[key] != d2[key]:
                    differences[current_path] = {
                        'type': 'modified',
                        'old_value': d1[key],
                        'new_value': d2[key]
                    }
                    
            return differences
            
        return _compare_dict(config1, config2)
        
    def rollback(self, version_id: str) -> Optional[Dict]:
        """回滚到指定版本"""
        config = self.load_version(version_id)
        if config:
            # 保存当前配置作为新版本
            self.save_version(config, comment=f"Rollback to {version_id}")
        return config
        
    def _cleanup_old_versions(self):
        """清理旧版本"""
        versions = self.list_versions()
        
        if len(versions) > self.max_versions:
            # 删除最旧的版本
            for version in versions[self.max_versions:]:
                version_dir = os.path.join(self.base_dir, version['version_id'])
                try:
                    shutil.rmtree(version_dir)
                    if self.logger:
                        self.logger.info(f"删除旧版本: {version['version_id']}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"删除版本失败: {e}")