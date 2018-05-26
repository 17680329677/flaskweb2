from . import db
# Werkzeug中的security模块能方便的计算密码散列值，generate_password_hash函数生成散列值，check_password_hash验证散列值
from werkzeug.security import generate_password_hash, check_password_hash
# flask_login专门用来管理用户认证系统中的认证状态 且不依赖特定的认证机制
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager
# itsdangerous提供了多种生成令牌的方法，其中TimedJSONWebSignatureSerializer类生成具有过期时间的JSON Web前面
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request
from datetime import datetime
import hashlib


class Permission:
    FOLLOW = 0x01   # 关注其他用户
    COMMENT = 0x02  # 在他人撰写的文章中发布评论
    WRITE_ARTICLES = 0x04   # 写原创文章
    MODERATE_COMMENTS = 0x08    # 查处他人发表的不当评论
    ADMINISTER = 0x80   # 管理员


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)      # 只有一个角色的default字段设置为True，其他均是False
    # 位标志 能执行某项操作的角色，其位会被设置为1  用八位二进制表示 只用5位 其他用作扩充
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    # 添加一个类方法 完成添加用户角色的操作
    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }

        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    # 添加权限
    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    # 移除权限
    def remove_permission(self,perm):
        if self.has_permission(perm):
            self.permissions -= perm

    # 重置权限
    def reset_permission(self):
        self.permissions = 0

    # 判断权限
    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name


# 关注关联表的模型实现
class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_if = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)    # 用户id
    email = db.Column(db.String(64), unique=True, index=True)   # email地址
    username = db.Column(db.String(64), unique=True, index=True)    # 用户名
    password_hash = db.Column(db.String(128))   # 散列的密码
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))  # 角色id
    confirmed = db.Column(db.Boolean, default=False)    # 是否确认邮箱
    name = db.Column(db.String(64))     # 真实姓名
    location = db.Column(db.String(64))     # 所在地
    about_me = db.Column(db.Text())     # 自我介绍
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)    # 注册时间
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)   # 上次登录时间
    avatar_hash = db.Column(db.String(32))      # 用于存储用户邮箱地址的hash值 便于获取头像
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    # 分配角色，当注册邮箱为FLASKY_ADMIN中的邮箱时  分配管理员角色，剩余均分配用户角色
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()

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
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True

    # 角色验证 验证用户是否拥有指定的权限
    def can(self, permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions   # 做与操作即可判断

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    # 修改最后登录时间
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    # 生成邮件md5的函数  提取出来为了方便
    def gravatar_hash(self):
        return hashlib.md5(self.email.encode('utf-8')).hexdigest()

    # 生成gravatar的URL
    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'https://www.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    # 关注关系的辅助方法
    # 关注他人
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(followed=user)
            self.followed.append(f)

    # 取消关注
    def unfollow(self, user):
        f = self.follower.filter_by(followed_id=user.id).first()
        if f:
            self.followed.remove(f)

    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def __repr__(self):
        return '<User %r>' % self.username


# 定义文章数据模型
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    # 增加博客内容html字段 将富文本编辑器中的内容转换成html存储 否则需要每次在_post.html中转换
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # 此处的含义看书 只要body字段设置了新值，函数就自动被调用
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


# on_changed_body函数注册在body字段上，是SQLAlchemy“set”事件的监听程序，这意味着只要这实例的body字段设置了新值，函数就被自动调用
db.event.listen(Post.body, 'set', Post.on_changed_body)


# 这个对象继承自flask-login中的AnonymousUserMixin，并将其设置为未登录时的current_user值，这样程序不用先检查用户是否登录，就能自由调用current_user.can()
class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


# flask_login要求程序实现一个回调函数，使用指定的标识符加载用户，该函数定义如下
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
