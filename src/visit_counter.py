# -*- coding: utf-8 -*-
"""
访问次数统计模块（最终稳定版）
✅ 修复：延迟初始化，避免主目录生成文件
✅ 异步批量写入，解决卡顿问题
✅ 线程安全，数据不丢失
"""
import json
import os
import threading
import time
from datetime import datetime

class VisitCounter:
    """访问计数器类：内存实时计数 + 异步批量写入"""
    
    def __init__(self, save_file="data/visit_count.json"):
        self.save_file = save_file
        self.count = 0  # 内存中实时计数
        self.lock = threading.Lock()  # 轻量级锁保护计数
        self.write_lock = threading.Lock()  # 写入锁
        self.last_write_time = 0  # 上次写入时间
        self.write_interval = 1  # 1秒批量写入一次
        self.pending_write = False  # 是否有等待写入的任务
        
        # 强制创建目录
        self._ensure_dir_exists()
        # 从文件加载历史计数
        self.load_count()
        
        # 注册程序退出时的保存钩子
        import atexit
        atexit.register(self._on_exit)

    def _ensure_dir_exists(self):
        """强制创建计数文件所在目录"""
        dir_name = os.path.dirname(self.save_file)
        if dir_name and not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name, exist_ok=True)
                print(f"✅ 已创建计数文件目录：{dir_name}")
            except Exception as e:
                print(f"⚠️ 创建计数目录失败：{e}")

    def load_count(self):
        """从文件加载历史访问次数"""
        try:
            if os.path.exists(self.save_file):
                with open(self.save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.count = int(data.get('total_visits', 0))
                print(f"✅ 加载历史访问次数：{self.count} 次")
            else:
                # 初始化文件（仅在指定目录创建）
                self.count = 0
                self._async_save_count(force=True)
                print(f"✅ 初始化访问计数文件：{self.save_file}")
        except Exception as e:
            print(f"⚠️  加载访问计数失败，重置为0：{e}")
            self.count = 0

    def _async_save_count(self, force=False):
        """异步保存计数到文件（核心优化）"""
        # 避免重复写入
        if not force and self.pending_write:
            return
        
        current_time = time.time()
        # 未到写入间隔且非强制，跳过
        if not force and (current_time - self.last_write_time) < self.write_interval:
            self.pending_write = True
            # 延迟1秒执行写入（批量处理）
            threading.Timer(self.write_interval, self._do_save).start()
            return
        
        # 立即异步写入
        threading.Thread(target=self._do_save, daemon=True).start()

    def _do_save(self):
        """实际执行保存操作（异步）"""
        with self.write_lock:
            try:
                # 双重锁保障：读取最新计数
                with self.lock:
                    current_count = self.count
                
                # 写入文件（非阻塞）
                self._ensure_dir_exists()
                with open(self.save_file, 'w', encoding='utf-8') as f:
                    data = {
                        'total_visits': current_count,
                        'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'update_timestamp': time.time()
                    }
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.last_write_time = time.time()
                self.pending_write = False
            except Exception as e:
                print(f"⚠️  异步保存访问计数失败：{e}")

    def _on_exit(self):
        """程序退出时强制保存最终计数"""
        self._async_save_count(force=True)
        # 短暂等待写入完成
        time.sleep(0.1)

    def increment(self):
        """增加访问次数（内存实时+异步写入）"""
        with self.lock:
            self.count += 1  # 内存中实时+1，无阻塞
            current_count = self.count
        
        # 触发异步写入（不会阻塞请求）
        self._async_save_count()
        return current_count

    def get_count(self):
        """获取当前总访问次数（仅读内存，极快）"""
        with self.lock:
            return self.count

    def reset_count(self):
        """重置访问次数为0"""
        with self.lock:
            self.count = 0
        self._async_save_count(force=True)
        print("🔄 访问次数已重置为0")

# ========== 关键修复：延迟初始化，不再提前创建全局实例 ==========
global_counter = None

def init_visit_counter(save_file="data/visit_count.json"):
    """
    延迟初始化访问计数器（解决路径提前创建问题）
    :param save_file: 计数文件保存路径
    """
    global global_counter
    if global_counter is None:
        # 确保目录存在后再创建实例
        dir_name = os.path.dirname(save_file)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        # 真正创建计数器实例
        global_counter = VisitCounter(save_file=save_file)
        print(f"✅ 访问计数器初始化完成，文件路径：{os.path.abspath(save_file)}")
    return global_counter

# 便捷函数：增加实例检查，避免未初始化调用
def count_visit():
    """记录一次访问，返回当前总次数"""
    if global_counter is None:
        raise RuntimeError("请先调用 init_visit_counter() 初始化计数器！")
    return global_counter.increment()

def get_total_visits():
    """获取当前总访问次数"""
    if global_counter is None:
        raise RuntimeError("请先调用 init_visit_counter() 初始化计数器！")
    return global_counter.get_count()

def reset_visits():
    """重置访问次数"""
    if global_counter is None:
        raise RuntimeError("请先调用 init_visit_counter() 初始化计数器！")
    global_counter.reset_count()