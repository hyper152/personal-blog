# -*- coding: utf-8 -*-
"""
留言板核心模块（修复所有POST数据问题）
数据存储：data/messages.json | 模板目录：talk/
"""
import json
import datetime
import os
from flask import Flask, Blueprint, render_template, request

# -------------------------- 核心配置 --------------------------
# 获取项目根目录（关键：修复路径问题）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Flask应用（模板目录指向项目根的talk文件夹）
app = Flask(__name__, template_folder=os.path.join(PROJECT_ROOT, 'talk'))
app.url_map.strict_slashes = False  # 兼容/talk和/talk/
app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False  # 修复POST数据缓存

# 蓝图
message_bp = Blueprint('message_board', __name__)

# -------------------------- 数据路径配置（修复上级目录问题） --------------------------
# 数据目录（项目根下的data文件夹）
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
# 留言数据文件
JSON_FILE = os.path.join(DATA_DIR, 'messages.json')

# -------------------------- 工具函数 --------------------------
def init_db():
    """初始化JSON数据文件"""
    # 确保data目录存在
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"✅ 已创建数据目录：{DATA_DIR}")
    # 初始化JSON文件
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        print(f"✅ 已创建留言数据文件：{JSON_FILE}")
    else:
        # 检查文件格式是否正确
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("文件格式错误，不是列表")
        except (json.JSONDecodeError, ValueError):
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            print(f"⚠️  留言文件损坏，已重置：{JSON_FILE}")

def get_all_messages():
    """读取所有留言，按时间倒序"""
    init_db()
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        if not isinstance(messages, list):
            messages = []
        
        # 按时间倒序
        messages.sort(key=lambda x: x.get('time', ''), reverse=True)
        return messages
    except Exception as e:
        print(f"❌ 读取留言失败：{e}")
        return []

def add_message(username, content):
    """添加新留言（确保写入成功）"""
    if not content.strip():
        print(f"❌ 留言内容为空，不写入")
        return False
    
    new_msg = {
        "username": username.strip() or "匿名用户",
        "content": content.strip(),
        "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        # 读取原有数据
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        # 添加新留言
        messages.append(new_msg)
        
        # 写入文件（强制刷新）
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)
            f.flush()
        
        print(f"✅ 新增留言：{new_msg}")
        return True
    except Exception as e:
        print(f"❌ 写入留言失败：{str(e)}")
        return False

# -------------------------- 核心路由 --------------------------
@message_bp.route('/talk', methods=["GET", "POST"])
def talk_board():
    """留言板主页面：GET展示，POST提交"""
    # 处理POST提交
    if request.method == "POST":
        # 调试输出所有POST数据
        print(f"\n📥 POST请求接收：")
        print(f"   表单数据：{dict(request.form)}")
        print(f"   JSON数据：{request.get_json(silent=True)}")
        print(f"   原始数据：{request.data.decode('utf-8', errors='ignore')}")
        
        # 多方式获取数据（终极兼容）
        username = request.form.get('username', '') or request.args.get('username', '')
        content = request.form.get('content', '') or request.args.get('content', '')
        
        # 兜底：解析原始POST数据
        if not content and request.data:
            try:
                from urllib.parse import parse_qs
                post_data = parse_qs(request.data.decode('utf-8'))
                username = post_data.get('username', [''])[0]
                content = post_data.get('content', [''])[0]
            except:
                pass
        
        print(f"   最终提取：用户名={username}，内容={content}")
        
        # 提交留言
        if content.strip():
            add_message(username, content)
    
    # 读取所有留言
    all_messages = get_all_messages()
    print(f"🔍 当前留言总数：{len(all_messages)}")
    
    # 渲染模板（路径已修复）
    return render_template('comment.html', messages=all_messages)

# -------------------------- 注册蓝图 --------------------------
app.register_blueprint(message_bp)

# -------------------------- 单独测试用（可选） --------------------------
if __name__ == "__main__":
    init_db()
    print("📝 留言板单独测试启动：http://localhost:5000/talk")
    app.run(debug=True, port=5000, host='0.0.0.0')