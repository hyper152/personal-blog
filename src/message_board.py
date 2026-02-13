# -*- coding: utf-8 -*-
"""
Flask留言板&用户认证核心模块
"""
import os
import json
import time
import logging
import random
import string
from flask import Flask, request, jsonify, make_response
from email.mime.text import MIMEText
from email.utils import formataddr

# ===================== 先初始化日志 =====================
logger = logging.getLogger("message_board")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(console_handler)

# ===================== 基础配置 =====================
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["SECRET_KEY"] = "personal_vlog_2026_key"

# 项目路径配置
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")
USER_FILE = os.path.join(DATA_DIR, "users.json")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.json")
VERIFY_CACHE = {}  # 验证码缓存

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# ===================== 导入认证模块（包含加密函数） =====================
try:
    from src.auth import (
        create_session,
        check_login_status,
        get_current_user,
        logout_user,
        hash_password,  # 导入加密函数
        verify_password  # 导入验证函数
    )
    logger.info("✅ auth模块导入成功")
except ImportError as e:
    logger.error(f"导入auth模块失败：{e}")
    # 简易版认证函数
    def create_session(email):
        session_id = f"session_{int(time.time())}_{email}"
        return session_id
    
    def check_login_status(session_id):
        return bool(session_id and session_id.startswith("session_"))
    
    def get_current_user(session_id):
        if session_id and session_id.startswith("session_"):
            return {"username": "测试用户", "email": session_id.split("_")[-1]}
        return {}
    
    def logout_user(session_id):
        return True
    
    # 简易加密函数（实际使用时应从auth导入）
    import hashlib
    import secrets
    def hash_password(password):
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
        return f"{salt}${hash_obj.hexdigest()}"
    
    def verify_password(password, hashed_password):
        try:
            salt, hash_value = hashed_password.split('$')
            hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
            return hash_obj.hexdigest() == hash_value
        except:
            return False

# ===================== 导入邮件模块 =====================
try:
    from src.qqmail import send_verify_code, generate_code
    logger.info("✅ 从src.qqmail导入邮件模块成功")
except ImportError:
    try:
        from qqmail import send_verify_code, generate_code
        logger.info("✅ 从qqmail导入邮件模块成功")
    except ImportError as e:
        logger.warning(f"导入邮件模块失败：{e}，使用内置函数")
        def generate_code(length=6):
            return ''.join(random.choices(string.digits, k=length))
        
        def send_verify_code(to_email, code=None):
            if code is None:
                code = generate_code()
            logger.info(f"[模拟发送] 验证码 {code} 发送至 {to_email}")
            return True, "验证码发送成功（测试模式）", code

