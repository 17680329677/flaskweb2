# 在蓝本中定义的路由处于休眠状态，直到蓝本注册到程序上后
from flask import render_template, request, jsonify
from . import main

# 为所有客户端生成适当响应的一种方式是，在错误处理程序中根据客户端请求的格式改写响应，这种技术成为内容协商


# 新版本的错误处理程序检查Accept请求首部（Werkzeug将其解码为request.accept_mimetypes），根据首部的值决定客户端期望接收的响应格式
# 浏览器一般不限制响应的格式，所以只为接受JSON格式而不接受HTML格式的客户端生成JSON格式响应
# 以下改写403错误处理程序，它向Web服务客户端发送JSON格式响应，除此之外都发送HTML格式响应
@main.app_errorhandler(403)
def forbidden(e):
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return render_template('403.html'), 403


# 以下改写404错误处理程序，它向Web服务客户端发送JSON格式响应，除此之外都发送HTML格式响应
@main.app_errorhandler(404)
def page_not_found(e):
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('404.html'), 404


# 以下改写500错误处理程序，它向Web服务客户端发送JSON格式响应，除此之外都发送HTML格式响应
@main.app_errorhandler(500)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return render_template('500.html'), 500
