import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 配置项
thread_num = 10  # 线程数（修正原拼写错误 thread_mum）
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
LIVE = {
    '热门': 'e7716fea6aa1483c80cfc10b7795fcb8', 
    '体育': '7538163cdac044398cb292ecf75db4e0',
    '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05', 
    '卫视': '0847b3f6c08a4ca28f85ba5701268424',
    '地方': '855e9adc91b04ea18ef3f2dbd43f495b', 
    '影视': '10b0d04cb23d4ac5945c4bc77c7ac44e',
    '新闻': 'c584f67ad63f4bc983c31de3a9be977c', 
    '教育': 'af72267483d94275995a4498b2799ecd',
    '熊猫': 'e76e56e88fff4c11b0168f55e826445d', 
    '综艺': '192a12edfef04b5eb616b878f031f32f',
    '少儿': 'fc2f5b8fd7db43ff88c4243e731ecede', 
    '纪实': 'e1165138bdaa44b9a3138d74af6c6673'
}
path = 'migu.txt'
appVersion = "2600034600"
appVersionID = appVersion + "-99000-201600010010028"
All_Live = []
FLAG = 0

# 增加720P相关配置
QUALITY_720P = "720p"
TIMEOUT = 10  # 请求超时时间


def format_date_ymd():
    """
    格式化日期为「年+补0月+补0日」字符串（对应JS逻辑）
    :return: 如"20251216"
    """
    current_date = datetime.now()
    return f"{current_date.year}{current_date.month:02d}{current_date.day:02d}"


def writefile(path, content):
    """覆盖写入文件"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"写入文件失败: {e}")


def appendfile(path, content):
    """追加写入文件"""
    try:
        with open(path, 'a+', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"追加写入文件失败: {e}")


def md5(text):
    """MD5加密：返回32位小写结果"""
    try:
        md5_obj = hashlib.md5()
        md5_obj.update(text.encode('utf-8'))
        return md5_obj.hexdigest()
    except Exception as e:
        print(f"MD5加密失败: {e}")
        return ""


def getSaltAndSign(pid):
    """生成salt和sign参数"""
    try:
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
    except Exception as e:
        print(f"生成签名失败: {e}")
        return None


def get_play_url(pid):
    """
    获取直播播放地址，优先720P
    """
    try:
        # 生成签名参数
        sign_data = getSaltAndSign(pid)
        if not sign_data:
            return None
        
        # 广东卫视特殊处理
        rateType = "2" if pid == "608831231" else "3"
        
        # 构建请求URL
        base_url = "https://play.miguvideo.com/playurl/v1/play/playurl"
        params = {
            "sign": sign_data['sign'],
            "rateType": rateType,
            "contId": pid,
            "timestamp": sign_data['timestamp'],
            "salt": sign_data['salt'],
            "quality": QUALITY_720P  # 指定720P清晰度
        }
        
        # 发送请求获取播放地址
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "AppVersion": appVersion,
            "TerminalId": "android",
            "X-UP-CLIENT-CHANNEL-ID": appVersionID
        }
        
        response = requests.get(
            base_url,
            params=params,
            headers=headers,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") != "0" or not result.get("body"):
            print(f"获取播放地址失败，返回码: {result.get('code')}")
            return None
            
        return result["body"]["urlInfo"]["url"]
        
    except Exception as e:
        print(f"获取{pid}播放地址异常: {e}")
        return None


def getddCalcu720p(url, pID):
    """生成720P专用的ddCalcu参数"""
    try:
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
                
        return f'{url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android&quality={QUALITY_720P}'
    except Exception as e:
        print(f"生成ddCalcu参数失败: {e}")
        return url


def get_final_play_url(playurl, pID):
    """获取最终可播放的720P地址"""
    try:
        # 添加720P参数
        playurl = getddCalcu720p(playurl, pID)
        
        # 跟踪重定向，获取真实播放地址
        max_redirects = 6
        current_redirects = 0
        
        while current_redirects < max_redirects:
            response = requests.get(
                playurl,
                allow_redirects=False,
                timeout=TIMEOUT,
                headers={"User-Agent": headers["User-Agent"]}
            )
            
            # 检查是否有重定向
            if 300 <= response.status_code < 400 and "Location" in response.headers:
                location = response.headers["Location"]
                if location.startswith("http://hlsz"):
                    return location
                playurl = location
                current_redirects += 1
                time.sleep(0.15)
            else:
                break
                
        return playurl
    except Exception as e:
        print(f"获取最终播放地址失败: {e}")
        return None


def append_All_Live(live, index, data):
    """处理单个频道的直播源"""
    global All_Live
    try:
        pID = data.get("pID")
        name = data.get("name", "未知频道")
        
        if not pID:
            print(f'频道 [{name}] 无pID，跳过')
            All_Live[index] = ""
            return
            
        # 获取播放地址
        playurl = get_play_url(pID)
        if not playurl:
            print(f'频道 [{name}] 获取初始播放地址失败！')
            All_Live[index] = ""
            return
            
        # 获取最终720P播放地址
        final_url = get_final_play_url(playurl, pID)
        if not final_url:
            print(f'频道 [{name}] 获取720P播放地址失败！')
            All_Live[index] = ""
            return
            
        # 构建M3U8格式内容
        logo = data.get("pics", {}).get("highResolutionH", "")
        content = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{live}",{name}\n{final_url}\n'
        
        All_Live[index] = content
        print(f'频道 [{name}] 720P直播源更新成功！')
        
    except Exception as e:
        print(f'频道 [{data.get("name", "未知")}] 处理失败！错误: {e}')
        All_Live[index] = ""


def update(live, url):
    """更新指定分类的直播源"""
    global FLAG
    global All_Live
    
    try:
        # 获取分类下的频道列表
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") != "0" or not result.get("body", {}).get("dataList"):
            print(f"分类 [{live}] 获取频道列表失败")
            return
            
        dataList = result["body"]["dataList"]
        if not dataList:
            print(f"分类 [{live}] 无频道数据")
            return
            
        # 初始化All_Live列表
        current_len = len(All_Live)
        needed_len = FLAG + len(dataList)
        if needed_len > current_len:
            All_Live.extend([""] * (needed_len - current_len))
        
        # 多线程处理
        with ThreadPoolExecutor(max_workers=thread_num) as pool:
            for flag, data in enumerate(dataList):
                pool.submit(append_All_Live, live, FLAG + flag, data)
        
        # 更新全局索引
        FLAG += len(dataList)
        
    except Exception as e:
        print(f"分类 [{live}] 更新失败！错误: {e}")


def main():
    """主函数"""
    # 初始化M3U8文件
    m3u8_header = '#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/erw.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n'
    writefile(path, m3u8_header)
    
    # 遍历所有分类更新直播源
    for live in lives:
        print(f"\n===== 分类 [{live}] 开始更新 =====")
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
        update(live, url)
    
    # 将结果写入文件
    print("\n===== 开始写入文件 =====")
    for content in All_Live:
        if content.strip():  # 只写入非空内容
            appendfile(path, content)
    
    print(f"\n所有直播源已写入 {path}，总计有效频道: {len([c for c in All_Live if c.strip()])}")


if __name__ == "__main__":
    # 设置随机种子
    random.seed(time.time())
    # 执行主程序
    main()
