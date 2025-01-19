from typing import Dict, Optional, Callable, Any
import logging
import threading
import time
from queue import PriorityQueue, Empty
from dataclasses import dataclass
from enum import Enum

class TaskPriority(Enum):
    """任务优先级"""
    HIGH = 0    # 高优先级
    NORMAL = 1  # 普通优先级
    LOW = 2     # 低优先级

@dataclass
class Task:
    """任务"""
    id: str  # 任务ID
    func: Callable  # 执行函数
    args: tuple = ()  # 位置参数
    kwargs: Dict = None  # 关键字参数
    priority: TaskPriority = TaskPriority.NORMAL  # 优先级
    timeout: float = None  # 超时时间(秒)
    retry: int = 0  # 重试次数
    created_at: float = None  # 创建时间
    
    def __post_init__(self):
        self.created_at = self.created_at or time.time()
        self.kwargs = self.kwargs or {}
        
    def __lt__(self, other):
        return self.priority.value < other.priority.value

@dataclass
class TaskResult:
    """任务结果"""
    task_id: str  # 任务ID
    success: bool  # 是否成功
    result: Any = None  # 执行结果
    error: str = None  # 错误信息
    execution_time: float = None  # 执行时间(秒)

class TaskQueue:
    """任务队列"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('TaskQueue')
        self.config = config
        
        # 任务队列
        self.queue = PriorityQueue()
        self.results: Dict[str, TaskResult] = {}
        
        # 工作线程
        self.workers: List[threading.Thread] = []
        self.worker_count = config.get('worker_count', 4)
        self.running = False
        
        # 任务监控
        self.task_count = 0
        self.failed_count = 0
        self.success_count = 0
        self.total_time = 0.0
        self.stats_lock = threading.Lock()
        
    def start(self):
        """启动任务队列"""
        self.running = True
        
        # 创建工作线程
        for i in range(self.worker_count):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"worker_{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
            
        self.logger.info(f"任务队列启动，{self.worker_count}个工作线程")
        
    def stop(self):
        """停止任务队列"""
        self.running = False
        
        # 等待工作线程结束
        for worker in self.workers:
            worker.join()
            
        self.logger.info("任务队列停止")
        
    def submit(self, func: Callable, *args,
              priority: TaskPriority = TaskPriority.NORMAL,
              timeout: float = None,
              retry: int = 0,
              **kwargs) -> str:
        """提交任务
        
        Args:
            func: 执行函数
            *args: 位置参数
            priority: 优先级
            timeout: 超时时间
            retry: 重试次数
            **kwargs: 关键字参数
            
        Returns:
            任务ID
        """
        task = Task(
            id=f"task_{self.task_count}",
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            retry=retry
        )
        
        self.queue.put(task)
        
        with self.stats_lock:
            self.task_count += 1
            
        return task.id
        
    def get_result(self, task_id: str, timeout: float = None) -> Optional[TaskResult]:
        """获取任务结果
        
        Args:
            task_id: 任务ID
            timeout: 等待超时时间
            
        Returns:
            任务结果
        """
        start_time = time.time()
        while timeout is None or time.time() - start_time < timeout:
            if task_id in self.results:
                return self.results[task_id]
            time.sleep(0.1)
        return None
        
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self.stats_lock:
            return {
                'task_count': self.task_count,
                'failed_count': self.failed_count,
                'success_count': self.success_count,
                'queue_size': self.queue.qsize(),
                'avg_time': self.total_time / (self.success_count or 1)
            }
            
    def _worker_loop(self):
        """工作线程循环"""
        while self.running:
            try:
                # 获取任务
                task = self.queue.get(timeout=1.0)
                
                # 执行任务
                start_time = time.time()
                retries = 0
                last_error = None
                
                while retries <= task.retry:
                    try:
                        # 设置超时
                        if task.timeout:
                            timer = threading.Timer(
                                task.timeout,
                                self._handle_timeout,
                                args=(threading.current_thread(),)
                            )
                            timer.start()
                            
                        # 执行函数
                        result = task.func(*task.args, **task.kwargs)
                        
                        # 取消超时
                        if task.timeout:
                            timer.cancel()
                            
                        # 保存结果
                        execution_time = time.time() - start_time
                        self.results[task.id] = TaskResult(
                            task_id=task.id,
                            success=True,
                            result=result,
                            execution_time=execution_time
                        )
                        
                        # 更新统计
                        with self.stats_lock:
                            self.success_count += 1
                            self.total_time += execution_time
                            
                        break
                        
                    except Exception as e:
                        last_error = str(e)
                        retries += 1
                        if retries <= task.retry:
                            self.logger.warning(
                                f"任务 {task.id} 执行失败，重试 {retries}/{task.retry}"
                            )
                            time.sleep(1.0)  # 重试延迟
                            
                # 处理失败
                if last_error:
                    self.results[task.id] = TaskResult(
                        task_id=task.id,
                        success=False,
                        error=last_error,
                        execution_time=time.time() - start_time
                    )
                    with self.stats_lock:
                        self.failed_count += 1
                        
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"工作线程错误: {str(e)}")
                
    def _handle_timeout(self, thread: threading.Thread):
        """处理超时"""
        thread.join(0)  # 非阻塞等待
        if thread.is_alive():
            self.logger.warning(f"任务超时，终止线程: {thread.name}")
            # 在Python中无法优雅地终止线程，这里仅作为示例 