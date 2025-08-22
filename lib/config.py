import os
import sys
import time

def get_resource_path(relative_path):
    """获取资源文件路径"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_date_path():
    """获取当前日期的路径格式 (年月日)"""
    current_time = time.localtime()
    return f"{current_time.tm_year}{str(current_time.tm_mon).zfill(2)}{str(current_time.tm_mday).zfill(2)}"

def get_exe_dir():
    """获取exe所在目录"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是开发环境
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 使用exe所在目录作为基础目录
base_dir = get_exe_dir()

# 创建统一的下载目录
download_dir = os.path.join(base_dir, 'download')

# 基础文件夹（使用exe所在目录的相对路径）
base_word_folder = os.path.join(download_dir, 'word')
base_pdf_folder = os.path.join(download_dir, 'pdf')
base_txt_folder = os.path.join(download_dir, 'txt')

# 获取当前日期路径
date_path = get_date_path()

# 完整的保存路径
folder_name_word = os.path.join(base_word_folder, date_path)
folder_name_pdf = os.path.join(base_pdf_folder, date_path)
folder_name_txt = os.path.join(base_txt_folder, date_path)


save_file_name = ''
log_file = os.path.join(download_dir, 'log', 'download.log')

def setLog(content):
    """写入日志"""
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(content + '\n')

def ensure_dir(dir_path):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# 确保主下载目录存在
ensure_dir(download_dir)
