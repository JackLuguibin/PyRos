from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from .advanced_controller import AdvancedController

class TD3Network(nn.Module):
    """TD3网络"""
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        
        # Actor网络
        self.actor = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Tanh()
        )
        
        # 双Q网络
        self.critic1 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
        self.critic2 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
    def forward(self, state):
        return self.actor(state)
        
    def q1(self, state, action):
        sa = torch.cat([state, action], dim=-1)
        return self.critic1(sa)
        
    def q2(self, state, action):
        sa = torch.cat([state, action], dim=-1)
        return self.critic2(sa)

class TD3Controller(AdvancedController):
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # 网络参数
        self.state_dim = config.get('state_dim', 10)
        self.action_dim = config.get('action_dim', 5)
        self.hidden_dim = config.get('hidden_dim', 256)
        
        # 创建网络
        self.td3_net = TD3Network(self.state_dim, self.action_dim, self.hidden_dim)
        self.target_net = TD3Network(self.state_dim, self.action_dim, self.hidden_dim)
        self.target_net.load_state_dict(self.td3_net.state_dict())
        
        # 优化器
        self.actor_optimizer = optim.Adam(
            self.td3_net.actor.parameters(),
            lr=config.get('actor_lr', 0.0003)
        )
        self.critic_optimizer = optim.Adam(
            list(self.td3_net.critic1.parameters()) +
            list(self.td3_net.critic2.parameters()),
            lr=config.get('critic_lr', 0.0003)
        )
        
        # TD3参数
        self.gamma = config.get('gamma', 0.99)
        self.tau = config.get('tau', 0.005)
        self.policy_noise = config.get('policy_noise', 0.2)
        self.noise_clip = config.get('noise_clip', 0.5)
        self.policy_delay = config.get('policy_delay', 2)
        self.update_counter = 0
        
        # 经验回放
        self.replay_buffer: List[Dict] = []
        self.buffer_size = config.get('buffer_size', 1000000)
        self.batch_size = config.get('batch_size', 256)
        self.min_buffer_size = config.get('min_buffer_size', 1000)
        
    def _compute_control(self, state: Dict,
                        predicted_action: Dict,
                        dt: float) -> Dict:
        """计算控制输出"""
        # 状态预处理
        state_tensor = self._preprocess_state(state)
        
        # 获取动作
        with torch.no_grad():
            action = self.td3_net(state_tensor)
            # 添加探索噪声
            noise = torch.randn_like(action) * self.policy_noise
            noise = torch.clamp(noise, -self.noise_clip, self.noise_clip)
            action = torch.clamp(action + noise, -1, 1)
            
        # 存储经验
        reward = self._calculate_reward(state)
        self._store_experience({
            'state': state_tensor,
            'action': action,
            'reward': reward
        })
        
        # 学习更新
        if len(self.replay_buffer) >= self.min_buffer_size:
            self._update_td3()
            
        # 转换为控制输出
        return self._action_to_control(action.numpy())
        
    def _update_td3(self):
        """TD3更新"""
        # 采样批次
        batch = self._sample_batch()
        
        state_batch = torch.stack([item['state'] for item in batch])
        action_batch = torch.stack([item['action'] for item in batch])
        reward_batch = torch.tensor([item['reward'] for item in batch])
        next_state_batch = torch.stack([item['next_state'] for item in batch])
        
        # 更新Critic
        with torch.no_grad():
            # 目标动作
            next_action = self.target_net(next_state_batch)
            noise = torch.randn_like(next_action) * self.policy_noise
            noise = torch.clamp(noise, -self.noise_clip, self.noise_clip)
            next_action = torch.clamp(next_action + noise, -1, 1)
            
            # 目标Q值
            target_q1 = self.target_net.q1(next_state_batch, next_action)
            target_q2 = self.target_net.q2(next_state_batch, next_action)
            target_q = torch.min(target_q1, target_q2)
            target_q = reward_batch.unsqueeze(-1) + self.gamma * target_q
            
        # 当前Q值
        current_q1 = self.td3_net.q1(state_batch, action_batch)
        current_q2 = self.td3_net.q2(state_batch, action_batch)
        
        # Critic损失
        critic_loss = nn.MSELoss()(current_q1, target_q) + \
                     nn.MSELoss()(current_q2, target_q)
                     
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()
        
        # 延迟更新Actor
        self.update_counter += 1
        if self.update_counter % self.policy_delay == 0:
            # Actor损失
            actor_loss = -self.td3_net.q1(
                state_batch,
                self.td3_net(state_batch)
            ).mean()
            
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            self.actor_optimizer.step()
            
            # 软更新目标网络
            self._soft_update_target()
            
    def _soft_update_target(self):
        """软更新目标网络"""
        for target_param, param in zip(self.target_net.parameters(),
                                     self.td3_net.parameters()):
            target_param.data.copy_(
                target_param.data * (1.0 - self.tau) +
                param.data * self.tau
            ) 