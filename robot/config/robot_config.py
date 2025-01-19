from typing import Dict, Any, Optional, List
import yaml
import json
import os
import logging
from datetime import datetime
from dataclasses import dataclass, field
from .version_manager import ConfigVersionManager

@dataclass
class ServoConfig:
    """舵机配置"""
    id: str
    min_angle: float = -90.0
    max_angle: float = 90.0
    default_speed: float = 100.0
    acceleration: float = 200.0
    inverse: bool = False
    offset: float = 0.0
    calibration: Dict[float, float] = field(default_factory=dict)

@dataclass
class ActionConfig:
    """动作配置"""
    max_velocity: float = 300.0
    min_delay: float = 0.02
    interpolation: str = 'linear'
    smoothing_factor: float = 0.1
    servo_pairs: Dict[str, str] = field(default_factory=dict)

@dataclass
class SystemConfig:
    """系统配置"""
    log_level: str = 'INFO'
    data_dir: str = 'data'
    backup_interval: int = 3600
    max_backup_count: int = 10
    enable_remote: bool = False
    remote_port: int = 8080

@dataclass
class NetworkConfig:
    """网络配置"""
    host: str = '0.0.0.0'
    port: int = 8080
    ssl_enabled: bool = False
    ssl_cert: str = ''
    ssl_key: str = ''
    max_connections: int = 10
    timeout: float = 30.0
    retry_interval: float = 5.0

@dataclass
class SecurityConfig:
    """安全配置"""
    enable_auth: bool = True
    token_expire: int = 3600
    max_attempts: int = 3
    lockout_time: int = 300
    allowed_ips: List[str] = field(default_factory=list)
    admin_users: List[str] = field(default_factory=list)

@dataclass
class PerformanceConfig:
    """性能配置"""
    max_threads: int = 4
    queue_size: int = 100
    cache_size: int = 1000
    batch_size: int = 32
    enable_gpu: bool = False
    profile_enabled: bool = False

