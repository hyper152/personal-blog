# Personal Vlog 个人博客/日志项目
这是一个记录个人成长、项目开发、旅行经历、校园生活等内容的个人博客/日志项目，包含了丰富的多媒体素材和配套的功能代码。

## 📁 项目结构
```
.personal_vlog/
├── .gitignore               # Git忽略文件配置
├── directory_template.html  # 目录模板HTML文件
├── git_batch_push.sh        # Git批量推送脚本
├── main.py                  # 项目主程序
├── README.md                # 项目说明文档
├── data/                    # 数据存储目录
│   ├── messages.json        # 留言板数据
│   └── visit_count.json     # 访问计数数据
├── home/                    # 首页相关文件
│   ├── index.html           # 首页HTML
│   └── img/                 # 首页图片资源
├── pages/                   # 各类内容页面
│   ├── devlog/              # 开发日志（项目开发记录）
│   ├── diy/                 # DIY相关（硬件改造等）
│   ├── travel/              # 旅行记录
│   ├── video/               # 视频文件
│   └── YY往事/              # 校园生活回忆
├── src/                     # 功能模块源码
│   ├── message_board.py     # 留言板功能
│   ├── qqmail.py            # QQ邮件相关功能
│   └── visit_counter.py     # 访问计数功能
└── talk/                    # 评论/留言相关页面
    ├── comment.html         # 评论页面
    └── show.html            # 展示页面
```

## 🗂️ 内容分类说明
### 1. 开发日志 (devlog)
记录各类技术项目的开发过程，包括：
- CQU-coursehelper：课程助手项目
- CQU-CRTC机器人比赛：机器人比赛开发记录（包含各版本迭代视频）
- Gsing：机械臂、视觉识别等项目开发
- personal-blog：个人博客网站迭代记录
- 声控开关灯：硬件DIY项目

### 2. DIY 专区
记录电脑硬件选购、改造等内容，包含各类硬件参数、改造过程照片。

### 3. 旅行记录 (travel)
包含上海、杭州、南京、百丈漈、雁荡山等地的旅行照片和记录，涵盖：
- 高校强基计划面试经历
- 足球观赛
- 自然景观游览

### 4. 校园生活回忆 (YY往事)
丰富的校园生活记录，包含：
- 班级日常（战狼班班务日志、成绩单）
- 各类活动（运动会、百日誓师、喊楼、远足等）
- 课间活动、寝室生活
- 高考倒计时记录
- 游戏相关记录（CS、LOL、VALORANT等）
- 校园雪景、纸飞机等趣味内容

## 🚀 功能模块
### 1. 访问计数 (visit_counter.py)
- 统计网站访问次数
- 数据存储在 `data/visit_count.json`

### 2. 留言板 (message_board.py)
- 处理用户留言功能
- 留言数据存储在 `data/messages.json`
- 配套页面：`talk/comment.html`、`talk/show.html`

### 3. 邮件功能 (qqmail.py)
- QQ邮件发送/接收相关功能
- 可用于留言通知、访问统计报告等

## 🛠️ 快速使用
### 环境要求
- Python 3.x
- 所需依赖可根据代码中import的库自行安装

### 运行主程序
```bash
python main.py
```

### Git批量推送
```bash
chmod +x git_batch_push.sh
./git_batch_push.sh
```

## 📋 维护说明
1. 新增内容时可参考 `directory_template.html` 创建页面
2. 多媒体文件按分类存放在对应目录下，保持命名规范
3. 定期备份 `data/` 目录下的JSON文件，防止数据丢失
4. 新增功能模块请放在 `src/` 目录下，并在main.py中集成

## 📄 许可证
本项目为个人记录用途，所有内容仅供参考，未经许可请勿商用。
