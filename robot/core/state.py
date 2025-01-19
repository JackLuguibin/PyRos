from dataclasses import dataclass

@dataclass
class JointState:
    """关节状态"""
    position: float = 0.0  # 位置
    velocity: float = 0.0  # 速度
    acceleration: float = 0.0  # 加速度
    effort: float = 0.0  # 力矩/力 