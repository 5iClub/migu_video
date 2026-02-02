import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

thread_num = 10  # 修正变量名 typo: thread_mum -> thread_num
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

# 添加锁来处理并发访问
lock = threading.Lock()


def format_date_ymd():
    """
    格式化日期为「年+补0月+补0日」字符串
    :return: 如"20251216"
    """
    current_date = datetime.now()
    return f"{current_date.year}{current_date.month:02d}{current_date.day:02d}"


def writefile(path, content):
    """写入文件"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def appendfile(path, content):
    """追加写入文件"""
    with open(path, 'a+', encoding='utf-8') as f:
        f.write(content)


def md5(text):
    """MD5加密：返回32位小写结果"""
    md5_obj = hashlib.md5()
    md5_obj.update(text.encode('utf-8'))
    return md5_obj.hexdigest()


def getSaltAndSign(pid):
    """生成salt和sign"""
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


def safe_request(url, method='GET', headers=None, data=None, retries=3):
    """安全的请求函数，带重试机制"""
    for attempt in range(retries):
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            else:
                response = requests.post(url, headers=headers, data=data, timeout=10)
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)  # 指数退避


def get_content(pid):
    """获取播放内容"""
    try:
        _headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "content-type": "application/json",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        }
        
        result = getSaltAndSign(pid)
        rateType = "2" if pid == "608831231" else "3"  # 广东卫视特殊处理
        
        URL = f"https://play.miguvideo.com/playurl/v1/play/playurl?sign={result['sign']}&rateType={rateType}&contId={pid}&timestamp={result['timestamp']}&salt={result['salt']}"
        
        # 简化的请求逻辑，避免复杂的API POST结构
        # 这里简化了原代码中的复杂请求结构
        response = safe_request(URL, method='GET', headers=_headers)
        
        if response.status_code != 200:
            return None
            
        return response.json()
        
    except Exception as e:
        print(f"获取内容失败 (PID: {pid}): {e}")
        return None


def getddCalcu720p(url, pID):
    """生成带ddCalcu参数的URL"""
    try:
        puData = url.split("&puData=")[1]
    except (IndexError, AttributeError):
        return url  # 如果无法解析，返回原URL
    
    keys = "cdabyzwxkl"
    ddCalcu = []
    
    for i in range(0, min(int(len(puData) / 2), 5)):  # 限制范围避免越界
        if i < len(puData) / 2:
            ddCalcu.append(puData[int(len(puData)) - i - 1])
            ddCalcu.append(puData[i])
            
        if i == 1:
            ddCalcu.append("v")
        if i == 2:
            try:
                ddCalcu.append(keys[int(format_date_ymd()[2]) % len(keys)])
            except (IndexError, ValueError):
                ddCalcu.append("c")
        if i == 3 and len(pID) > 6:
            try:
                ddCalcu.append(keys[int(pID[6]) % len(keys)])
            except (IndexError, ValueError):
                ddCalcu.append("d")
        if i == 4:
            ddCalcu.append("a")
            
    return f'{url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android'


def process_channel(live, data, index, results):
    """处理单个频道的线程函数"""
    channel_name = data.get("name", "未知频道")
    pid = data.get("pID", "")
    
    if not pid:
        print(f'频道 [{channel_name}] 跳过: 无PID')
        results[index] = None
        return
        
    try:
        respData = get_content(pid)
        if not respData or "body" not in respData or "urlInfo" not in respData["body"]:
            print(f'频道 [{channel_name}] 获取播放信息失败')
            results[index] = None
            return
            
        playurl = getddCalcu720p(respData["body"]["urlInfo"]["url"], pid)
        if not playurl:
            print(f'频道 [{channel_name}] 生成播放URL失败')
            results[index] = None
            return
            
        # 获取最终播放链接（最多重试3次）
        final_url = None
        for retry in range(3):
            try:
                obj = requests.get(playurl, allow_redirects=False, timeout=5)
                location = obj.headers.get("Location", "")
                
                if location and location.startswith("http://hlsz"):
                    final_url = location
                    break
                elif location:
                    final_url = location
                    
                time.sleep(0.3)
            except Exception as e:
                if retry == 2:
                    print(f'频道 [{channel_name}] 重定向失败: {e}')
        
        if not final_url:
            final_url = playurl
            
        # 获取高清logo
        logo_url = ""
        if "pics" in data:
            logo_url = data["pics"].get("highResolutionH", "")
            if not logo_url and "smallResolutionH" in data["pics"]:
                logo_url = data["pics"]["smallResolutionH"]
                
        content = f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{live}",{channel_name}\n{final_url}\n'
        
        with lock:
            results[index] = content
            print(f'频道 [{channel_name}] 更新成功！')
            
    except Exception as e:
        print(f'频道 [{channel_name}] 更新失败: {e}')
        with lock:
            results[index] = None


def update(live, url):
    """更新指定分类的频道"""
    print(f"分类 ----- [{live}] ----- 开始更新. . .")
    
    try:
        response = safe_request(url, headers=headers)
        if response.status_code != 200:
            print(f"获取分类 [{live}] 数据失败: HTTP {response.status_code}")
            return []
            
        data = response.json()
        if "body" not in data or "dataList" not in data["body"]:
            print(f"分类 [{live}] 数据结构异常")
            return []
            
        dataList = data["body"]["dataList"]
        results = [None] * len(dataList)
        
        # 使用线程池处理
        with ThreadPoolExecutor(max_workers=thread_num) as executor:
            futures = []
            for i, channel_data in enumerate(dataList):
                future = executor.submit(process_channel, live, channel_data, i, results)
                futures.append(future)
                
            # 等待所有任务完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    pass  # 错误已在process_channel中处理
                    
        # 过滤掉失败的结果
        return [r for r in results if r is not None]
        
    except Exception as e:
        print(f"更新分类 [{live}] 失败: {e}")
        return []


def main():
    """主函数"""
    print("开始更新咪咕直播源...")
    
    # 写入文件头部
    m3u_header = '''#EXTM3U x-tvg-url="https://cdn.jsdelivr.net/gh/develop202/migu_video/playback.xml,https://ghfast.top/raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml,https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"
'''
    
    writefile(path, m3u_header)
    
    all_channels = []
    
    # 处理所有分类
    for live in lives:
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
        channels = update(live, url)
        all_channels.extend(channels)
        
        # 添加分类分隔符
        if channels:
            all_channels.append(f'\n# 分类: {live}\n')
    
    # 写入所有频道
    for content in all_channels:
        if content:
            appendfile(path, content)
    
    print(f"\n更新完成！共更新了 {len([c for c in all_channels if c and '#EXTINF' in c])} 个频道")
    
    # 读取并显示文件大小
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"生成的M3U文件大小: {len(content) // 1024} KB")
    except Exception as e:
        print(f"读取生成的文件失败: {e}")


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"总耗时: {end_time - start_time:.2f} 秒")
