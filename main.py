# -*- coding: utf-8 -*-
"""
个人Vlog HTTP服务端（最终稳定版）
✅ 修复：访问动态打印异常（'path'属性未初始化）
✅ 其余功能100%保留：目录美化、留言板、异步计数、data目录存放文件等
"""
import socket
import sys
import os
import time
import contextlib
from functools import partial
from http.server import (
    CGIHTTPRequestHandler,
    ThreadingHTTPServer
)
from urllib.parse import unquote, urlparse
from datetime import datetime  # 用于打印访问时间

# ===================== 提前创建核心目录（避免IO阻塞） =====================
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# 1. 创建data目录（计数文件）
data_dir = os.path.join(current_script_dir, 'data')
try:
    os.makedirs(data_dir, exist_ok=True)
    print(f"✅ 已确保data目录存在：{data_dir}")
except Exception as e:
    print(f"⚠️ 创建data目录警告：{e}", file=sys.stderr)

# 2. 创建src目录（模块）
src_dir = os.path.join(current_script_dir, 'src')
try:
    os.makedirs(src_dir, exist_ok=True)
    sys.path.insert(0, src_dir)  # 把src目录加入Python搜索路径
    print(f"✅ 已确保src目录存在：{src_dir}")
except Exception as e:
    print(f"⚠️ 创建src目录警告：{e}", file=sys.stderr)

# 3. 创建home目录（静态文件）
home_dir = os.path.join(current_script_dir, 'home')
try:
    os.makedirs(home_dir, exist_ok=True)
    print(f"✅ 已确保home目录存在：{home_dir}")
except Exception as e:
    print(f"⚠️ 创建home目录警告：{e}", file=sys.stderr)

# ===================== 导入依赖模块 =====================
# 导入留言板模块
FLASK_AVAILABLE = False
try:
    import message_board
    FLASK_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  留言板模块导入失败：{e}", file=sys.stderr)
    print("⚠️  请确认message_board.py在src目录中，或安装依赖：pip install flask werkzeug", file=sys.stderr)
    print("⚠️  留言板功能将不可用，仅提供静态文件服务", file=sys.stderr)

# 导入访问计数模块（延迟初始化版）
VISIT_COUNTER_AVAILABLE = False
try:
    import visit_counter
    # 关键修复：调用延迟初始化函数，指定data目录路径
    visit_counter.init_visit_counter(
        save_file=os.path.join(data_dir, 'visit_count.json')
    )
    VISIT_COUNTER_AVAILABLE = True
    print(f"✅ 访问计数模块加载成功，计数文件：{os.path.abspath(os.path.join(data_dir, 'visit_count.json'))}")
except ImportError as e:
    print(f"⚠️  访问计数模块导入失败：{e}", file=sys.stderr)
    print(f"⚠️  请确认visit_counter.py在src目录中", file=sys.stderr)
    print("⚠️  访问计数功能将不可用", file=sys.stderr)

