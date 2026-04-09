"""
日志配置模块
提供统一的日志管理，同时输出到控制台和文件
支持生产环境 JSON 结构化日志和开发环境人类可读格式
"""

import os
import sys
import json
import logging
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler


# 请求 ID 的线程本地存储
_request_id_context = threading.local()


def set_request_id(rid: str) -> None:
    """
    设置当前请求的 ID
    使用线程本地存储确保线程隔离

    Args:
        rid: 请求 ID
    """
    _request_id_context.id = rid


def get_request_id() -> str:
    """
    获取当前请求的 ID

    Returns:
        请求 ID，如果未设置则返回 '-'
    """
    return getattr(_request_id_context, 'id', '-')


def _ensure_utf8_stdout():
    """
    确保 stdout/stderr 使用 UTF-8 编码
    解决 Windows 控制台中文乱码问题
    """
    if sys.platform == 'win32':
        # Windows 下重新配置标准输出为 UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')


class JSONFormatter(logging.Formatter):
    """
    生产环境用的 JSON 结构化日志格式化器
    输出格式: {"timestamp":"...","level":"...","logger":"...","function":"...","line":N,"message":"...","request_id":"..."}
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        将日志记录格式化为 JSON

        Args:
            record: 日志记录

        Returns:
            JSON 格式的日志字符串
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'request_id': get_request_id()
        }

        # 如果有异常信息，添加到日志
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class DevelopmentFormatter(logging.Formatter):
    """
    开发环境用的人类可读日志格式化器
    """
    pass


# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')


def setup_logger(name: str = 'mirofish', level: int = logging.DEBUG) -> logging.Logger:
    """
    设置日志器

    根据 FLASK_DEBUG 环境变量判断是否为开发模式：
    - FLASK_DEBUG != 'true': 生产模式，使用 JSON 结构化日志
    - FLASK_DEBUG == 'true': 开发模式，使用人类可读格式

    Args:
        name: 日志器名称
        level: 日志级别

    Returns:
        配置好的日志器
    """
    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)

    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 阻止日志向上传播到根 logger，避免重复输出
    logger.propagate = False

    # 如果已经有处理器，不重复添加
    if logger.handlers:
        return logger

    # 判断是否为开发模式
    is_debug = os.environ.get('FLASK_DEBUG', '').lower() == 'true'

    if is_debug:
        # 开发模式：人类可读格式
        detailed_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        simple_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        # 生产模式：JSON 结构化日志
        detailed_formatter = JSONFormatter()
        simple_formatter = JSONFormatter()

    # 1. 文件处理器 - 详细日志（按日期命名，带轮转）
    log_filename = datetime.now().strftime('%Y-%m-%d') + '.log'
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, log_filename),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # 2. 控制台处理器 - 简洁日志（INFO及以上）
    # 确保 Windows 下使用 UTF-8 编码，避免中文乱码
    _ensure_utf8_stdout()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = 'mirofish') -> logging.Logger:
    """
    获取日志器（如果不存在则创建）

    Args:
        name: 日志器名称

    Returns:
        日志器实例
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


# 创建默认日志器
logger = setup_logger()


# 便捷方法
def debug(msg, *args, **kwargs):
    """记录 DEBUG 级别日志"""
    logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    """记录 INFO 级别日志"""
    logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """记录 WARNING 级别日志"""
    logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """记录 ERROR 级别日志"""
    logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    """记录 CRITICAL 级别日志"""
    logger.critical(msg, *args, **kwargs)
