import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= 配置核心参数 =================
THREAD_NUM = 15  # 线程数（全频道较多，适当提高）
OUTPUT_PATH = 'migu_all_channels.txt'
APP_VERSION = "2600034600"
APP_VERSION_ID = APP_VERSION + "-99000-201600010010028"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SIMULATOR) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36",
    "Origin": "https://m.miguvideo.com",
    "Referer": "https://m.miguvideo.com/",
    "appCode": "miguvideo_default_h5",
    "appId": "miguvideo",
    "channel": "H5",
    "terminalId": "h5"
}

# 咪咕全部分类 ID（涵盖全网频道）
LIVE_CATEGORIES = {
    '热门': 'e7716fea6aa1483c80cfc10b7795fcb8', 
    '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05', 
    '卫视': '0847b3f6c08a4ca28f85ba5701268424',
    '地方': '855e9adc91b04ea18ef3f2dbd43f495b', 
    '体育': '7538163cdac044398cb292ecf75db4e0', 
    '影视': '10b0d04cb23d4ac5945c4bc77c7ac44e',
    '新闻': 'c584f67ad63f4bc983c31de3a9be977c', 
    '教育': 'af72267483d94275995a4498b2799ecd', 
    '熊猫': 'e76e56e88fff4c11b0168f55e826445d', 
    '综艺': '192a12edfef04b5eb616b878f031f32f',
    '少儿': 'fc2f5b8fd7db43ff88c4243e731ecede', 
    '纪实': 'e1165138bdaa44b9a3138d74af6c6673'
}

def md5(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def getSaltAndSign(pid):
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + pid + APP_VERSION[:8]
    sign = md5(md5(app_t) + suffix)
    return {"salt": salt, "sign": sign, "timestamp": timestamp}

def get_content_direct(pid):
    """直接请求咪咕官方高画质接口"""
    result = getSaltAndSign(pid)
    # rateType: 3为720P超清，4为1080P原画（部分频道支持4，默认用3最稳定）
    rateType = "3" 
    
    url = "https://play.miguvideo.com/playurl/v1/play/playurl"
    params = {
        "sign": result['sign'],
        "rateType": rateType,
        "contId": pid,
        "timestamp": result['timestamp'],
        "salt": result['salt']
    }
    api_headers = {
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
        "AppVersion": APP_VERSION,
        "TerminalId": "android",
        "X-UP-CLIENT-CHANNEL-ID": APP_VERSION_ID
    }
    try:
        resp = requests.get(url, params=params, headers=api_headers, timeout=4)
        return resp.json()
    except:
        return None

def getddCalcu720p(url, pID):
    if "&puData=" not in url:
        return url
    puData = url.split("&puData=")[1]
    keys = "cdabyzwxkl"
    ymd = datetime.now().strftime("%Y%m%d")
    ddCalcu = []
    for i in range(0, int(len(puData) / 2)):
        ddCalcu.append(puData[int(len(puData)) - i - 1])
        ddCalcu.append(puData[i])
        if i == 1: ddCalcu.append("v")
        if i == 2: ddCalcu.append(keys[int(ymd[2])])
        if i == 3: ddCalcu.append(keys[int(pID[6])])
        if i == 4: ddCalcu.append("a")
    return f'{url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android'

def parse_channel_stream(live_group, channel_data):
    """解析单个频道的真实播放流"""
    name = channel_data.get("name", "未知频道")
    pid = channel_data.get("pID")
    logo = channel_data.get("pics", {}).get("highResolutionH", "")
    
    if not pid:
        return None
        
    try:
        res = get_content_direct(pid)
        if not res or res.get("code") != "200":
            return None
            
        raw_url = res["body"]["urlInfo"]["url"]
        playurl = getddCalcu720p(raw_url, pid)

        # 跟踪重定向获取 HLS 真实流
        if playurl:
            for _ in range(5):
                obj = requests.get(playurl, headers=HEADERS, allow_redirects=False, timeout=3)
                location = obj.headers.get("Location")
                if not location:
                    break
                if "hlsz" in location or location.startswith("http"):
                    playurl = location
                    break
                time.sleep(0.1)
                
        print(f"【成功】-> {name}")
        return f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{live_group}",{name}\n{playurl}\n'
    except Exception:
        print(f"【失败】-> {name}")
        return None

def main():
    print("====== 正在初始化咪咕全频道抓取程序 ======")
    unique_channels = {}  # 用于全局频道去重 { pid: (group_name, data_dict) }

    # 第一步：遍历所有分类，拉取全部频道元数据并去重
    print("\n[步骤 1] 正在同步全网频道列表中...")
    for group_name, codec in LIVE_CATEGORIES.items():
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{codec}'
        try:
            res = requests.get(url, headers=HEADERS, timeout=5).json()
            data_list = res.get("body", {}).get("dataList", [])
            for item in data_list:
                pid = item.get("pID")
                if pid and pid not in unique_channels:
                    unique_channels[pid] = (group_name, item)
        except Exception as e:
            print(f"拉取分类 [{group_name}] 失败: {e}")

    total_count = len(unique_channels)
    print(f"\n[结果] 共发现 {total_count} 个不重复的频道。")
    print("\n[步骤 2] 开始多线程解析 720P 播放源...")

    # 初始化写入 M3U 头部
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/epg.xml" catchup="append" catchup-source="&playbackbegin=\\${(b)yyyyMMddHHmmss}&playbackend=\\${(e)yyyyMMddHHmmss}"\n')

    # 第二步：多线程高并发解析音视频流
    success_count = 0
    with ThreadPoolExecutor(max_workers=THREAD_NUM) as pool:
        futures = {
            pool.submit(parse_channel_stream, g_name, chunk): pid 
            for pid, (g_name, chunk) in unique_channels.items()
        }
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                success_count += 1
                with open(OUTPUT_PATH, 'a+', encoding='utf-8') as f:
                    f.write(result)

    print(f"\n====== 抓取任务完成 ======")
    print(f"成功获取：{success_count}/{total_count} 个频道")
    print(f"文件已保存至当前目录下的：{OUTPUT_PATH}")

if __name__ == "__main__":
    main()
