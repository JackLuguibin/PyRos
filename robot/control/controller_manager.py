from typing import Dict, Optional
import logging
from .balance_controller import BalanceController
from .trajectory_controller import TrajectoryController
from .motion_controller import MotionController

class ControllerManager:
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """控制器管理器
        
        Args:
            config: 控制器配置
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('ControllerManager')
        self.config = config
        
        # 创建控制器
        self.controllers: Dict[str, MotionController] = {}
        self._init_controllers()
        
        # 状态变量
        self.active_controller = None
        
    def _init_controllers(self):
        """初始化控制器"""
        # 创建平衡控制器
        if 'balance' in self.config:
            self.controllers['balance'] = BalanceController(
                self.config['balance'],
                self.logger
            )
            
        # 创建轨迹控制器
        if 'trajectory' in self.config:
            self.controllers['trajectory'] = TrajectoryController(
                self.config['trajectory'],
                self.config['trajectory'].get('generator'),
                self.logger
            )
            
    def update(self, state: Dict, dt: float) -> Dict:
        """更新控制
        
        Args:
            state: 当前状态
            dt: 时间间隔
            
        Returns:
            控制输出
        """
        if not self.active_controller:
            return {}
            
        controller = self.controllers.get(self.active_controller)
        if not controller:
            return {}
            
        try:
            return controller.update(state, dt)
        except Exception as e:
            self.logger.error(f"控制器更新错误: {str(e)}")
            return {}
            
    def activate_controller(self, name: str):
        """激活控制器"""
        if name not in self.controllers:
            raise ValueError(f"未知的控制器: {name}")
            
        if self.active_controller:
            self.controllers[self.active_controller].reset()
            
        self.active_controller = name
        
    def get_controller(self, name: str) -> Optional[MotionController]:
        """获取控制器"""
        return self.controllers.get(name)
        
    def get_state(self) -> Dict:
        """获取控制器状态"""
        return {
            'active_controller': self.active_controller,
            'controllers': {
                name: controller.get_state()
                for name, controller in self.controllers.items()
            }
        } 