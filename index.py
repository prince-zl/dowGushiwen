import requests
from bs4 import BeautifulSoup
import time
import os
import json
import re
from urllib.parse import urljoin

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
        print("🚀 开始爬取《济公全传》...")
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
            
            time.sleep(delay)
        
        # 保存结果
        print("-" * 60)
        print(f"📋 爬取完成:")
        print(f"   总章节: {len(chapters_data)}")
        print(f"   成功: {success_count}")
        print(f"   失败: {len(chapters_data) - success_count}")
        
        # 统计段落信息
        total_paragraphs = sum(ch.get('paragraph_count', 0) for ch in chapters_data)
        print(f"   总段落数: {total_paragraphs}")
        
        if success_count > 0:
            self.save_to_file(chapters_data)
            self.save_to_json(chapters_data)
            print(f"\n🎉 爬取完成！获得 {success_count} 个有效章节，共 {total_paragraphs} 个段落")
        else:
            print("❌ 没有成功获取任何章节内容")
            print("\n💡 建议:")
            print("   1. 检查网络连接")
            print("   2. 稍后重试（可能遇到频率限制）")
            print("   3. 尝试使用VPN或更换IP")
    
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
                    
                    f.write(f"\n\n\n\n")
                    # f.write(f"\n来源: {chapter['url']}")
                    # f.write("\n\n" + "=" * 50 + "\n\n")
                
                f.write(f"\n总计: {len(chapters_data)} 章, {total_chars} 字, {total_paragraphs} 段落\n")
            
            print(f"✅ 内容已保存到: {filename} (保持原始段落格式)")
            
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
    
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
            
            print(f"✅ JSON数据已保存到: {filename}")
            
        except Exception as e:
            print(f"❌ 保存JSON失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("        济公全传 - 专业版爬虫 v2.1")
    print("        (严格按p标签分段版本)")
    print("=" * 60)
    print("🎯 针对古诗文网优化，严格按p标签分段")
    print("⚠️  请遵守网站使用条款，仅用于学习研究")
    print("=" * 60)
    
    crawler = JigongCrawler()
    
    # 询问用户想要的模式
    print("请选择爬取模式:")
    print("1. 🧪 测试模式（只爬取3章，快速验证分段效果）")
    print("2. 🚀 完整模式（爬取所有章节，严格分段）")
    print("3. 📊 先测试再决定（推荐）")
    
    while True:
        choice = input("\n请输入选择 (1/2/3): ").strip()
        
        if choice == "1":
            print("\n🧪 开始测试模式...")
            crawler.crawl_book(delay=2, test_mode=True)
            break
            
        elif choice == "2":
            print("\n🚀 开始完整爬取...")
            crawler.crawl_book(delay=3, test_mode=False)
            break
            
        elif choice == "3":
            print("\n🧪 开始测试模式（前3章）...")
            crawler.crawl_book(delay=2, test_mode=True)
            
            print("\n" + "=" * 40)
            continue_choice = input("测试完成！是否继续爬取完整版本？(y/n): ").strip().lower()
            
            if continue_choice in ['y', 'yes', '是']:
                print("\n🚀 开始完整爬取...")
                crawler.crawl_book(delay=3, test_mode=False)
            else:
                print("👋 感谢使用！")
            break
            
        else:
            print("❌ 无效选择，请输入 1、2 或 3")
    
    print(f"\n📁 文件保存在当前目录:")
    print(f"   📄 济公全传.txt - 严格按段落格式的文本")
    print(f"   📋 济公全传.json - 包含段落统计的数据格式")

if __name__ == "__main__":
    main()