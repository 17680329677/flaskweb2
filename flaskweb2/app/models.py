from . import db
# Werkzeug中的security模块能方便的计算密码散列值，generate_password_hash函数生成散列值，check_password_hash验证散列值
from werkzeug.security import generate_password_hash, check_password_hash
# flask_login专门用来管理用户认证系统中的认证状态 且不依赖特定的认证机制
from flask_login import UserMixin
from . import login_manager


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username


# flask_login要求程序实现一个回调函数，使用指定的标识符加载用户，该函数定义如下
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
