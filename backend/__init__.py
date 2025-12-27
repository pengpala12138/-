# backend/__init__.py
from flask import Flask
from flask_cors import CORS
from .routes import register_routes

def create_app():
    app = Flask(__name__, static_folder="../frontend", template_folder="../frontend")
    # 解决跨域
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    # 注册接口
    register_routes(app)
    return app