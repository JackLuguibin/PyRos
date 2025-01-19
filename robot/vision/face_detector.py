import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

class FaceDetector:
    def __init__(self, cascade_file: str = 'haarcascade_frontalface_default.xml',
                 scale_factor: float = 1.1,
                 min_neighbors: int = 5,
                 min_size: Tuple[int, int] = (30, 30),
                 logger: logging.Logger = None):
        """初始化人脸检测器
        
        Args:
            cascade_file: Haar级联分类器文件路径
            scale_factor: 图像缩放因子
            min_neighbors: 最小邻居数
            min_size: 最小人脸尺寸
        """
        self.logger = logger
        self.classifier = cv2.CascadeClassifier(cascade_file)
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size
        
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """检测人脸
        
        Args:
            frame: 输入图像
            
        Returns:
            检测到的人脸列表，每个人脸包含位置和大小信息
        """
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 人脸检测
        faces = self.classifier.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size
        )
        
        results = []
        for (x, y, w, h) in faces:
            face_info = {
                'bbox': (x, y, w, h),
                'center': (x + w//2, y + h//2),
                'size': (w, h)
            }
            results.append(face_info)
            
        if self.logger:
            self.logger.debug(f"检测到 {len(results)} 个人脸")
            
        return results
        
    def draw_faces(self, frame: np.ndarray, faces: List[Dict],
                   color: Tuple[int, int, int] = (0, 255, 0),
                   thickness: int = 2):
        """在图像上绘制人脸框
        
        Args:
            frame: 输入图像
            faces: 人脸信息列表
            color: 绘制颜色
            thickness: 线条粗细
        """
        for face in faces:
            x, y, w, h = face['bbox']
            # 绘制矩形框
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, thickness)
            # 绘制中心点
            cv2.circle(frame, face['center'], 3, color, -1)
            
    def get_largest_face(self, faces: List[Dict]) -> Optional[Dict]:
        """获取最大的人脸"""
        if not faces:
            return None
            
        return max(faces, key=lambda x: x['size'][0] * x['size'][1]) 