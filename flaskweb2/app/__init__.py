# 程序包的构造文件 延迟创建程序实例，把创建过程移到可显示调用的工厂函数中
from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_login import LoginManager
from flask_pagedown import PageDown

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()
# flask_login在程序的工厂函数中初始化
login_manager = LoginManager()
# LoginManager对象的session_protection属性可以设为None， ‘basic’或‘strong’
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'


# 工厂函数
def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(Config[config_name])
    Config[config_name].init_app(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    # 附加路由和自定义的错误页面

    # 注册蓝本
    from .main import main as main_blueprint
    from .auth import auth as auth_blueprint
    app.register_blueprint(main_blueprint)
    # url_prefix是可选参数 使用这个参数后，注册后蓝本中定义的所有路由都会加上指定的前缀
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    return app

