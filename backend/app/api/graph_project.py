"""
项目管理API路由
Project management API routes
"""

from __future__ import annotations

import os
from flask import request, jsonify, Response

from . import graph_bp
from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import t
from ..models.project import ProjectManager, ProjectStatus

# 获取日志器
logger = get_logger('mirofish.api')


def allowed_file(filename: str) -> bool:
    """
    验证文件扩展名是否允许 / Check if file extension is allowed.
    First layer of validation — extension check only.
    Use validate_file_magic() for full magic byte validation.
    """
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


def validate_file_magic(file_stream: any, filename: str) -> tuple[bool, str]:
    """
    Validate file using magic bytes (content inspection).
    Second layer of validation — ensures file content matches declared extension.

    文件内容验证（魔数检查）/ Magic byte validation.
    确保文件内容与声明的扩展名一致 / Ensures content matches extension.

    Args:
        file_stream: file-like object (e.g. from request.files)
        filename: original filename for extension context

    Returns:
        (is_valid: bool, reason: str)
    """
    ext = os.path.splitext(filename)[1].lower().lstrip('.')

    try:
        import magic
        # Read first 2KB for magic detection, then reset stream
        header = file_stream.read(2048)
        file_stream.seek(0)

        mime = magic.from_buffer(header, mime=True)

        ALLOWED_MIMES = {
            'pdf': ['application/pdf'],
            'txt': ['text/plain'],
            'md': ['text/plain', 'text/markdown', 'text/x-markdown'],
            'markdown': ['text/plain', 'text/markdown', 'text/x-markdown'],
        }

        allowed = ALLOWED_MIMES.get(ext, [])
        if not allowed:
            return False, f"Extension '{ext}' not in allowed list"

        if mime not in allowed:
            return False, f"File content ({mime}) does not match extension (.{ext})"

        return True, "ok"

    except ImportError:
        # python-magic not installed — fall back to extension-only check
        logger.warning("python-magic no instalado — usando solo validación por extensión / falling back to extension-only validation")
        file_stream.seek(0)
        return True, "magic_unavailable"
    except Exception as e:
        logger.warning(f"Error en validación magic bytes: {e} — usando extensión")
        file_stream.seek(0)
        return True, "magic_error"


@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str) -> tuple[Response, int] | Response:
    """
    获取项目详情
    """
    project = ProjectManager.get_project(project_id)

    if not project:
        return jsonify({
            "success": False,
            "error": t('api.projectNotFound', id=project_id)
        }), 404

    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects() -> Response:
    """
    列出所有项目
    """
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)

    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str) -> tuple[Response, int] | Response:
    """
    删除项目
    """
    success = ProjectManager.delete_project(project_id)

    if not success:
        return jsonify({
            "success": False,
            "error": t('api.projectDeleteFailed', id=project_id)
        }), 404

    return jsonify({
        "success": True,
        "message": t('api.projectDeleted', id=project_id)
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str) -> tuple[Response, int] | Response:
    """
    重置项目状态（用于重新构建图谱）
    """
    project = ProjectManager.get_project(project_id)

    if not project:
        return jsonify({
            "success": False,
            "error": t('api.projectNotFound', id=project_id)
        }), 404

    # 重置到本体已生成状态
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED

    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.save_project(project)

    return jsonify({
        "success": True,
        "message": t('api.projectReset', id=project_id),
        "data": project.to_dict()
    })
