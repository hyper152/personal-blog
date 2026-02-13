# -*- coding: utf-8 -*-
"""
个人Vlog HTTP服务端（安全增强版）
✅ 修复：访问动态重复打印（整合为一行）
✅ 修复：/visit-count接口触发计数增加
✅ 修复：bytes仅支持ASCII字符的语法错误
✅ 修复：/talk 路径404问题（映射到静态页面）
✅ 修复：登录后无法留言（导入错误+容错逻辑）
✅ 新增：访问动态输出用户信息
✅ 新增：数据目录访问保护
✅ 新增：敏感文件访问限制
✅ 保留：所有原有功能（目录美化、留言板、异步计数等）
"""
import socket
import sys
import os
import time
import json
import logging
import argparse
import contextlib
from functools import partial
from datetime import datetime
from collections import defaultdict
from http.server import CGIHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

# ===================== 配置抽离 =====================
class Config:
    HOST = "0.0.0.0"
    PORT = 8000
    SERVER_DIR = None

    RATE_LIMIT = 60
    RATE_LIMIT_WINDOW = 60
    MAX_POST_SIZE = 1 * 1024 * 1024
    ALLOWED_EXTENSIONS = None

    LOG_DIR = "logs"
    LOG_LEVEL = logging.INFO
    LOG_ROTATE = True

    # 排除计数的路径
    EXCLUDE_COUNT_PATHS = ['/visit-count']
    EXCLUDE_STATIC_EXT = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.css', '.js', '.ico', '.svg']
    RESET_VISITS = False
    
    # 敏感文件列表
    SENSITIVE_FILES = ['users.json', 'sessions.json', 'messages.json', 'visit_count.json']
    # 保护的数据目录
    PROTECTED_DIRS = ['/data/', '/data\\']

# ===================== 日志初始化 =====================
def init_logging():
    """初始化日志：同时输出到控制台+文件"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), Config.LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"access_{datetime.now().strftime('%Y%m%d')}.log" if Config.LOG_ROTATE else "access.log"
    log_file = os.path.join(log_dir, log_filename)

    # 自定义日志格式
    class AccessDynamicFormatter(logging.Formatter):
        def format(self, record):
            if record.msg.startswith("[访问动态]"):
                self._style._fmt = "%(message)s"
            else:
                self._style._fmt = "%(asctime)s - %(levelname)s - %(message)s"
            return super().format(record)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(AccessDynamicFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # 配置日志
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        handlers=[file_handler, console_handler]
    )
    return logging.getLogger(__name__)

logger = init_logging()

# ===================== 目录创建 =====================
current_script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(current_script_dir, 'data')
src_dir = os.path.join(current_script_dir, 'src')
home_dir = os.path.join(current_script_dir, 'home')
talk_dir = os.path.join(current_script_dir, 'talk')

for d in [data_dir, src_dir, home_dir, talk_dir]:
    try:
        os.makedirs(d, exist_ok=True)
    except Exception as e:
        logger.warning(f"创建目录 {d} 失败：{e}")

# 在data目录创建index.html防止目录浏览
data_index_path = os.path.join(data_dir, 'index.html')
if not os.path.exists(data_index_path):
    try:
        with open(data_index_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html>
<head><title>禁止访问</title></head>
<body style="background:#f8f9fa; text-align:center; padding:50px;">
    <h1 style="color:#6a5acd;">403 Forbidden</h1>
    <p style="color:#495057;">你没有权限访问此目录</p>
</body>
</html>""")
    except Exception as e:
        logger.warning(f"创建data目录保护文件失败：{e}")

sys.path.insert(0, src_dir)

# ===================== 依赖导入 =====================
FLASK_AVAILABLE = False
try:
    import message_board
    FLASK_AVAILABLE = True
    logger.info("✅ 留言板模块导入成功")
except ImportError as e:
    logger.warning(f"⚠️ 留言板模块导入失败：{e}")

# 导入认证模块获取用户信息
try:
    from src.auth import get_current_user, check_login_status
    AUTH_AVAILABLE = True
    logger.info("✅ 认证模块导入成功")
