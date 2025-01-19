from typing import List, Dict, Optional, Callable
import logging
import threading
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Task:
    def __init__(self, name: str, action: Callable, 
                 prerequisites: List[str] = None,
                 timeout: float = None):
        self.name = name
        self.action = action
        self.prerequisites = prerequisites or []
        self.timeout = timeout
        self.status = TaskStatus.PENDING
        self.result = None
        
class TaskPlanner:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        
    def add_task(self, task: Task):
        """添加任务"""
        with self._lock:
            self.tasks[task.name] = task
            
    def execute_task(self, task_name: str) -> bool:
        """执行任务"""
        with self._lock:
            if task_name not in self.tasks:
                if self.logger:
                    self.logger.error(f"任务不存在: {task_name}")
                return False
                
            task = self.tasks[task_name]
            
            # 检查前置条件
            for prereq in task.prerequisites:
                if prereq not in self.tasks or \
                   self.tasks[prereq].status != TaskStatus.COMPLETED:
                    if self.logger:
                        self.logger.error(f"前置条件未满足: {prereq}")
                    return False
                    
            # 创建执行线程
            def _execute():
                try:
                    task.status = TaskStatus.RUNNING
                    task.result = task.action()
                    task.status = TaskStatus.COMPLETED
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.result = e
                    if self.logger:
                        self.logger.error(f"任务执行失败: {task_name}, {e}")
                finally:
                    with self._lock:
                        del self.running_tasks[task_name]
                        
            thread = threading.Thread(target=_execute)
            self.running_tasks[task_name] = thread
            thread.start()
            
            return True
            
    def cancel_task(self, task_name: str):
        """取消任务"""
        with self._lock:
            if task_name in self.tasks:
                self.tasks[task_name].status = TaskStatus.CANCELLED
                
    def get_task_status(self, task_name: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        return self.tasks.get(task_name).status if task_name in self.tasks \
               else None
               
    def cleanup(self):
        """清理资源"""
        with self._lock:
            for task_name in list(self.running_tasks.keys()):
                self.cancel_task(task_name)
            for thread in self.running_tasks.values():
                thread.join() 