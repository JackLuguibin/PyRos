from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from .advanced_controller import AdvancedController, LearningController

class DQNNetwork(nn.Module):
    """DQN网络"""
    
    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)
        )
        
    def forward(self, x):
        return self.network(x)

class RLController(AdvancedController):
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # 创建DQN网络
        self.state_dim = config.get('state_dim', 10)
        self.action_dim = config.get('action_dim', 5)
        
        self.dqn = DQNNetwork(self.state_dim, self.action_dim)
        self.target_dqn = DQNNetwork(self.state_dim, self.action_dim)
        self.target_dqn.load_state_dict(self.dqn.state_dict())
        
        # 优化器
        self.optimizer = optim.Adam(self.dqn.parameters(), 
                                  lr=config.get('learning_rate', 0.001))
        
        # 经验回放缓冲
        self.replay_buffer: List[Tuple] = []
        self.buffer_size = config.get('buffer_size', 10000)
        self.batch_size = config.get('batch_size', 32)
        
        # 学习参数
        self.gamma = config.get('gamma', 0.99)
        self.epsilon = config.get('epsilon', 0.1)
        self.target_update = config.get('target_update', 10)
        self.update_counter = 0
        
    def _compute_control(self, state: Dict,
                        predicted_action: Dict,
                        dt: float) -> Dict:
        """计算控制输出"""
        # 状态预处理
        state_tensor = self._preprocess_state(state)
        
        # ε-贪婪策略
        if np.random.random() < self.epsilon:
            action_values = np.random.rand(self.action_dim)
        else:
            with torch.no_grad():
                action_values = self.dqn(state_tensor).numpy()
                
        # 转换为控制输出
        output = self._action_to_control(action_values)
        
        # 存储经验
        reward = self._calculate_reward(state)
        self._store_experience(state, action_values, reward)
        
        # 学习更新
        if len(self.replay_buffer) >= self.batch_size:
            self._learn()
            
        return output
        
    def _preprocess_state(self, state: Dict) -> torch.Tensor:
        """状态预处理"""
        # 提取关键状态变量
        state_values = []
        for key in ['position', 'velocity', 'target']:
            if key in state:
                values = state[key]
                if isinstance(values, dict):
                    state_values.extend(values.values())
                else:
                    state_values.append(values)
                    
        # 填充或截断
        while len(state_values) < self.state_dim:
            state_values.append(0.0)
        state_values = state_values[:self.state_dim]
        
        return torch.FloatTensor(state_values)
        
    def _action_to_control(self, action_values: np.ndarray) -> Dict:
        """动作值转换为控制输出"""
        # 简单示例：将动作值映射到关节角度
        outputs = {}
        for i, value in enumerate(action_values):
            outputs[f'joint_{i}'] = value * 180  # 映射到±180度
            
        return outputs
        
    def _calculate_reward(self, state: Dict) -> float:
        """计算奖励"""
        reward = 0.0
        
        # 位置误差惩罚
        target = state.get('target', {})
        current = state.get('current', {})
        
        for key in target:
            if key in current:
                error = abs(target[key] - current[key])
                reward -= error * 0.1
                
        # 能量消耗惩罚
        energy = state.get('energy', 0.0)
        reward -= energy * 0.01
        
        # 稳定性奖励
        stability = state.get('stability', 0.0)
        reward += stability * 0.1
        
        return reward
        
    def _store_experience(self, state: Dict,
                         action: np.ndarray,
                         reward: float):
        """存储经验"""
        self.replay_buffer.append((
            self._preprocess_state(state),
            torch.FloatTensor(action),
            reward
        ))
        
        if len(self.replay_buffer) > self.buffer_size:
            self.replay_buffer.pop(0)
            
    def _learn(self):
        """学习更新"""
        # 采样批次
        batch = np.random.choice(
            len(self.replay_buffer),
            self.batch_size,
            replace=False
        )
        
        states = []
        actions = []
        rewards = []
        
        for idx in batch:
            state, action, reward = self.replay_buffer[idx]
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            
        states = torch.stack(states)
        actions = torch.stack(actions)
        rewards = torch.FloatTensor(rewards)
        
        # 计算目标Q值
        with torch.no_grad():
            next_q = self.target_dqn(states).max(1)[0]
            target_q = rewards + self.gamma * next_q
            
        # 计算当前Q值
        current_q = self.dqn(states).gather(1, actions.long())
        
        # 计算损失并更新
        loss = nn.MSELoss()(current_q, target_q.unsqueeze(1))
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # 更新目标网络
        self.update_counter += 1
        if self.update_counter >= self.target_update:
            self.target_dqn.load_state_dict(self.dqn.state_dict())
            self.update_counter = 0
            
        # 记录性能
        self.performance_metrics['rewards'].append(rewards.mean().item()) 