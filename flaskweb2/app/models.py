from . import db
# Werkzeug中的security模块能方便的计算密码散列值，generate_password_hash函数生成散列值，check_password_hash验证散列值
from werkzeug.security import generate_password_hash, check_password_hash
# flask_login专门用来管理用户认证系统中的认证状态 且不依赖特定的认证机制
from flask_login import UserMixin
from . import login_manager
# itsdangerous提供了多种生成令牌的方法，其中TimedJSONWebSignatureSerializer类生成具有过期时间的JSON Web前面
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 生成令牌 有效期为1小时
    def generate_confirmation_token(self, expiration=3600):
        # 这个类构造函数接受的参数是一个密钥，在Flask程序中可以使用SECRET_KEY设置
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        # dumps()函数为指定的数据生成一个加密签名，然后再对数据和签名进行序列化，生成令牌字符串，expiration设置过期时间
        return s.dumps({'confirm': self.id}).decode('utf-8')

    # 此方法验证令牌
    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    # 生成重设密码令牌
    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id}).decode('utf-8')

    # 重设密码函数
    @staticmethod
    def reset_password(token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True

    # 生成修改电子邮件的令牌
    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email}).decode('utf-8')

    # 修改电子邮件函数
    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        db.session.add(self)
        return True


    def __repr__(self):
        return '<User %r>' % self.username


# flask_login要求程序实现一个回调函数，使用指定的标识符加载用户，该函数定义如下
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
