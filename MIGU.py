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
    """
    格式化日期为「年+补0月+补0日」字符串（对应JS逻辑）
    :return: 如"20251216"
    """
    current_date = datetime.now()
    return f"{current_date.year}{current_date.month:02d}{current_date.day:02d}"


def writefile(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def appendfile(path, content):
    with open(path, 'a+', encoding='utf-8') as f:
        f.write(content)


def md5(text):
    """MD5加密：返回32位小写结果"""
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
    rateType = "3" if pid == "608831231" else "3"
    URL = f"https://play.miguvideo.com/playurl/v1/play/playurl?sign={result['sign']}&rateType={rateType}&contId={pid}&timestamp={result['timestamp']}&salt={result['salt']}"
    
    # 简化请求头，使用原始的headers
    req_headers = {
        "User-Agent": headers["User-Agent"],
        "Accept": "application/json, text/plain, */*",
        "appCode": headers["appCode"],
        "appId": headers["appId"],
        "channel": headers["channel"],
        "terminalId": headers["terminalId"],
        "Referer": "https://m.miguvideo.com/"
    }
    
    try:
        resp = requests.get(URL, headers=req_headers, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"请求异常: {e}")
        return None


def getddCalcu720p(url, pID):
    """修复后的ddCalcu计算函数"""
    try:
        # 提取puData参数
        if "&puData=" not in url:
            return url
        
        puData = url.split("&puData=")[1]
        # 如果puData包含其他参数，只取前面的部分
        if "&" in puData:
            puData = puData.split("&")[0]
        
        keys = "cdabyzwxkl"
        ddCalcu = []
        puData_len = len(puData)
        
        # 修复：正确处理循环逻辑
        for i in range(puData_len // 2):
            if i < puData_len:
                ddCalcu.append(puData[puData_len - i - 1])
            if i < puData_len:
                ddCalcu.append(puData[i])
            if i == 1:
                ddCalcu.append("v")
            if i == 2:
                # 获取日期字符串的第3个字符（索引2）
                date_str = format_date_ymd()
                if len(date_str) > 2:
                    ddCalcu.append(keys[int(date_str[2]) % len(keys)])
            if i == 3:
                if len(pID) > 6:
                    ddCalcu.append(keys[int(pID[6]) % len(keys)])
            if i == 4:
                ddCalcu.append("a")
        
        # 移除URL中的原puData参数，添加新的ddCalcu
        base_url = url.split("&puData=")[0]
        return f'{base_url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android'
    
    except Exception as e:
        print(f"ddCalcu计算错误: {e}")
        return url


def append_All_Live(live, flag, data):
    try:
        # 修复：获取正确的pID
        pID = data.get("contId") or data.get("pID")
        if not pID:
            print(f'频道 [{data.get("name", "未知")}] 没有contId，跳过')
            return
        
        respData = get_content(pID)
        
        if not respData or "body" not in respData or "urlInfo" not in respData["body"]:
            print(f'频道 [{data["name"]}] 获取流地址失败！')
            return
        
        playurl = respData["body"]["urlInfo"]["url"]
        
        # 计算ddCalcu
        playurl = getddCalcu720p(playurl, pID)
        
        if playurl:
            z = 1
            location = ""
            while z <= 6:
                try:
                    obj = requests.get(playurl, headers=headers, allow_redirects=False, timeout=10)
                    if obj.status_code in [301, 302] and "Location" in obj.headers:
                        location = obj.headers["Location"]
                        if location and (location.startswith("http://hlsz") or location.endswith(".m3u8")):
                            playurl = location
                            break
                    time.sleep(0.15)
                except Exception as e:
                    pass
                z += 1
            
            if z == 7:
                print(f'频道 [{data["name"]}] 更新失败！')
            else:
                # 获取频道图标
                logo = ""
                if "pics" in data:
                    logo = data["pics"].get("highResolutionH", "")
                
                content = f'#EXTINF:-1 tvg-id="{data["name"]}" tvg-name="{data["name"]}" tvg-logo="{logo}" group-title="{live}",{data["name"]}\n{playurl}\n'
                All_Live[flag] = content
                print(f'频道 [{data["name"]}] 更新成功！')
        else:
            print(f'频道 [{data["name"]}] 更新失败！')
            
    except Exception as e:
        print(f'频道 [{data["name"]}] 更新失败！')
        print(f"ERROR:{e}")


def update(live, url):
    global FLAG
    global All_Live
    global headers
    
    pool = ThreadPoolExecutor(thread_mum)
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "body" in data and "dataList" in data["body"]:
            dataList = data["body"]["dataList"]
            # 预分配列表空间
            All_Live.extend([""] * len(dataList))
            
            for flag, channel_data in enumerate(dataList):
                pool.submit(append_All_Live, live, FLAG + flag, channel_data)
            
            pool.shutdown(wait=True)
            FLAG += len(dataList)
        else:
            print(f"分类 [{live}] 数据格式错误")
            
    except Exception as e:
        print(f"更新分类 [{live}] 失败: {e}")
        pool.shutdown(wait=False)


def main():
    writefile(path,
              '#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/epg.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n')

    for live in lives:
        print(f"分类 ----- [{live}] ----- 开始更新. . .")
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
        update(live, url)

    for content in All_Live:
        if content:  # 只写入成功的内容
            appendfile(path, content)


if __name__ == "__main__":
    main()
