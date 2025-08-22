# lib/cleaner.py

import re

# 定义要替换的异常字符类别
def replace_pua_chars(text):
    """
    替换 Unicode 私有区域字符（如 、、 等）
    范围：U+E000–U+F8FF
    """
    return re.sub(r'[\uE000-\uF8FF]', '###', text)

def replace_control_chars(text):
    """
    替换不可见控制字符（如 \x00, \x01 等）
    """
    return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

def replace_specific_garbled(text):
    """
    替换已知的具体乱码字符（可根据实际补充）
    """
    # 示例：如果发现某些固定乱码，可手动替换
    # text = text.replace('\ue225', '###')  # 
    # text = text.replace('\uea68', '###')  # 
    return text

def clean_text(text):
    """
    综合清洗函数：处理乱码、多余空白、控制符
    """
    if not isinstance(text, str):
        return ""

    # 1. 替换私有区字符（主要乱码来源）
    text = replace_pua_chars(text)

    # 2. 替换其他已知乱码（可扩展）
    text = replace_specific_garbled(text)

    # 3. 移除控制字符
    text = replace_control_chars(text)

    # 4. 清理多余空白（多个空格/换行 → 单空格）
    text = re.sub(r'\s+', ' ', text)

    return text.strip()

def clean_paragraphs(paragraphs):
    """
    清洗段落列表，自动过滤空段
    """
    cleaned = []
    for p in paragraphs:
        p = clean_text(p)
        if p:  # 非空才保留
            cleaned.append(p)
    return cleaned

# --- 调试工具 ---
def show_unicode_info(text):
    """
    调试用：打印文本中非常规字符的 Unicode 信息
    """
    for i, char in enumerate(text):
        code = ord(char)
        if code < 128 and char.isprintable():  # 基本 ASCII 可见字符
            continue
        if 0x4E00 <= code <= 0x9FFF:  # 中文字符
            continue
        print(f"位置 {i}: '{repr(char)}' -> U+{code:04X}")