# ===================== 工具函数 =====================
def load_users():
    """加载用户数据"""
    try:
        if not os.path.exists(USER_FILE):
            return {}
        with open(USER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载用户数据失败：{e}")
        return {}

def save_users(users):
    """保存用户数据"""
    try:
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存用户数据失败：{e}")
        return False

def load_messages():
    """加载留言数据"""
    try:
        if not os.path.exists(MESSAGES_FILE):
            return []
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载留言数据失败：{e}")
        return []

def save_messages(messages):
    """保存留言数据"""
    try:
        with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存留言数据失败：{e}")
        return False

def get_session_id_from_request():
    """从请求中获取session_id（支持cookie和header）"""
    # 1. 从cookie获取
    session_id = request.cookies.get('session_id', '')
    if session_id:
        print(f"从cookie获取session_id: {session_id}")
        return session_id
    
    # 2. 从Authorization header获取
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Session '):
        session_id = auth_header[8:].strip()
        print(f"从header获取session_id: {session_id}")
        return session_id
    
    # 3. 从请求参数获取
    session_id = request.args.get('session_id', '') or request.form.get('session_id', '')
    if session_id:
        print(f"从参数获取session_id: {session_id}")
        return session_id
    
    # 4. 从JSON body获取
    if request.is_json:
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id', '')
        if session_id:
            print(f"从JSON获取session_id: {session_id}")
            return session_id
    
    return ''

# ===================== 注册接口 =====================
@app.route("/api/register/send-code", methods=["POST"])
def send_register_code():
    """发送注册验证码"""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip()
        
        if not email or "@" not in email:
            return jsonify({"code": 400, "msg": "请输入有效的邮箱地址"})
        
        # 检查邮箱是否已注册
        users = load_users()
        if email in users:
            return jsonify({"code": 400, "msg": "该邮箱已注册，请直接登录"})
        
        # 检查是否频繁发送
        if email in VERIFY_CACHE:
            cache = VERIFY_CACHE[email]
            if cache["expire"] > time.time() + 240:
                return jsonify({"code": 400, "msg": "验证码已发送，请5分钟后重试"})
        
        # 发送验证码
        success, msg, code = send_verify_code(email)
        
        if success:
            # 保存验证码
            VERIFY_CACHE[email] = {
                "code": code,
                "expire": time.time() + 300,
                "type": "register"
            }
            logger.info(f"注册验证码发送成功：{email}")
            return jsonify({"code": 200, "msg": "验证码发送成功，请查收邮箱"})
        else:
            logger.error(f"注册验证码发送失败：{email} - {msg}")
            return jsonify({"code": 500, "msg": msg})
            
    except Exception as e:
        logger.error(f"发送注册验证码异常：{e}", exc_info=True)
        return jsonify({"code": 500, "msg": f"服务器内部错误：{str(e)}"})

@app.route("/api/register", methods=["POST"])
def register():
    """用户注册（密码加密存储）"""
    try:
        data = request.get_json(silent=True) or {}
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        code = data.get("code", "").strip()
        
        if not all([username, email, password, code]):
            return jsonify({"code": 400, "msg": "请填写完整注册信息"})
        
        if len(username) < 2 or len(username) > 20:
            return jsonify({"code": 400, "msg": "用户名长度为2-20个字符"})
        
        if len(password) < 6:
            return jsonify({"code": 400, "msg": "密码长度至少6位"})
        
        # 校验验证码
        if email not in VERIFY_CACHE:
            return jsonify({"code": 400, "msg": "验证码已过期，请重新获取"})
        
        cache = VERIFY_CACHE[email]
        if cache["type"] != "register" or cache["code"] != code:
            return jsonify({"code": 400, "msg": "验证码错误"})
        
        if time.time() > cache["expire"]:
            del VERIFY_CACHE[email]
            return jsonify({"code": 400, "msg": "验证码已过期，请重新获取"})
        
        # 检查邮箱是否已注册
        users = load_users()
        if email in users:
            return jsonify({"code": 400, "msg": "该邮箱已注册"})
        
        # 加密密码
        encrypted_password = hash_password(password)
        logger.info(f"密码加密成功: {password} -> {encrypted_password[:20]}...")
        
        # 保存用户（使用加密后的密码）
        users[email] = {
            "username": username,
            "password": encrypted_password,  # 存储加密后的密码
            "email": email,
            "create_time": time.time(),
            "create_time_str": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if save_users(users):
            del VERIFY_CACHE[email]
            logger.info(f"用户注册成功：{username}({email})")
            return jsonify({"code": 200, "msg": "注册成功，请登录"})
        else:
            return jsonify({"code": 500, "msg": "保存用户信息失败"})
            
    except Exception as e:
        logger.error(f"注册异常：{e}", exc_info=True)
        return jsonify({"code": 500, "msg": f"服务器内部错误：{str(e)}"})

# ===================== 登录接口 =====================
@app.route("/api/login/send-code", methods=["POST"])
def send_login_code():
    """发送登录验证码"""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip()
        
        if not email or "@" not in email:
            return jsonify({"code": 400, "msg": "请输入有效的邮箱地址"})
        
        # 检查邮箱是否已注册
        users = load_users()
        if email not in users:
            return jsonify({"code": 400, "msg": "该邮箱未注册，请先注册"})
        
        # 发送验证码
        success, msg, code = send_verify_code(email)
        
        if success:
            VERIFY_CACHE[email] = {
                "code": code,
                "expire": time.time() + 300,
                "type": "login"
            }
            return jsonify({"code": 200, "msg": "验证码发送成功，请查收邮箱"})
        else:
            return jsonify({"code": 500, "msg": msg})
            
    except Exception as e:
        logger.error(f"发送登录验证码异常：{e}", exc_info=True)
        return jsonify({"code": 500, "msg": f"服务器内部错误：{str(e)}"})

@app.route("/api/login/code", methods=["POST"])
def login_by_code():
    """验证码登录"""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip()
        code = data.get("code", "").strip()
        
        if not email or not code:
            return jsonify({"code": 400, "msg": "请输入邮箱和验证码"})
        
        # 校验验证码
        if email not in VERIFY_CACHE:
            return jsonify({"code": 400, "msg": "验证码已过期，请重新获取"})
        
        cache = VERIFY_CACHE[email]
        if cache["type"] != "login" or cache["code"] != code:
            return jsonify({"code": 400, "msg": "验证码错误"})
        
        if time.time() > cache["expire"]:
            del VERIFY_CACHE[email]
            return jsonify({"code": 400, "msg": "验证码已过期，请重新获取"})
        
        # 获取用户信息
        users = load_users()
        if email not in users:
            return jsonify({"code": 400, "msg": "用户不存在"})
        
        user = users[email]
        
        # 创建会话
        session_id = create_session(email)
        
        # 删除验证码
        del VERIFY_CACHE[email]
        
        # 创建响应
        response = make_response(jsonify({
            "code": 200,
            "msg": "登录成功",
            "data": {
                "username": user["username"],
                "email": email,
                "session_id": session_id
            }
        }))
        
        # 设置cookie
        response.set_cookie(
            'session_id',
            session_id,
            max_age=30*24*60*60,  # 30天
            path='/'
        )
        
        print(f"验证码登录成功，设置cookie: session_id={session_id}")
        logger.info(f"用户验证码登录成功：{user['username']}({email})")
        return response
        
    except Exception as e:
        print(f"验证码登录异常：{e}")
        logger.error(f"验证码登录异常：{e}", exc_info=True)
        return jsonify({"code": 500, "msg": f"服务器内部错误：{str(e)}"})

@app.route("/api/login/password", methods=["POST"])
def login_by_password():
    """密码登录（验证加密密码）"""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        
        if not email or not password:
            return jsonify({"code": 400, "msg": "请输入邮箱和密码"})
        
        # 验证用户
        users = load_users()
        if email not in users:
            return jsonify({"code": 400, "msg": "邮箱或密码错误"})
        
        user = users[email]
        
        # 验证加密密码
        if not verify_password(password, user["password"]):
            logger.warning(f"密码验证失败: {email}")
            return jsonify({"code": 400, "msg": "邮箱或密码错误"})
        
        # 创建会话
        session_id = create_session(email)
        
        # 创建响应
        response = make_response(jsonify({
            "code": 200,
            "msg": "登录成功",
            "data": {
                "username": user["username"],
                "email": email,
                "session_id": session_id
            }
        }))
        
        # 设置cookie
        response.set_cookie(
            'session_id',
            session_id,
            max_age=30*24*60*60,  # 30天
            path='/'
        )
        
        print(f"密码登录成功，设置cookie: session_id={session_id}")
        logger.info(f"用户密码登录成功：{user['username']}({email})")
        return response
        
    except Exception as e:
        print(f"密码登录异常：{e}")
        logger.error(f"密码登录异常：{e}", exc_info=True)
        return jsonify({"code": 500, "msg": f"服务器内部错误：{str(e)}"})

# ===================== 状态接口 =====================
@app.route("/api/check-login", methods=["POST", "GET"])
def check_login():
    """检查登录状态"""
    try:
        # 获取session_id
        session_id = get_session_id_from_request()
        
        is_login = check_login_status(session_id)
        user = get_current_user(session_id) if is_login else {}
        
        print(f"登录状态结果 - is_login: {is_login}, user: {user}")
        
        return jsonify({
            "isLogin": is_login,
            "user": user
        })
    except Exception as e:
        print(f"检查登录状态异常: {e}")
        logger.error(f"检查登录状态异常：{e}")
        return jsonify({"isLogin": False, "user": {}})

@app.route("/api/logout", methods=["POST"])
def logout():
    """退出登录"""
    try:
        # 获取session_id
        session_id = get_session_id_from_request()
        print(f"登出 - session_id: '{session_id}'")
        
        if session_id and logout_user(session_id):
            response = make_response(jsonify({
                "code": 200, 
                "msg": "退出登录成功"
            }))
            # 清除cookie
            response.set_cookie('session_id', '', expires=0, path='/')
            print("登出成功，已清除cookie")
            return response
        else:
            print("登出失败：session_id无效或不存在")
            return jsonify({"code": 400, "msg": "退出失败"})
            
    except Exception as e:
        print(f"退出登录异常：{e}")
        logger.error(f"退出登录异常：{e}")
        return jsonify({"code": 500, "msg": "服务器内部错误"})

# ===================== 留言板接口 =====================
@app.route("/api/talk/list", methods=["GET"])
def get_message_list():
    """获取留言列表"""
    try:
        messages = load_messages()
        # 按时间倒序排列
        messages.sort(key=lambda x: x.get("create_time", 0), reverse=True)
        return jsonify({"code": 200, "msg": "获取成功", "data": messages})
    except Exception as e:
        logger.error(f"获取留言列表异常：{e}")
        return jsonify({"code": 500, "msg": "服务器内部错误"})

@app.route("/api/talk/add", methods=["POST"])
def add_message():
    """添加留言"""
    try:
        # 获取session_id
        session_id = get_session_id_from_request()
        print(f"添加留言 - session_id: '{session_id}'")
        
        # 检查登录状态
        if not session_id:
            return jsonify({"code": 401, "msg": "请先登录"})
        
        is_login = check_login_status(session_id)
        if not is_login:
            return jsonify({"code": 401, "msg": "登录已过期，请重新登录"})
        
        # 获取用户信息
        user = get_current_user(session_id)
        if not user:
            return jsonify({"code": 401, "msg": "用户信息不存在"})
        
        # 获取留言内容
        data = request.get_json(silent=True) or {}
        content = data.get("content", "").strip()
        
        if not content:
            return jsonify({"code": 400, "msg": "留言内容不能为空"})
        
        # 加载现有留言
        messages = load_messages()
        
        # 创建新留言
        message = {
            "id": str(int(time.time() * 1000)) + str(random.randint(100, 999)),
            "username": user.get("username", "匿名用户"),
            "content": content,
            "create_time": time.time(),
            "create_time_str": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 添加留言
        messages.append(message)
        
        # 保存留言
        if save_messages(messages):
            logger.info(f"用户{user.get('username')}添加留言成功")
            return jsonify({"code": 200, "msg": "留言成功"})
        else:
            return jsonify({"code": 500, "msg": "保存留言失败"})
        
    except Exception as e:
        logger.error(f"添加留言异常：{e}")
        return jsonify({"code": 500, "msg": f"服务器内部错误：{str(e)}"})

# ===================== 启动服务 =====================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8001, debug=True)