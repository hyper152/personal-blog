# -*- coding: utf-8 -*-
"""
用户认证模块（带密码加密）
"""
import json
import os
import time
import uuid
import hashlib
import secrets
from datetime import datetime

# 数据文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
SESSIONS_FILE = os.path.join(BASE_DIR, "data", "sessions.json")

# 初始化数据文件
def init_files():
    """确保数据文件存在"""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    if not os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

# ==================== 密码加密函数 ====================

def hash_password(password):
    """
    密码加密
    使用盐值+SHA256加密
    """
    # 生成随机盐值（16字节=32个十六进制字符）
    salt = secrets.token_hex(16)
    # 使用SHA-256加密
    hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
    # 返回 盐值$哈希值 格式
    return f"{salt}${hash_obj.hexdigest()}"

def verify_password(password, hashed_password):
    """
    验证密码
    hashed_password格式: 盐值$哈希值
    """
    try:
        salt, hash_value = hashed_password.split('$')
        hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
        return hash_obj.hexdigest() == hash_value
    except:
        return False

# ==================== 会话管理函数 ====================

def create_session(email):
    """创建用户会话"""
    init_files()
    
    # 生成session_id
    session_id = str(uuid.uuid4())
    expire_time = time.time() + 30*24*60*60  # 30天过期
    
    # 存储会话
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        sessions = json.load(f)
    
    sessions[session_id] = {
        "email": email,
        "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expire_time": expire_time
    }
    
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)
    
    print(f"创建会话: {session_id} for {email}")
    return session_id

def check_login_status(session_id):
    """检查登录状态"""
    print(f"check_login_status 被调用, session_id: '{session_id}'")
    
    if not session_id:
        print("session_id 为空")
        return False
    
    init_files()
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            sessions = json.load(f)
        
        if session_id not in sessions:
            print(f"session_id {session_id} 不存在")
            return False
        
        # 检查是否过期
        if time.time() > sessions[session_id]["expire_time"]:
            print(f"session_id {session_id} 已过期")
            del sessions[session_id]
            with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
            return False
        
        print(f"session_id {session_id} 有效")
        return True
    except Exception as e:
        print(f"检查登录状态出错: {e}")
        return False

def get_current_user(session_id):
    """获取当前用户信息"""
    if not session_id:
        return {}
    
    init_files()
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        sessions = json.load(f)
    
    if session_id not in sessions:
        return {}
    
    # 检查是否过期
    if time.time() > sessions[session_id]["expire_time"]:
        del sessions[session_id]
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
        return {}
    
    email = sessions[session_id]["email"]
    
    # 获取用户详细信息
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    
    if email not in users:
        return {}
    
    user = users[email]
    return {
        "username": user.get("username", ""),
        "email": email
    }

def logout_user(session_id):
    """退出登录"""
    if not session_id:
        return False
    
    init_files()
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        sessions = json.load(f)
    
    if session_id in sessions:
        del sessions[session_id]
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
        return True
    
    return False

# 用户注册（使用加密密码）
def register(username, email, password):
    """用户注册（密码加密存储）"""
    init_files()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    
    if email in users:
        return {"code": 1, "msg": "邮箱已存在"}
    
    # 加密密码并存储用户信息
    users[email] = {
        "username": username,
        "password": hash_password(password),  # 加密存储
        "email": email,
        "create_time": time.time(),
        "create_time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    
    return {"code": 0, "msg": "注册成功"}

# 密码登录（验证加密密码）
def login(email, password):
    """密码登录（验证加密密码）"""
    init_files()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    
    if email not in users:
        return {"code": 1, "msg": "邮箱或密码错误"}
    
    # 验证密码
    if not verify_password(password, users[email]["password"]):
        return {"code": 1, "msg": "邮箱或密码错误"}
    
    # 创建会话
    session_id = create_session(email)
    
    return {
        "code": 0, 
        "msg": "登录成功", 
        "data": {
            "session_id": session_id, 
            "username": users[email]["username"],
            "email": email
        }
    }


if __name__ == "__main__":
    # 测试代码
    init_files()
    print(register("test", "test@qq.com", "123456"))
    print(login("test@qq.com", "123456"))