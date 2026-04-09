"""
OpenAPI / Swagger configuration
Auto-generated API documentation available at /api/docs
Install: pip install flasgger
"""

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/api/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "MiroFish API",
        "description": (
            "MiroFish — Multi-Agent Social Simulation Platform. "
            "Build knowledge graphs, run AI agent simulations, generate reports."
        ),
        "version": "1.0.0",
        "contact": {
            "name": "MiroFish",
            "url": "https://github.com/666ghj/MiroFish",
        },
        "license": {
            "name": "AGPL-3.0",
            "url": "https://www.gnu.org/licenses/agpl-3.0.html",
        },
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Optional API key auth. Set API_KEY env var to enable.",
        }
    },
    "tags": [
        {"name": "health", "description": "Health check"},
        {"name": "graph", "description": "Knowledge graph operations"},
        {"name": "simulation", "description": "Agent simulation"},
        {"name": "report", "description": "Report generation"},
    ],
    "definitions": {
        "Error": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "example": False},
                "error": {"type": "string", "example": "Error description"},
            },
        },
        "Success": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "example": True},
                "message": {"type": "string"},
            },
        },
    },
}
