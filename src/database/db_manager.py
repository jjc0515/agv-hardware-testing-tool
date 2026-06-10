"""
数据库管理器
"""
import os
from datetime import datetime, timedelta
import yaml
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from src.database.models import Base, AGVDevice, MotorData, BatteryData, NavigationData, LocalizationData, ObstacleData, NetworkData, TestResult, HealthCheck, TrajectoryData

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, config_path='config/database.yaml'):
        """初始化数据库管理器"""
        self.config = self._load_config(config_path)
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._init_database()
    
    def _load_config(self, config_path):
        """加载数据库配置"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config['database']
        except FileNotFoundError:
            logger.warning(f"配置文件 {config_path} 未找到，使用默认配置")
            return {
                'uri': 'sqlite:///agv_test.db',
                'pool': {'size': 20, 'max_overflow': 40},
                'echo': False
            }
    
    def _create_engine(self):
        """创建数据库引擎"""
        uri = self.config.get('uri', 'sqlite:///agv_test.db')
        pool_config = self.config.get('pool', {})
        echo = self.config.get('echo', False)
        
        engine_kwargs = {
            'echo': echo,
            'pool_size': pool_config.get('size', 20),
            'max_overflow': pool_config.get('max_overflow', 40),
            'pool_recycle': pool_config.get('pool_recycle', 3600)
        }
        
        if 'sqlite' not in uri:
            engine_kwargs['pool_pre_ping'] = True
        
        return create_engine(uri, **engine_kwargs)
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("数据库初始化成功")
        except SQLAlchemyError as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    # AGV设备管理
    def add_device(self, serial_number, model_name, agv_type, firmware_version=None):
        """添加AGV设备"""
        session = self.get_session()
        try:
            device = AGVDevice(
                serial_number=serial_number,
                model_name=model_name,
                agv_type=agv_type,
                firmware_version=firmware_version
            )
            session.add(device)
            session.commit()
            logger.info(f"添加设备: {serial_number}")
            return device.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加设备失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_device(self, device_id):
        """获取AGV设备"""
        session = self.get_session()
        try:
            return session.query(AGVDevice).filter(AGVDevice.id == device_id).first()
        finally:
            session.close()
    
    def get_all_devices(self):
        """获取所有AGV设备"""
        session = self.get_session()
        try:
            return session.query(AGVDevice).all()
        finally:
            session.close()
    
    # 电机数据
    def add_motor_data(self, device_id, left_current, right_current, left_speed, right_speed, 
                       left_temperature, right_temperature, voltage):
        """添加电机数据"""
        session = self.get_session()
        try:
            data = MotorData(
                device_id=device_id,
                left_current=left_current,
                right_current=right_current,
                left_speed=left_speed,
                right_speed=right_speed,
                left_temperature=left_temperature,
                right_temperature=right_temperature,
                voltage=voltage
            )
            session.add(data)
            session.commit()
            return data.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加电机数据失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_motor_data(self, device_id, minutes=60):
        """获取电机数据（最近N分钟）"""
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            return session.query(MotorData).filter(
                MotorData.device_id == device_id,
                MotorData.timestamp >= cutoff_time
            ).order_by(MotorData.timestamp.desc()).all()
        finally:
            session.close()
    
    # 电池数据
    def add_battery_data(self, device_id, voltage, current, soc, temperature, health, cycles, remaining_time):
        """添加电池数据"""
        session = self.get_session()
        try:
            data = BatteryData(
                device_id=device_id,
                voltage=voltage,
                current=current,
                soc=soc,
                temperature=temperature,
                health=health,
                cycles=cycles,
                remaining_time=remaining_time
            )
            session.add(data)
            session.commit()
            return data.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加电池数据失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_battery_data(self, device_id, minutes=60):
        """获取电池数据"""
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            return session.query(BatteryData).filter(
                BatteryData.device_id == device_id,
                BatteryData.timestamp >= cutoff_time
            ).order_by(BatteryData.timestamp.desc()).all()
        finally:
            session.close()
    
    # 导航数据
    def add_navigation_data(self, device_id, linear_velocity, angular_velocity, target_x, target_y, 
                           navigation_status, path_progress):
        """添加导航数据"""
        session = self.get_session()
        try:
            data = NavigationData(
                device_id=device_id,
                linear_velocity=linear_velocity,
                angular_velocity=angular_velocity,
                target_x=target_x,
                target_y=target_y,
                navigation_status=navigation_status,
                path_progress=path_progress
            )
            session.add(data)
            session.commit()
            return data.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加导航数据失败: {str(e)}")
            return None
        finally:
            session.close()
    
    # 定位数据
    def add_localization_data(self, device_id, x, y, theta, x_variance, y_variance, 
                             theta_variance, confidence, map_id):
        """添加定位数据"""
        session = self.get_session()
        try:
            data = LocalizationData(
                device_id=device_id,
                x=x,
                y=y,
                theta=theta,
                x_variance=x_variance,
                y_variance=y_variance,
                theta_variance=theta_variance,
                confidence=confidence,
                map_id=map_id
            )
            session.add(data)
            session.commit()
            return data.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加定位数据失败: {str(e)}")
            return None
        finally:
            session.close()
    
    # 避障数据
    def add_obstacle_data(self, device_id, obstacle_detected, min_distance, obstacles_count,
                         obstacle_positions, safety_level, emergency_stop_triggered):
        """添加避障数据"""
        session = self.get_session()
        try:
            data = ObstacleData(
                device_id=device_id,
                obstacle_detected=obstacle_detected,
                min_distance=min_distance,
                obstacles_count=obstacles_count,
                obstacle_positions=obstacle_positions,
                safety_level=safety_level,
                emergency_stop_triggered=emergency_stop_triggered
            )
            session.add(data)
            session.commit()
            return data.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加避障数据失败: {str(e)}")
            return None
        finally:
            session.close()
    
    # 网络数据
    def add_network_data(self, device_id, signal_strength, signal_quality, latency, 
                        packet_loss, bandwidth, protocol, connection_status):
        """添加网络数据"""
        session = self.get_session()
        try:
            data = NetworkData(
                device_id=device_id,
                signal_strength=signal_strength,
                signal_quality=signal_quality,
                latency=latency,
                packet_loss=packet_loss,
                bandwidth=bandwidth,
                protocol=protocol,
                connection_status=connection_status
            )
            session.add(data)
            session.commit()
            return data.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加网络数据失败: {str(e)}")
            return None
        finally:
            session.close()
    
    # 测试结果
    def add_test_result(self, device_id, test_type, test_name, status, result_data, error_message=None, duration=None):
        """添加测试结果"""
        session = self.get_session()
        try:
            data = TestResult(
                device_id=device_id,
                test_type=test_type,
                test_name=test_name,
                status=status,
                result_data=result_data,
                error_message=error_message,
                duration=duration
            )
            session.add(data)
            session.commit()
            return data.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加测试结果失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_test_results(self, device_id, test_type=None, minutes=1440):
        """获取测试结果"""
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            query = session.query(TestResult).filter(
                TestResult.device_id == device_id,
                TestResult.timestamp >= cutoff_time
            )
            if test_type:
                query = query.filter(TestResult.test_type == test_type)
            return query.order_by(TestResult.timestamp.desc()).all()
        finally:
            session.close()
    
    # 轨迹数据
    def add_trajectory_data(self, device_id, test_id, planned_x, planned_y, actual_x, 
                           actual_y, error, cumulative_error):
        """添加轨迹数据"""
        session = self.get_session()
        try:
            data = TrajectoryData(
                device_id=device_id,
                test_id=test_id,
                planned_x=planned_x,
                planned_y=planned_y,
                actual_x=actual_x,
                actual_y=actual_y,
                error=error,
                cumulative_error=cumulative_error
            )
            session.add(data)
            session.commit()
            return data.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加轨迹数据失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_trajectory_data(self, device_id, test_id):
        """获取轨迹数据"""
        session = self.get_session()
        try:
            return session.query(TrajectoryData).filter(
                TrajectoryData.device_id == device_id,
                TrajectoryData.test_id == test_id
            ).order_by(TrajectoryData.timestamp).all()
        finally:
            session.close()
    
    # 健康检查
    def add_health_check(self, device_id, motor_health, battery_health, sensor_health, 
                        communication_health, overall_health, issues):
        """添加健康检查记录"""
        session = self.get_session()
        try:
            data = HealthCheck(
                device_id=device_id,
                motor_health=motor_health,
                battery_health=battery_health,
                sensor_health=sensor_health,
                communication_health=communication_health,
                overall_health=overall_health,
                issues=issues
            )
            session.add(data)
            session.commit()
            return data.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加健康检查记录失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def cleanup_old_data(self, days=30):
        """清理旧数据"""
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            tables = [MotorData, BatteryData, NavigationData, LocalizationData, 
                     ObstacleData, NetworkData, TrajectoryData]
            
            deleted_count = 0
            for table in tables:
                count = session.query(table).filter(table.timestamp < cutoff_time).delete()
                deleted_count += count
            
            session.commit()
            logger.info(f"清理了 {deleted_count} 条旧数据")
            return deleted_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"清理旧数据失败: {str(e)}")
            return 0
        finally:
            session.close()
