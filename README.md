# 项目启动指南

## 环境要求
### python 3.10.11 64bit

## 安装步骤

### 1. 下载项目
* git clone [项目地址]

### 2. 安装依赖包
* pip install -r requirements.txt
```
取消证书验证
按 Win + R，输入 %APPDATA% 回车，进入 Roaming 目录。
找到或创建 pip 文件夹（如果没有就新建）。
在 pip 文件夹内创建 pip.ini 文件（如果已有则直接编辑）。
[global]
trusted-host = pypi.org
             files.pythonhosted.org
```
#### 使用方式
* 文章列表的链接放到links.txt文件启动后就会自动下载
#### 控制台运行
* python index.py

