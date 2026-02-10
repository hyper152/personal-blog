# -*- coding: utf-8 -*-
"""
个人Vlog HTTP服务端（最终稳定版）
✅ 修复POST数据seek失败问题
✅ 修复/talk 500错误
✅ 适配Conda环境
✅ 支持IPv4/IPv6双栈
✅ 自动创建home目录
留言板路由：/talk | 模板目录：talk/
"""
import socket
import sys
import os
import contextlib
from functools import partial
from http.server import (
    CGIHTTPRequestHandler,
    ThreadingHTTPServer
)
from urllib.parse import unquote, urlparse

# 确保当前目录加入Python路径（适配Conda环境）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import message_board
    FLASK_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  留言板模块导入失败：{e}", file=sys.stderr)
    print("⚠️  请先安装依赖：pip install flask werkzeug", file=sys.stderr)
    print("⚠️  留言板功能将不可用，仅提供静态文件服务", file=sys.stderr)
    FLASK_AVAILABLE = False

class BeautifulDirectoryHandler(CGIHTTPRequestHandler):
    """自定义美化目录列表处理器"""
    
    @staticmethod
    def get_template():
        """读取directory_template.html模板，不存在则使用内置极简模板"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, 'directory_template.html')
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"提示：未找到模板文件 {template_path}，使用内置美化模板", file=sys.stderr)
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
        """重写GET请求处理：优先转发 /talk 路由，再处理首页跳转"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # 匹配留言板路由
        message_routes = ['/talk']
        if FLASK_AVAILABLE and any(path.startswith(route) for route in message_routes):
            self._forward_to_flask()
            return
        
        # 根路径自动跳转到 /home/，先确保home目录存在
        if path == '/' or path == '':
            home_dir = os.path.join(os.getcwd(), 'home')
            if not os.path.exists(home_dir):
                os.makedirs(home_dir)
                print(f"✅ 自动创建home目录：{home_dir}")
            self.send_response(301)
            self.send_header('Location', '/home/')
            self.end_headers()
            return
        
        super().do_GET()

    def do_POST(self):
        """重写POST请求处理：转发所有留言板相关POST请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        message_routes = ['/talk']
        if FLASK_AVAILABLE and any(path.startswith(route) for route in message_routes):
            self._forward_to_flask()
            return
        super().do_POST()

    def _forward_to_flask(self):
        """极简版Flask请求转发（彻底修复500错误+POST数据丢失）"""
        if not FLASK_AVAILABLE:
            self.send_error(500, "留言板模块未加载，请检查依赖和文件")
            return
            
        try:
            # 1. 基础请求信息
            path = self.path
            method = self.command
            headers = {k: v for k, v in self.headers.items()}
            
            # 2. 读取POST数据（适配socket流，不使用seek）
            data = b""
            if method == "POST":
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    if content_length > 0 and content_length < 1024 * 1024:
                        data = self.rfile.read(content_length)
                        print(f"📤 转发POST数据：{data.decode('utf-8', errors='ignore')}")
                except Exception as e:
                    print(f"读取POST数据警告：{e}", file=sys.stderr)
                    data = b""
            
            # 3. 使用Flask test_client转发（最稳定的方式）
            with message_board.app.test_client() as client:
                if method == "GET":
                    response = client.get(path, headers=headers)
                elif method == "POST":
                    # 显式指定Content-Type，确保表单数据解析正常
                    content_type = self.headers.get('Content-Type', 'application/x-www-form-urlencoded')
                    response = client.post(path, data=data, headers=headers, content_type=content_type)
                else:
                    self.send_error(405, "Method Not Allowed")
                    return
            
            # 4. 发送Flask响应给客户端
            self.send_response(response.status_code)
            # 转发所有响应头
            for k, v in response.headers.items():
                self.send_header(k, v)
            self.end_headers()
            # 发送响应体
            self.wfile.write(response.data)
            
        except Exception as e:
            error_msg = f"转发请求失败: {str(e)}"
            print(f"❌ 500错误详情：{error_msg}", file=sys.stderr)
            # 返回友好的错误页面
            self.send_response(500)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            error_html = f"""
            <html>
            <head><title>500 服务器内部错误</title></head>
            <body style="font-family: 'Microsoft YaHei'; padding: 40px;">
                <h1 style="color: #dc3545;">500 Internal Server Error</h1>
                <p style="font-size: 16px; margin: 20px 0;">错误详情：{error_msg}</p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h3 style="color: #6a5acd;">排查步骤：</h3>
                    <ol style="font-size: 14px; line-height: 1.8;">
                        <li>确认已安装依赖：<code>pip install flask werkzeug</code></li>
                        <li>确认message_board.py在当前目录</li>
                        <li>确认talk/comment.html模板文件存在</li>
                        <li>检查终端日志，查看具体错误原因</li>
                    </ol>
                </div>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode('utf-8'))

    def list_directory(self, path):
        """重写目录列表方法，生成美化的HTML页面"""
        try:
            list_dir = os.listdir(path)
        except OSError:
            self.send_error(404, "无法列出目录")
            return None
        
        list_dir.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
        cur_path = unquote(self.path)
        if not cur_path.endswith('/'):
            cur_path += '/'
        
        # 生成面包屑导航
        breadcrumb_parts = cur_path.strip('/').split('/')
        breadcrumb_html = []
        breadcrumb_path = ''
        breadcrumb_html.append(f'<a href="/"><i class="fas fa-home"></i> 首页</a>')
        for part in breadcrumb_parts:
            if part:
                breadcrumb_path += part + '/'
                breadcrumb_html.append(f'<span>/</span>')
                breadcrumb_html.append(f'<a href="/{breadcrumb_path}">{part}</a>')
        
        # 生成返回上一级按钮
        back_button = ''
        if cur_path != '/':
            parent_path = os.path.dirname(cur_path.rstrip('/')).replace('\\', '/')
            if parent_path == '':
                parent_path = '/'
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
                if file_ext in ['.html', '.htm']:
                    icon = 'fas fa-file-html'
                elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    icon = 'fas fa-file-image'
                elif file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
                    icon = 'fas fa-file-video'
                elif file_ext in ['.css']:
                    icon = 'fas fa-file-css'
                elif file_ext in ['.js']:
                    icon = 'fas fa-file-js'
                elif file_ext in ['.pdf']:
                    icon = 'fas fa-file-pdf'
                elif file_ext in ['.mp3', '.wav']:
                    icon = 'fas fa-file-audio'
                
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


