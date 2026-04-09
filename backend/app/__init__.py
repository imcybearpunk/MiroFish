"""
MiroFish Backend - Flask应用工厂
"""

import os
import warnings

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 设置JSON编码：确保中文直接显示（而不是 \uXXXX 格式）
    # Flask >= 2.3 使用 app.json.ensure_ascii，旧版本使用 JSON_AS_ASCII 配置
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False

    # 设置日志
    logger = setup_logger('mirofish')

    # 只在 reloader 子进程中打印启动信息（避免 debug 模式下打印两次）
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend 启动中...")
        logger.info("=" * 50)

    # CORS — origins from env var, fallback to localhost for dev
    # Set ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com in production
    allowed_origins_raw = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
    allowed_origins = [o.strip() for o in allowed_origins_raw.split(',') if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
    logger.info(f"CORS habilitado para / CORS enabled for: {allowed_origins}")

    # --- Swagger / OpenAPI docs ---
    try:
        from flasgger import Swagger
        from .api.openapi import SWAGGER_CONFIG, SWAGGER_TEMPLATE
        Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)
        logger.info("Swagger UI disponible en /api/docs")
    except ImportError:
        logger.warning("flasgger no instalado — /api/docs no disponible")

    # Sentry 错误追踪 / Error tracking (only if SENTRY_DSN is configured)
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        logger.info("Sentry 错误追踪已启用 / Sentry error tracking enabled")

    # 速率限制 / Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://",
    )
    logger.info("速率限制已启用 / Rate limiting enabled")

    # 注册模拟进程清理函数（确保服务器关闭时终止所有模拟进程）
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("已注册模拟进程清理函数")

    # 请求ID注入到日志 / Request ID injection into logs
    @app.before_request
    def inject_request_id():
        import uuid
        from .utils.logger import set_request_id
        rid = request.headers.get('X-Request-ID') or str(uuid.uuid4())[:8]
        set_request_id(rid)

    # 认证API密钥中间件 / API key authentication middleware
    # Set API_KEY env var to enable. Leave unset to disable (dev mode).
    _api_key = os.environ.get('API_KEY')

    @app.before_request
    def require_api_key():
        # Skip auth for health check and OPTIONS preflight
        if request.path == '/health' or request.method == 'OPTIONS':
            return None
        if _api_key:
            provided = request.headers.get('X-API-Key') or request.args.get('api_key')
            if provided != _api_key:
                from flask import jsonify as _jsonify
                return _jsonify({'error': 'Unauthorized', 'message': 'Invalid or missing API key'}), 401
        return None

    # 请求日志中间件 / Request logging middleware
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"请求: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"请求体: {request.get_json(silent=True)}")

    # 响应日志中间件 / Response logging middleware
    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"响应: {response.status_code}")
        return response

    # 安全响应头 / Security response headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Only add HSTS in production
        if not debug_mode:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # 指标Prometheus / Prometheus metrics endpoint
    try:
        from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
        import time as _time

        REQUEST_COUNT = Counter('mirofish_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
        REQUEST_LATENCY = Histogram('mirofish_request_duration_seconds', 'Request latency', ['endpoint'])

        @app.before_request
        def start_timer():
            request._start_time = _time.time()

        @app.after_request
        def record_metrics(response):
            latency = _time.time() - getattr(request, '_start_time', _time.time())
            endpoint = request.endpoint or 'unknown'
            REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status=response.status_code).inc()
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)
            return response

        @app.route('/metrics')
        def metrics():
            from flask import Response
            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

        logger.info("Prometheus /metrics habilitado / Prometheus /metrics enabled")
    except ImportError:
        logger.warning("prometheus_client no instalado — /metrics no disponible")

    # 注册蓝图 / Register blueprints
    from .api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')

    # 健康检查 / Health check
    @app.route('/health')
    def health():
        from flask import jsonify
        config_errors = config_class.validate()
        return jsonify({
            'status': 'degraded' if config_errors else 'ok',
            'service': 'MiroFish Backend',
            'version': '0.1.0',
            'config_warnings': config_errors,
        }), 200

    if should_log_startup:
        logger.info("MiroFish Backend 启动完成")

    return app
