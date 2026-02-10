#!/bin/bash
# 安全批量推送文件：优先拉取远程代码+排除压缩文件/图片/视频+抗限流推送
# 适配全新仓库拉取逻辑，支持自定义提交备注+精准时间戳

# ===================== 可配置参数 =====================
BATCH_SIZE=200  # 增大批次，减少推送次数
REMOTE_REPO="git@github.com:hyper152/personal-blog.git"  # 已修改仓库地址
REMOTE_BRANCH="master"  # 核心修改：main → master
RETRY_TIMES=5   # 推送失败重试次数
DELAY_SECONDS=5 # 批次间延迟
# 排除压缩文件+图片+视频+无用路径（新增图片/视频排除）
EXCLUDE_PATHS=(
    "./.git/*"
    "./data/video/*"
    "./git_batch_push.sh"
    # 压缩文件
    "*.rar"
    "*.zip"
    "*.7z"
    "*.tar"
    "*.gz"
    "*.bz2"
    "*.xz"
    "*.iso"
    # 图片文件
    "*.jpg"
    "*.jpeg"
    "*.png"
    "*.gif"
    "*.bmp"
    "*.tiff"
    "*.webp"
    "*.svg"
    "*.ico"
    "*.heic"
    "*.heif"
    # 视频文件
    "*.mp4"
    "*.avi"
    "*.mov"
    "*.wmv"
    "*.flv"
    "*.mkv"
    "*.webm"
    "*.mpeg"
    "*.mpg"
    "*.m4v"
    "*.3gp"
    "*.ogv"
    "*.ts"
    "*.mts"
    "*.f4v"
)

# ===================== 工具函数 =====================
# 带重试的推送
push_with_retry() {
    local batch_num=$1
    local custom_note=$2
    local retry=0
    while [ $retry -lt $RETRY_TIMES ]; do
        echo -e "\033[33m🔄 推送批次$batch_num（重试$((retry+1))/$RETRY_TIMES）...\033[0m"
        if git push -f origin "$REMOTE_BRANCH"; then  # 引用修改后的master分支
            echo -e "\033[32m🚀 [批次$batch_num] 已推送到远程仓库\033[0m"
            return 0
        else
            echo -e "\033[31m⚠️  [批次$batch_num] 推送失败，${DELAY_SECONDS}秒后重试...\033[0m"
            retry=$((retry+1))
            sleep $DELAY_SECONDS
        fi
    done
    echo -e "\033[31m❌ [批次$batch_num] 推送失败（已重试$RETRY_TIMES次）\033[0m"
    return 1
}

# 安全拉取远程代码（适配全新仓库）
safe_git_pull() {
    echo -e "\033[33m🔄 拉取远程$REMOTE_BRANCH分支最新代码...\033[0m"  # 引用修改后的master分支
    # 先检查本地是否有提交（全新仓库无提交则跳过合并）
    if git rev-parse --verify HEAD >/dev/null 2>&1; then
        # 本地有提交：正常拉取+合并
        if git pull origin "$REMOTE_BRANCH" --allow-unrelated-histories 2>/dev/null; then  # 引用master
            echo -e "\033[32m✅ 已成功拉取并合并远程最新代码\033[0m"
            return 0
        else
            echo -e "\033[31m⚠️  拉取代码冲突，尝试强制拉取...\033[0m"
            git pull origin "$REMOTE_BRANCH" --allow-unrelated-histories -f 2>/dev/null && echo -e "\033[32m✅ 强制拉取成功\033[0m" || return 1  # 引用master
        fi
    else
        # 本地无提交（全新仓库）：直接获取远程分支，不合并
        if git fetch origin "$REMOTE_BRANCH":temp_branch 2>/dev/null; then  # 引用master
            echo -e "\033[32m✅ 已获取远程代码（全新仓库，跳过合并）\033[0m"
            git branch -D temp_branch 2>/dev/null # 清理临时分支
            return 0
        else
            echo -e "\033[31m⚠️  远程仓库无代码，跳过拉取\033[0m"
            return 0
        fi
    fi
}

