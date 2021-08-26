#!/user/bin/python3
# -*- coding: utf-8 -*-
from playwright.async_api import async_playwright
import asyncio
import os
import json
from PIL import Image
from loguru import logger
import time
import re


# # 定义自定义异常
# class DIYException(Exception):
#     def __init__(self, err_msg):
#         self.err_msg = err_msg
#
#     # 定义异常输出
#     def __str__(self):
#         return "[DIYException] %s" % self.err_msg
#
#     # 定义erpr输出
#     def __erpr__(self):
#         return self.err_msg


# 异常处理
def errPro(func):
    '''
       一个装饰器，用来记录异常
    '''

    def inner(*args, **kwargs):

        try:
            return func(*args, **kwargs)

        except Exception as e:
            raise Exception(f"{func.__name__} - {str(e)}")

    return inner


# 去除特殊字符
def isSpec(l):
    '''
    有些 title 或 artist 会包含 "/"，会导致异常，这里正则处理一下
    只有中文，英文字符，-，数字才会保留下来
    '''

    l = json.loads(l)

    comp = re.compile("[\u4e00-\u9fa5a-zA-Z\-0-9]{0,}")

    for k, v in l.items():
        words = comp.findall(v)  # 等价于re.findall("[\u4e00-\u9fa5a-zA-Z\-0-9]{0,}",v)
        words = "".join(words)  # 连接序列中的元素

        l[k] = words

    return l


# 读取songs.txt
@errPro
def readSong():
    '''
    读取 songs.txt 返回要爬取的歌曲信息
    '''

    # songs = os.path.join(os.path.abspath(os.path.dirname(__file__)), "songs.txt")
    songs = "D://software//Python//test1//songs.txt"

    with open(songs, "r", encoding='utf-8') as f:
        song_list = [isSpec(l) for l in f.readlines()]

    return song_list


# 剪切图片
@errPro
def cropPic(pic_path, box):
    '''
    使用 crop 剪切出最终图片
    '''

    img = Image.open(pic_path)
    img = img.convert("RGB")

    img = img.crop(box)

    img.save(pic_path)

    logger.info(f"{pic_path} ok")


@errPro
async def screenshotPic(song_list, browser, semaphore):
    '''
    处理单个网页
    '''

    # 网页url

    url = f"https://yoopu.me/view/{song_list['id']}"
    # 图片保存路径
    pic_path = os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)), "pus"),
                            f"{song_list['title']}-{song_list['artist']}-{song_list['type']}.png")

    async with semaphore:
        page = await browser.new_page()

        await page.goto(url)

        logger.info(f"{song_list['title']} start")

        # 等待直到 selector出现，相当于selenium的隐式等待
        await page.wait_for_selector("//hexi-sheet")

        # 注入js，这个api是在加载网站js后再运行，实现清除两个功能键
        await page.add_script_tag(content='''
                document.getElementsByTagName("yp-slider-play")[0].style.display = "none";
                document.getElementsByClassName("fullscreen-button yoopu3-icon")[0].style.display = "none";
            ''')

        # 获得谱子对象
        pu = await page.query_selector("//hexi-sheet")

        # 获得谱子的边界框值: {左上点xy坐标和宽高} -> dict
        location = await pu.bounding_box()

        # 调整页面大小
        # await page.set_viewport_size(width=int(location['width'] * 1.2), height=int(location['height'] * 1.2))
        await page.set_viewport_size({"width": 1000, "height": 2000})

        # 重新获取谱子的大小
        location = await pu.bounding_box()

        # 截屏
        await page.screenshot(path=pic_path)

        # 剪切图片
        box = [location["x"], location["y"], location["x"] + location["width"], location["y"] + location["height"]]
        cropPic(pic_path, box)

        # 关闭单个页面
        await page.close()
        logger.info(f"{song_list['title']} end")


async def main():
    async with async_playwright() as asp:
        # 打开浏览器
        browser = await asp.chromium.launch(headless=True)

        # 信号量，限制并发数
        semaphore = asyncio.Semaphore(10)

        song_list = readSong()

        #  创建任务列表，这时任务状态还是 Pending
        tasks = [asyncio.ensure_future(screenshotPic(song, browser, semaphore)) for song in song_list]

        # 实现异步嵌套
        dones, pendings = await asyncio.wait(tasks)

        for t in dones:
            t.result()

        # 关闭浏览器
        await browser.close()


if __name__ == "__main__":
    # 记录一下时间
    start = time.time()

    # 日志保存位置
    log = logger.add(os.path.join(os.path.abspath(os.path.dirname(__file__)), "yoopu.log"))

    loop = asyncio.get_event_loop()

    loop.run_until_complete(main())

    end = time.time()

    logger.info(f"共耗时：{end - start}s")
