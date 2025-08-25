# lib/downGSW.py

import requests
from lxml import etree
import re
from lib.cleaner import clean_text

# 全局变量：存储所有章节内容
ALL_CONTENT = []


# 单个章节抓取类（不保存，只返回内容）
class Chapter:
    def __init__(self, title, url):
        self.title = title
        self.url = url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        self.line0SetTitle = False #设置第0行到标题,处理特别格式

    def fetch(self):
        """抓取本章内容，返回 (combined_title, paragraphs)"""
        try:
            res = requests.get(self.url, headers=self.headers, timeout=10)
            res.encoding = "utf-8"
            # 移除 a 标签干扰
            content = re.sub(r"</?a[^>]*>", "", res.text)
            tree = etree.HTML(content)

            # 1. 提取标题
            title_parts = tree.xpath('//div[@class="main3"]//h1/span/b/text()')
            chapter_title = "".join(t.strip() for t in title_parts).strip()
            if not chapter_title:
                chapter_title = self.title

            # 2. 提取段落节点和文本
            p_nodes = tree.xpath('//div[@class="contson"]/p')
            titleTree = tree.xpath('//div[@class="contson"]/p/strong/text()')

            paragraphs = []
            for p in p_nodes:
                text = "".join(p.xpath(".//text()")).strip()
                textTitle = "".join(p.xpath(".//strong/text()")).strip()
                if textTitle:
                    textTitle = clean_text(text)  # 每段都清洗
                    paragraphs.append({"content": textTitle, "type": "title"})
                elif text:
                    text = clean_text(text)  # 每段都清洗
                    paragraphs.append({"content": text, "type": "text"})

            # 3. 判断第一个段落是否包含 <strong>，如是则拼接到标题
            combined_title = chapter_title
            # 只有一个标题
            if len(titleTree) == 1 or self.line0SetTitle:
                if paragraphs and p_nodes:
                    first_p = p_nodes[0]
                    strong_texts = first_p.xpath(".//strong//text()")
                    if self.line0SetTitle :
                        strong_texts = first_p.xpath(".//text()")     
                    if strong_texts:
                        subtitle = "".join(s.strip() for s in strong_texts)
                        combined_title = f"{chapter_title} {subtitle}"
                        # 移除已合并的首段
                        paragraphs.pop(0)

            print(f"✅ 已抓取：{combined_title}")
            return combined_title, paragraphs

        except Exception as e:
            print(f"❌ 抓取失败 {self.url}: {e}")
            return self.title + "：内容获取失败", []


# 提供给 downList.py 调用的接口函数
def down(title, url):
    """
    接收章节标题和链接
    返回内容（不保存），由 downList 统一收集
    """
    chap = Chapter(title, url)
    content = chap.fetch()
    # print("content")
    # print(content)
    ALL_CONTENT.append(content)
    return content  # 可选返回，用于调试


# 提供获取全部内容的接口
def get_all_content():
    return ALL_CONTENT


# 清空内容（可选）
def clear_content():
    global ALL_CONTENT
    ALL_CONTENT = []
