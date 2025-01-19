from typing import Dict, List, Optional, Protocol
import numpy as np
import logging
from abc import ABC, abstractmethod
from .motion_controller import MotionController

class LearningController(Protocol):
    """学习控制器协议"""
    
    def learn(self, state: Dict, action: Dict, reward: float):
        """学习更新"""
        pass
        
    def predict(self, state: Dict) -> Dict:
        """预测动作"""
        pass

class AdvancedController(MotionController):
    """高级控制器基类"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('AdvancedController')
        self.config = config
        
        # 学习控制器
        self.learner: Optional[LearningController] = None
        
        # 状态历史
        self.state_history: List[Dict] = []
        self.max_history = config.get('max_history', 1000)
        
        # 性能指标
        self.performance_metrics = {
            'mse': [],
            'mae': [],
            'rewards': []
        }
        
    def update(self, state: Dict, dt: float) -> Dict:
        """更新控制
        
        结合传统控制和学习控制
        """
        # 保存状态历史
        self.state_history.append(state)
        if len(self.state_history) > self.max_history:
            self.state_history.pop(0)
            
        # 获取学习预测
        if self.learner:
            predicted_action = self.learner.predict(state)
        else:
            predicted_action = {}
            
        # 计算控制输出
        output = self._compute_control(state, predicted_action, dt)
        
        # 更新性能指标
        self._update_metrics(state, output)
        
        return output
        
    @abstractmethod
    def _compute_control(self, state: Dict, 
                        predicted_action: Dict,
                        dt: float) -> Dict:
        """计算控制输出"""
        pass
        
    def _update_metrics(self, state: Dict, output: Dict):
        """更新性能指标"""
        if not self.state_history:
            return
            
        # 计算误差
        target = state.get('target', {})
        current = state.get('current', {})
        
        errors = []
        abs_errors = []
        
        for key in target:
            if key in current:
                error = target[key] - current[key]
                errors.append(error * error)
                abs_errors.append(abs(error))
                
        if errors:
            self.performance_metrics['mse'].append(np.mean(errors))
            self.performance_metrics['mae'].append(np.mean(abs_errors))
            
    def get_metrics(self) -> Dict:
        """获取性能指标"""
        return {
            'mse': np.mean(self.performance_metrics['mse'][-100:]),
            'mae': np.mean(self.performance_metrics['mae'][-100:]),
            'rewards': np.mean(self.performance_metrics['rewards'][-100:])
        } 