# ===================== 第一步：获取用户自定义备注 =====================
echo -e "\033[34m==================== 请输入本次提交的自定义备注 ====================\033[0m"
read -p "👉 输入备注内容（例如：数学标签数据-第1批）：" CUSTOM_NOTE
# 如果用户未输入，默认备注
if [ -z "$CUSTOM_NOTE" ]; then
    CUSTOM_NOTE="批量提交数据文件"
fi
echo -e "\033[32m✅ 本次提交备注：$CUSTOM_NOTE\033[0m"

# ===================== 第二步：优先拉取远程代码（核心恢复） =====================
echo -e "\033[34m==================== 第一步：拉取远程最新代码 ====================\033[0m"
if [ ! -d ".git" ]; then
    git init
    git branch -M "$REMOTE_BRANCH"  # 核心修改：初始化分支为master
    git remote add origin "$REMOTE_REPO"
    echo -e "\033[32m✅ 已初始化本地Git仓库，分支为$REMOTE_BRANCH\033[0m"  # 显示master
else
    git remote set-url origin "$REMOTE_REPO" 2>/dev/null || git remote add origin "$REMOTE_REPO"
    echo -e "\033[32m✅ 已更新远程仓库地址：$REMOTE_REPO\033[0m"
fi

# 执行安全拉取（适配所有场景）
if ! safe_git_pull; then
    echo -e "\033[31m❌ 拉取远程代码失败，但继续执行推送流程（仅影响历史合并）\033[0m"
fi

# ===================== 第三步：配置.gitignore（永久忽略压缩/图片/视频文件） =====================
echo -e "\033[34m==================== 第二步：配置永久忽略压缩/图片/视频文件 ====================\033[0m"
# 生成精准时间戳（年-月-日 时:分:秒）
TIMESTAMP_GITIGNORE=$(date +"%Y-%m-%d %H:%M:%S")
IGNORE_RULES=(
    # 压缩文件
    "*.rar"
    "*.zip"
    "*.7z"
    "*.tar"
    "*.gz"
    "*.bz2"
    "*.xz"
    "*.iso"
    # 图片文件
    "*.jpg"
    "*.jpeg"
    "*.png"
    "*.gif"
    "*.bmp"
    "*.tiff"
    "*.webp"
    "*.svg"
    "*.ico"
    "*.heic"
    "*.heif"
    # 视频文件
    "*.mp4"
    "*.avi"
    "*.mov"
    "*.wmv"
    "*.flv"
    "*.mkv"
    "*.webm"
    "*.mpeg"
    "*.mpg"
    "*.m4v"
    "*.3gp"
    "*.ogv"
    "*.ts"
    "*.mts"
    "*.f4v"
    # 路径忽略
    "data/video/"
)

for rule in "${IGNORE_RULES[@]}"; do
    if ! grep -qxF "$rule" .gitignore 2>/dev/null; then
        echo "$rule" >> .gitignore
        echo -e "\033[32m✅ 已添加忽略规则：$rule\033[0m"
    fi
done

# .gitignore提交信息：精准时间+自定义备注
git add .gitignore
git commit -m "[$TIMESTAMP_GITIGNORE] 更新.gitignore - $CUSTOM_NOTE" >/dev/null 2>&1

# ===================== 第四步：获取待推送文件 =====================
echo -e "\033[34m==================== 第三步：获取待推送文件列表 ====================\033[0m"
EXCLUDE_ARGS=()
for path in "${EXCLUDE_PATHS[@]}"; do
    [[ "$path" == *"*."* ]] && EXCLUDE_ARGS+=("-not" "-name" "$path") || EXCLUDE_ARGS+=("-not" "-path" "$path")
done

TEMP_FILE_LIST=$(mktemp)
# 优先取变更文件，无变更则取所有非压缩/图片/视频文件
git status --porcelain | grep -E '^[AM]' | awk '{print $2}' > "$TEMP_FILE_LIST"
[ ! -s "$TEMP_FILE_LIST" ] && find . -type f "${EXCLUDE_ARGS[@]}" > "$TEMP_FILE_LIST"

