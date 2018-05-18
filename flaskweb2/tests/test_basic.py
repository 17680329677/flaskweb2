# 单元测试
# 这个测试使用Python标准库中的unittest包编写，setUp（）和tearDown（）方法分别在各测试前后执行，并以test_开头的函数都作为测试执行
import unittest
from flask import current_app
from app import create_app, db


class BasicsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(create_app is None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])


