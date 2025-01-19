import time
from ..task_queue import TaskQueue, TaskPriority

def run_task_example():
    """运行任务队列示例"""
    
    # 配置
    config = {
        'worker_count': 4,
        'default_timeout': 60.0
    }
    
    # 创建任务队列
    queue = TaskQueue(config)
    
    # 测试任务
    def long_task(duration: float) -> str:
        time.sleep(duration)
        return f"任务完成，耗时 {duration}秒"
        
    def error_task() -> None:
        raise RuntimeError("任务执行失败")
        
    # 启动队列
    queue.start()
    
    try:
        # 提交任务
        task1_id = queue.submit(
            long_task,
            2.0,
            priority=TaskPriority.HIGH
        )
        
        task2_id = queue.submit(
            long_task,
            1.0,
            priority=TaskPriority.NORMAL
        )
        
        task3_id = queue.submit(
            error_task,
            priority=TaskPriority.LOW,
            retry=2
        )
        
        # 等待结果
        result1 = queue.get_result(task1_id)
        print(f"任务1结果: {result1}")
        
        result2 = queue.get_result(task2_id)
        print(f"任务2结果: {result2}")
        
        result3 = queue.get_result(task3_id)
        print(f"任务3结果: {result3}")
        
        # 打印统计信息
        stats = queue.get_stats()
        print("统计信息:", stats)
        
    finally:
        queue.stop()

if __name__ == '__main__':
    run_task_example() 