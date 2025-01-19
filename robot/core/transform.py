from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import logging
import time

@dataclass
class Transform:
    """坐标变换"""
    translation: np.ndarray  # 平移向量 [x, y, z]
    rotation: np.ndarray    # 旋转矩阵 3x3
    timestamp: float = 0.0  # 时间戳

class TransformManager:
    """坐标变换管理器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('TransformManager')
        self.config = config
        
        # 坐标系关系
        self.transforms: Dict[str, Dict[str, Transform]] = {}
        
        # 缓存设置
        self.cache_duration = config.get('cache_duration', 1.0)  # 缓存时长(秒)
        self.max_cache_size = config.get('max_cache_size', 1000)  # 最大缓存数量
        
    def add_transform(self, parent_frame: str, child_frame: str,
                     translation: np.ndarray, rotation: np.ndarray,
                     timestamp: float = None) -> bool:
        """添加坐标变换
        
        Args:
            parent_frame: 父坐标系
            child_frame: 子坐标系
            translation: 平移向量
            rotation: 旋转矩阵
            timestamp: 时间戳
            
        Returns:
            是否添加成功
        """
        try:
            if parent_frame not in self.transforms:
                self.transforms[parent_frame] = {}
                
            transform = Transform(
                translation=translation,
                rotation=rotation,
                timestamp=timestamp or time.time()
            )
            
            self.transforms[parent_frame][child_frame] = transform
            return True
            
        except Exception as e:
            self.logger.error(f"添加变换失败: {str(e)}")
            return False
            
    def get_transform(self, target_frame: str, source_frame: str,
                     timestamp: float = None) -> Optional[Transform]:
        """获取坐标变换
        
        Args:
            target_frame: 目标坐标系
            source_frame: 源坐标系
            timestamp: 时间戳
            
        Returns:
            坐标变换
        """
        try:
            # 直接变换
            if target_frame in self.transforms and \
               source_frame in self.transforms[target_frame]:
                return self.transforms[target_frame][source_frame]
                
            # 反向变换
            if source_frame in self.transforms and \
               target_frame in self.transforms[source_frame]:
                transform = self.transforms[source_frame][target_frame]
                return Transform(
                    translation=-transform.rotation.T @ transform.translation,
                    rotation=transform.rotation.T,
                    timestamp=transform.timestamp
                )
                
            # 查找变换路径
            path = self._find_transform_path(target_frame, source_frame)
            if path:
                return self._chain_transforms(path)
                
            return None
            
        except Exception as e:
            self.logger.error(f"获取变换失败: {str(e)}")
            return None
            
    def transform_point(self, point: np.ndarray, target_frame: str,
                       source_frame: str) -> Optional[np.ndarray]:
        """变换点坐标
        
        Args:
            point: 源坐标系中的点 [x, y, z]
            target_frame: 目标坐标系
            source_frame: 源坐标系
            
        Returns:
            目标坐标系中的点
        """
        try:
            transform = self.get_transform(target_frame, source_frame)
            if transform is None:
                return None
                
            return transform.rotation @ point + transform.translation
            
        except Exception as e:
            self.logger.error(f"点变换失败: {str(e)}")
            return None
            
    def _find_transform_path(self, target: str, source: str,
                           visited: Optional[List[str]] = None) -> Optional[List[str]]:
        """查找变换路径"""
        if visited is None:
            visited = []
            
        visited.append(source)
        
        # 直接连接
        if source in self.transforms and target in self.transforms[source]:
            return [source, target]
            
        # 递归搜索
        for frame in self.transforms.get(source, {}):
            if frame not in visited:
                path = self._find_transform_path(target, frame, visited)
                if path:
                    return [source] + path[1:]
                    
        return None
        
    def _chain_transforms(self, path: List[str]) -> Transform:
        """链接变换"""
        result = Transform(
            translation=np.zeros(3),
            rotation=np.eye(3),
            timestamp=time.time()
        )
        
        for i in range(len(path) - 1):
            transform = self.get_transform(path[i+1], path[i])
            if transform:
                result.translation = result.rotation @ transform.translation + \
                                   result.translation
                result.rotation = transform.rotation @ result.rotation
                
        return result
        
    def cleanup_cache(self):
        """清理过期缓存"""
        try:
            current_time = time.time()
            for parent in list(self.transforms.keys()):
                for child in list(self.transforms[parent].keys()):
                    transform = self.transforms[parent][child]
                    if current_time - transform.timestamp > self.cache_duration:
                        del self.transforms[parent][child]
                        
                if not self.transforms[parent]:
                    del self.transforms[parent]
                    
        except Exception as e:
            self.logger.error(f"清理缓存失败: {str(e)}") 