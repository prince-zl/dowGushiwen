import requests
from bs4 import BeautifulSoup
import time
import os
import json
import re
from urllib.parse import urljoin, urlparse

# Word文档相关导入
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    DOCX_AVAILABLE = True
    print("✅ python-docx 已安装，将自动生成Word文档")
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️  python-docx 未安装，请运行: pip install python-docx")
    print("   将只生成TXT和JSON文件")

class UniversalNovelCrawler:
    def __init__(self, catalog_url=None):
        self.catalog_url = catalog_url
        self.base_domain = self.get_base_domain(catalog_url) if catalog_url else ""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.book_info = {'title': '未知书名', 'author': '未知作者'}
        
    def get_base_domain(self, url):
        """获取URL的基础域名"""
        if not url:
            return ""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def get_book_info_from_catalog(self, soup):
        """从目录页面提取书名和作者信息"""
        try:
            # 提取书名
            title_selectors = ['h1', 'h2', '.book-title', '.title', '#title', '.book-name', '[class*="title"]']
            book_title = "未知书名"
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    if title_text and 3 < len(title_text) < 50:
                        book_title = title_text
                        break
            
            # 提取作者
            author_selectors = ['.author', '.book-author', '#author', '[class*="author"]', '.writer']
            book_author = "未知作者"
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author_text = re.sub(r'作者[：:]\s*', '', author_elem.get_text(strip=True))
                    if author_text and len(author_text) < 30:
                        book_author = author_text
                        break
            
            # 从标题中提取作者
            if "作者" in book_title:
                parts = re.split(r'[作者：:]', book_title)
                if len(parts) >= 2:
                    book_title = parts[0].strip()
                    book_author = parts[1].strip()
            
            self.book_info = {'title': book_title, 'author': book_author}
            print(f"📚 书名: {book_title} | 作者: {book_author}")
            
        except Exception as e:
            print(f"⚠️  获取书籍信息失败: {e}")
    
    def parse_chapter_list(self):
        """解析章节列表"""
        print(f"🔍 正在解析目录页面: {self.catalog_url}")
        
        try:
            response = self.session.get(self.catalog_url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"❌ 目录页面访问失败: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            self.get_book_info_from_catalog(soup)
            
            chapters = []
            
            # 策略1: 寻找章节容器
            container_selectors = [
                '.chapter-list', '.catalogue', '.catalog', '.list', '.content-list', 
                '#list', '#catalog', '[class*="chapter"]', '[class*="catalog"]', 'ul', 'ol'
            ]
            
            for selector in container_selectors:
                container = soup.select_one(selector)
                if container:
                    links = container.find_all('a', href=True)
                    if len(links) >= 3:
                        print(f"✅ 找到章节容器: {selector} ({len(links)} 个链接)")
                        chapters = self._extract_chapters_from_links(links)
                        break
            
            # 策略2: 模式匹配查找章节
            if not chapters:
                print("🔧 在整个页面查找章节链接...")
                all_links = soup.find_all('a', href=True)
                chapters = self._extract_chapters_from_links(all_links, pattern_match=True)
            
            # 去重并排序
            unique_chapters = self._deduplicate_chapters(chapters)
            if unique_chapters:
                sorted_chapters = self.sort_chapters(unique_chapters)
                print(f"📋 共解析到 {len(sorted_chapters)} 个章节")
                self._preview_chapters(sorted_chapters)
                return sorted_chapters
            
            print("❌ 未找到任何章节")
            return []
            
        except Exception as e:
            print(f"❌ 解析失败: {e}")
            return []
    
    def _extract_chapters_from_links(self, links, pattern_match=False):
        """从链接中提取章节信息"""
        chapters = []
        skip_keywords = ['首页', '书架', '登录', '注册', '搜索', '排行', 'home', 'login', 
                        'register', 'search', 'rank', '上一页', '下一页', '返回', '目录']
        
        for link in links:
            href = link.get('href')
            title = link.get_text(strip=True)
            
            if not title or len(title) > 100:
                continue
                
            # 过滤导航链接
            if any(skip in title.lower() for skip in skip_keywords):
                continue
            
            # 如果需要模式匹配，检查是否像章节标题
            if pattern_match:
                if not self._is_chapter_title(title):
                    continue
            
            full_url = urljoin(self.catalog_url, href)
            chapters.append({'title': title, 'url': full_url})
        
        return chapters
    
    def _is_chapter_title(self, title):
        """判断是否是章节标题"""
        patterns = [
            r'第[一二三四五六七八九十百千万\d]+[章回节卷集部]',
            r'[第]?\d+[章回节卷集部]',
            r'chapter\s*\d+',
        ]
        return any(re.search(pattern, title, re.I) for pattern in patterns) or '章' in title or '回' in title
    
    def _deduplicate_chapters(self, chapters):
        """去重"""
        unique_chapters = []
        seen_urls = set()
        for chapter in chapters:
            if chapter['url'] not in seen_urls:
                unique_chapters.append(chapter)
                seen_urls.add(chapter['url'])
        return unique_chapters
    
    def _preview_chapters(self, chapters):
        """预览章节"""
        print("📖 章节预览:")
        for i, chapter in enumerate(chapters[:5], 1):
            print(f"   {i}. {chapter['title']}")
        if len(chapters) > 5:
            print(f"   ... 还有 {len(chapters) - 5} 个章节")
    
    def sort_chapters(self, chapters):
        """对章节进行排序 - 修正排序问题"""
        print("🔄 正在排序章节...")
        
        def get_sort_key(title):
            """提取排序关键字 - 修正版本"""
            title_lower = title.lower().strip()
            
            # 特殊章节处理
            special_order = {
                '序章': (0, 0), '序言': (0, 0), '序': (0, 0), '前言': (0, 0),
                '楔子': (1, 0), '引子': (1, 0), '开篇': (1, 0),
                '终章': (999, 0), '尾声': (999, 0), '后记': (999, 0), '番外': (1000, 0)
            }
            
            for keyword, order in special_order.items():
                if keyword in title_lower:
                    return order
            
            # 提取章节号 - 优化版本
            patterns = [
                (r'第([一二三四五六七八九十百千万]+)[章回节卷集部篇]', self._chinese_to_number),
                (r'第(\d+)[章回节卷集部篇]', int),
                (r'^(\d+)[章回节卷集部篇]', int),
                (r'chapter\s*(\d+)', int),
                (r'[章回节卷集部篇](\d+)', int),
                (r'^(\d+)', int),
            ]
            
            for pattern, converter in patterns:
                match = re.search(pattern, title_lower)
                if match:
                    try:
                        num = converter(match.group(1))
                        return (10, num)  # 正常章节
                    except:
                        continue
            
            # 无法识别的放最后
            return (500, hash(title) % 1000)  # 使用hash保证稳定排序
        
        # 排序并添加调试信息
        chapters_with_key = [(get_sort_key(ch['title']), ch) for ch in chapters]
        chapters_with_key.sort(key=lambda x: x[0])
        
        sorted_chapters = [ch for _, ch in chapters_with_key]
        
        print(f"✅ 排序完成，前10章:")
        for i, chapter in enumerate(sorted_chapters[:10], 1):
            print(f"   {i}. {chapter['title']}")
        
        return sorted_chapters
    
    def _chinese_to_number(self, chinese_str):
        """中文数字转换"""
        chinese_dict = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15, '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
            '二十一': 21, '二十二': 22, '二十三': 23, '二十四': 24, '二十五': 25, '二十六': 26, '二十七': 27, '二十八': 28, '二十九': 29, '三十': 30,
            '三十一': 31, '三十二': 32, '三十三': 33, '三十四': 34, '三十五': 35, '三十六': 36, '三十七': 37, '三十八': 38, '三十九': 39, '四十': 40,
            '四十一': 41, '四十二': 42, '四十三': 43, '四十四': 44, '四十五': 45, '四十六': 46, '四十七': 47, '四十八': 48, '四十九': 49, '五十': 50,
            '五十一': 51, '五十二': 52, '五十三': 53, '五十四': 54, '五十五': 55, '五十六': 56, '五十七': 57, '五十八': 58, '五十九': 59, '六十': 60,
            '六十一': 61, '六十二': 62, '六十三': 63, '六十四': 64, '六十五': 65, '六十六': 66, '六十七': 67, '六十八': 68, '六十九': 69, '七十': 70,
            '七十一': 71, '七十二': 72, '七十三': 73, '七十四': 74, '七十五': 75, '七十六': 76, '七十七': 77, '七十八': 78, '七十九': 79, '八十': 80,
            '八十一': 81, '八十二': 82, '八十三': 83, '八十四': 84, '八十五': 85, '八十六': 86, '八十七': 87, '八十八': 88, '八十九': 89, '九十': 90,
            '九十一': 91, '九十二': 92, '九十三': 93, '九十四': 94, '九十五': 95, '九十六': 96, '九十七': 97, '九十八': 98, '九十九': 99, '一百': 100,
        }
        
        if chinese_str in chinese_dict:
            return chinese_dict[chinese_str]
        
        # 处理百位数
        if '百' in chinese_str:
            parts = chinese_str.split('百')
            if len(parts) == 2:
                hundred = chinese_dict.get(parts[0], 1) * 100
                remainder = chinese_dict.get(parts[1], 0) if parts[1] else 0
                return hundred + remainder
        
        return 0
    
    def get_chapter_content(self, chapter_url, chapter_title):
        """获取章节内容 - 保持原有的标题处理逻辑"""
        try:
            print(f"  📖 获取: {chapter_title}")
            
            response = self.session.get(chapter_url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"    ❌ HTTP错误: {response.status_code}")
                return {"title": chapter_title, "content": ""}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除不需要的元素
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            content = self._extract_content(soup)
            
            if content:
                # 智能标题合并处理 - 保持原有逻辑
                merged_title, cleaned_content = self.merge_titles(chapter_title, content)
                paragraph_count = cleaned_content.count('\n\n') + 1
                
                if len(cleaned_content) > 50:
                    print(f"    ✅ 成功 ({paragraph_count} 个段落)")
                    if merged_title != chapter_title:
                        print(f"    🔗 标题已合并")
                    return {"title": merged_title, "content": cleaned_content}
            
            print(f"    ❌ 内容提取失败")
            return {"title": chapter_title, "content": ""}
            
        except Exception as e:
            print(f"    ❌ 获取失败: {e}")
            return {"title": chapter_title, "content": ""}
    
    def _extract_content(self, soup):
        """提取正文内容"""
        # 策略1: 寻找内容容器
        content_selectors = [
            '.content', '.main-content', '.chapter-content', '.text-content',
            '#content', '#main-content', '#chapter-content',
            '.post-content', '.entry-content', '.article-content',
            '.main .content', '.container .content', '[class*="content"]',
            '.main3 .left .cont', '.cont', '.chapter', '.article'
        ]
        
        for selector in content_selectors:
            container = soup.select_one(selector)
            if container:
                # 提取p标签段落
                paragraphs = container.find_all('p')
                if paragraphs:
                    para_texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 5]
                    if para_texts:
                        return '\n\n'.join(para_texts)
                
                # 尝试其他段落结构
                divs = container.find_all(['div', 'span'])
                if len(divs) > 1:
                    div_texts = [div.get_text(strip=True) for div in divs if len(div.get_text(strip=True)) > 10]
                    if len(div_texts) > 1:
                        return '\n\n'.join(div_texts)
        
        # 策略2: 全页面p标签
        all_paragraphs = soup.find_all('p')
        if all_paragraphs:
            skip_keywords = ['导航', '菜单', '登录', '版权', 'copyright', '上一章', '下一章']
            para_texts = []
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                if (text and len(text) > 15 and 
                    not any(skip in text.lower() for skip in skip_keywords)):
                    para_texts.append(text)
            
            if len(para_texts) > 2:
                return '\n\n'.join(para_texts)
        
        return ""
    
    # 保持原有的标题处理逻辑 - 用户强调这部分很关键
    def merge_titles(self, catalog_title, content):
        """智能合并目录标题和内容标题"""
        if not content:
            return catalog_title, content
        
        lines_double = content.split('\n\n')
        lines_single = content.split('\n')
        
        first_line = ""
        remaining_content = content
        
        if lines_double and lines_double[0].strip():
            first_line = lines_double[0].strip()
            if len(first_line) <= 150:
                remaining_content = '\n\n'.join(lines_double[1:]).strip() if len(lines_double) > 1 else ""
            else:
                if lines_single and lines_single[0].strip():
                    first_line = lines_single[0].strip()
                    remaining_content = '\n'.join(lines_single[1:]).strip() if len(lines_single) > 1 else ""
        elif lines_single and lines_single[0].strip():
            first_line = lines_single[0].strip()
            remaining_content = '\n'.join(lines_single[1:]).strip() if len(lines_single) > 1 else ""
        
        if not first_line:
            return catalog_title, content
        
        print(f"    🔍 检查第一行: {first_line[:50]}{'...' if len(first_line) > 50 else ''}")
        
        if self.is_likely_title(first_line):
            merged_title = self.combine_titles(catalog_title, first_line)
            print(f"    🔗 检测到内容标题，已合并")
            return merged_title, remaining_content
        else:
            print(f"    ❌ 第一行不被识别为标题")
            return catalog_title, content
    
    def is_likely_title(self, text):
        """判断文本是否可能是标题"""
        if not text or len(text) > 200 or len(text) < 3:
            return False
        
        print(f"    🔍 标题判断: '{text}'")
        
        # 强标题特征
        strong_patterns = [
            r'第[一二三四五六七八九十百千万\d]+[章回节卷集部篇]',
            r'^[第]?\d+[章回节卷集部篇]',
            r'chapter\s*\d+',
            r'^[\d\s\-\.]+[章回节卷集部篇]',
            r'^第.*[章回节卷集部篇]',
        ]
        
        for pattern in strong_patterns:
            if re.search(pattern, text, re.I):
                print(f"    ✅ 匹配强标题模式")
                return True
        
        # 综合评分
        score = 0
        chapter_keywords = ['章', '回', '节', '卷', '集', '部', '篇', 'chapter']
        if any(keyword in text.lower() for keyword in chapter_keywords):
            score += 2
        if re.search(r'\d+', text):
            score += 1
        if not text.endswith(('。', '！', '？', '.', '!', '?')):
            score += 1
        if 5 <= len(text) <= 50:
            score += 1
        
        punctuation_ratio = len(re.findall(r'[，。！？、；：""''（）【】《》]', text)) / len(text)
        if punctuation_ratio < 0.3:
            score += 1
        
        print(f"    📊 综合得分: {score}/6")
        return score >= 3
    
    def combine_titles(self, catalog_title, content_title):
        """合并目录标题和内容标题"""
        catalog_clean = catalog_title.strip()
        content_clean = content_title.strip()
        
        print(f"    🔗 合并: 目录='{catalog_clean}' | 内容='{content_clean}'")
        
        if content_clean in catalog_clean:
            return catalog_clean
        if catalog_clean in content_clean:
            return content_clean
        
        # 检查章节号
        catalog_num = self.extract_chapter_number(catalog_clean)
        content_num = self.extract_chapter_number(content_clean)
        
        if catalog_num and content_num and catalog_num == content_num:
            catalog_without_num = re.sub(r'第[一二三四五六七八九十百千万\d]+[章回节卷集部篇]\s*', '', catalog_clean)
            content_without_num = re.sub(r'第[一二三四五六七八九十百千万\d]+[章回节卷集部篇]\s*', '', content_clean)
            content_without_num = re.sub(r'^\d+[章回节卷集部篇]\s*', '', content_without_num)
            
            if catalog_without_num and content_without_num and catalog_without_num != content_without_num:
                return f"{catalog_clean} {content_without_num}"
            else:
                return catalog_clean
        
        return f"{catalog_clean} {content_clean}"
    
    def extract_chapter_number(self, title):
        """提取章节号"""
        patterns = [
            r'第([一二三四五六七八九十百千万]+)[章回节卷集部篇]',
            r'第(\d+)[章回节卷集部篇]',
            r'^(\d+)[章回节卷集部篇]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        return None
    
    def crawl_book(self, delay=3, test_mode=False):
        """爬取整本书"""
        mode_text = "测试模式（前3章）" if test_mode else "完整模式"
        print(f"🚀 开始爬取《{self.book_info['title']}》 - {mode_text}")
        print("=" * 60)
        
        chapters = self.parse_chapter_list()
        if not chapters:
            print("❌ 无法获取章节信息")
            return
        
        if test_mode:
            chapters = chapters[:3]
            print(f"🧪 测试模式：爬取前 {len(chapters)} 章")
        
        print(f"📚 开始爬取 {len(chapters)} 个章节...")
        print("-" * 60)
        
        chapters_data = []
        success_count = 0
        
        for i, chapter in enumerate(chapters, 1):
            print(f"[{i:3d}/{len(chapters)}] {chapter['title']}")
            
            result = self.get_chapter_content(chapter['url'], chapter['title'])
            content = result["content"]
            paragraph_count = content.count('\n\n') + 1 if content else 0
            
            chapter_data = {
                'original_title': chapter['title'],
                'title': result["title"],
                'url': chapter['url'],
                'content': content,
                'char_count': len(content),
                'paragraph_count': paragraph_count,
                'success': len(content) > 50 and paragraph_count >= 1
            }
            
            chapters_data.append(chapter_data)
            
            if chapter_data['success']:
                success_count += 1
            
            if i < len(chapters):
                print(f"           ⏳ 等待 {delay} 秒...")
                time.sleep(delay)
        
        # 保存结果
        print("-" * 60)
        total_chars = sum(ch['char_count'] for ch in chapters_data)
        total_paragraphs = sum(ch['paragraph_count'] for ch in chapters_data)
        print(f"📋 完成: {success_count}/{len(chapters_data)} 章节, {total_chars:,} 字, {total_paragraphs} 段落")
        
        if success_count > 0:
            folder_name = self._save_results(chapters_data)
            print(f"🎉 文件已保存到: {folder_name}")
            return folder_name
        else:
            print("❌ 没有成功获取任何内容")
    
    def _save_results(self, chapters_data):
        """保存所有格式的文件"""
        # 创建文件夹
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', self.book_info['title']).strip('_').strip()
        if not safe_title:
            safe_title = f"小说_{int(time.time())}"
        
        os.makedirs(safe_title, exist_ok=True)
        
        # 保存文件
        txt_path = os.path.join(safe_title, f"{safe_title}.txt")
        json_path = os.path.join(safe_title, f"{safe_title}.json")
        docx_path = os.path.join(safe_title, f"{safe_title}.docx")
        
        self._save_txt(chapters_data, txt_path)
        self._save_json(chapters_data, json_path)
        
        if DOCX_AVAILABLE:
            self._save_word(chapters_data, docx_path)
        
        return safe_title
    
    def _save_txt(self, chapters_data, filename):
        """保存TXT文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{self.book_info['title']}\n")
                f.write("=" * 60 + "\n")
                f.write(f"作者：{self.book_info['author']}\n")
                f.write("爬取时间：" + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
                f.write(f"来源：{self.catalog_url}\n\n")
                
                for chapter in chapters_data:
                    f.write(f"{chapter['title']}\n")
                    f.write("-" * 50 + "\n\n")
                    if chapter['content']:
                        f.write(chapter['content'])
                    else:
                        f.write("[此章节内容获取失败]")
                    f.write(f"\n\n\n")
            
            print(f"✅ TXT文件已保存: {filename}")
        except Exception as e:
            print(f"❌ 保存TXT失败: {e}")
    
    def _save_json(self, chapters_data, filename):
        """保存JSON文件"""
        try:
            data = {
                'title': self.book_info['title'],
                'author': self.book_info['author'],
                'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'source_url': self.catalog_url,
                'chapters': chapters_data
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON文件已保存: {filename}")
        except Exception as e:
            print(f"❌ 保存JSON失败: {e}")
    
    def _save_word(self, chapters_data, filename):
        """保存Word文档"""
        try:
            document = Document()
            
            # 设置字体
            document.styles['Normal'].font.name = '楷体'
            document.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
            document.styles['Normal'].font.size = Pt(14)
            
            # 文档标题
            title = document.add_heading(self.book_info['title'], 0)
            title.runs[0].font.name = '楷体'
            title.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
            title.runs[0].font.size = Pt(18)

        
            
            # 作者信息
            author_para = document.add_paragraph()
            author_run = author_para.add_run(f'作者：{self.book_info["author"]}')
            author_run.font.name = '楷体'
            author_run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
            author_run.font.size = Pt(14)
           
            
            document.add_page_break()
            
            # 章节内容
            for i, chapter in enumerate(chapters_data):
                if not chapter.get('success', False) or not chapter.get('content'):
                    continue
                
                # 章节标题
                title_heading = document.add_heading(chapter['title'], 1)
                title_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
                title_heading.runs[0].font.name = '楷体'
                title_heading.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
                title_heading.runs[0].font.size = Pt(18)
                title_heading.runs[0].bold = True
                title_heading.runs[0].font.color.rgb = RGBColor(0, 0, 0)  # 设置为黑色
                title_heading.paragraph_format.space_after = Pt(12)  # 章节标题后增加间距
                
                # 章节内容
                paragraphs = chapter['content'].split('\n\n')
                for para_text in paragraphs:
                    para_text = para_text.strip()
                    if para_text:
                        para = document.add_paragraph()
                        para_run = para.add_run(para_text)
                        para_run.font.name = '楷体'
                        para_run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
                        para_run.font.size = Pt(12)
                        
                        para.paragraph_format.first_line_indent = Pt(24)
                        para.paragraph_format.space_after = Pt(8)
                        para.paragraph_format.line_spacing = 1.15
                        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                
                # 每章分页（除最后一章）
                if i < len([ch for ch in chapters_data if ch.get('success', False)]) - 1:
                    document.add_page_break()
            
            document.save(filename)
            print(f"✅ Word文档已保存: {filename}")
            
        except Exception as e:
            print(f"❌ 保存Word失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("        通用小说爬虫 v3.1 - 优化版")
    print("=" * 60)
    print("🎯 支持大部分小说网站目录页面")
    print("🔗 智能合并标题，严格按p标签分段")
    print("📄 自动生成TXT、JSON、Word三种格式")
    print("⚠️  请遵守网站使用条款")
    print("=" * 60)
    
    # 获取URL
    while True:
        catalog_url = input("\n📝 请输入小说目录页面URL: ").strip()
        
        if not catalog_url:
            print("❌ URL不能为空")
            continue
        
        if not catalog_url.startswith(('http://', 'https://')):
            print("❌ 请输入完整URL")
            continue
        
        # 测试URL
        try:
            test_response = requests.get(catalog_url, timeout=10)
            if test_response.status_code == 200:
                print("✅ URL可访问")
                break
            else:
                print(f"⚠️  返回状态码 {test_response.status_code}")
                if input("继续使用此URL？(y/n): ").lower() in ['y', 'yes']:
                    break
        except Exception as e:
            print(f"⚠️  URL测试失败: {e}")
            if input("仍要使用此URL？(y/n): ").lower() in ['y', 'yes']:
                break
    
    crawler = UniversalNovelCrawler(catalog_url)
    
    # 选择模式
    while True:
        print("\n请选择模式:")
        print("1. 🧪 测试模式（前3章）")
        print("2. 🚀 完整模式（所有章节）")
        print("3. 📊 先测试再决定（推荐）")
        print("4. ❌ 退出")
        
        choice = input("选择 (1/2/3/4): ").strip()
        
        if choice == "1":
            crawler.crawl_book(delay=2, test_mode=True)
            break
        elif choice == "2":
            if input("确认爬取所有章节？(y/n): ").lower() in ['y', 'yes']:
                crawler.crawl_book(delay=3, test_mode=False)
                break
        elif choice == "3":
            print("📊 先进行测试...")
            test_folder = crawler.crawl_book(delay=2, test_mode=True)
            if test_folder and input("满意吗？继续爬取完整版？(y/n): ").lower() in ['y', 'yes']:
                crawler.crawl_book(delay=3, test_mode=False)
            break
        elif choice == "4":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择")

if __name__ == "__main__":
    main()