except ImportError as e:
    logger.warning(f"⚠️ 认证模块导入失败：{e}")
    AUTH_AVAILABLE = False
    # 定义空函数避免错误
    def get_current_user(session_id): return {}
    def check_login_status(session_id): return False

# 简化访问计数（内置版，无需额外模块）
VISIT_COUNT_FILE = os.path.join(data_dir, 'visit_count.json')
def count_visit():
    """计数访问量"""
    try:
        if not os.path.exists(VISIT_COUNT_FILE):
            with open(VISIT_COUNT_FILE, 'w', encoding='utf-8') as f:
                json.dump({"count": 0, "total_visits": 0}, f)
        
        with open(VISIT_COUNT_FILE, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            current_count = data.get("count", 0)
            data["count"] = current_count + 1
            data["total_visits"] = data["count"]  # 同步total_visits
            data["update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.truncate()
        return data["count"]
    except Exception as e:
        logger.error(f"计数失败：{e}")
        return 0

def get_total_visits():
    """获取总访问量"""
    try:
        if not os.path.exists(VISIT_COUNT_FILE):
            return 0
        with open(VISIT_COUNT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("count", data.get("total_visits", 0))
    except Exception as e:
        logger.error(f"获取计数失败：{e}")
        return 0

def get_session_id_from_request(request_handler):
    """从请求中获取session_id"""
    # 从cookie获取
    cookie_header = request_handler.headers.get('Cookie', '')
    cookies = {}
    for cookie in cookie_header.split(';'):
        if '=' in cookie:
            key, value = cookie.strip().split('=', 1)
            cookies[key] = value
    
    session_id = cookies.get('session_id', '')
    if session_id:
        return session_id
    
    # 从Authorization头获取
    auth_header = request_handler.headers.get('Authorization', '')
    if auth_header.startswith('Session '):
        session_id = auth_header[8:].strip()
        return session_id
    
    return ''

def get_user_info_from_request(request_handler):
    """从请求中获取用户信息"""
    if not AUTH_AVAILABLE:
        return {}
    
    session_id = get_session_id_from_request(request_handler)
    if not session_id:
        return {}
    
    if not check_login_status(session_id):
        return {}
    
    return get_current_user(session_id)

# ===================== HTTP 处理器 =====================
class BeautifulDirectoryHandler(CGIHTTPRequestHandler):
    ip_request_cache = defaultdict(list)

    def __init__(self, *args, **kwargs):
        self.request_handled = False
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        """覆盖默认日志"""
        try:
            client_ip = self.address_string()
            logger.info(f"[访问日志] {client_ip} - {format % args}")
        except Exception as e:
            logger.error(f"日志打印异常：{e}")

    def check_rate_limit(self):
        """限流检查"""
        try:
            client_ip = self.address_string()
            now = time.time()
            self.ip_request_cache[client_ip] = [t for t in self.ip_request_cache[client_ip] if now - t < Config.RATE_LIMIT_WINDOW]
            
            # API请求更严格的限制
            if self.path.startswith('/api/'):
                if len(self.ip_request_cache[client_ip]) >= 30:  # API每分钟30次
                    self.send_response(429)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    error_html = """
                    <html>
                    <head><title>429 Too Many Requests</title></head>
                    <body style='padding:40px'>
                        <h1>429 API请求频率过高</h1>
                        <p>API请求频率过高，请稍后再试</p>
                    </body>
                    </html>
                    """
                    self.wfile.write(error_html.encode('utf-8'))
                    return False
            
            # 普通请求限制
            elif len(self.ip_request_cache[client_ip]) >= Config.RATE_LIMIT:
                self.send_response(429)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                error_html = """
                <html>
                <head><title>429 Too Many Requests</title></head>
                <body style='padding:40px'>
                    <h1>429 请求频率过高</h1>
                    <p>请求频率过高，请60秒后再试</p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode('utf-8'))
                return False
                
            self.ip_request_cache[client_ip].append(now)
            return True
        except Exception as e:
            logger.error(f"限流检查异常：{e}")
            return True

    def validate_path(self, path):
        """路径校验"""
        try:
            safe_path = os.path.abspath(path)
            server_root = os.path.abspath(self.directory)
            
            # 安全检查：防止路径遍历
            if not safe_path.startswith(server_root):
                logger.warning(f"禁止访问：非法路径 {path}")
                self.send_error(403, "禁止访问：非法路径")
                return None
                
            return safe_path
        except Exception as e:
            logger.error(f"路径校验异常：{e}")
            self.send_error(400, "路径格式错误")
            return None

    def is_protected_path(self, path):
        """检查是否是受保护的路径"""
        # 检查是否是数据目录
        for protected_dir in Config.PROTECTED_DIRS:
            if path.startswith(protected_dir):
                return True
        
        # 检查是否是敏感文件
        for sensitive_file in Config.SENSITIVE_FILES:
            if path.endswith(f'/data/{sensitive_file}') or path.endswith(f'\\data\\{sensitive_file}'):
                return True
        
        return False

    def handle_one_request(self):
        """处理单个请求"""
        if self.request_handled:
            return
        self.request_handled = True

        if not self.check_rate_limit():
            return

        try:
            super().handle_one_request()
        except Exception as e:
            logger.error(f"[请求处理异常] {e}")
            return

        # 访问动态统计（带用户信息）
        try:
            visit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            client_ip = self.address_string()
            request_path = getattr(self, 'path', '未知路径')
            request_method = getattr(self, 'command', '未知方法')
            
            # 获取用户信息
            user_info = get_user_info_from_request(self)
            username = user_info.get('username', '') if user_info else ''
            
            # 计数访问
            is_static = any(request_path.lower().endswith(ext) for ext in Config.EXCLUDE_STATIC_EXT)
            is_exclude_path = any(request_path.startswith(path) for path in Config.EXCLUDE_COUNT_PATHS)
            
            if not is_static and not is_exclude_path:
                total_visits = count_visit()
            else:
                total_visits = get_total_visits()

            # 构建访问动态信息
            if username:
                access_msg = f"[访问动态] {visit_time} | 用户: {username} | IP: {client_ip} | {request_method} | {request_path} | 总访问量：{total_visits}"
            else:
                access_msg = f"[访问动态] {visit_time} | 游客 | IP: {client_ip} | {request_method} | {request_path} | 总访问量：{total_visits}"
            
            logger.info(access_msg)
            
        except Exception as e:
            logger.error(f"[访问动态打印异常] {e}")

    @staticmethod
    def get_template():
        """目录美化模板"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:Microsoft YaHei }}
        body {{ background:#f8f9fa; padding:40px }}
        .container {{ max-width:1000px; margin:0 auto; background:white; padding:30px; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,0.1) }}
        h1 {{ color:#6a5acd; margin-bottom:20px }}
        .breadcrumb {{ margin:20px 0; display:flex; gap:8px }}
        .back-btn {{ display:inline-block; padding:8px 16px; background:#6a5acd; color:white; border-radius:8px; text-decoration:none }}
        .items {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:15px }}
        .item {{ display:flex; align-items:center; padding:12px; border-radius:8px; text-decoration:none; color:#495057 }}
        .folder i {{ color:#ffc107 }}
        .file i {{ color:#6a5acd }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📂 目录列表: {path}</h1>
        <div class="breadcrumb">{breadcrumb}</div>
        {back_button}
        <div class="items">{items}</div>
    </div>
</body>
</html>
        """

    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        # 检查是否是受保护的路径
        if self.is_protected_path(path):
            logger.warning(f"阻止访问受保护路径: {path} 来自 {self.address_string()}")
            self.send_error(403, "禁止访问")
            return

        # 处理/talk路径，返回静态页面
        if path == '/talk':
            self._serve_talk_static_page()
            return

        # 访问计数接口
        if path == '/visit-count':
            self._handle_visit_count()
            return

        # 转发API请求到Flask
        if FLASK_AVAILABLE and path.startswith('/api/'):
            self._forward_to_flask()
            return

        # 首页重定向
        if path in ('', '/'):
            self.send_response(301)
            self.send_header('Location', '/home/')
            self.end_headers()
            return

        # 静态文件/目录
        local = self.translate_path(self.path)
        if not self.validate_path(local):
            return
        super().do_GET()

    def do_POST(self):
        """处理POST请求"""
        # 检查是否是受保护的路径
        if self.is_protected_path(self.path):
            logger.warning(f"阻止POST访问受保护路径: {self.path} 来自 {self.address_string()}")
            self.send_error(403, "禁止访问")
            return
            
        local = self.translate_path(self.path)
        if not self.validate_path(local):
            return
        
        # 转发API请求到Flask
        if FLASK_AVAILABLE and self.path.startswith('/api/'):
            self._forward_to_flask()
            return
        super().do_POST()

    def do_DELETE(self):
        """处理DELETE请求"""
        # 检查是否是受保护的路径
        if self.is_protected_path(self.path):
            logger.warning(f"阻止DELETE访问受保护路径: {self.path} 来自 {self.address_string()}")
            self.send_error(403, "禁止访问")
            return
            
        local = self.translate_path(self.path)
        if not self.validate_path(local):
            return
        
        # 转发API请求到Flask
        if FLASK_AVAILABLE and self.path.startswith('/api/'):
            self._forward_to_flask()
            return
        super().do_DELETE()

    def _serve_talk_static_page(self):
        """返回留言板静态页面"""
        talk_html_path = os.path.join(current_script_dir, 'talk', 'comment.html')
        try:
            with open(talk_html_path, 'rb') as f:
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            logger.error(f"留言板静态页面不存在：{talk_html_path}")
            self.send_error(404, "留言板页面不存在，请检查talk/comment.html文件")
        except Exception as e:
            logger.error(f"读取留言板页面失败：{e}")
            self.send_error(500, "读取留言板页面失败")

    def _handle_visit_count(self):
        """处理访问计数请求"""
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        
        # 读取完整的数据文件
        try:
            if os.path.exists(VISIT_COUNT_FILE):
                with open(VISIT_COUNT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                total = get_total_visits()
                data = {"count": total, "total_visits": total, "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        except:
            total = get_total_visits()
            data = {"count": total, "total_visits": total, "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        self.wfile.write(json.dumps({
            "code": 200, 
            "message": "success",
            "data": data
        }, ensure_ascii=False).encode('utf-8'))

    def _forward_to_flask(self):
        """转发请求到Flask"""
        if not FLASK_AVAILABLE:
            self.send_error(500, "留言板模块未加载")
            return
        try:
            data = b""
            if self.command in ["POST", "PUT", "DELETE"]:
                cl = int(self.headers.get("Content-Length", 0))
                if 0 < cl < Config.MAX_POST_SIZE:
                    data = self.rfile.read(cl)

            with message_board.app.test_client() as client:
                headers = dict(self.headers)
                if self.command == "GET":
                    resp = client.get(self.path, headers=headers)
                elif self.command == "DELETE":
                    resp = client.delete(self.path, headers=headers)
                else:
                    content_type = self.headers.get('Content-Type', 'application/x-www-form-urlencoded')
                    resp = client.post(self.path, data=data, headers=headers, content_type=content_type)

            self.send_response(resp.status_code)
            for k, v in resp.headers.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp.data)
        except Exception as e:
            logger.error(f"Flask转发异常：{e}")
            self.send_response(500)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            error_html = """
            <html>
            <head><title>500 服务器内部错误</title></head>
            <body style='padding:40px'>
                <h1>500 接口请求处理失败</h1>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode('utf-8'))

    def list_directory(self, path):
        """目录列表美化"""
        if not self.validate_path(path):
            return None
        try:
            lst = os.listdir(path)
        except OSError as e:
            logger.error(f"读取目录 {path} 失败：{e}")
            self.send_error(404)
            return None

        lst.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
        cur = unquote(self.path)
        if not cur.endswith('/'):
            cur += '/'

        bread = []
        p = ''
        bread.append('<a href="/"><i class="fas fa-home"></i> 首页</a>')
        for part in cur.strip('/').split('/'):
            if part:
                p += part + '/'
                bread.append(f'<span>/</span><a href="/{p}">{part}</a>')

        back = ''
        if cur != '/':
            parent = os.path.dirname(cur.rstrip('/')).replace('\\', '/') or '/'
            back = f'<a href="{parent}" class="back-btn"><i class="fas fa-arrow-left"></i> 返回上一级</a>'

        items = []
        for name in lst:
            fp = os.path.join(path, name)
            url = self.path + name
            if os.path.isdir(fp):
                items.append(f'''
                <a href="{url}/" class="item folder">
                    <i class="fas fa-folder"></i>
                    <div class="item-name">{name}</div>
                </a>''')
            else:
                file_ext = os.path.splitext(name)[1].lower()
                icon = 'fas fa-file'
                if file_ext in ['.html', '.htm']: icon = 'fas fa-file-html'
                elif file_ext in ['.jpg', '.jpeg', '.png']: icon = 'fas fa-file-image'
                elif file_ext in ['.mp4', '.avi']: icon = 'fas fa-file-video'
                items.append(f'''
                <a href="{url}" class="item file">
                    <i class="{icon}"></i>
                    <div class="item-name">{name}</div>
                </a>''')

        html = self.get_template().format(
            title=f"目录列表 - {cur}",
            path=cur,
            breadcrumb=''.join(bread),
            back_button=back,
            items=''.join(items)
        )
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
        return None

# ===================== 服务器 =====================
class DualStackServer(ThreadingHTTPServer):
    def server_bind(self):
        """绑定服务器"""
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.settimeout(10)
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            super().server_bind()
            logger.info(f"✅ 服务器绑定成功：{self.server_address}")
        except Exception as e:
            logger.error(f"服务器绑定异常：{e}")
            raise

    def finish_request(self, request, client_address):
        """处理请求"""
        try:
            request.settimeout(10)
            super().finish_request(request, client_address)
        except Exception as e:
            logger.error(f"请求处理超时 {client_address}：{e}")
            with contextlib.suppress(Exception):
                request.close()

# ===================== 启动 =====================
def run_server():
    """启动服务器"""
    # 重置访问计数
    if Config.RESET_VISITS:
        try:
            with open(VISIT_COUNT_FILE, 'w', encoding='utf-8') as f:
                json.dump({"count": 0, "total_visits": 0}, f)
            logger.info("✅ 访问计数已重置为0")
        except Exception as e:
            logger.error(f"重置计数失败：{e}")

    # 启动服务器
    server_dir = Config.SERVER_DIR or current_script_dir
    os.chdir(server_dir)
    handler = partial(BeautifulDirectoryHandler, directory=server_dir)
    httpd = DualStackServer((Config.HOST, Config.PORT), handler)
    httpd.timeout = 10
    httpd.daemon_threads = True

    local_ip = socket.gethostbyname(socket.gethostname())
    logger.info("\n🚀 服务启动成功！")
    logger.info(f"├─ 本地访问: http://localhost:{Config.PORT}")
    logger.info(f"├─ 外网访问: http://{local_ip}:{Config.PORT}")
    logger.info(f"├─ 留言板: http://localhost:{Config.PORT}/talk")
    logger.info(f"├─ 计数查询: http://localhost:{Config.PORT}/visit-count")
    logger.info(f"├─ 数据目录保护: 已启用")
    logger.info(f"└─ 根目录: {os.path.abspath(server_dir)}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n🛑 服务正在停止...")
        httpd.server_close()
        logger.info("✅ 服务已停止")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="个人Vlog HTTP服务端")
    parser.add_argument("-p", "--port", type=int, default=8000, help="监听端口")
    parser.add_argument("-H", "--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("--reset-visits", action="store_true", help="重置访问次数")
    args = parser.parse_args()
    
    Config.PORT = args.port
    Config.HOST = args.host
    Config.RESET_VISITS = args.reset_visits 
    
    run_server()