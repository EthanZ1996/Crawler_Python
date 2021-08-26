import requests
from faker import Faker
import asyncio
import os
import json
import aiohttp

fake = Faker()

YOOPU_TYPE = ["guitar", "ukulele"]


# 获得榜单用户id
def userCodeList(t):
    url = f"https://yoopu.me/users/ranking/totalscore?instrument={t}"

    headers = {
        "User-Agent": fake.user_agent()
    }

    resp = requests.get(url, headers=headers)
    data = resp.json()

    codeList = [user["userCode"] for user in data["userRanks"]]

    return codeList


# 获得用户的曲子id，title
async def songInfo(userCode):
    headers = {
        "User-Agent": fake.user_agent(),
        "Referer": "https://yoopu.me/view-user"
    }

    song_list = []

    async with aiohttp.ClientSession() as session:

        for i in range(0, 10000, 20):

            url = f"https://yoopu.me/api/user/sheets?code={userCode}&start={i}&sort=views"
            print(url, "start")

            async with session.get(url, headers=headers) as resp:

                # 边界值
                data = await resp.text()
                if data == "[]":
                    break

                data = await resp.json()

                for song in data:
                    item = {
                        "type": song['type'],
                        "title": song['title'],
                        "artist": song['artist'],
                        "id": song['id']
                    }

                    song_list.append(item)
            # break

    return song_list


# 回调函数，保存数据
def callback_songInfo(future):
    song_list = future.result()

    songs = os.path.join(os.path.abspath(os.path.dirname(__file__)), "songs.txt")

    with open(songs, "a+", encoding='utf-8') as f:
        for song in song_list:
            f.write(json.dumps(song, ensure_ascii=False) + "\n")
            print(song)


def async_run():
    loop = asyncio.get_event_loop()

    tasks = []

    for t in YOOPU_TYPE:
        code_list = userCodeList(t)

        for code in code_list:
            print(code, "start")

            task = asyncio.ensure_future(songInfo(code))
            task.add_done_callback(callback_songInfo)  # 回调

            tasks.append(task)

    loop.run_until_complete(asyncio.wait(tasks))


if __name__ == "__main__":
    async_run()