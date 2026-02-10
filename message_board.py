# coding='UTF-8'
"""
留言板核心模块（修复POST表单数据为空问题）
无独立端口 | 依赖main.py转发 | 数据存储：data/messages.json
"""
import json
import datetime
import os
from flask import Flask, Blueprint, render_template, request

# -------------------------- 核心配置 --------------------------
# Flask应用（模板目录指向talk）
app = Flask(__name__, template_folder='talk')
# 关闭Flask的严格斜杠规则（兼容/talk和/talk/）
app.url_map.strict_slashes = False
# 关闭Flask的请求数据缓存（修复POST数据读取）
app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
# 蓝图（管理留言板路由）
message_bp = Blueprint('message_board', __name__, template_folder='talk')

# -------------------------- 数据文件路径配置（核心修改） --------------------------
# 定义data目录路径（当前文件所在目录下的data文件夹）
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
# 确保data目录存在，不存在则创建
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"✅ 已创建数据目录：{DATA_DIR}")

# JSON数据文件（data目录下的messages.json）
JSON_FILE = os.path.join(DATA_DIR, 'messages.json')

# -------------------------- 工具函数 --------------------------
def init_db():
    """初始化JSON文件（兼容main.py的调用）"""
    init_json()

def init_json():
    """确保JSON文件存在且格式正确"""
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        print(f"✅ 已创建留言数据文件：{JSON_FILE}")
    else:
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
    init_json()
    try:
        # 强制使用绝对路径，禁用缓存
        json_path = os.path.abspath(JSON_FILE)
        with open(json_path, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        # 确保是列表
        if not isinstance(messages, list):
            messages = []
        
        # 按时间倒序排序
        messages.sort(key=lambda x: x.get('time', ''), reverse=True)
        return messages
    except Exception as e:
        print(f"❌ 读取留言失败：{e}")
        return []

def add_message(username, content):
    """添加新留言到JSON文件"""
    if not content.strip():
        print(f"❌ 留言内容为空，不写入")
        return False
    
    # 构造留言数据
    new_msg = {
        "username": username.strip() or "匿名用户",
        "content": content.strip(),
        "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        # 强制使用绝对路径（核心修复）
        json_path = os.path.abspath(JSON_FILE)
        print(f"📝 写入路径：{json_path}")
        
        # 读取原有数据
        with open(json_path, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        # 添加新留言
        messages.append(new_msg)
        
        # 写入文件（加flush确保立即写入）
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)
            f.flush()  # 强制写入磁盘
        
        print(f"✅ 新增留言：{new_msg}")
        return True
    except Exception as e:
        print(f"❌ 写入失败：{str(e)}")  # 打印具体错误
        return False

# -------------------------- 核心路由 --------------------------
@message_bp.route('/talk', methods=["GET", "POST"])
def talk_board():
    """留言板主页面：GET展示，POST提交（修复表单数据接收）"""
    # 处理POST提交
    if request.method == "POST":
        # 打印所有POST数据（调试用）
        print(f"\n📥 POST请求接收：")
        print(f"   表单数据：{dict(request.form)}")
        print(f"   JSON数据：{request.get_json(silent=True)}")
        print(f"   请求数据：{request.data.decode('utf-8', errors='ignore')}")
        
        # 多方式获取数据（兼容不同提交格式）
        username = request.form.get('username', '') or request.args.get('username', '')
        content = request.form.get('content', '') or request.args.get('content', '')
        
        # 兜底：从原始数据解析（终极修复）
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
            write_result = add_message(username, content)
            print(f"   写入结果：{write_result}")
        else:
            print(f"   跳过：内容为空")
    
    # 读取所有留言
    all_messages = get_all_messages()
    print(f"🔍 当前留言总数：{len(all_messages)}")
    
    # 渲染页面（确保模板路径正确）
    return render_template('comment.html', messages=all_messages)

# -------------------------- 注册蓝图 --------------------------
app.register_blueprint(message_bp)

# -------------------------- 单独测试用（可选注释） --------------------------
# if __name__ == "__main__":
#     init_json()
#     print("留言板单独测试启动：http://localhost:5000/talk")
#     app.run(debug=True, port=5000)