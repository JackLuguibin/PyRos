from enum import Enum
from typing import Dict, Callable, Optional
import logging
import threading

class RobotState(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    CALIBRATING = "calibrating"
    RECORDING = "recording"
    EXECUTING = "executing"

class StateMachine:
    def __init__(self, initial_state: RobotState = RobotState.IDLE,
                 logger: logging.Logger = None):
        self.logger = logger
        self.current_state = initial_state
        self.transitions: Dict[RobotState, Dict[RobotState, Callable]] = {}
        self.state_handlers: Dict[RobotState, Callable] = {}
        self._lock = threading.Lock()
        
    def add_transition(self, from_state: RobotState, to_state: RobotState,
                      handler: Optional[Callable] = None):
        """添加状态转换"""
        with self._lock:
            if from_state not in self.transitions:
                self.transitions[from_state] = {}
            self.transitions[from_state][to_state] = handler
            
    def add_state_handler(self, state: RobotState, handler: Callable):
        """添加状态处理器"""
        self.state_handlers[state] = handler
        
    def transition_to(self, new_state: RobotState) -> bool:
        """执行状态转换"""
        with self._lock:
            if self.current_state not in self.transitions or \
               new_state not in self.transitions[self.current_state]:
                if self.logger:
                    self.logger.error(
                        f"无效的状态转换: {self.current_state} -> {new_state}")
                return False
                
            # 执行转换处理器
            handler = self.transitions[self.current_state][new_state]
            if handler:
                try:
                    handler()
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"状态转换失败: {e}")
                    return False
                    
            # 更新状态
            old_state = self.current_state
            self.current_state = new_state
            
            # 执行新状态的处理器
            if new_state in self.state_handlers:
                try:
                    self.state_handlers[new_state]()
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"状态处理失败: {e}")
                    
            if self.logger:
                self.logger.info(f"状态转换: {old_state} -> {new_state}")
                
            return True
            
    def get_state(self) -> RobotState:
        """获取当前状态"""
        return self.current_state 