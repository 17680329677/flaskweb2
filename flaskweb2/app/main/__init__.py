from flask import Blueprint

main = Blueprint('main', __name__)

from . import views, errors
from ..models import Permission


# 把模板类加入上下文
@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)