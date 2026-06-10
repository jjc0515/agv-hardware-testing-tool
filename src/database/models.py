"""
数据库模型定义
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AGVDevice(Base):
    """AGV设备表"""
    __tablename__ = 'agv_devices'
    
    id = Column(Integer, primary_key=True)
    serial_number = Column(String(50), unique=True, nullable=False)
    model_name = Column(String(50), nullable=False)
    agv_type = Column(String(20), nullable=False)  # warehouse, factory
    firmware_version = Column(String(20))
    status = Column(String(20), default='online')  # online, offline, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    motor_data = relationship('MotorData', back_populates='device')
    battery_data = relationship('BatteryData', back_populates='device')
    navigation_data = relationship('NavigationData', back_populates='device')
    localization_data = relationship('LocalizationData', back_populates='device')
    obstacle_data = relationship('ObstacleData', back_populates='device')
    network_data = relationship('NetworkData', back_populates='device')
    test_results = relationship('TestResult', back_populates='device')


class MotorData(Base):
    """电机数据表"""
    __tablename__ = 'motor_data'
    __table_args__ = (Index('idx_device_timestamp', 'device_id', 'timestamp'),)
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('agv_devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    left_current = Column(Float)  # 左电机电流 (A)
    right_current = Column(Float)  # 右电机电流 (A)
    left_speed = Column(Float)  # 左电机速度 (m/s)
    right_speed = Column(Float)  # 右电机速度 (m/s)
    left_temperature = Column(Float)  # 左电机温度 (°C)
    right_temperature = Column(Float)  # 右电机温度 (°C)
    voltage = Column(Float)  # 供电电压 (V)
    
    device = relationship('AGVDevice', back_populates='motor_data')


class BatteryData(Base):
    """电池数据表"""
    __tablename__ = 'battery_data'
    __table_args__ = (Index('idx_device_timestamp', 'device_id', 'timestamp'),)
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('agv_devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    voltage = Column(Float)  # 电压 (V)
    current = Column(Float)  # 电流 (A)
    soc = Column(Float)  # 剩余电量 (%)
    temperature = Column(Float)  # 温度 (°C)
    health = Column(Float)  # 健康度 (%)
    cycles = Column(Integer)  # 充放电循环次数
    remaining_time = Column(Integer)  # 预计续航时间 (分钟)
    
    device = relationship('AGVDevice', back_populates='battery_data')


class NavigationData(Base):
    """导航数据表"""
    __tablename__ = 'navigation_data'
    __table_args__ = (Index('idx_device_timestamp', 'device_id', 'timestamp'),)
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('agv_devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    linear_velocity = Column(Float)  # 线速度 (m/s)
    angular_velocity = Column(Float)  # 角速度 (rad/s)
    target_x = Column(Float)  # 目标X坐标 (m)
    target_y = Column(Float)  # 目标Y坐标 (m)
    navigation_status = Column(String(20))  # idle, moving, blocked
    path_progress = Column(Float)  # 路径进度 (%)
    
    device = relationship('AGVDevice', back_populates='navigation_data')


class LocalizationData(Base):
    """定位数据表"""
    __tablename__ = 'localization_data'
    __table_args__ = (Index('idx_device_timestamp', 'device_id', 'timestamp'),)
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('agv_devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    x = Column(Float)  # X坐标 (m)
    y = Column(Float)  # Y坐标 (m)
    theta = Column(Float)  # 角度 (rad)
    x_variance = Column(Float)  # X方差
    y_variance = Column(Float)  # Y方差
    theta_variance = Column(Float)  # θ方差
    confidence = Column(Float)  # 置信度 (0-1)
    map_id = Column(String(50))  # 地图ID
    
    device = relationship('AGVDevice', back_populates='localization_data')


class ObstacleData(Base):
    """避障数据表"""
    __tablename__ = 'obstacle_data'
    __table_args__ = (Index('idx_device_timestamp', 'device_id', 'timestamp'),)
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('agv_devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    obstacle_detected = Column(Boolean)  # 是否检测到障碍物
    min_distance = Column(Float)  # 最小距离 (m)
    obstacles_count = Column(Integer)  # 障碍物数量
    obstacle_positions = Column(JSON)  # 障碍物位置JSON
    safety_level = Column(String(10))  # safe, warning, critical
    emergency_stop_triggered = Column(Boolean)  # 是否触发紧急停止
    
    device = relationship('AGVDevice', back_populates='obstacle_data')


class NetworkData(Base):
    """网络数据表"""
    __tablename__ = 'network_data'
    __table_args__ = (Index('idx_device_timestamp', 'device_id', 'timestamp'),)
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('agv_devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    signal_strength = Column(Float)  # 信号强度 (dBm)
    signal_quality = Column(Float)  # 信号质量 (%)
    latency = Column(Float)  # 延迟 (ms)
    packet_loss = Column(Float)  # 丢包率 (%)
    bandwidth = Column(Float)  # 带宽 (Mbps)
    protocol = Column(String(20))  # http, custom, ros
    connection_status = Column(String(20))  # connected, disconnected
    
    device = relationship('AGVDevice', back_populates='network_data')


class TestResult(Base):
    """测试结果表"""
    __tablename__ = 'test_results'
    __table_args__ = (Index('idx_device_timestamp', 'device_id', 'timestamp'),)
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('agv_devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    test_type = Column(String(50))  # motor, battery, navigation, localization等
    test_name = Column(String(100))
    status = Column(String(20))  # pass, fail, warning
    result_data = Column(JSON)  # 详细结果数据
    error_message = Column(String(500))  # 错误信息
    duration = Column(Float)  # 测试耗时 (秒)
    
    device = relationship('AGVDevice', back_populates='test_results')


class HealthCheck(Base):
    """硬件健康检查表"""
    __tablename__ = 'health_checks'
    __table_args__ = (Index('idx_device_timestamp', 'device_id', 'timestamp'),)
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('agv_devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    motor_health = Column(Float)  # 电机健康度 (%)
    battery_health = Column(Float)  # 电池健康度 (%)
    sensor_health = Column(Float)  # 传感器健康度 (%)
    communication_health = Column(Float)  # 通信健康度 (%)
    overall_health = Column(Float)  # 整体健康度 (%)
    issues = Column(JSON)  # 问题列表


class TrajectoryData(Base):
    """轨迹数据表"""
    __tablename__ = 'trajectory_data'
    __table_args__ = (Index('idx_device_timestamp', 'device_id', 'timestamp'),)
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('agv_devices.id'), nullable=False)
    test_id = Column(String(50))  # 测试ID
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    planned_x = Column(Float)  # 计划X坐标
    planned_y = Column(Float)  # 计划Y坐标
    actual_x = Column(Float)  # 实际X坐标
    actual_y = Column(Float)  # 实际Y坐标
    error = Column(Float)  # 误差 (m)
    cumulative_error = Column(Float)  # 累计误差
