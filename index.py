import requests
from bs4 import BeautifulSoup
import time
import os
import json
import re
from urllib.parse import urljoin

# Word文档相关导入
try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    DOCX_AVAILABLE = True
    print("✅ python-docx 已安装，将自动生成Word文档")
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️  python-docx 未安装，请运行: pip install python-docx")
    print("   将只生成TXT和JSON文件")

class JigongCrawler:
    def __init__(self):
        self.base_url = "https://m.gushiwen.cn"  # 使用移动版，更稳定
        self.desktop_url = "https://www.gushiwen.cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Referer': 'https://m.gushiwen.cn/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def generate_known_chapters(self):
        """基于搜索结果生成已知存在的章节"""
        chapters = []
        
        # 从搜索结果中获得的确实存在的章节
        known_chapters = [
            # 基于搜索结果的真实URL
            ("第一百六十一回 逛西湖恶霸遇妖风 看偈语私访白鱼寺", 
             "https://m.gushiwen.cn/guwen/bookv_098fbba030de.aspx"),
        ]
        
        # 添加已知章节
        for title, url in known_chapters:
            chapters.append({'title': title, 'url': url})
        
        print(f"✅ 准备了 {len(chapters)} 个确认存在的章节")
        return chapters
    
    def try_find_chapter_pattern(self):
        """尝试发现章节URL规律"""
        print("🔍 分析网站章节URL模式...")
        
        # 由于我们知道主页面有章节链接，尝试不同的方法获取
        main_page_urls = [
            "https://www.gushiwen.cn/guwen/book_ce3ab505d8e6.aspx",
            "https://m.gushiwen.cn/guwen/book_ce3ab505d8e6.aspx"
        ]
        
        chapters = []
        
        for url in main_page_urls:
            try:
                print(f"尝试分析: {url}")
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    # 检查是否有JavaScript动态加载的内容
                    if 'bookv_' in response.text:
                        print("✅ 发现bookv_模式的链接")
                        
                        # 使用正则提取所有可能的章节ID
                        pattern = r'bookv_([a-f0-9]{12})\.aspx'
                        matches = re.findall(pattern, response.text)
                        
                        # 不限制数量，发现所有章节
                        for i, chapter_id in enumerate(matches, 1):
                            chapter_url = f"https://m.gushiwen.cn/guwen/bookv_{chapter_id}.aspx"
                            chapters.append({
                                'title': f'第{i}回',
                                'url': chapter_url
                            })
                            print(f"  发现章节: bookv_{chapter_id}.aspx")
                
            except Exception as e:
                print(f"分析 {url} 失败: {e}")
                continue
        
        if chapters:
            print(f"🎯 通过模式分析发现 {len(chapters)} 个章节")
        else:
            print("⚠️  无法通过模式分析发现章节")
            
        return chapters
    
    def get_chapter_content(self, chapter_url, chapter_title):
        """获取单个章节内容 - 严格按照p标签分段"""
        try:
            print(f"  📖 获取: {chapter_title}")
            
            response = self.session.get(chapter_url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"    ❌ HTTP错误: {response.status_code}")
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除不需要的元素
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            content = ""
            
            # 策略1: 严格按p标签分段 - 针对古诗文网的特定结构
            gushiwen_selectors = [
                '.main3 .left .cont',  # 古诗文网桌面版常用结构
                '.main3 .cont',        # 简化版
                '.cont',               # 主内容区
                '[class*="main"] .cont',
                '#main .cont',
                '.left .cont',
                '.content',
                '.main-content'
            ]
            
            for selector in gushiwen_selectors:
                content_container = soup.select_one(selector)
                if content_container:
                    print(f"    ✅ 找到内容容器: {selector}")
                    
                    # 严格提取所有p标签作为段落
                    paragraphs = content_container.find_all('p')
                    
                    if paragraphs:
                        paragraph_texts = []
                        for p in paragraphs:
                            p_text = p.get_text(strip=True)
                            if p_text and len(p_text) > 5:  # 过滤太短的段落
                                paragraph_texts.append(p_text)
                        
                        if paragraph_texts:
                            content = '\n\n'.join(paragraph_texts)  # 每个p标签间用双换行分隔
                            print(f"    ✅ 严格按p标签提取到 {len(paragraph_texts)} 个段落")
                            break
                    
                    # 如果容器内没有p标签，检查是否有其他段落标记
                    if not content:
                        # 检查是否有div或span作为段落分隔
                        div_paragraphs = content_container.find_all(['div', 'span'])
                        if div_paragraphs and len(div_paragraphs) > 1:
                            para_texts = []
                            for div in div_paragraphs:
                                div_text = div.get_text(strip=True)
                                if div_text and len(div_text) > 10:  # 过滤太短的内容
                                    para_texts.append(div_text)
                            
                            if para_texts and len(para_texts) > 1:
                                content = '\n\n'.join(para_texts)
                                print(f"    ✅ 按div/span标签提取到 {len(para_texts)} 个段落")
                                break
                        
                        # 如果都没有，检查是否有br标签分割的内容
                        container_html = str(content_container)
                        if '<br' in container_html.lower():
                            # 将br标签替换为段落分隔符
                            br_separated = re.sub(r'<br[^>]*?/?>', '\n||PARAGRAPH_BREAK||\n', container_html)
                            # 移除其他HTML标签
                            clean_text = BeautifulSoup(br_separated, 'html.parser').get_text()
                            # 按段落分隔符分段
                            paragraphs = [p.strip() for p in clean_text.split('||PARAGRAPH_BREAK||')]
                            paragraphs = [p for p in paragraphs if p and len(p) > 10]
                            
                            if paragraphs:
                                content = '\n\n'.join(paragraphs)
                                print(f"    ✅ 按br标签分段提取到 {len(paragraphs)} 个段落")
                                break
            
            # 策略2: 如果容器策略失败，直接在整个页面中查找所有p标签
            if not content or len(content) < 200:
                print(f"    🔧 策略1失败，在整个页面查找p标签...")
                
                all_paragraphs = soup.find_all('p')
                
                if all_paragraphs:
                    paragraph_texts = []
                    for p in all_paragraphs:
                        p_text = p.get_text(strip=True)
                        # 过滤掉明显的导航、菜单、版权信息
                        if (p_text and len(p_text) > 15 and 
                            not any(skip in p_text.lower() for skip in 
                                   ['导航', '菜单', '登录', '注册', '首页', '版权', 'copyright', 
                                    '关于我们', '联系我们', '用户协议', '隐私政策', '意见反馈'])):
                            paragraph_texts.append(p_text)
                    
                    if paragraph_texts and len(paragraph_texts) > 2:
                        content = '\n\n'.join(paragraph_texts)
                        print(f"    ✅ 从全页面严格按p标签提取到 {len(paragraph_texts)} 个段落")
            
            # 策略3: 查找具有明确段落结构的大文本块
            if not content or len(content) < 100:
                print(f"    🔧 策略2失败，查找结构化文本块...")
                
                # 查找可能包含故事内容的元素
                content_elements = soup.find_all(['div', 'article', 'section', 'main'])
                
                best_content = ""
                best_paragraph_count = 0
                
                for elem in content_elements:
                    # 检查该元素内的段落结构
                    elem_paragraphs = elem.find_all('p')
                    
                    if elem_paragraphs and len(elem_paragraphs) >= 3:  # 至少3个段落才考虑
                        para_texts = []
                        for p in elem_paragraphs:
                            p_text = p.get_text(strip=True)
                            if p_text and len(p_text) > 10:
                                para_texts.append(p_text)
                        
                        # 过滤掉明显不是正文的内容
                        filtered_paras = []
                        for para in para_texts:
                            if not any(skip in para.lower() for skip in 
                                     ['导航', '菜单', '登录', '注册', '首页', 'javascript:', 
                                      '版权所有', '关于我们', '联系我们', '用户协议']):
                                filtered_paras.append(para)
                        
                        if len(filtered_paras) > best_paragraph_count and len(filtered_paras) >= 3:
                            best_content = '\n\n'.join(filtered_paras)
                            best_paragraph_count = len(filtered_paras)
                
                if best_content:
                    content = best_content
                    print(f"    ✅ 找到结构化内容块，严格按段落分割 ({best_paragraph_count} 个段落)")
            
            # 最终内容验证和格式化
            if content:
                # 清理多余的空行，但保持双换行的段落分隔
                content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
                content = content.strip()
                
                # 验证内容质量
                paragraph_count = content.count('\n\n') + 1
                
                if len(content) > 100 and paragraph_count >= 2:
                    print(f"    ✅ 最终成功 ({len(content)} 字符, {paragraph_count} 个段落)")
                    print(f"    📋 段落预览: {content[:100]}...")
                    return content
                else:
                    print(f"    ⚠️  内容质量不足 ({len(content)} 字符, {paragraph_count} 个段落)")
            
            print(f"    ❌ 所有策略都未能提取到有效的分段内容")
            
            # 调试信息
            print(f"    🔍 调试信息:")
            print(f"       页面标题: {soup.title.string if soup.title else '无标题'}")
            print(f"       页面大小: {len(response.text)} 字符")
            print(f"       p标签数量: {len(soup.find_all('p'))}")
            print(f"       是否包含'话说': {'话说' in response.text}")
            print(f"       是否包含'济公': {'济公' in response.text}")
            
            return ""
            
        except Exception as e:
            print(f"    ❌ 获取失败: {e}")
            return ""
    
    def crawl_book(self, delay=3, test_mode=False):
        """爬取整本书"""
        mode_text = "测试模式（前3章）" if test_mode else "完整模式（所有章节）"
        print(f"🚀 开始爬取《济公全传》 - {mode_text}")
        print("=" * 60)
        
        # 获取章节列表
        chapters = []
        
        # 方法1: 尝试模式分析
        pattern_chapters = self.try_find_chapter_pattern()
        chapters.extend(pattern_chapters)
        
        # 方法2: 使用已知章节
        known_chapters = self.generate_known_chapters()
        chapters.extend(known_chapters)
        
        # 去除重复
        unique_chapters = []
        seen_urls = set()
        for chapter in chapters:
            if chapter['url'] not in seen_urls:
                unique_chapters.append(chapter)
                seen_urls.add(chapter['url'])
        
        chapters = unique_chapters
        
        if not chapters:
            print("❌ 无法获取任何章节信息")
            return
        
        # 测试模式：只爬取前几章
        if test_mode:
            chapters = chapters[:3]
            print(f"🧪 测试模式：只爬取前 {len(chapters)} 章")
        else:
            print(f"🚀 完整模式：准备爬取所有 {len(chapters)} 个章节")
        
        print(f"📚 找到 {len(chapters)} 个章节，开始爬取...")
        print("-" * 60)
        
        # 爬取章节内容
        chapters_data = []
        success_count = 0
        
        for i, chapter in enumerate(chapters, 1):
            print(f"[{i:3d}/{len(chapters)}] {chapter['title']}")
            
            content = self.get_chapter_content(chapter['url'], chapter['title'])
            
            # 计算段落数量
            paragraph_count = content.count('\n\n') + 1 if content else 0
            
            chapter_data = {
                'title': chapter['title'],
                'url': chapter['url'],
                'content': content,
                'char_count': len(content),
                'paragraph_count': paragraph_count,
                'success': len(content) > 100 and paragraph_count >= 2
            }
            
            chapters_data.append(chapter_data)
            
            if chapter_data['success']:
                success_count += 1
                print(f"           ✅ 成功 ({paragraph_count} 个段落)")
            else:
                print(f"           ❌ 失败或内容不完整")
            
            # 添加延迟，避免请求过快
            if i < len(chapters):  # 最后一章不需要延迟
                print(f"           ⏳ 等待 {delay} 秒...")
                time.sleep(delay)
        
        # 保存结果
        print("-" * 60)
        print(f"📋 爬取完成:")
        print(f"   总章节: {len(chapters_data)}")
        print(f"   成功: {success_count}")
        print(f"   失败: {len(chapters_data) - success_count}")
        
        # 统计段落信息
        total_paragraphs = sum(ch.get('paragraph_count', 0) for ch in chapters_data)
        total_chars = sum(ch.get('char_count', 0) for ch in chapters_data)
        print(f"   总段落数: {total_paragraphs}")
        print(f"   总字符数: {total_chars:,}")
        
        if success_count > 0:
            # 保存所有格式
            self.save_to_file(chapters_data)
            self.save_to_json(chapters_data)
            
            # 🎯 重点：直接生成Word文档
            if DOCX_AVAILABLE:
                self.save_to_word(chapters_data)
            
            print(f"\n🎉 爬取完成！获得 {success_count} 个有效章节，共 {total_paragraphs} 个段落")
        else:
            print("❌ 没有成功获取任何章节内容")
            print("\n💡 建议:")
            print("   1. 检查网络连接")
            print("   2. 稍后重试（可能遇到频率限制）")
            print("   3. 尝试使用VPN或更换IP")
            print("   4. 检查目标网站是否正常访问")
    
    def save_to_file(self, chapters_data, filename="济公全传.txt"):
        """保存内容到文件 - 保持段落格式"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("济公全传\n")
                f.write("=" * 60 + "\n")
                f.write("作者：郭小亭（清代）\n")
                f.write("爬取时间：" + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
                f.write("说明：严格按照原网站p标签分段保存\n")
                f.write("=" * 60 + "\n\n")
                
                total_chars = 0
                total_paragraphs = 0
                
                for i, chapter in enumerate(chapters_data, 1):
                    f.write(f"{chapter['title']}\n")
                    f.write("-" * 50 + "\n\n")
                    
                    if chapter['content']:
                        f.write(chapter['content'])  # 内容已经按段落格式化，直接写入
                        total_chars += len(chapter['content'])
                        total_paragraphs += chapter.get('paragraph_count', 0)
                    else:
                        f.write("[此章节内容获取失败]")
                    
                    f.write(f"\n\n\n")
                
                f.write(f"\n\n总计: {len(chapters_data)} 章, {total_chars:,} 字, {total_paragraphs} 段落\n")
            
            print(f"✅ TXT文件已保存: {filename}")
            
        except Exception as e:
            print(f"❌ 保存TXT文件失败: {e}")
    
    def save_to_json(self, chapters_data, filename="济公全传.json"):
        """保存为JSON格式"""
        try:
            data = {
                'title': '济公全传',
                'author': '郭小亭',
                'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'format_note': '严格按照原网站p标签分段',
                'total_chapters': len(chapters_data),
                'success_chapters': len([ch for ch in chapters_data if ch.get('success', False)]),
                'total_chars': sum(ch['char_count'] for ch in chapters_data),
                'total_paragraphs': sum(ch.get('paragraph_count', 0) for ch in chapters_data),
                'chapters': chapters_data
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON文件已保存: {filename}")
            
        except Exception as e:
            print(f"❌ 保存JSON失败: {e}")
    
    def save_to_word(self, chapters_data, filename="济公全传.docx"):
        """直接保存为Word文档 - 格式化章节标题（加粗）"""
        try:
            print("📝 正在生成Word文档...")
            
            # 创建新的Word文档
            document = Document()
            
            # 设置中文字体
            document.styles['Normal'].font.name = '宋体'
            document.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
            document.styles['Normal'].font.size = Pt(12)
            
            # 添加文档标题
            title = document.add_heading('济公全传', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title.runs[0].font.name = '黑体'
            title.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
            title.runs[0].font.size = Pt(22)
            title.runs[0].bold = True
            
            # 添加作者信息
            author_para = document.add_paragraph()
            author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            author_run = author_para.add_run('作者：郭小亭（清代）')
            author_run.font.name = '楷体'
            author_run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
            author_run.font.size = Pt(14)
            author_run.italic = True
            
            # 添加爬取信息
            info_para = document.add_paragraph()
            info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            info_run = info_para.add_run(f'爬取时间：{time.strftime("%Y-%m-%d %H:%M:%S")}')
            info_run.font.name = '仿宋'
            info_run._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋')
            info_run.font.size = Pt(10)
            
            # 添加分割线
            document.add_paragraph('─' * 50).alignment = WD_ALIGN_PARAGRAPH.CENTER
            document.add_paragraph()  # 空行
            
            # 添加统计信息
            stats_heading = document.add_heading('书籍统计', 1)
            stats_heading.runs[0].bold = True
            stats_heading.runs[0].font.name = '黑体'
            stats_heading.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
            
            total_chapters = len(chapters_data)
            success_chapters = len([ch for ch in chapters_data if ch.get('success', False)])
            total_chars = sum(ch.get('char_count', 0) for ch in chapters_data)
            total_paragraphs = sum(ch.get('paragraph_count', 0) for ch in chapters_data)
            
            stats_text = f"""总章节数：{total_chapters}