class RobotConfig:
    def __init__(self, config_dir: str = 'config'):
        """机器人配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir
        self.logger = logging.getLogger('RobotConfig')
        self.version_manager = ConfigVersionManager(config_dir)
        
        # 创建配置目录
        os.makedirs(config_dir, exist_ok=True)
        
        # 默认配置
        self.servos: Dict[str, ServoConfig] = {}
        self.action = ActionConfig()
        self.system = SystemConfig()
        self.network = NetworkConfig()
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()
        
        # 配置模板
        self.templates = {
            'minimal': self._get_minimal_template(),
            'standard': self._get_standard_template(),
            'advanced': self._get_advanced_template()
        }
        
        # 加载配置
        self.load_config()
        
    def load_config(self, version: Optional[str] = None):
        """加载配置
        
        Args:
            version: 指定版本号，None表示最新版本
        """
        if version:
            config_data = self.version_manager.load_version(version)
        else:
            config_file = os.path.join(self.config_dir, 'config.yaml')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
            else:
                config_data = self._get_default_config()
                
        self._parse_config(config_data)
        
    def save_config(self, version_name: Optional[str] = None,
                   comment: str = ''):
        """保存配置
        
        Args:
            version_name: 版本名称
            comment: 版本说明
        """
        config_data = {
            'servos': {
                servo_id: {
                    'min_angle': servo.min_angle,
                    'max_angle': servo.max_angle,
                    'default_speed': servo.default_speed,
                    'acceleration': servo.acceleration,
                    'inverse': servo.inverse,
                    'offset': servo.offset,
                    'calibration': servo.calibration
                }
                for servo_id, servo in self.servos.items()
            },
            'action': {
                'max_velocity': self.action.max_velocity,
                'min_delay': self.action.min_delay,
                'interpolation': self.action.interpolation,
                'smoothing_factor': self.action.smoothing_factor,
                'servo_pairs': self.action.servo_pairs
            },
            'system': {
                'log_level': self.system.log_level,
                'data_dir': self.system.data_dir,
                'backup_interval': self.system.backup_interval,
                'max_backup_count': self.system.max_backup_count,
                'enable_remote': self.system.enable_remote,
                'remote_port': self.system.remote_port
            },
            'network': {
                'host': self.network.host,
                'port': self.network.port,
                'ssl_enabled': self.network.ssl_enabled,
                'ssl_cert': self.network.ssl_cert,
                'ssl_key': self.network.ssl_key,
                'max_connections': self.network.max_connections,
                'timeout': self.network.timeout,
                'retry_interval': self.network.retry_interval
            },
            'security': {
                'enable_auth': self.security.enable_auth,
                'token_expire': self.security.token_expire,
                'max_attempts': self.security.max_attempts,
                'lockout_time': self.security.lockout_time,
                'allowed_ips': self.security.allowed_ips,
                'admin_users': self.security.admin_users
            },
            'performance': {
                'max_threads': self.performance.max_threads,
                'queue_size': self.performance.queue_size,
                'cache_size': self.performance.cache_size,
                'batch_size': self.performance.batch_size,
                'enable_gpu': self.performance.enable_gpu,
                'profile_enabled': self.performance.profile_enabled
            }
        }
        
        # 保存当前配置
        config_file = os.path.join(self.config_dir, 'config.yaml')
        with open(config_file, 'w') as f:
            yaml.safe_dump(config_data, f, default_flow_style=False)
            
        # 保存版本
        if version_name:
            self.version_manager.save_version(
                version_name,
                config_data,
                comment
            )
            
    def add_servo(self, servo_id: str, config: Dict[str, Any]):
        """添加舵机配置"""
        self.servos[servo_id] = ServoConfig(
            id=servo_id,
            **config
        )
        
    def remove_servo(self, servo_id: str):
        """删除舵机配置"""
        if servo_id in self.servos:
            del self.servos[servo_id]
            
    def update_servo(self, servo_id: str, 
                    updates: Dict[str, Any]):
        """更新舵机配置"""
        if servo_id in self.servos:
            servo = self.servos[servo_id]
            for key, value in updates.items():
                if hasattr(servo, key):
                    setattr(servo, key, value)
                    
    def get_servo_config(self, servo_id: str) -> Optional[ServoConfig]:
        """获取舵机配置"""
        return self.servos.get(servo_id)
        
    def update_action_config(self, updates: Dict[str, Any]):
        """更新动作配置"""
        for key, value in updates.items():
            if hasattr(self.action, key):
                setattr(self.action, key, value)
                
    def update_system_config(self, updates: Dict[str, Any]):
        """更新系统配置"""
        for key, value in updates.items():
            if hasattr(self.system, key):
                setattr(self.system, key, value)
                
    def update_network_config(self, updates: Dict[str, Any]):
        """更新网络配置"""
        for key, value in updates.items():
            if hasattr(self.network, key):
                setattr(self.network, key, value)
                
    def update_security_config(self, updates: Dict[str, Any]):
        """更新安全配置"""
        for key, value in updates.items():
            if hasattr(self.security, key):
                setattr(self.security, key, value)
                
    def update_performance_config(self, updates: Dict[str, Any]):
        """更新性能配置"""
        for key, value in updates.items():
            if hasattr(self.performance, key):
                setattr(self.performance, key, value)
                
    def export_config(self, format: str = 'yaml') -> str:
        """导出配置
        
        Args:
            format: 导出格式 ('yaml' 或 'json')
            
        Returns:
            配置字符串
        """
        config_data = {
            'servos': {
                servo_id: {
                    'min_angle': servo.min_angle,
                    'max_angle': servo.max_angle,
                    'default_speed': servo.default_speed,
                    'acceleration': servo.acceleration,
                    'inverse': servo.inverse,
                    'offset': servo.offset,
                    'calibration': servo.calibration
                }
                for servo_id, servo in self.servos.items()
            },
            'action': {
                'max_velocity': self.action.max_velocity,
                'min_delay': self.action.min_delay,
                'interpolation': self.action.interpolation,
                'smoothing_factor': self.action.smoothing_factor,
                'servo_pairs': self.action.servo_pairs
            },
            'system': {
                'log_level': self.system.log_level,
                'data_dir': self.system.data_dir,
                'backup_interval': self.system.backup_interval,
                'max_backup_count': self.system.max_backup_count,
                'enable_remote': self.system.enable_remote,
                'remote_port': self.system.remote_port
            },
            'network': {
                'host': self.network.host,
                'port': self.network.port,
                'ssl_enabled': self.network.ssl_enabled,
                'ssl_cert': self.network.ssl_cert,
                'ssl_key': self.network.ssl_key,
                'max_connections': self.network.max_connections,
                'timeout': self.network.timeout,
                'retry_interval': self.network.retry_interval
            },
            'security': {
                'enable_auth': self.security.enable_auth,
                'token_expire': self.security.token_expire,
                'max_attempts': self.security.max_attempts,
                'lockout_time': self.security.lockout_time,
                'allowed_ips': self.security.allowed_ips,
                'admin_users': self.security.admin_users
            },
            'performance': {
                'max_threads': self.performance.max_threads,
                'queue_size': self.performance.queue_size,
                'cache_size': self.performance.cache_size,
                'batch_size': self.performance.batch_size,
                'enable_gpu': self.performance.enable_gpu,
                'profile_enabled': self.performance.profile_enabled
            }
        }
        
        if format == 'json':
            return json.dumps(config_data, indent=2)
        else:
            return yaml.safe_dump(config_data, default_flow_style=False)
            
    def import_config(self, config_str: str, format: str = 'yaml'):
        """导入配置
        
        Args:
            config_str: 配置字符串
            format: 配置格式 ('yaml' 或 'json')
        """
        if format == 'json':
            config_data = json.loads(config_str)
        else:
            config_data = yaml.safe_load(config_str)
            
        self._parse_config(config_data)
        
    def validate_config(self) -> List[str]:
        """验证配置
        
        Returns:
            错误信息列表
        """
        errors = []
        
        # 验证舵机配置
        for servo_id, servo in self.servos.items():
            if servo.min_angle >= servo.max_angle:
                errors.append(
                    f"舵机 {servo_id} 角度范围无效: "
                    f"{servo.min_angle} >= {servo.max_angle}"
                )
            if servo.default_speed <= 0:
                errors.append(
                    f"舵机 {servo_id} 默认速度无效: {servo.default_speed}"
                )
            if servo.acceleration <= 0:
                errors.append(
                    f"舵机 {servo_id} 加速度无效: {servo.acceleration}"
                )
                
        # 验证动作配置
        if self.action.max_velocity <= 0:
            errors.append(f"最大速度无效: {self.action.max_velocity}")
        if self.action.min_delay <= 0:
            errors.append(f"最小延时无效: {self.action.min_delay}")
        if self.action.smoothing_factor < 0 or self.action.smoothing_factor > 1:
            errors.append(
                f"平滑因子无效: {self.action.smoothing_factor}"
            )
            
        # 验证系统配置
        if self.system.backup_interval <= 0:
            errors.append(
                f"备份间隔无效: {self.system.backup_interval}"
            )
        if self.system.max_backup_count <= 0:
            errors.append(
                f"最大备份数无效: {self.system.max_backup_count}"
            )
        if self.system.remote_port <= 0:
            errors.append(f"远程端口无效: {self.system.remote_port}")
            
        # 网络配置验证
        if not self._is_valid_ip(self.network.host):
            errors.append(f"无效的主机地址: {self.network.host}")
        if self.network.port < 1 or self.network.port > 65535:
            errors.append(f"无效的端口号: {self.network.port}")
        if self.network.ssl_enabled:
            if not os.path.exists(self.network.ssl_cert):
                errors.append(f"SSL证书文件不存在: {self.network.ssl_cert}")
            if not os.path.exists(self.network.ssl_key):
                errors.append(f"SSL密钥文件不存在: {self.network.ssl_key}")
                
        # 安全配置验证
        for ip in self.security.allowed_ips:
            if not self._is_valid_ip(ip):
                errors.append(f"无效的IP地址: {ip}")
        if self.security.token_expire <= 0:
            errors.append(f"无效的令牌过期时间: {self.security.token_expire}")
            
        # 性能配置验证
        if self.performance.max_threads < 1:
            errors.append(f"无效的最大线程数: {self.performance.max_threads}")
        if self.performance.queue_size < 1:
            errors.append(f"无效的队列大小: {self.performance.queue_size}")
            
        return errors
        
    def _parse_config(self, config_data: Dict):
        """解析配置数据"""
        # 解析舵机配置
        self.servos.clear()
        for servo_id, servo_data in config_data.get('servos', {}).items():
            self.servos[servo_id] = ServoConfig(
                id=servo_id,
                **servo_data
            )
            
        # 解析动作配置
        action_data = config_data.get('action', {})
        self.action = ActionConfig(**action_data)
        
        # 解析系统配置
        system_data = config_data.get('system', {})
        self.system = SystemConfig(**system_data)
        
        # 解析网络配置
        network_data = config_data.get('network', {})
        self.network = NetworkConfig(**network_data)
        
        # 解析安全配置
        security_data = config_data.get('security', {})
        self.security = SecurityConfig(**security_data)
        
        # 解析性能配置
        performance_data = config_data.get('performance', {})
        self.performance = PerformanceConfig(**performance_data)
        
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'servos': {},
            'action': {
                'max_velocity': 300.0,
                'min_delay': 0.02,
                'interpolation': 'linear',
                'smoothing_factor': 0.1,
                'servo_pairs': {}
            },
            'system': {
                'log_level': 'INFO',
                'data_dir': 'data',
                'backup_interval': 3600,
                'max_backup_count': 10,
                'enable_remote': False,
                'remote_port': 8080
            },
            'network': {
                'host': '0.0.0.0',
                'port': 8080,
                'ssl_enabled': False
            },
            'security': {
                'enable_auth': True,
                'token_expire': 3600,
                'max_attempts': 3,
                'lockout_time': 300,
                'allowed_ips': [],
                'admin_users': []
            },
            'performance': {
                'max_threads': 4,
                'queue_size': 100,
                'cache_size': 1000,
                'batch_size': 32,
                'enable_gpu': False,
                'profile_enabled': False
            }
        }
        
    def apply_template(self, template_name: str):
        """应用配置模板"""
        if template_name not in self.templates:
            raise ValueError(f"未知的模板名称: {template_name}")
            
        template = self.templates[template_name]
        self._parse_config(template)
        
    def migrate_config(self, old_config: Dict) -> Dict[str, Any]:
        """配置迁移工具"""
        migration_log = []
        new_config = self._get_default_config()
        
        try:
            # 迁移舵机配置
            if 'servos' in old_config:
                for servo_id, old_servo in old_config['servos'].items():
                    new_servo = {}
                    # 处理字段名变更
                    field_mapping = {
                        'min_pos': 'min_angle',
                        'max_pos': 'max_angle',
                        'speed': 'default_speed'
                    }
                    for old_key, new_key in field_mapping.items():
                        if old_key in old_servo:
                            new_servo[new_key] = old_servo[old_key]
                            migration_log.append(
                                f"迁移舵机 {servo_id} 的 {old_key} -> {new_key}"
                            )
                    new_config['servos'][servo_id] = new_servo
                    
            # 迁移动作配置
            if 'action' in old_config:
                old_action = old_config['action']
                new_action = new_config['action']
                # 处理值格式变更
                if 'max_velocity' in old_action:
                    old_value = old_action['max_velocity']
                    new_action['max_velocity'] = float(old_value)
                    migration_log.append("转换max_velocity为float类型")
                    
            # 迁移系统配置
            if 'system' in old_config:
                old_system = old_config['system']
                new_system = new_config['system']
                # 处理配置项合并
                if 'logging' in old_system:
                    new_system['log_level'] = old_system['logging'].get(
                        'level', 'INFO'
                    )
                    migration_log.append("合并logging配置到log_level")
                    
        except Exception as e:
            migration_log.append(f"迁移错误: {str(e)}")
            
        return {
            'config': new_config,
            'log': migration_log
        }
        
    def _get_minimal_template(self) -> Dict:
        """最小配置模板"""
        return {
            'servos': {},
            'action': {
                'max_velocity': 200.0,
                'min_delay': 0.02,
                'interpolation': 'linear',
                'smoothing_factor': 0.1
            },
            'system': {
                'log_level': 'INFO',
                'data_dir': 'data'
            }
        }
        
    def _get_standard_template(self) -> Dict:
        """标准配置模板"""
        return {
            'servos': {
                'servo1': {
                    'min_angle': -90,
                    'max_angle': 90,
                    'default_speed': 100,
                    'acceleration': 200
                }
            },
            'action': {
                'max_velocity': 300.0,
                'min_delay': 0.02,
                'interpolation': 'cubic',
                'smoothing_factor': 0.2,
                'servo_pairs': {
                    'left_arm': 'right_arm'
                }
            },
            'system': {
                'log_level': 'INFO',
                'data_dir': 'data',
                'backup_interval': 3600,
                'max_backup_count': 10
            },
            'network': {
                'host': '0.0.0.0',
                'port': 8080,
                'ssl_enabled': False
            },
            'security': {
                'enable_auth': True,
                'token_expire': 3600,
                'allowed_ips': ['127.0.0.1']
            }
        }
        
    def _get_advanced_template(self) -> Dict:
        """高级配置模板"""
        config = self._get_standard_template()
        config.update({
            'performance': {
                'max_threads': 8,
                'queue_size': 200,
                'cache_size': 2000,
                'batch_size': 64,
                'enable_gpu': True,
                'profile_enabled': True
            },
            'network': {
                'host': '0.0.0.0',
                'port': 8443,
                'ssl_enabled': True,
                'ssl_cert': 'certs/server.crt',
                'ssl_key': 'certs/server.key',
                'max_connections': 20
            },
            'security': {
                'enable_auth': True,
                'token_expire': 7200,
                'max_attempts': 5,
                'lockout_time': 600,
                'allowed_ips': ['127.0.0.1', '192.168.1.0/24'],
                'admin_users': ['admin']
            }
        })
        return config
        
    def _is_valid_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('/')[0].split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    
    def check_health(self) -> Dict[str, Any]:
        """执行配置健康检查
        
        Returns:
            健康状态报告
        """
        health = {
            'status': 'healthy',
            'issues': [],
            'warnings': [],
            'metrics': {}
        }
        
        # 检查配置完整性
        missing_fields = []
        for servo_id, servo in self.servos.items():
            for field in ['min_angle', 'max_angle', 'default_speed']:
                if not hasattr(servo, field):
                    missing_fields.append(f'servo.{servo_id}.{field}')
                
        if missing_fields:
            health['status'] = 'degraded'
            health['issues'].append({
                'type': 'missing_fields',
                'fields': missing_fields
            })
        
        # 检查配置值范围
        if self.performance.max_threads > os.cpu_count():
            health['warnings'].append({
                'type': 'high_thread_count',
                'message': f'线程数 ({self.performance.max_threads}) 超过CPU核心数'
            })
        
        # 计算配置指标
        health['metrics'] = {
            'servo_count': len(self.servos),
            'memory_usage': self._estimate_memory_usage(),
            'config_complexity': self._calculate_complexity()
        }
        
        return health
        
    def _estimate_memory_usage(self) -> int:
        """估算配置占用内存"""
        import sys
        
        size = 0
        size += sys.getsizeof(self.servos)
        size += sum(sys.getsizeof(servo) for servo in self.servos.values())
        size += sys.getsizeof(self.action)
        size += sys.getsizeof(self.system)
        size += sys.getsizeof(self.network)
        size += sys.getsizeof(self.security)
        size += sys.getsizeof(self.performance)
        
        return size
        
    def _calculate_complexity(self) -> float:
        """计算配置复杂度"""
        complexity = 0
        
        # 舵机配置复杂度
        complexity += len(self.servos) * 0.5
        for servo in self.servos.values():
            if servo.calibration:
                complexity += len(servo.calibration) * 0.1
            
        # 动作配置复杂度
        complexity += len(self.action.servo_pairs) * 0.3
        if self.action.interpolation != 'linear':
            complexity += 0.5
        
        # 安全配置复杂度
        complexity += len(self.security.allowed_ips) * 0.2
        complexity += len(self.security.admin_users) * 0.2
        if self.network.ssl_enabled:
            complexity += 1.0
        
        return complexity