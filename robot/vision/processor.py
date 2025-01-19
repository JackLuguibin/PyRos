import cv2
import numpy as np
from typing import Tuple, List, Optional
import logging

class VisionProcessor:
    def __init__(self, camera_index: int = 0, resolution: Tuple[int, int] = (640, 480),
                 logger: logging.Logger = None):
        self.camera = cv2.VideoCapture(camera_index)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.logger = logger
        
    def get_frame(self) -> Optional[np.ndarray]:
        """获取一帧图像"""
        ret, frame = self.camera.read()
        if not ret:
            if self.logger:
                self.logger.error("读取摄像头帧失败")
            return None
        return frame
        
    def detect_color(self, frame: np.ndarray, color_lower: np.ndarray,
                    color_upper: np.ndarray) -> List[dict]:
        """检测指定颜色的物体
        
        Args:
            frame: 输入图像
            color_lower: HSV颜色下限
            color_upper: HSV颜色上限
            
        Returns:
            检测到的物体列表，每个物体包含位置和面积信息
        """
        # 转换到HSV色彩空间
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 颜色阈值分割
        mask = cv2.inRange(hsv, color_lower, color_upper)
        
        # 形态学处理
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, 
                                     cv2.CHAIN_APPROX_SIMPLE)
        
        objects = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 500:  # 过滤小面积
                x, y, w, h = cv2.boundingRect(cnt)
                center = (x + w//2, y + h//2)
                objects.append({
                    'center': center,
                    'area': area,
                    'bbox': (x, y, w, h)
                })
                
        return objects
        
    def detect_apriltag(self, frame: np.ndarray) -> List[dict]:
        """检测AprilTag标记"""
        # 需要安装apriltag库
        # 实现AprilTag检测算法
        pass
        
    def draw_objects(self, frame: np.ndarray, objects: List[dict],
                    color: Tuple[int, int, int] = (0, 255, 0)):
        """在图像上绘制检测到的物体"""
        for obj in objects:
            x, y, w, h = obj['bbox']
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.circle(frame, obj['center'], 5, color, -1)
            
    def release(self):
        """释放资源"""
        self.camera.release() 