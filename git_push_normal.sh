#!/bin/bash
# 日常正常推送脚本（适配常规开发，SSH协议）
# 功能：拉取远程最新 → 检查本地修改 → 批量提交 → 推送
# 使用方式：./git_push_normal.sh "自定义提交备注"

# ===================== 配置项（可根据需要修改） =====================
REMOTE_REPO="git@github.com:hyper152/Gsing-log.git"  # SSH远程地址
BRANCH="main"                                         # 推送分支
COMMIT_REMARK=$1                                      # 自定义提交备注（运行时传入）

# ===================== 核心逻辑 =====================
echo -e "\033[34m==================== 日常推送流程 ====================\033[0m"

# 1. 检查是否传入提交备注
if [ -z "$COMMIT_REMARK" ]; then
    echo -e "\033[31m❌ 错误：请传入提交备注！示例：./git_push_normal.sh '修复xxx功能'\033[0m"
    exit 1
fi

# 2. 检查是否在Git仓库目录
if [ ! -d ".git" ]; then
    echo -e "\033[31m❌ 错误：当前目录不是Git仓库！\033[0m"
    exit 1
fi

# 3. 拉取远程最新代码（解决冲突，日常开发必备）
echo -e "\033[32m🔄 拉取远程$BRANCH分支最新代码...\033[0m"
git fetch origin $BRANCH
git pull origin $BRANCH --rebase

# 4. 检查本地是否有修改
LOCAL_CHANGES=$(git status --porcelain)
if [ -z "$LOCAL_CHANGES" ]; then
    echo -e "\033[33m⚠️  本地无修改，无需提交！\033[0m"
    exit 0
fi

# 5. 添加所有修改的文件（排除.gitignore屏蔽的文件）
echo -e "\033[32m📝 添加所有修改的文件到暂存区...\033[0m"
git add .

# 6. 提交（日期+自定义备注，规范提交信息）
CURRENT_DATE=$(date +"%Y-%m-%d %H:%M:%S")
COMMIT_MSG="[$CURRENT_DATE] $COMMIT_REMARK"
echo -e "\033[32m✅ 提交信息：$COMMIT_MSG\033[0m"
git commit -m "$COMMIT_MSG"

# 7. SSH协议推送（常规推送，非强制）
echo -e "\033[32m🚀 推送$BRANCH分支到远程（SSH协议）...\033[0m"
git push origin $BRANCH

# 8. 完成提示
echo -e "\033[34m==================== 推送完成 ====================\033[0m"
echo -e "\033[31m✅ 1. 已拉取远程最新代码\n✅ 2. 本地修改已提交并推送\n✅ 3. 提交信息：$COMMIT_MSG\033[0m"