成功章节：{success_chapters}
总字符数：{total_chars:,}
总段落数：{total_paragraphs}
格式说明：严格按照原网站p标签分段"""
            
            stats_para = document.add_paragraph(stats_text)
            stats_para.runs[0].font.size = Pt(11)
            stats_para.runs[0].font.name = '仿宋'
            stats_para.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋')
            
            document.add_paragraph()  # 空行
            
            # 添加章节内容
            success_count = 0
            
            for i, chapter in enumerate(chapters_data, 1):
                if not chapter.get('success', False) or not chapter.get('content'):
                    continue
                    
                success_count += 1
                print(f"📄 正在处理第 {success_count} 章: {chapter['title']}")
                
                # 🎯 重点：章节标题加粗
                chapter_heading = document.add_heading(chapter['title'], 1)
                chapter_heading.runs[0].bold = True  # 确保标题加粗
                chapter_heading.runs[0].font.name = '黑体'
                chapter_heading.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
                chapter_heading.runs[0].font.size = Pt(16)
                
                # 章节内容 - 按段落分割
                content = chapter['content']
                paragraphs = content.split('\n\n')  # 按双换行分段
                
                for para_text in paragraphs:
                    para_text = para_text.strip()
                    if para_text:
                        # 创建段落
                        para = document.add_paragraph()
                        para_run = para.add_run(para_text)
                        para_run.font.name = '宋体'
                        para_run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
                        para_run.font.size = Pt(12)
                        
                        # 设置段落格式
                        para.paragraph_format.first_line_indent = Inches(0.5)  # 首行缩进
                        para.paragraph_format.space_after = Pt(6)  # 段后间距
                        para.paragraph_format.line_spacing = 1.5  # 行距
                
                # 章节之间添加分页符（除了最后一章）
                if success_count < success_chapters:
                    document.add_page_break()
            
            # 保存Word文档
            document.save(filename)
            print(f"✅ Word文档已保存: {filename}")
            print(f"📊 成功处理 {success_count} 个章节，标题已加粗")
            
        except Exception as e:
            print(f"❌ 保存Word文档失败: {e}")
            print("💡 可能是python-docx库问题，请检查安装：pip install python-docx")

def main():
    """主函数 - 包含完整的用户选择界面"""
    print("=" * 60)
    print("        济公全传 - 专业版爬虫 v2.1")
    print("        (自动生成Word文档版)")
    print("=" * 60)
    print("🎯 针对古诗文网优化，严格按p标签分段")
    print("📝 爬取完成后自动生成格式化Word文档")
    print("⚠️  请遵守网站使用条款，仅用于学习研究")
    print("=" * 60)
    
    crawler = JigongCrawler()
    
    # 询问用户想要的模式
    while True:
        print("\n请选择爬取模式:")
        print("1. 🧪 测试模式（只爬取前3章，快速验证效果）")
        print("2. 🚀 完整模式（爬取所有章节，生成完整Word文档）")
        print("3. 📊 先测试再决定（推荐）")
        print("4. ❌ 退出程序")
        
        try:
            choice = input("\n请输入选择 (1/2/3/4): ").strip()
            
            if choice == "1":
                print("\n" + "="*50)
                print("🧪 已选择：测试模式")
                print("📝 将爬取前3章并生成测试Word文档...")
                crawler.crawl_book(delay=2, test_mode=True)
                break
                
            elif choice == "2":
                print("\n" + "="*50)
                print("🚀 已选择：完整模式")
                print("📚 将爬取所有章节并生成完整Word文档...")
                
                # 二次确认
                confirm = input("⚠️  完整爬取可能需要较长时间，确认继续？(y/n): ").strip().lower()
                if confirm in ['y', 'yes', '是', '确认']:
                    crawler.crawl_book(delay=3, test_mode=False)
                    break
                else:
                    print("❌ 已取消完整爬取，返回主菜单")
                    continue
                
            elif choice == "3":
                print("\n" + "="*50)
                print("📊 推荐模式：先测试再决定")
                print("🧪 首先进行测试模式（前3章）...")
                crawler.crawl_book(delay=2, test_mode=True)
                
                print("\n" + "="*40)
                print("📋 测试阶段完成！")
                continue_choice = input("✨ 效果满意吗？是否继续爬取完整版本？(y/n): ").strip().lower()
                
                if continue_choice in ['y', 'yes', '是', '满意']:
                    print("\n🚀 开始完整爬取并生成完整Word文档...")
                    crawler.crawl_book(delay=3, test_mode=False)
                else:
                    print("👋 测试完成，感谢使用！")
                break
                
            elif choice == "4":
                print("👋 感谢使用济公全传爬虫！再见！")
                break
                
            else:
                print("❌ 无效选择，请输入 1、2、3 或 4")
                
        except KeyboardInterrupt:
            print("\n\n👋 程序被用户中断，再见！")
            break
        except Exception as e:
            print(f"❌ 输入处理错误: {e}")
            print("请重新选择...")
            continue
    
    print(f"\n📁 生成的文件:")
    print(f"   📄 济公全传.txt - 纯文本格式")
    print(f"   📋 济公全传.json - 数据格式（包含元数据）")
    if DOCX_AVAILABLE:
        print(f"   📝 济公全传.docx - Word文档（标题加粗，格式化）")
    else:
        print(f"   ⚠️  Word文档未生成（需要安装：pip install python-docx）")
    
    print(f"\n🎉 所有文件已保存在当前目录！")

if __name__ == "__main__":
    main()