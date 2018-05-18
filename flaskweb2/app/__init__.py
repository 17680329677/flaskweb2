# 程序包的构造文件 延迟创建程序实例，把创建过程移到可显示调用的工厂函数中
from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import Config

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()


# 工厂函数
def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(Config[config_name])
    Config[config_name].init_app(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)

    # 附加路由和自定义的错误页面

    # 注册蓝本
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app

