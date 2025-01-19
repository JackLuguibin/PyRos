from typing import Dict, Optional, List
import logging
import time
import threading
from dataclasses import dataclass
import Adafruit_PCA9685
from .pca9685_servo import PCA9685Servo

@dataclass
class ManagerConfig:
    """管理器配置"""
    update_rate: float = 50.0  # 更新频率(Hz)
    enable_sync: bool = True   # 启用同步模式

class ServoManager:
    """舵机管理器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """初始化管理器
        
        Args:
            config: 管理器配置
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('ServoManager')
        self.config = ManagerConfig(**config)
        
        # 创建PCA9685
        self.pca = Adafruit_PCA9685.PCA9685()
        self.pca.set_pwm_freq(50)
        
        # 舵机字典
        self.servos: Dict[str, PCA9685Servo] = {}
        
        # 同步控制
        self.sync_lock = threading.Lock()
        self.sync_targets: Dict[str, float] = {}
        
        # 更新线程
        self.running = False
        self.update_thread = None
        
    def add_servo(self, name: str, channel: int, config: Dict):
        """添加舵机
        
        Args:
            name: 舵机名称
            channel: 通道号
            config: 舵机配置
        """
        try:
            servo = PCA9685Servo(
                channel=channel,
                config=config,
                pca=self.pca,
                logger=self.logger
            )
            self.servos[name] = servo
            self.logger.info(f"添加舵机: {name}")
            
        except Exception as e:
            self.logger.error(f"添加舵机失败: {str(e)}")
            
    def remove_servo(self, name: str):
        """移除舵机"""
        if name in self.servos:
            self.servos[name].disable()
            del self.servos[name]
            self.logger.info(f"移除舵机: {name}")
            
    def enable_all(self):
        """使能所有舵机"""
        for servo in self.servos.values():
            servo.enable()
            
    def disable_all(self):
        """失能所有舵机"""
        for servo in self.servos.values():
            servo.disable()
            
    def set_angle(self, name: str, angle: float, speed: Optional[int] = None):
        """设置舵机角度"""
        if name in self.servos:
            if self.config.enable_sync:
                with self.sync_lock:
                    self.sync_targets[name] = angle
            else:
                self.servos[name].set_angle(angle, speed)
                
    def sync_move(self, positions: Dict[str, float], duration: float):
        """同步运动
        
        Args:
            positions: 目标位置{name: angle}
            duration: 运动时间(秒)
        """
        if not self.config.enable_sync:
            return
            
        with self.sync_lock:
            self.sync_targets.clear()
            self.sync_targets.update(positions)
            
        # 计算每个舵机的速度
        speeds = {}
        for name, target in positions.items():
            if name in self.servos:
                servo = self.servos[name]
                delta = abs(target - servo.get_angle())
                speeds[name] = int(delta / duration) if duration > 0 else None
                
        # 设置目标位置和速度
        for name, target in positions.items():
            if name in self.servos:
                self.servos[name].set_angle(target, speeds.get(name))
                
        # 等待运动完成
        if duration > 0:
            time.sleep(duration)
            
    def start(self):
        """启动管理器"""
        if self.running:
            return
            
        self.running = True
        self.update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self.update_thread.start()
        self.logger.info("舵机管理器已启动")
        
    def stop(self):
        """停止管理器"""
        self.running = False
        if self.update_thread:
            self.update_thread.join()
        self.disable_all()
        self.logger.info("舵机管理器已停止")
        
    def _update_loop(self):
        """更新循环"""
        dt = 1.0 / self.config.update_rate
        
        while self.running:
            try:
                start_time = time.time()
                
                # 同步更新
                if self.config.enable_sync:
                    with self.sync_lock:
                        for name, target in self.sync_targets.items():
                            if name in self.servos:
                                self.servos[name].set_angle(target)
                        self.sync_targets.clear()
                        
                # 等待下一个周期
                elapsed = time.time() - start_time
                if elapsed < dt:
                    time.sleep(dt - elapsed)
                    
            except Exception as e:
                self.logger.error(f"更新循环错误: {str(e)}") 