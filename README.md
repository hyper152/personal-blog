以下是为你生成的 `README.md` 文件，它清晰地介绍了项目的整体结构、功能模块、技术栈以及如何快速上手，适合放在 GitHub 或其他代码托管平台上作为项目说明文档：

```markdown
# 🎥 hyper 的个人 Vlog

这是一个记录个人成长、项目开发、旅行经历、校园生活等内容的个人博客/日志项目。它不仅仅是一个静态网站，还包含了用户认证、留言板、访问统计等动态功能，是一个功能相对完整的小型 Web 应用。

## ✨ 功能特性

-   **用户系统**
    -   邮箱注册/登录
    -   密码加密存储
    -   验证码登录
    -   基于 Session 的登录状态管理
-   **交互功能**
    -   留言板：登录用户可留言，实时显示留言列表
    -   访问统计：记录网站总访问量
-   **内容展示**
    -   美观的首页，展示最新动态和内容分类
    -   分类浏览（旅行、DIY、开发日志、校园生活等）
    -   目录美化功能，方便浏览服务器上的文件
-   **技术特性**
    -   纯 Python 实现，无需额外安装复杂的 Web 服务器
    -   `main.py` 提供静态文件服务和 API 代理
    -   `developing.py` 提供网站升级维护模式
    -   内置邮件发送功能（QQ邮箱）
    -   请求限流、敏感路径保护等安全增强

## 🗂️ 项目结构

```text
.personal_vlog/
├── main.py                  # 主服务程序（静态文件+API代理）
├── developing.py            # 升级维护模式服务
├── git_batch_push.sh        # Git批量推送脚本
├── directory_template.html  # 目录列表页面的HTML模板
├── README.md                # 项目说明文档
├── .gitignore               # Git忽略文件配置
├── data/                    # 数据存储目录
│   ├── messages.json        # 留言板数据
│   ├── users.json           # 用户注册信息
│   ├── sessions.json        # 用户登录会话
│   └── visit_count.json     # 访问计数数据
├── home/                     # 首页相关文件
│   ├── index.html            # 首页HTML
│   └── img/                  # 首页图片资源
├── pages/                    # 各类内容页面
│   ├── devlog/               # 开发日志
│   ├── diy/                  # DIY专区
│   ├── travel/               # 旅行记录
│   ├── video/                # 视频文件
│   └── YY往事/               # 校园生活回忆
├── src/                      # 功能模块源码
│   ├── auth.py               # 用户认证核心（加密、会话管理）
│   ├── message_board.py      # Flask留言板应用
│   ├── qqmail.py             # QQ邮件发送模块
│   ├── test_email.py         # 邮件发送测试脚本
│   └── visit_counter.py      # 异步访问计数模块
├── static/                   # 静态资源
│   └── js/
│       ├── auth.js            # 前端登录状态管理
│       └── auth-interceptor.js # 请求拦截器（自动处理未授权）
├── login/                    # 登录注册页面
│   ├── index.html             # 登录页
│   └── register.html          # 注册页
├── talk/                      # 留言板页面
│   └── comment.html           # 留言板主页面
└── logs/                      # 运行日志（自动生成）
```

## 🚀 快速开始

### 环境要求

-   Python 3.6+
-   无需安装第三方库（全部使用 Python 标准库）

### 启动主服务

1.  **克隆项目**
    ```bash
    git clone https://github.com/hyper152/personal-blog.git
    cd .personal_vlog
    ```

2.  **运行主程序**
    ```bash
    python main.py
    ```
    服务启动后，访问 `http://localhost:8000` 即可看到首页。

3.  **命令行选项**
    ```bash
    # 指定端口和地址
    python main.py -p 8080 -H 127.0.0.1

    # 重置访问计数
    python main.py --reset-visits
    ```

### 启动升级维护模式

当需要对网站进行升级或维护时，可以运行 `developing.py`，它将显示一个友好的维护提示页面。

```bash
python developing.py
```

访问 `http://localhost:8000` 将看到“网站升级中”的提示。

### 邮件功能配置（可选）

如果需要完整的注册/登录功能（验证码发送），需要在 `src/qqmail.py` 中配置你的 QQ 邮箱和授权码：

```python
QQ_MAIL_USER = "你的QQ邮箱@qq.com"
QQ_MAIL_AUTH_CODE = "你的16位SMTP授权码"  # 在QQ邮箱设置中获取
```

## 🛠️ 核心技术点

-   **双模式服务**：`main.py` 用于日常运行，`developing.py` 用于维护模式，互不干扰。
-   **统一入口**：`main.py` 同时处理静态文件请求，并将 `/api/` 开头的请求转发给 `message_board.py` (Flask 应用)，实现了前后端分离。
-   **安全设计**：
    -   密码使用 `盐值+SHA256` 加密存储。
    -   数据目录 (`/data/`) 和敏感文件受到访问保护。
    -   内置请求限流，防止恶意攻击。
-   **异步计数**：`visit_counter.py` 使用多线程异步保存访问计数，避免频繁磁盘 I/O 影响性能。
-   **前端工程化**：`auth.js` 统一管理前端登录状态，`auth-interceptor.js` 自动拦截 401 响应并跳转到登录页。

## 📝 维护与扩展

1.  **新增内容页面**：参考 `directory_template.html` 的结构，在 `pages/` 目录下按分类创建新的 HTML 文件。
2.  **修改数据存储**：所有 JSON 数据文件位于 `data/` 目录，可直接编辑，但建议通过程序接口操作。
3.  **日志查看**：运行日志保存在 `logs/` 目录下，按天分割，方便排查问题。
4.  **添加新功能**：可在 `src/` 目录下创建新的 Python 模块，并在 `main.py` 的 `do_GET/do_POST` 中添加路由转发逻辑。

## 📄 许可证

本项目为个人学习与记录用途，代码开源仅供交流参考，未经许可请勿用于商业目的。
```

这个 README 文件涵盖了项目的核心信息，包括：
1.  **项目简介**：让访客快速了解这个项目是做什么的。
2.  **功能特性**：清晰地列出了项目的亮点。
3.  **项目结构**：用树状图展示了所有重要文件和目录的作用。
4.  **快速开始**：提供了从零开始运行项目的详细步骤。
5.  **技术解析**：解释了项目中一些巧妙的设计和实现。
6.  **维护指南**：为后续的更新和扩展提供了方向。

你可以直接将其复制到项目的根目录下。