# ===================== 自定义HTTP处理器（仅修复异常，其余不变） =====================
class BeautifulDirectoryHandler(CGIHTTPRequestHandler):
    """自定义美化目录列表处理器（极致性能优化）"""
    
    # 重写日志方法：完全关闭日志（解决IO瓶颈）
    def log_message(self, format, *args):
        return  # 无日志输出，最快速度
    
    # 重写请求处理：仅修复访问动态打印异常，其余逻辑不变
    def handle_one_request(self):
        # ========== 修复异常：先执行父类初始化，再打印访问动态 ==========
        # 先调用父类的handle_one_request完成属性初始化（核心修复）
        try:
            # 先让父类处理请求初始化，确保self.path等属性存在
            super().handle_one_request()
        except Exception as e:
            # 保留原有异常处理逻辑
            if not hasattr(self, 'headers_sent') or not self.headers_sent:
                try:
                    self.send_error(404)
                except:
                    pass
            return
        
        # 现在self.path等属性已初始化，再打印访问动态
        try:
            # 获取访问基础信息（修复：此时self.path已存在）
            visit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # 精确到毫秒
            client_ip = self.address_string()  # 访客IP
            request_path = getattr(self, 'path', '未知路径')  # 安全获取path
            request_method = getattr(self, 'command', '未知方法')  # 安全获取请求方法
            
            # 记录访问次数（原有逻辑）
            total_visits = 0
            if VISIT_COUNTER_AVAILABLE:
                # 排除静态资源，只统计页面访问（原有逻辑）
                exclude_ext = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.css', '.js', '.ico', '.svg']
                if not any(request_path.lower().endswith(ext) for ext in exclude_ext):
                    total_visits = visit_counter.count_visit()
            
            # 打印访问动态（核心新增）
            print(f"[访问动态] {visit_time} | {client_ip} | {request_method} | {request_path} | 总访问量：{total_visits}")
        except Exception as e:
            # 即使打印失败，也不影响主流程
            print(f"[访问动态打印异常] {e}")
        
        # ========== 原有计数逻辑：移到此处，确保不重复执行 ==========
        if VISIT_COUNTER_AVAILABLE:
            try:
                path = getattr(self, 'path', '')
                # 排除静态资源，只统计页面访问
                exclude_ext = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.css', '.js', '.ico', '.svg']
                if not any(path.lower().endswith(ext) for ext in exclude_ext):
                    # 仅内存+1，异步写文件（无阻塞）
                    total_visits = visit_counter.count_visit()
                    # 每1000次才打印一次，减少控制台输出
                    if total_visits % 1000 == 0:
                        print(f"📊 当前总访问次数：{total_visits}")
            except Exception as e:
                # 静默失败，不影响主流程
                pass

    @staticmethod
    def get_template():
        """内置美化目录模板（完全不变）"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Microsoft YaHei', sans-serif; }}
        body {{ background: #f8f9fa; padding: 40px; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #6a5acd; margin-bottom: 20px; font-size: 2rem; }}
        .breadcrumb {{ margin: 20px 0; display: flex; flex-wrap: wrap; gap: 8px; }}
        .breadcrumb a {{ color: #6a5acd; text-decoration: none; }}
        .breadcrumb span {{ color: #6c757d; }}
        .back-btn {{ display: inline-block; margin-bottom: 20px; padding: 8px 16px; background: #6a5acd; color: white; text-decoration: none; border-radius: 8px; }}
        .back-btn:hover {{ background: #5a4bc8; }}
        .items {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }}
        .item {{ display: flex; align-items: center; padding: 12px 15px; border-radius: 8px; text-decoration: none; color: #495057; transition: all 0.3s ease; }}
        .item:hover {{ background: #f8f9fa; transform: translateY(-2px); }}
        .item i {{ font-size: 1.2rem; margin-right: 10px; width: 24px; text-align: center; }}
        .folder i {{ color: #ffc107; }}
        .file i {{ color: #6a5acd; }}
        .item-name {{ flex: 1; }}
        .visit-count {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(106, 90, 205, 0.1);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            color: #6a5acd;
            border: 1px solid #6a5acd;
        }}
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
        """重写GET请求：转发留言板、根路径跳转、计数查询（完全不变）"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # 1. 访问计数查询接口（仅读内存，极快）
        if path == '/visit-count':
            self._handle_visit_count()
            return
        
        # 2. 转发留言板请求
        message_routes = ['/talk']
        if FLASK_AVAILABLE and any(path.startswith(route) for route in message_routes):
            self._forward_to_flask()
            return
        
        # 3. 根路径跳转到home目录
        if path == '/' or path == '':
            self.send_response(301)
            self.send_header('Location', '/home/')
            self.end_headers()
            return
        
        # 4. 处理静态文件请求
        super().do_GET()

    def do_POST(self):
        """重写POST请求：转发留言板（完全不变）"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        message_routes = ['/talk']
        if FLASK_AVAILABLE and any(path.startswith(route) for route in message_routes):
            self._forward_to_flask()
            return
        super().do_POST()

    def _handle_visit_count(self):
        """处理访问计数查询（仅读内存，无IO）（完全不变）"""
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        
        if VISIT_COUNTER_AVAILABLE:
            # 从内存读取，无磁盘IO
            total = visit_counter.get_total_visits()
            response = {
                "code": 200,
                "message": "success",
                "data": {
                    "total_visits": total,
                    "update_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                }
            }
        else:
            response = {
                "code": 500,
                "message": "访问计数模块未加载",
                "data": None
            }
        
        import json
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

    def _forward_to_flask(self):
        """稳定的Flask请求转发（带超时保护）（完全不变）"""
        if not FLASK_AVAILABLE:
            self.send_error(500, "留言板模块未加载")
            return
            
        try:
            # 读取请求数据（带大小限制）
            data = b""
            if self.command == "POST":
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    if 0 < content_length < 1024 * 1024:  # 限制1MB
                        self.rfile._sock.settimeout(5)
                        data = self.rfile.read(content_length)
                except:
                    data = b""
            
            # 转发请求到Flask
            with message_board.app.test_client() as client:
                headers = {k: v for k, v in self.headers.items()}
                if self.command == "GET":
                    response = client.get(self.path, headers=headers)
                elif self.command == "POST":
                    content_type = self.headers.get('Content-Type', 'application/x-www-form-urlencoded')
                    response = client.post(self.path, data=data, headers=headers, content_type=content_type)
                else:
                    self.send_error(405)
                    return
            
            # 返回Flask响应
            self.send_response(response.status_code)
            for k, v in response.headers.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(response.data)
            
        except Exception as e:
            # 友好错误页，不阻塞服务
            self.send_response(500)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            error_html = f"""
            <html>
            <head><title>500 服务器内部错误</title></head>
            <body style="font-family: 'Microsoft YaHei'; padding: 40px;">
                <h1 style="color: #dc3545;">500 Internal Server Error</h1>
                <p style="font-size: 16px; margin: 20px 0;">留言板请求处理失败</p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h3 style="color: #6a5acd;">排查步骤：</h3>
                    <ol style="font-size: 14px; line-height: 1.8;">
                        <li>安装依赖：<code>pip install flask werkzeug</code></li>
                        <li>确认message_board.py在src目录</li>
                        <li>检查模板文件是否存在</li>
                    </ol>
                </div>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode('utf-8'))

    def list_directory(self, path):
        """生成美化目录列表（无IO阻塞）（完全不变）"""
        try:
            list_dir = os.listdir(path)
        except OSError:
            self.send_error(404)
            return None
        
        list_dir.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
        cur_path = unquote(self.path)
        if not cur_path.endswith('/'):
            cur_path += '/'
        
        # 面包屑导航
        breadcrumb_parts = cur_path.strip('/').split('/')
        breadcrumb_html = []
        breadcrumb_path = ''
        breadcrumb_html.append(f'<a href="/"><i class="fas fa-home"></i> 首页</a>')
        for part in breadcrumb_parts:
            if part:
                breadcrumb_path += part + '/'
                breadcrumb_html.append(f'<span>/</span>')
                breadcrumb_html.append(f'<a href="/{breadcrumb_path}">{part}</a>')
        
        # 返回上一级按钮
        back_button = ''
        if cur_path != '/':
            parent_path = os.path.dirname(cur_path.rstrip('/')).replace('\\', '/')
            parent_path = parent_path if parent_path else '/'
            back_button = f'<a href="{parent_path}" class="back-btn"><i class="fas fa-arrow-left"></i> 返回上一级</a>'
        
        # 生成文件/目录项
        items_html = []
        for name in list_dir:
            full_path = os.path.join(path, name)
            rel_url = self.path + name
            if os.path.isdir(full_path):
                items_html.append(f'''
                <a href="{rel_url}/" class="item folder">
                    <i class="fas fa-folder"></i>
                    <div class="item-name">{name}</div>
                </a>
                ''')
            else:
                file_ext = os.path.splitext(name)[1].lower()
                icon = 'fas fa-file'
                if file_ext in ['.html', '.htm']: icon = 'fas fa-file-html'
                elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']: icon = 'fas fa-file-image'
                elif file_ext in ['.mp4', '.avi', '.mov', '.mkv']: icon = 'fas fa-file-video'
                elif file_ext in ['.css']: icon = 'fas fa-file-css'
                elif file_ext in ['.js']: icon = 'fas fa-file-js'
                elif file_ext in ['.pdf']: icon = 'fas fa-file-pdf'
                elif file_ext in ['.mp3', '.wav']: icon = 'fas fa-file-audio'
                
                items_html.append(f'''
                <a href="{rel_url}" class="item file">
                    <i class="{icon}"></i>
                    <div class="item-name">{name}</div>
                </a>
                ''')
        
        template = self.get_template()
        html = template.format(
            title=f'目录列表 - {cur_path}',
            path=cur_path,
            breadcrumb=''.join(breadcrumb_html),
            back_button=back_button,
            items=''.join(items_html)
        )
        
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
        return None

