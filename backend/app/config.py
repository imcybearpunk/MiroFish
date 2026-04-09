"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
import secrets
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)


class Config:
    """Flask配置类"""

    # Flask配置
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    @classmethod
    def _get_secret_key(cls):
        """获取SECRET_KEY，在生产环境中必须配置"""
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            if cls.DEBUG:
                # 开发模式：警告但继续工作，生成临时密钥
                import warnings
                warnings.warn(
                    "SECRET_KEY 未配置！在开发模式下使用临时密钥。"
                    "对于生产环境，必须设置 SECRET_KEY 环境变量。"
                    f"示例密钥: {secrets.token_hex(32)}",
                    RuntimeWarning
                )
                return secrets.token_hex(32)
            else:
                # 生产模式：必须配置
                raise ValueError(
                    "SECRET_KEY 环境变量未配置！\n"
                    "在生产环境（DEBUG=False）中必须显式设置 SECRET_KEY。\n"
                    f"示例：export SECRET_KEY={secrets.token_hex(32)}"
                )
        return secret_key

    SECRET_KEY = None  # 将在应用启动时通过 _get_secret_key() 设置
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_MB', '25')) * 1024 * 1024  # 25MB default, configurable
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    @classmethod
    def validate(cls):
        """验证必要配置"""
        errors = []

        # 验证SECRET_KEY
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            if not cls.DEBUG:
                errors.append(
                    "SECRET_KEY 未配置。生产环境（DEBUG=False）必须设置此值。"
                )
        elif secret_key == 'mirofish-secret-key':
            errors.append(
                "SECRET_KEY 使用了默认硬编码值！必须在 .env 中设置唯一的密钥。"
            )

        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY 未配置")
        return errors


# 在配置类加载时初始化SECRET_KEY
Config.SECRET_KEY = Config._get_secret_key()

