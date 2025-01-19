from typing import Dict, Optional
import hashlib
import hmac
import base64
from cryptography.fernet import Fernet
from dataclasses import dataclass

@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str  # 密钥
    enable_encryption: bool = True  # 是否启用加密
    enable_auth: bool = True  # 是否启用认证
    token_expire: int = 3600  # Token过期时间(秒)

class SecurityManager:
    """安全管理器"""
    
    def __init__(self, config: Dict):
        self.config = SecurityConfig(**config)
        self.cipher = Fernet(self._get_or_generate_key())
        
    def encrypt_message(self, message: bytes) -> bytes:
        """加密消息"""
        if not self.config.enable_encryption:
            return message
        return self.cipher.encrypt(message)
        
    def decrypt_message(self, message: bytes) -> bytes:
        """解密消息"""
        if not self.config.enable_encryption:
            return message
        return self.cipher.decrypt(message)
        
    def generate_token(self, client_id: str) -> str:
        """生成认证Token"""
        if not self.config.enable_auth:
            return ""
            
        message = f"{client_id}:{time.time()}"
        signature = hmac.new(
            self.config.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return base64.b64encode(
            f"{message}:{signature}".encode()
        ).decode()
        
    def verify_token(self, token: str) -> bool:
        """验证Token"""
        if not self.config.enable_auth:
            return True
            
        try:
            decoded = base64.b64decode(token.encode()).decode()
            message, signature = decoded.rsplit(":", 1)
            
            expected = hmac.new(
                self.config.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected):
                return False
                
            # 检查过期时间
            client_id, timestamp = message.split(":", 1)
            if time.time() - float(timestamp) > self.config.token_expire:
                return False
                
            return True
            
        except Exception:
            return False
            
    def _get_or_generate_key(self) -> bytes:
        """获取或生成密钥"""
        if not self.config.secret_key:
            self.config.secret_key = Fernet.generate_key().decode()
        return self.config.secret_key.encode() 