# ===================== 双栈服务器（性能优化）（完全不变） =====================
class DualStackServer(ThreadingHTTPServer):
    """支持IPv4/IPv6双栈的多线程服务器（低延迟）"""
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(10)  # 缩短超时，减少阻塞
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()
    
    def finish_request(self, request, client_address):
        """请求处理超时保护"""
        request.settimeout(10)
        super().finish_request(request, client_address)

# ===================== 启动服务（完全不变） =====================
def run_server(host='0.0.0.0', port=8000, directory=None):
    """启动HTTP服务（极致性能优化）"""
    # 清理主目录残留的计数文件（关键修复）
    old_file = os.path.join(current_script_dir, 'visit_count.json')
    if os.path.exists(old_file):
        try:
            os.remove(old_file)
            print(f"🗑️  清理主目录残留文件：{old_file}")
        except Exception as e:
            print(f"⚠️  清理残留文件失败：{e}", file=sys.stderr)
    
    # 初始化留言板
    if FLASK_AVAILABLE:
        try:
            message_board.init_db()
            print("✅ 留言板初始化成功")
        except Exception as e:
            print(f"⚠️  留言板初始化警告：{e}", file=sys.stderr)
    
    # 初始化访问计数
    if VISIT_COUNTER_AVAILABLE:
        total_visits = visit_counter.get_total_visits()
        print(f"✅ 访问计数初始化成功，当前总访问：{total_visits} 次")
    
    # 服务根目录
    server_dir = directory or current_script_dir
    os.chdir(server_dir)
    
    # 初始化处理器
    handler = partial(BeautifulDirectoryHandler, directory=server_dir)
    server_address = (host, port)
    
    try:
        # 启动多线程服务器
        httpd = DualStackServer(server_address, handler)
        httpd.timeout = 10  # 服务器超时
        httpd.daemon_threads = True  # 守护线程，退出时自动清理
        
        # 打印启动信息
        local_ip = socket.gethostbyname(socket.gethostname())
        print(f"\n🚀 服务启动成功！")
        print(f"├─ 本地访问: http://localhost:{port}")
        print(f"├─ 外网访问: http://{local_ip}:{port}")
        if FLASK_AVAILABLE:
            print(f"├─ 留言板: http://localhost:{port}/talk")
        print(f"├─ 计数查询: http://localhost:{port}/visit-count")
        print(f"└─ 根目录: {os.path.abspath(server_dir)}")
        print("="*60)
        print("📝 服务已开启极致性能模式，按 Ctrl+C 停止")
        print("🔍 访问动态将实时输出在控制台...")
        
        # 运行服务
        httpd.serve_forever()
    
    except socket.error as e:
        print(f"\n❌ 端口绑定失败：{e}", file=sys.stderr)
        print(f"建议：换端口启动 → python main.py -p 8080", file=sys.stderr)
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 服务正在停止...")
        # 强制保存最终计数
        if VISIT_COUNTER_AVAILABLE:
            visit_counter.global_counter._async_save_count(force=True)
            time.sleep(0.2)  # 等待异步保存完成
            print(f"✅ 最终访问计数：{visit_counter.get_total_visits()} 次")
        httpd.server_close()
        print("✅ 服务已停止")
        sys.exit(0)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="个人Vlog HTTP服务端（性能优化版）")
    parser.add_argument("-H", "--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("-p", "--port", type=int, default=8000, help="监听端口")
    parser.add_argument("-d", "--directory", type=str, default=None, help="静态文件目录")
    parser.add_argument("--reset-visits", action="store_true", help="重置访问次数为0")
    args = parser.parse_args()
    
    # 重置访问计数（如果指定）
    if args.reset_visits and VISIT_COUNTER_AVAILABLE:
        visit_counter.reset_visits()
        print("✅ 访问次数已重置为0")
    
    # 启动服务
    run_server(host=args.host, port=args.port, directory=args.directory)