class DualStackServer(ThreadingHTTPServer):
    """支持IPv4/IPv6双栈的多线程HTTP服务端"""
    
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def run_server(port=8000, directory=None):
    """启动HTTP服务端（简化版，适配Conda环境）"""
    # 初始化留言板
    if FLASK_AVAILABLE:
        try:
            message_board.init_db()
            print("✅ 留言板初始化成功")
        except Exception as e:
            print(f"⚠️  留言板初始化警告：{e}", file=sys.stderr)
    
    # 确定服务根目录
    server_dir = directory or os.getcwd()
    if not os.path.exists(server_dir):
        os.makedirs(server_dir)
    
    # 确保home目录存在
    home_dir = os.path.join(server_dir, 'home')
    if not os.path.exists(home_dir):
        os.makedirs(home_dir)
    
    os.chdir(server_dir)
    handler = partial(BeautifulDirectoryHandler, directory=server_dir)
    server_address = ('', port)
    
    try:
        httpd = DualStackServer(server_address, handler)
        print(f"\n🚀 服务启动成功！")
        print(f"首页地址: http://localhost:{port} (自动跳转到 /home/)")
        if FLASK_AVAILABLE:
            print(f"留言板地址: http://localhost:{port}/talk")
        print(f"服务根目录: {os.path.abspath(server_dir)}")
        print(f"Python环境: {sys.executable}")
        print("="*60)
        print("按 Ctrl+C 停止服务")
        
        httpd.serve_forever()
    
    except socket.error as e:
        print(f"\n❌ 端口绑定失败：{e}", file=sys.stderr)
        print(f"建议：换端口启动，例如：python main.py -p 8080", file=sys.stderr)
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 服务正在停止...")
        httpd.server_close()
        print("✅ 服务已停止")
        sys.exit(0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="个人Vlog HTTP服务端（稳定版）")
    parser.add_argument("-p", "--port", type=int, default=8000, help="监听端口（默认：8000）")
    parser.add_argument("-d", "--directory", type=str, default=".", help="静态文件根目录（默认：当前目录）")
    args = parser.parse_args()
    
    # 启动服务
    run_server(port=args.port, directory=args.directory)