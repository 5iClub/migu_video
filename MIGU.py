import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置参数
thread_num = 10  # 线程数
path = 'migu.txt'
appVersion = "2600034600"
appVersionID = appVersion + "-99000-201600010010028"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Origin": "https://m.miguvideo.com",
    "Referer": "https://m.miguvideo.com/",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SIMULATOR) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36",
    "appCode": "miguvideo_default_h5",
    "appId": "miguvideo",
    "channel": "H5",
    "terminalId": "h5"
}

LIVE = {
    '热门': 'e7716fea6aa1483c80cfc10b7795fcb8', '体育': '7538163cdac044398cb292ecf75db4e0',
    '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05', '卫视': '0847b3f6c08a4ca28f85ba5701268424',
    '地方': '855e9adc91b04ea18ef3f2dbd43f495b', '影视': '10b0d04cb23d4ac5945c4bc77c7ac44e',
    '新闻': 'c584f67ad63f4bc983c31de3a9be977c', '教育': 'af72267483d94275995a4498b2799ecd',
    '熊猫': 'e76e56e88fff4c11b0168f55e826445d', '综艺': '192a12edfef04b5eb616b878f031f32f',
    '少儿': 'fc2f5b8fd7db43ff88c4243e731ecede', '纪实': 'e1165138bdaa44b9a3138d74af6c6673'
}

def format_date_ymd():
    return datetime.now().strftime("%Y%m%d")

def md5(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def getSaltAndSign(pid):
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + pid + appVersion[:8]
    sign = md5(md5(app_t) + suffix)
    return {"salt": salt, "sign": sign, "timestamp": timestamp}

def get_content_direct(pid):
    """
    直接请求咪咕官方播放鉴权接口，绕过 Apipost 代理
    """
    result = getSaltAndSign(pid)
    rateType = "3"  # 3 代表高清/720P，可根据需要尝试 "4" (1080P) 
    
    # 咪咕官方核心原生接口
    url = "https://play.miguvideo.com/playurl/v1/play/playurl"
    
    params = {
        "sign": result['sign'],
        "rateType": rateType,
        "contId": pid,
        "timestamp": result['timestamp'],
        "salt": result['salt']
    }
    
    # 模拟安卓端核心头部
    api_headers = {
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
        "AppVersion": appVersion,
        "TerminalId": "android",
        "X-UP-CLIENT-CHANNEL-ID": appVersionID,
        "Connection": "keep-alive"
    }
    
    try:
        resp = requests.get(url, params=params, headers=api_headers, timeout=5)
        return resp.json()
    except Exception as e:
        print(f"请求咪咕接口失败 pid {pid}: {e}")
        return None

def getddCalcu720p(url, pID):
    if "&puData=" not in url:
        return url
    puData = url.split("&puData=")[1]
    keys = "cdabyzwxkl"
    ddCalcu = []
    for i in range(0, int(len(puData) / 2)):
        ddCalcu.append(puData[int(len(puData)) - i - 1])
        ddCalcu.append(puData[i])
        if i == 1:
            ddCalcu.append("v")
        if i == 2:
            ddCalcu.append(keys[int(format_date_ymd()[2])])
        if i == 3:
            ddCalcu.append(keys[int(pID[6])])
        if i == 4:
            ddCalcu.append("a")
    return f'{url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android'

def process_channel(live, data):
    """
    单条频道的处理逻辑
    """
    name = data.get("name", "未知频道")
    pid = data.get("pID")
    logo = data.get("pics", {}).get("highResolutionH", "")
    
    try:
        respData = get_content_direct(pid)
        if not respData or respData.get("code") != "200":
            return None
            
        raw_url = respData["body"]["urlInfo"]["url"]
        playurl = getddCalcu720p(raw_url, pid)

        # 跟踪 302 重定向获取真正的流媒体 HLS 链接
        if playurl:
            for _ in range(6):
                obj = requests.get(playurl, headers=headers, allow_redirects=False, timeout=3)
                location = obj.headers.get("Location")
                if not location:
                    break
                if "hlsz" in location or location.startswith("http"):
                    playurl = location
                    break
                time.sleep(0.15)
                
        content = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{live}",{name}\n{playurl}\n'
        print(f'频道 [{name}] 成功获取 720P 链接')
        return content
    except Exception as e:
        print(f'频道 [{name}] 更新失败: {e}')
        return None

def main():
    print("开始更新咪咕直播源...")
    all_contents = []
    
    # 初始化文件
    with open(path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/epg.xml" catchup="append" catchup-source="&playbackbegin=\\${(b)yyyyMMddHHmmss}&playbackend=\\${(e)yyyyMMddHHmmss}"\n')

    # 循环分类抓取
    for live, codec in LIVE.items():
        print(f"\n分类 ----- [{live}] ----- 开始抓取")
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{codec}'
        
        try:
            response = requests.get(url, headers=headers, timeout=5).json()
            dataList = response.get("body", {}).get("dataList", [])
        except Exception as e:
            print(f"获取分类 [{live}] 列表失败: {e}")
            continue

        # 使用线程池并发请求当前分类下的频道
        with ThreadPoolExecutor(max_workers=thread_num) as pool:
            futures = [pool.submit(process_channel, live, data) for data in dataList]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_contents.append(result)
                    # 实时写入文件
                    with open(path, 'a+', encoding='utf-8') as f:
                        f.write(result)

    print(f"\n全部更新完成！已保存至 {path}")

if __name__ == "__main__":
    main()
