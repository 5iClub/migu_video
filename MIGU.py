import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

thread_mum = 10  # 线程
headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Origin": "https://m.miguvideo.com",
    "Pragma": "no-cache",
    "Referer": "https://m.miguvideo.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Support-Pendant": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
    "appCode": "miguvideo_default_h5",
    "appId": "miguvideo",
    "channel": "H5",
    "sec-ch-ua": "\"Chromium\";v=\"136\", \"Microsoft Edge\";v=\"136\", \"Not.A/Brand\";v=\"99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "terminalId": "h5"
}
lives = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']
LIVE = {'热门': 'e7716fea6aa1483c80cfc10b7795fcb8', '体育': '7538163cdac044398cb292ecf75db4e0',
        '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05', '卫视': '0847b3f6c08a4ca28f85ba5701268424',
        '地方': '855e9adc91b04ea18ef3f2dbd43f495b', '影视': '10b0d04cb23d4ac5945c4bc77c7ac44e',
        '新闻': 'c584f67ad63f4bc983c31de3a9be977c', '教育': 'af72267483d94275995a4498b2799ecd',
        '熊猫': 'e76e56e88fff4c11b0168f55e826445d', '综艺': '192a12edfef04b5eb616b878f031f32f',
        '少儿': 'fc2f5b8fd7db43ff88c4243e731ecede', '纪实': 'e1165138bdaa44b9a3138d74af6c6673'}
path = 'migu.txt'
appVersion = "2600034600"
appVersionID = appVersion + "-99000-201600010010028"
All_Live = []
FLAG = 0


def format_date_ymd():
    current_date = datetime.now()
    return f"{current_date.year}{current_date.month:02d}{current_date.day:02d}"


