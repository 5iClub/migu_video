import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= 核心参数配置 =================
THREAD_NUM = 20  # 抓取全量频道，提高线程数以加快速度
OUTPUT_PATH = 'migu_full_channels.m3u'
APP_VERSION = "2600034600"
APP_VERSION_ID = APP_VERSION + "-99000-201600010010028"

# 统一请求头（模拟移动端）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SIMULATOR) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36",
    "Origin": "https://m.miguvideo.com",
    "Referer": "https://m.miguvideo.com/",
    "appCode": "miguvideo_default_h5",
    "appId": "miguvideo",
    "channel": "H5",
    "terminalId": "h5"
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
    """核心鉴权：向咪咕请求指定频道的 720P 播放配置"""
    result = getSaltAndSign(pid)
    # rateType: 3 = 超清720P / 4 = 原画1080P
    # 全量频道中包含大量地方小台，统一使用 '3' 兼容性最好。如果喜欢 1080P 可以尝试改为 '4'
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

def parse_channel_stream(channel_data):
    """处理并追踪单个流的真实重定向地址"""
    name = channel_data.get("name", "未知频道")
    pid = channel_data.get("pID")
    logo = channel_data.get("pics", {}).get("highResolutionH", "")
    # 获取它原本自带的分类标签（如果没有则归入‘其它’）
    group = channel_data.get("nodeName", "全部频道")
    
    if not pid:
        return None
        
    try:
        res = get_content_direct(pid)
        if not res or res.get("code") != "200":
            return None
            
        raw_url = res["body"]["urlInfo"]["url"]
        playurl = getddCalcu720p(raw_url, pid)

        # 进行 302 重定向追踪，直达真正的流媒体点（如 hlsz 或实时 cdn）
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
                
        print(f"【成功提取】-> {name}")
        return f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n{playurl}\n'
    except Exception:
        return None

def main():
    print("=========================================")
    print("    正在执行：咪咕全量频道终极提取程序    ")
    print("=========================================")
    
    # 咪咕全频道底层无分页大接口
    full_list_url = "https://program-sc.miguvideo.com/live/v2/tv-data/all-channels"
    
    print("\n[第一步] 正在连接咪咕网关获取全量清单...")
    try:
        # 如果大清单由于地区限制/版本迭代有变，备用方案是通过接口批量拉取底层大包
        res = requests.get(full_list_url, headers=HEADERS, timeout=8).json()
        raw_channels = res.get("body", {}).get("dataList", [])
    except Exception as e:
        print(f"💔 大清单接口请求失败: {e}。切换到全域并发扫描备用模式...")
        raw_channels = []
        # 备用：一次性扫描咪咕已知的底层所有核心节点块
        backups = ['e7716fea6aa1483c80cfc10b7795fcb8', '1ff892f2b5ab4a79be6e25b69d2f5d05', 
                   '0847b3f6c08a4ca28f85ba5701268424', '855e9adc91b04ea18ef3f2dbd43f495b',
                   '7538163cdac044398cb292ecf75db4e0', '10b0d04cb23d4ac5945c4bc77c7ac44e',
                   'c584f67ad63f4bc983c31de3a9be977c', 'af72267483d94275995a4498b2799ecd']
        for bk in backups:
            try:
                r = requests.get(f'https://program-sc.miguvideo.com/live/v2/tv-data/{bk}', headers=HEADERS, timeout=4).json()
                raw_channels.extend(r.get("body", {}).get("dataList", []))
            except:
                continue

    # 去重并清洗数据
    final_task_list = {}
    for item in raw_channels:
        pid = item.get("pID")
        if pid and pid not in final_task_list:
            final_task_list[pid] = item

    total_count = len(final_task_list)
    print(f"\n[分析结果] 全网总共筛选出 {total_count} 个不重复的独立直播频道。")
    print(f"[第二步] 启动 {THREAD_NUM} 线程并发跑通 720P 鉴权地址...")

    # 初始化 M3U 头部信息
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/epg.xml" catchup="append"\n')

    success_count = 0
    # 线程池并发处理
    with ThreadPoolExecutor(max_workers=THREAD_NUM) as pool:
        futures = [pool.submit(parse_channel_stream, item) for pid, item in final_task_list.items()]
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                success_count += 1
                with open(OUTPUT_PATH, 'a+', encoding='utf-8') as f:
                    f.write(result)

    print("\n=========================================")
    print(f"   🎉 任务全部完成！")
    print(f"   成功生成全量频道: {success_count} / {total_count}")
    print(f"   文件已妥善保存至: {OUTPUT_PATH}")
    print("=========================================")

if __name__ == "__main__":
    main()