TOTAL_FILES=$(wc -l < "$TEMP_FILE_LIST")
echo -e "\033[32m📊 待推送文件总数：$TOTAL_FILES 个，批量大小：$BATCH_SIZE 个/批\033[0m"
[ "$TOTAL_FILES" -eq 0 ] && echo -e "\033[32mℹ️  无待推送文件\033[0m" && rm -f "$TEMP_FILE_LIST" && exit 0

# ===================== 第五步：批量提交+推送 =====================
echo -e "\033[34m==================== 第四步：批量提交+推送 ====================\033[0m"
FILE_COUNT=0
BATCH_NUMBER=1
FAILED_BATCHES=()

while IFS= read -r file; do
    [ -z "$file" ] || [ ! -f "$file" ] && continue

    git add "$file"
    FILE_COUNT=$((FILE_COUNT + 1))
    echo -e "\033[32m[批次$BATCH_NUMBER] 已添加：$file（$FILE_COUNT/$BATCH_SIZE）\033[0m"

    if [ "$FILE_COUNT" -eq "$BATCH_SIZE" ] || [ "$(($BATCH_NUMBER * $BATCH_SIZE - ($BATCH_SIZE - $FILE_COUNT)))" -ge "$TOTAL_FILES" ]; then
        # 生成每个批次的精准时间戳
        TIMESTAMP_BATCH=$(date +"%Y-%m-%d %H:%M:%S")
        COMMIT_MSG="[$TIMESTAMP_BATCH] $CUSTOM_NOTE - 批次$BATCH_NUMBER：共$FILE_COUNT个文件"
        
        if git commit -m "$COMMIT_MSG" >/dev/null 2>&1; then
            echo -e "\033[32m✅ [批次$BATCH_NUMBER] 已提交$FILE_COUNT个文件\033[0m"
            push_with_retry $BATCH_NUMBER "$CUSTOM_NOTE" || FAILED_BATCHES+=($BATCH_NUMBER)
        else
            echo -e "\033[31m⚠️  [批次$BATCH_NUMBER] 无变更，跳过\033[0m"
            FILE_COUNT=0
            BATCH_NUMBER=$((BATCH_NUMBER + 1))
            continue
        fi
        
        FILE_COUNT=0
        BATCH_NUMBER=$((BATCH_NUMBER + 1))
        sleep $DELAY_SECONDS
    fi
done < "$TEMP_FILE_LIST"

# 处理剩余文件
if [ "$FILE_COUNT" -gt 0 ]; then
    TIMESTAMP_REMAIN=$(date +"%Y-%m-%d %H:%M:%S")
    COMMIT_MSG="[$TIMESTAMP_REMAIN] $CUSTOM_NOTE - 批次$BATCH_NUMBER：剩余$FILE_COUNT个文件"
    if git commit -m "$COMMIT_MSG" >/dev/null 2>&1; then
        echo -e "\033[32m✅ [批次$BATCH_NUMBER] 已提交剩余$FILE_COUNT个文件\033[0m"
        push_with_retry $BATCH_NUMBER "$CUSTOM_NOTE" || FAILED_BATCHES+=($BATCH_NUMBER)
    fi
fi

# ===================== 操作完成 =====================
echo -e "\033[34m==================== 所有操作完成 ====================\033[0m"
if [ ${#FAILED_BATCHES[@]} -eq 0 ]; then
    echo -e "\033[32m✅ 1. 已成功拉取远程最新代码（适配全新仓库）\n✅ 2. 已配置.gitignore忽略压缩/图片/视频文件\n✅ 3. 所有文件推送完成（备注：$CUSTOM_NOTE）\033[0m"
else
    echo -e "\033[32m✅ 1. 已拉取远程代码（或适配全新仓库跳过合并）\n✅ 2. 已配置.gitignore忽略压缩/图片/视频文件\n⚠️  3. 失败批次：${FAILED_BATCHES[*]}（备注：$CUSTOM_NOTE）\033[0m"
    echo -e "\033[33m📌 手动重试：git push -f origin $REMOTE_BRANCH\033[0m"  # 提示master分支
fi
echo -e "\033[33m📌 验证：git log origin/$REMOTE_BRANCH\033[0m"  # 验证master分支

rm -f "$TEMP_FILE_LIST"