def writefile(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def appendfile(path, content):
    with open(path, 'a+', encoding='utf-8') as f:
        f.write(content)


def md5(text):
    md5_obj = hashlib.md5()
    md5_obj.update(text.encode('utf-8'))
    return md5_obj.hexdigest()


def getSaltAndSign(pid):
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + pid + appVersion[:8]
    sign = md5(md5(app_t) + suffix)
    return {
        "salt": salt,
        "sign": sign,
        "timestamp": timestamp
    }


def get_content(pid):
    result = getSaltAndSign(pid)
    rateType = "3"  # 统一使用3（720p）
    URL = f"https://play.miguvideo.com/playurl/v1/play/playurl?sign={result['sign']}&rateType={rateType}&contId={pid}&timestamp={result['timestamp']}&salt={result['salt']}"
    
    # 使用精简请求头，避免被拦截
    req_headers = {
        "User-Agent": headers["User-Agent"],
        "Accept": "application/json",
        "appCode": headers["appCode"],
        "appId": headers["appId"],
        "channel": headers["channel"],
        "terminalId": headers["terminalId"],
        "Referer": "https://m.miguvideo.com/"
    }
    try:
        resp = requests.get(URL, headers=req_headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"get_content 状态码异常: {resp.status_code}")
            return None
    except Exception as e:
        print(f"get_content 请求异常: {e}")
        return None


def getddCalcu720p(url, pID):
    """
    修复版：正确生成 ddCalcu 参数
    """
    try:
        # 提取 puData
        if "&puData=" not in url:
            return url
        parts = url.split("&puData=")
        base = parts[0]
        puData_part = parts[1]
        # puData 可能还包含其他参数，只取 & 之前的部分
        if "&" in puData_part:
            puData = puData_part.split("&")[0]
        else:
            puData = puData_part
        
        if not puData:
            return url
        
        keys = "cdabyzwxkl"
        ddCalcu = []
        length = len(puData)
        # 按照原 JS 逻辑：遍历前 length/2 次，每次取对称位置的两个字符
        for i in range(length // 2):
            # 取对称的两个字符（从外向内）
            ddCalcu.append(puData[length - 1 - i])
            ddCalcu.append(puData[i])
            if i == 1:
                ddCalcu.append("v")
            if i == 2:
                # 取日期第3个字符（索引2）
                day_char = format_date_ymd()[2]
                index = int(day_char) % len(keys)
                ddCalcu.append(keys[index])
            if i == 3:
                # 取 pID 的第7个字符（索引6）
                pid_char = pID[6] if len(pID) > 6 else "0"
                index = int(pid_char) % len(keys)
                ddCalcu.append(keys[index])
            if i == 4:
                ddCalcu.append("a")
        
        # 重新组装 URL
        new_url = f"{base}&ddCalcu={''.join(ddCalcu)}&sv=10004&ct=android"
        # 如果原 URL 中 puData 后面还有其它参数，需要保留
        if "&" in parts[1]:
            remaining = "&" + parts[1].split("&", 1)[1]
            new_url += remaining
        return new_url
    except Exception as e:
        print(f"getddCalcu720p 错误: {e}")
        return url


def append_All_Live(live, flag, data):
    try:
        # 获取正确的 contId
        pID = data.get("contId") or data.get("pID")
        if not pID:
            print(f'频道 [{data.get("name", "未知")}] 无 contId，跳过')
            return
        
        respData = get_content(pID)
        if not respData or "body" not in respData or "urlInfo" not in respData["body"]:
            print(f'频道 [{data["name"]}] 获取 playurl 失败')
            return
        
        raw_url = respData["body"]["urlInfo"]["url"]
        if not raw_url:
            print(f'频道 [{data["name"]}] 返回的 url 为空')
            return
        
        # 生成带 ddCalcu 的地址
        playurl = getddCalcu720p(raw_url, pID)
        
        # 重定向解析，直到拿到真实 m3u8
        final_url = None
        for attempt in range(6):
            try:
                resp = requests.get(playurl, headers=headers, allow_redirects=False, timeout=10)
                if resp.status_code in (301, 302):
                    location = resp.headers.get("Location")
                    if location:
                        # 如果已经是 m3u8 或者 hls 地址，直接使用
                        if location.endswith('.m3u8') or 'hls' in location:
                            final_url = location
                            break
                        else:
                            playurl = location
                            continue
                else:
                    # 非重定向响应，检查内容是否为 m3u8
                    if resp.status_code == 200 and '#EXTM3U' in resp.text:
                        final_url = playurl
                        break
            except Exception:
                pass
            time.sleep(0.15)
        
        if final_url:
            logo = data.get("pics", {}).get("highResolutionH", "")
            content = f'#EXTINF:-1 tvg-id="{data["name"]}" tvg-name="{data["name"]}" tvg-logo="{logo}" group-title="{live}",{data["name"]}\n{final_url}\n'
            All_Live[flag] = content
            print(f'频道 [{data["name"]}] 更新成功！')
        else:
            print(f'频道 [{data["name"]}] 重定向解析失败')
    except Exception as e:
        print(f'频道 [{data["name"]}] 更新异常: {e}')


def update(live, url):
    global FLAG, All_Live
    pool = ThreadPoolExecutor(thread_mum)
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        dataList = data.get("body", {}).get("dataList", [])
        if not dataList:
            print(f"分类 [{live}] 无频道数据")
            return
        # 预扩展列表
        All_Live.extend([""] * len(dataList))
        for idx, ch in enumerate(dataList):
            pool.submit(append_All_Live, live, FLAG + idx, ch)
        pool.shutdown(wait=True)
        FLAG += len(dataList)
    except Exception as e:
        print(f"分类 [{live}] 更新失败: {e}")
        pool.shutdown(wait=False)


def main():
    writefile(path,
              '#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/epg.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n')
    for live in lives:
        print(f"分类 ----- [{live}] ----- 开始更新. . .")
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
        update(live, url)
    for content in All_Live:
        if content:
            appendfile(path, content)


if __name__ == "__main__":
    main()
