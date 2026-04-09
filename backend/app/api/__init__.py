"""
API路由模块
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)

from . import graph_project  # noqa: E402, F401
from . import graph_ontology  # noqa: E402, F401
from . import graph_build  # noqa: E402, F401
from . import graph_query  # noqa: E402, F401
from . import simulation_helpers  # noqa: E402, F401
from . import simulation_entities  # noqa: E402, F401
from . import simulation_setup  # noqa: E402, F401
from . import simulation_run  # noqa: E402, F401
from . import simulation_status  # noqa: E402, F401
from . import simulation_data  # noqa: E402, F401
from . import simulation_interview  # noqa: E402, F401
from . import report  # noqa: E402, F401

