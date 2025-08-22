# -*- coding: utf-8 -*-
from lib import downGSWByLink
import time

class DownArticle:
    def __init__(self):
        pass  # 初始化不执行下载

    def download_article(self, down_url):
        """
        根据链接下载文章
        """
        if not down_url:
            print("警告：链接为空，跳过。")
            return

        if down_url.lower() in ["q", "exit"]:
            print("收到退出指令，程序结束。")
            exit(0)

        print("\n开始下载...")

        if down_url.startswith("https://www.gushiwen.cn/"):
            print(f"正在下载: {down_url}")
            try:
                downGSWByLink.down(down_url)
                print("下载完成。")
            except Exception as e:
                print(f"下载失败 {down_url} : {e}")
        else:
            print(f"不支持该类型的链接: {down_url}")

if __name__ == "__main__":
    print("欢迎使用文章下载工具！")

    file_path = 'links.txt'

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            links = file.readlines()

        # 创建下载器实例
        downloader = DownArticle()

        # 遍历每一个链接
        for index, line in enumerate(links, start=1):
            link = line.strip()
            if not link:
                continue  # 跳过空行

            print(f"\n[{index}/{len(links)}] 正在处理: {link}")
            downloader.download_article(link)

            print('下载完成，延迟 10 秒...')
            time.sleep(10)  # 延迟 10 秒，避免请求过快

    except FileNotFoundError:
        print(f"错误：找不到文件 '{file_path}'，请确认文件是否存在。")
    except KeyboardInterrupt:
        print("\n\n用户中断操作，程序退出。")
    except Exception as e:
        print(f"发生错误：{e}")

    print("所有链接处理完成，程序结束。")