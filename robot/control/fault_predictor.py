from typing import Dict, List, Optional
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
import statsmodels.api as sm
from scipy import stats
from .performance_monitor import PerformanceMetrics

class FaultPredictor:
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """故障预测器"""
        self.logger = logger or logging.getLogger('FaultPredictor')
        self.config = config
        
        # 数据预处理
        self.scaler = StandardScaler()
        self.feature_buffer: List[np.ndarray] = []
        self.sequence_length = config.get('sequence_length', 100)
        
        # 特征工程
        self.feature_extractors = {
            'statistical': self._extract_statistical_features,
            'frequency': self._extract_frequency_features,
            'trend': self._extract_trend_features
        }
        
        # 预处理器
        self.preprocessors = {
            'scaler': StandardScaler(),
            'pca': PCA(n_components=0.95),
            'outlier_detector': IsolationForest(contamination=0.1)
        }
        
        # 集成模型
        self.models = {
            'rf': RandomForestClassifier(n_estimators=100),
            'svr': SVR(kernel='rbf'),
            'mlp': MLPRegressor(hidden_layer_sizes=(64, 32))
        }
        
        # 模型权重
        self.model_weights = {
            'rf': 0.4,
            'svr': 0.3,
            'mlp': 0.3
        }
        
        # 故障阈值
        self.fault_threshold = config.get('fault_threshold', 0.8)
        
    def _extract_statistical_features(self, data: np.ndarray) -> np.ndarray:
        """提取统计特征"""
        features = []
        
        # 基本统计量
        features.extend([
            np.mean(data, axis=0),
            np.std(data, axis=0),
            np.median(data, axis=0),
            np.percentile(data, 25, axis=0),
            np.percentile(data, 75, axis=0)
        ])
        
        # 高阶统计量
        features.extend([
            stats.skew(data, axis=0),
            stats.kurtosis(data, axis=0)
        ])
        
        return np.concatenate(features)
        
    def _extract_frequency_features(self, data: np.ndarray) -> np.ndarray:
        """提取频域特征"""
        features = []
        
        # FFT变换
        fft_values = np.fft.fft(data, axis=0)
        frequencies = np.fft.fftfreq(len(data))
        
        # 主要频率分量
        for i in range(data.shape[1]):
            freq_magnitudes = np.abs(fft_values[:, i])
            peak_indices = np.argsort(freq_magnitudes)[-3:]  # 取前3个峰值
            
            features.extend([
                frequencies[peak_indices],
                freq_magnitudes[peak_indices]
            ])
            
        return np.array(features).flatten()
        
    def _extract_trend_features(self, data: np.ndarray) -> np.ndarray:
        """提取趋势特征"""
        features = []
        
        # 线性趋势
        for i in range(data.shape[1]):
            slope, intercept = np.polyfit(range(len(data)), data[:, i], 1)
            features.extend([slope, intercept])
            
        # 变化率
        features.extend(np.mean(np.diff(data, axis=0), axis=0))
        
        # 周期性检测
        for i in range(data.shape[1]):
            acf = sm.tsa.acf(data[:, i], nlags=10)
            features.extend(acf[1:])  # 去除lag=0的自相关
            
        return np.array(features)
        
    def _preprocess_features(self, features: np.ndarray) -> np.ndarray:
        """预处理特征"""
        # 标准化
        features = self.preprocessors['scaler'].fit_transform(features)
        
        # 降维
        features = self.preprocessors['pca'].fit_transform(features)
        
        # 异常检测
        outliers = self.preprocessors['outlier_detector'].fit_predict(features)
        features = features[outliers == 1]  # 保留非异常样本
        
        return features
        
    def _ensemble_predict(self, features: np.ndarray) -> float:
        """集成预测"""
        predictions = []
        
        # 随机森林预测
        rf_prob = self.models['rf'].predict_proba(features)[:, 1]
        predictions.append(rf_prob * self.model_weights['rf'])
        
        # SVR预测
        svr_pred = self.models['svr'].predict(features)
        svr_prob = 1 / (1 + np.exp(-svr_pred))  # sigmoid转换
        predictions.append(svr_prob * self.model_weights['svr'])
        
        # MLP预测
        mlp_pred = self.models['mlp'].predict(features)
        mlp_prob = 1 / (1 + np.exp(-mlp_pred))  # sigmoid转换
        predictions.append(mlp_prob * self.model_weights['mlp'])
        
        # 加权平均
        return np.mean(predictions)
        
    def update(self, metrics: PerformanceMetrics) -> float:
        """更新预测"""
        # 提取基础特征
        base_features = self._extract_features(metrics)
        self.feature_buffer.append(base_features)
        
        # 保持固定长度
        if len(self.feature_buffer) > self.sequence_length:
            self.feature_buffer.pop(0)
            
        # 预测故障概率
        if len(self.feature_buffer) == self.sequence_length:
            # 提取高级特征
            data = np.stack(self.feature_buffer)
            features = []
            
            for extractor in self.feature_extractors.values():
                features.append(extractor(data))
                
            # 合并特征
            combined_features = np.concatenate(features)
            
            # 预处理
            processed_features = self._preprocess_features(combined_features.reshape(1, -1))
            
            # 集成预测
            return self._ensemble_predict(processed_features)
            
        return 0.0
        
    def _extract_features(self, metrics: PerformanceMetrics) -> np.ndarray:
        """提取基础特征"""
        features = [
            metrics.mse,
            metrics.mae,
            metrics.latency,
            metrics.cpu_usage,
            metrics.memory_usage,
            metrics.network_usage
        ]
        return np.array(features)
        
    def check_fault(self, prob: float) -> Optional[Dict]:
        """检查故障"""
        if prob > self.fault_threshold:
            return {
                'probability': prob,
                'threshold': self.fault_threshold,
                'features': self.feature_buffer[-1].tolist(),
                'trend': self._analyze_trend(),
                'pattern': self._detect_pattern()
            }
        return None
        
    def _analyze_trend(self) -> Dict:
        """分析趋势"""
        if len(self.feature_buffer) < 2:
            return {}
            
        recent_data = np.stack(self.feature_buffer[-10:])
        trends = {}
        
        for i in range(recent_data.shape[1]):
            # 计算趋势
            slope, _, r_value, _, _ = stats.linregress(
                range(len(recent_data)),
                recent_data[:, i]
            )
            
            trends[f'feature_{i}'] = {
                'slope': slope,
                'r_squared': r_value ** 2
            }
            
        return trends
        
    def _detect_pattern(self) -> Dict:
        """检测模式"""
        if len(self.feature_buffer) < self.sequence_length:
            return {}
            
        data = np.stack(self.feature_buffer)
        patterns = {}
        
        for i in range(data.shape[1]):
            # 周期性检测
            acf = sm.tsa.acf(data[:, i], nlags=20)
            
            # 查找显著的自相关
            significant_lags = np.where(np.abs(acf[1:]) > 0.3)[0] + 1
            
            if len(significant_lags) > 0:
                patterns[f'feature_{i}'] = {
                    'periodic': True,
                    'periods': significant_lags.tolist(),
                    'strength': acf[significant_lags].tolist()
                }
            else:
                patterns[f'feature_{i}'] = {
                    'periodic': False
                }
                
        return patterns 