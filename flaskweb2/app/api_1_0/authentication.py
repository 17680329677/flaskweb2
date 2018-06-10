# 因为REST架构基于HTTP协议，所以发送密令的最佳方式是使用HTTP认证，基本认证和摘要认证都可以，在HTTP认证中，用户密令包含在请求的Authorization首部中
# HTTP认证协议很简单，可以直接实现，但Flask-HTTPAuth扩展提供了一个便利的包装，可以把协议的细节隐藏在修饰器中，类似于Flask-Login提供的login_required修饰器
from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth
from ..models import User
from . import api
from .errors import forbidden, unauthorized

auth = HTTPBasicAuth()


# 验证回调函数， 该函数将通过验证的用户保存在Flask全局对象g中，如此一来，视图函数便能进行访问
@auth.verify_password
def verify_password(email_or_token, password):
    if email_or_token == '':
        return False
    if password == '':
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


# 在before_request处理程序中进行认证
@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and not g.current_user.confirmed:
        return forbidden('Unconfirmed account')


# 把认证令牌发送给客户端的路由也要添加到API蓝本中,生成认证令牌
@api.route('/token/', methods=['GET', 'POST'])
def get_token():
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized('Invalid credentials')
    # json格式响应也包含过期时间
    return jsonify({'token': g.current_user.generate_auth_token(expiration=3600), 'expiration': 3600})


