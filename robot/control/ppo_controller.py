from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
from .advanced_controller import AdvancedController

class ActorCritic(nn.Module):
    """PPO的Actor-Critic网络"""
    
    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        
        # 共享特征提取层
        self.feature_net = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU()
        )
        
        # Actor网络(策略网络)
        self.actor_mean = nn.Linear(128, action_dim)
        self.actor_std = nn.Parameter(torch.ones(action_dim) * 0.1)
        
        # Critic网络(价值网络)
        self.critic = nn.Linear(128, 1)
        
    def forward(self, state):
        features = self.feature_net(state)
        
        # 计算动作分布
        action_mean = self.actor_mean(features)
        action_std = self.actor_std.expand_as(action_mean)
        
        # 计算状态价值
        value = self.critic(features)
        
        return action_mean, action_std, value
        
    def evaluate(self, state, action):
        action_mean, action_std, value = self(state)
        dist = Normal(action_mean, action_std)
        
        action_log_probs = dist.log_prob(action).sum(-1)
        entropy = dist.entropy().mean()
        
        return action_log_probs, value, entropy
        
    def get_action(self, state):
        action_mean, action_std, _ = self(state)
        dist = Normal(action_mean, action_std)
        action = dist.sample()
        action_log_prob = dist.log_prob(action).sum(-1)
        
        return action, action_log_prob

class PPOController(AdvancedController):
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # 网络参数
        self.state_dim = config.get('state_dim', 10)
        self.action_dim = config.get('action_dim', 5)
        
        # 创建Actor-Critic网络
        self.ac_net = ActorCritic(self.state_dim, self.action_dim)
        self.optimizer = optim.Adam(self.ac_net.parameters(), 
                                  lr=config.get('learning_rate', 0.0003))
        
        # PPO参数
        self.clip_param = config.get('clip_param', 0.2)
        self.ppo_epochs = config.get('ppo_epochs', 10)
        self.batch_size = config.get('batch_size', 32)
        self.value_coef = config.get('value_coef', 0.5)
        self.entropy_coef = config.get('entropy_coef', 0.01)
        
        # 经验缓存
        self.rollouts: List[Dict] = []
        self.max_rollouts = config.get('max_rollouts', 2048)
        
    def _compute_control(self, state: Dict,
                        predicted_action: Dict,
                        dt: float) -> Dict:
        """计算控制输出"""
        # 状态预处理
        state_tensor = self._preprocess_state(state)
        
        # 获取动作
        with torch.no_grad():
            action, action_log_prob = self.ac_net.get_action(state_tensor)
            _, _, value = self.ac_net(state_tensor)
            
        # 存储经验
        self._store_experience({
            'state': state_tensor,
            'action': action,
            'action_log_prob': action_log_prob,
            'value': value,
            'reward': self._calculate_reward(state)
        })
        
        # 学习更新
        if len(self.rollouts) >= self.max_rollouts:
            self._update_ppo()
            self.rollouts.clear()
            
        # 转换为控制输出
        return self._action_to_control(action.numpy())
        
    def _update_ppo(self):
        """PPO更新"""
        # 计算优势估计
        advantages = self._compute_advantages()
        
        # 多轮更新
        for _ in range(self.ppo_epochs):
            # 批次采样
            batch_indices = np.random.choice(
                len(self.rollouts),
                self.batch_size,
                replace=False
            )
            
            batch_states = torch.stack([self.rollouts[i]['state'] 
                                      for i in batch_indices])
            batch_actions = torch.stack([self.rollouts[i]['action'] 
                                       for i in batch_indices])
            batch_old_log_probs = torch.stack([self.rollouts[i]['action_log_prob'] 
                                             for i in batch_indices])
            batch_advantages = advantages[batch_indices]
            batch_returns = batch_advantages + torch.stack([self.rollouts[i]['value'] 
                                                          for i in batch_indices])
            
            # 评估动作
            log_probs, values, entropy = self.ac_net.evaluate(
                batch_states, batch_actions)
            
            # 计算比率
            ratio = torch.exp(log_probs - batch_old_log_probs)
            
            # 计算surrogate目标
            surr1 = ratio * batch_advantages
            surr2 = torch.clamp(ratio, 1-self.clip_param, 1+self.clip_param) * batch_advantages
            
            # 计算actor损失
            actor_loss = -torch.min(surr1, surr2).mean()
            
            # 计算critic损失
            value_loss = 0.5 * (batch_returns - values).pow(2).mean()
            
            # 计算总损失
            loss = (actor_loss + 
                   self.value_coef * value_loss - 
                   self.entropy_coef * entropy)
            
            # 更新网络
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
    def _compute_advantages(self) -> torch.Tensor:
        """计算优势估计"""
        advantages = []
        returns = []
        gae = 0
        
        # 计算GAE
        for t in reversed(range(len(self.rollouts)-1)):
            reward = self.rollouts[t]['reward']
            value = self.rollouts[t]['value']
            next_value = self.rollouts[t+1]['value']
            
            delta = reward + self.gamma * next_value - value
            gae = delta + self.gamma * self.gae_lambda * gae
            
            returns.insert(0, gae + value)
            advantages.insert(0, gae)
            
        return torch.tensor(advantages) 