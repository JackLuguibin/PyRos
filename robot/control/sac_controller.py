from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
from .advanced_controller import AdvancedController

class SACNetwork(nn.Module):
    """SAC网络"""
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        
        # Q网络1
        self.q1 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
        # Q网络2
        self.q2 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
        # 策略网络
        self.policy = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        self.policy_mean = nn.Linear(hidden_dim, action_dim)
        self.policy_log_std = nn.Linear(hidden_dim, action_dim)
        
    def forward(self, state, action=None):
        policy_features = self.policy(state)
        mean = self.policy_mean(policy_features)
        log_std = self.policy_log_std(policy_features)
        log_std = torch.clamp(log_std, -20, 2)
        std = log_std.exp()
        
        if action is None:
            dist = Normal(mean, std)
            action = dist.rsample()
            
        q1_input = torch.cat([state, action], dim=-1)
        q2_input = torch.cat([state, action], dim=-1)
        
        q1 = self.q1(q1_input)
        q2 = self.q2(q2_input)
        
        return action, mean, std, q1, q2

class SACController(AdvancedController):
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # 网络参数
        self.state_dim = config.get('state_dim', 10)
        self.action_dim = config.get('action_dim', 5)
        self.hidden_dim = config.get('hidden_dim', 256)
        
        # 创建网络
        self.sac_net = SACNetwork(self.state_dim, self.action_dim, self.hidden_dim)
        self.target_sac_net = SACNetwork(self.state_dim, self.action_dim, self.hidden_dim)
        self.target_sac_net.load_state_dict(self.sac_net.state_dict())
        
        # 优化器
        self.policy_optimizer = optim.Adam(
            self.sac_net.policy.parameters(),
            lr=config.get('policy_lr', 0.0003)
        )
        self.q_optimizer = optim.Adam(
            list(self.sac_net.q1.parameters()) + 
            list(self.sac_net.q2.parameters()),
            lr=config.get('q_lr', 0.0003)
        )
        
        # SAC参数
        self.gamma = config.get('gamma', 0.99)
        self.tau = config.get('tau', 0.005)
        self.alpha = config.get('alpha', 0.2)
        self.target_update_interval = config.get('target_update_interval', 1)
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
            action, _, _, _, _ = self.sac_net(state_tensor)
            
        # 存储经验
        reward = self._calculate_reward(state)
        self._store_experience({
            'state': state_tensor,
            'action': action,
            'reward': reward
        })
        
        # 学习更新
        if len(self.replay_buffer) >= self.min_buffer_size:
            self._update_sac()
            
        # 转换为控制输出
        return self._action_to_control(action.numpy())
        
    def _update_sac(self):
        """SAC更新"""
        # 采样批次
        batch = self._sample_batch()
        
        state_batch = torch.stack([item['state'] for item in batch])
        action_batch = torch.stack([item['action'] for item in batch])
        reward_batch = torch.tensor([item['reward'] for item in batch])
        next_state_batch = torch.stack([item['next_state'] for item in batch])
        
        # 更新Q网络
        with torch.no_grad():
            next_action, next_mean, next_std, _, _ = self.target_sac_net(next_state_batch)
            next_dist = Normal(next_mean, next_std)
            next_log_prob = next_dist.log_prob(next_action).sum(-1, keepdim=True)
            
            next_q_target1, next_q_target2 = self.target_sac_net.q1(next_state_batch, next_action), \
                                            self.target_sac_net.q2(next_state_batch, next_action)
            next_q_target = torch.min(next_q_target1, next_q_target2)
            next_q_target = next_q_target - self.alpha * next_log_prob
            q_target = reward_batch.unsqueeze(-1) + self.gamma * next_q_target
            
        q1, q2 = self.sac_net.q1(state_batch, action_batch), \
                 self.sac_net.q2(state_batch, action_batch)
                 
        q1_loss = nn.MSELoss()(q1, q_target)
        q2_loss = nn.MSELoss()(q2, q_target)
        q_loss = q1_loss + q2_loss
        
        self.q_optimizer.zero_grad()
        q_loss.backward()
        self.q_optimizer.step()
        
        # 更新策略网络
        action, mean, std, q1, q2 = self.sac_net(state_batch)
        dist = Normal(mean, std)
        log_prob = dist.log_prob(action).sum(-1, keepdim=True)
        
        q_value = torch.min(q1, q2)
        policy_loss = (self.alpha * log_prob - q_value).mean()
        
        self.policy_optimizer.zero_grad()
        policy_loss.backward()
        self.policy_optimizer.step()
        
        # 更新目标网络
        self.update_counter += 1
        if self.update_counter % self.target_update_interval == 0:
            self._soft_update_target()
            
    def _soft_update_target(self):
        """软更新目标网络"""
        for target_param, param in zip(self.target_sac_net.parameters(),
                                     self.sac_net.parameters()):
            target_param.data.copy_(
                target_param.data * (1.0 - self.tau) +
                param.data * self.tau
            )
            
    def _sample_batch(self) -> List[Dict]:
        """采样经验批次"""
        indices = np.random.choice(
            len(self.replay_buffer),
            self.batch_size,
            replace=False
        )
        return [self.replay_buffer[i] for i in indices] 