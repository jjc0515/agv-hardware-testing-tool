"""
通信协议处理器
支持HTTP API、自定义协议和ROS三种方式
"""
import json
import socket
import struct
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ProtocolHandler(ABC):
    """协议处理基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """连接到AGV"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass
    
    @abstractmethod
    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """发送命令"""
        pass
    
    @abstractmethod
    def receive_data(self) -> Optional[Dict[str, Any]]:
        """接收数据"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass


class HTTPAPIHandler(ProtocolHandler):
    """HTTP API协议处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = f"http://{config.get('host', 'localhost')}:{config.get('port', 8080)}"
        self.session = self._create_session()
        self.timeout = config.get('timeout', 10)
    
    def _create_session(self):
        """创建带重试机制的HTTP会话"""
        session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def connect(self) -> bool:
        """连接到HTTP API服务"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            self.connected = response.status_code == 200
            if self.connected:
                logger.info(f"成功连接到HTTP API: {self.base_url}")
            return self.connected
        except Exception as e:
            logger.error(f"HTTP API连接失败: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """断开HTTP连接"""
        self.session.close()
        self.connected = False
        return True
    
    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """发送HTTP命令"""
        if not self.connected:
            return {'success': False, 'error': '未连接到服务器'}
        
        try:
            endpoint = command.get('endpoint', '/api/command')
            method = command.get('method', 'POST').upper()
            payload = command.get('payload', {})
            
            url = f"{self.base_url}{endpoint}"
            
            if method == 'GET':
                response = self.session.get(url, params=payload, timeout=self.timeout)
            elif method == 'POST':
                response = self.session.post(url, json=payload, timeout=self.timeout)
            elif method == 'PUT':
                response = self.session.put(url, json=payload, timeout=self.timeout)
            else:
                return {'success': False, 'error': f'不支持的方法: {method}'}
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'success': False, 'error': f'HTTP错误: {response.status_code}'}
        except Exception as e:
            logger.error(f"发送HTTP命令失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def receive_data(self) -> Optional[Dict[str, Any]]:
        """从HTTP API获取数据"""
        try:
            response = self.session.get(f"{self.base_url}/api/data", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"获取HTTP数据失败: {str(e)}")
            return None
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected


class CustomProtocolHandler(ProtocolHandler):
    """自定义协议处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5000)
        self.socket = None
        self.buffer_size = config.get('buffer_size', 4096)
        self.timeout = config.get('timeout', 10)
    
    def connect(self) -> bool:
        """建立Socket连接"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"成功连接到自定义协议服务: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"自定义协议连接失败: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """断开Socket连接"""
        if self.socket:
            self.socket.close()
        self.connected = False
        return True
    
    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """发送自定义协议命令"""
        if not self.connected:
            return {'success': False, 'error': '未连接到服务器'}
        
        try:
            # 协议格式: [消息类型(1字节)][数据长度(4字节)][数据(JSON)]
            msg_type = command.get('type', 1).to_bytes(1, byteorder='big')
            payload = json.dumps(command.get('payload', {})).encode('utf-8')
            data_len = len(payload).to_bytes(4, byteorder='big')
            
            message = msg_type + data_len + payload
            self.socket.sendall(message)
            
            # 接收响应
            response_type = self.socket.recv(1)
            if not response_type:
                return {'success': False, 'error': '连接已关闭'}
            
            response_len_bytes = self.socket.recv(4)
            response_len = struct.unpack('>I', response_len_bytes)[0]
            response_data = self.socket.recv(response_len)
            
            return json.loads(response_data.decode('utf-8'))
        except Exception as e:
            logger.error(f"发送自定义协议命令失败: {str(e)}")
            self.connected = False
            return {'success': False, 'error': str(e)}
    
    def receive_data(self) -> Optional[Dict[str, Any]]:
        """接收自定义协议数据"""
        if not self.connected:
            return None
        
        try:
            msg_type = self.socket.recv(1)
            if not msg_type:
                self.connected = False
                return None
            
            data_len_bytes = self.socket.recv(4)
            data_len = struct.unpack('>I', data_len_bytes)[0]
            data = self.socket.recv(data_len)
            
            return json.loads(data.decode('utf-8'))
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"接收自定义协议数据失败: {str(e)}")
            self.connected = False
            return None
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self.connected or not self.socket:
            return False
        
        try:
            # 尝试发送心跳包检查连接
            self.socket.send(b'\x00')
            return True
        except:
            self.connected = False
            return False


class ROSBridgeHandler(ProtocolHandler):
    """ROS协议处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.master_uri = config.get('master_uri', 'http://localhost:11311')
        self.node_name = config.get('node_name', '/agv_tester')
        self.client = None
        
        # 尝试导入ROS
        try:
            import rospy
            self.rospy = rospy
            self.has_ros = True
        except ImportError:
            logger.warning("ROS未安装，ROS功能将不可用")
            self.has_ros = False
    
    def connect(self) -> bool:
        """连接ROS"""
        if not self.has_ros:
            logger.error("ROS未安装")
            return False
        
        try:
            self.rospy.init_node(self.node_name)
            self.connected = True
            logger.info("成功连接到ROS")
            return True
        except Exception as e:
            logger.error(f"ROS连接失败: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """断开ROS连接"""
        if self.has_ros and self.connected:
            self.rospy.signal_shutdown("测试完成")
        self.connected = False
        return True
    
    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """通过ROS发送命令"""
        if not self.connected or not self.has_ros:
            return {'success': False, 'error': 'ROS未连接或未安装'}
        
        try:
            topic = command.get('topic', '/agv/command')
            data = command.get('data', {})
            
            # 这里需要根据具体的ROS消息类型发布
            # 示例实现
            logger.info(f"ROS命令发布到主题: {topic}")
            return {'success': True, 'message': '命令已发布'}
        except Exception as e:
            logger.error(f"ROS命令发送失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def receive_data(self) -> Optional[Dict[str, Any]]:
        """接收ROS数据"""
        if not self.connected or not self.has_ros:
            return None
        
        try:
            # 这里需要订阅ROS主题并接收数据
            # 示例实现
            return {'data': '来自ROS的数据'}
        except Exception as e:
            logger.error(f"ROS数据接收失败: {str(e)}")
            return None
    
    def is_connected(self) -> bool:
        """检查ROS连接状态"""
        if not self.has_ros:
            return False
        return self.connected


class ProtocolFactory:
    """协议工厂类"""
    
    _handlers = {
        'http': HTTPAPIHandler,
        'custom': CustomProtocolHandler,
        'ros': ROSBridgeHandler
    }
    
    @classmethod
    def create_handler(cls, protocol_type: str, config: Dict[str, Any]) -> Optional[ProtocolHandler]:
        """创建协议处理器"""
        handler_class = cls._handlers.get(protocol_type.lower())
        if not handler_class:
            logger.error(f"不支持的协议类型: {protocol_type}")
            return None
        
        return handler_class(config)
    
    @classmethod
    def register_handler(cls, protocol_type: str, handler_class):
        """注册新的协议处理器"""
        cls._handlers[protocol_type.lower()] = handler_class
