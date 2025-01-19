import logging
import os
from datetime import datetime

class RobotLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self._setup_logger()
        
    def _setup_logger(self):
        """设置日志系统"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        # 创建日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"robot_{timestamp}.log")
        
        # 配置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 配置根日志器
        self.logger = logging.getLogger("Robot")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def get_logger(self) -> logging.Logger:
        """获取日志器"""
        return self.logger 