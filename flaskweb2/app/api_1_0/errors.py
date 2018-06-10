# 其他状态码都由Web服务生成，因此可在蓝本的errors.py模块作为辅助函数实现

from flask import jsonify
from app.exceptions import ValidationError
from . import api


# API蓝本中400状态码的错误处理程序
def bad_request(message):
    response = jsonify({'error': 'bad_request', 'message':message})
    response.status_code = 400
    return response


# API蓝本中403状态码的错误处理程序
def forbidden(message):
    response = jsonify({'error': 'forbidden', 'message': message})
    response.status_code = 403
    return response


# API蓝本中未授权错误的处理程序
def unauthorized(message):
    response = jsonify({'error': 'unauthorized', 'message': message})
    response.status_code = 401
    return response


# 为了避免在视图函数中编写捕获异常的代码，我们创建一个全局异常处理程序，对于ValidationError异常，其处理程序如下
@api.errorhandler(ValidationError)
def validation_error(e):
    return bad_request(e.args[0])

