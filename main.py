# -*- coding: utf-8 -*-
"""
个人Vlog HTTP服务端（带美化目录列表+home为首页）
支持根路径跳转到/home/，home目录为站点首页
HTML模板已分离为独立文件
"""
import socket
import sys
import os
import contextlib
from functools import partial
from http.server import (
    SimpleHTTPRequestHandler,
    CGIHTTPRequestHandler,
    ThreadingHTTPServer
)
from urllib.parse import unquote, urlparse


class BeautifulDirectoryHandler(CGIHTTPRequestHandler):
    """自定义美化目录列表处理器（新增首页跳转逻辑）"""
    
    @staticmethod
    def get_template():
        """读取外部HTML模板文件"""
        # 获取模板文件路径（和当前py文件同目录）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, 'directory_template.html')
        
        # 读取模板内容
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            # 降级方案：如果模板文件不存在，使用极简模板
            print(f"警告：未找到模板文件 {template_path}，使用极简模板", file=sys.stderr)
            return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>body{{font-family:Arial;margin:20px;}}</style>
</head>
<body>
    <h1>目录列表: {path}</h1>
    {back_button}
    <div>{items}</div>
</body>
</html>
            """

    def do_GET(self):
        """重写GET请求处理，实现根路径跳转到/home/"""
        # 解析请求路径
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # 1. 根路径（/）自动跳转到/home/
        if path == '/' or path == '':
            self.send_response(301)  # 永久重定向
            self.send_header('Location', '/home/')
            self.end_headers()
            return
        
        # 2. 访问/home/时优先加载index.html（默认行为，无需额外处理）
        # 3. 其他路径正常处理（目录列表/文件访问）
        super().do_GET()

    def list_directory(self, path):
        """重写目录列表方法，使用外部模板生成美化后的HTML"""
        try:
            list_dir = os.listdir(path)
        except OSError:
            self.send_error(404, "无法列出目录")
            return None
        
        # 排序：文件夹在前，文件在后，按名称排序
        list_dir.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
        
        # 当前请求路径
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
        
        # 生成目录/文件项
        items_html = []
        for name in list_dir:
            # 处理路径分隔符（兼容Windows）
            full_path = os.path.join(path, name)
            rel_url = self.path + name
            if os.path.isdir(full_path):
                # 文件夹
                items_html.append(f'''
                <a href="{rel_url}/" class="item folder">
                    <i class="fas fa-folder"></i>
                    <div class="item-name">{name}</div>
                </a>
                ''')
            else:
                # 文件（简单识别常见类型图标）
                file_ext = os.path.splitext(name)[1].lower()
                icon = 'fas fa-file'
                if file_ext in ['.html', '.htm']:
                    icon = 'fas fa-file-html'
                elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    icon = 'fas fa-file-image'
                elif file_ext in ['.mp4', '.avi', '.mov']:
                    icon = 'fas fa-file-video'
                elif file_ext in ['.css']:
                    icon = 'fas fa-file-css'
                elif file_ext in ['.js']:
                    icon = 'fas fa-file-js'
                elif file_ext in ['.pdf']:
                    icon = 'fas fa-file-pdf'
                
                items_html.append(f'''
                <a href="{rel_url}" class="item file">
                    <i class="{icon}"></i>
                    <div class="item-name">{name}</div>
                </a>
                ''')
        
        # 获取外部模板并渲染
        template = self.get_template()
        html = template.format(
            title=f'目录列表 - {cur_path}',
            path=cur_path,
            breadcrumb=''.join(breadcrumb_html),
            back_button=back_button,
            items=''.join(items_html)
        )
        
        # 发送响应
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
        return None


class DualStackServer(ThreadingHTTPServer):
    """支持IPv4/IPv6双栈的多线程HTTP服务端"""
    
    def server_bind(self):
        """重写绑定方法，实现双栈监听"""
        # 设置套接字可重用地址，避免端口占用问题
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # 尝试启用IPv6兼容模式（兼容IPv4）
        with contextlib.suppress(Exception):
            self.socket.setsockopt(
                socket.IPPROTO_IPV6,
                socket.IPV6_V6ONLY,
                0  # 关闭IPv6独用，允许同一端口监听IPv4
            )
        
        # 执行父类绑定逻辑
        super().server_bind()


def run_server(
    server_class=DualStackServer,
    handler_class=BeautifulDirectoryHandler,  # 使用美化处理器
    port=8000,
    directory=None
):
    """
    启动HTTP服务端
    :param server_class: 服务端类
    :param handler_class: 请求处理器类
    :param port: 监听端口
    :param directory: 静态文件根目录
    """
    # 确定服务根目录（优先自定义，否则用当前工作目录）
    server_dir = directory or os.getcwd()
    
    # 检查目录是否存在，不存在则自动创建
    if not os.path.exists(server_dir):
        os.makedirs(server_dir)
        print(f"目录不存在，已自动创建：{os.path.abspath(server_dir)}")
    
    os.chdir(server_dir)
    
    # 绑定处理器与根目录
    handler = partial(handler_class, directory=server_dir)
    
    # 配置服务端地址（0.0.0.0表示监听所有网卡）
    server_address = ('', port)
    
    try:
        # 创建服务端实例
        httpd = server_class(server_address, handler)
        print(f"服务启动成功 🚀")
        print(f"首页地址: http://localhost:{port} (自动跳转到 /home/)")
        print(f"直接访问首页: http://localhost:{port}/home/")
        print(f"服务根目录: {os.path.abspath(server_dir)}")
        print(f"支持协议: IPv4 + IPv6 (双栈)")
        print("按 Ctrl+C 停止服务")
        
        # 持续运行服务
        httpd.serve_forever()
    
    except socket.error as e:
        print(f"端口绑定失败 ❌: {e}", file=sys.stderr)
        print(f"请检查端口 {port} 是否被占用，或尝试使用其他端口", file=sys.stderr)
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n服务正在停止... 🛑")
        httpd.server_close()
        print("服务已停止 ✅")
        sys.exit(0)


if __name__ == "__main__":
    # 命令行参数解析（支持自定义端口和目录）
    import argparse
    parser = argparse.ArgumentParser(description="个人Vlog HTTP服务端（带美化目录列表+home为首页）")
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8000,
        help="监听端口（默认：8000）"
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        default=".",  # 默认当前目录
        help="静态文件根目录（默认：当前目录）"
    )
    args = parser.parse_args()
    
    # 启动服务
    run_server(port=args.port, directory=args.directory)