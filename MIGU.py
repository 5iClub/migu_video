import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import base64

thread_num = 10
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

# 更新分类ID（增加更多分类）
lives = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实', '4K', 'HDR']
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
    '纪实': 'e1165138bdaa44b9a3138d74af6c6673',
    '4K': '8a6b5e3c9f014d7a8c2d1b3e4f5a6c7d',      # 新增4K分类
    'HDR': 'f5a6c7d8e9b0a1b2c3d4e5f6a7b8c9d0'      # 新增HDR分类
}

path = 'migu_hq.txt'
appVersion = "2600034600"
appVersionID = appVersion + "-99000-201600010010028"
All_Live = []
FLAG = 0

# 新增：高质量源专用headers
hq_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.miguvideo.com/",
    "Origin": "https://www.miguvideo.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Content-Type": "application/json;charset=UTF-8"
}

# 新增：替代接口地址
ALTERNATE_API_URLS = [
    "https://playback.miguvideo.com/delegate/playback/play",
    "https://stream.miguvideo.com/live/play",
    "https://web-play.migu.cn/live/stream"
]

def format_date_ymd():
    """格式化日期为「年+补0月+补0日」字符串"""
    current_date = datetime.now()
    return f"{current_date.year}{current_date.month:02d}{current_date.day:02d}"

def writefile(path, content):
    """覆盖写入文件"""
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
    """生成接口所需的salt、sign、timestamp参数"""
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

def decode_migu_url(encrypted_url):
    """解密咪咕加密链接"""
    try:
        # 移除可能的base64前缀
        if encrypted_url.startswith('b64:'):
            encrypted_url = encrypted_url[4:]
        
        # Base64解码
        decoded = base64.b64decode(encrypted_url).decode('utf-8')
        
        # 简单替换解密（针对咪咕常见加密方式）
        replacements = {
            'z': 'a', 'y': 'b', 'x': 'c', 'w': 'd', 'v': 'e',
            'u': 'f', 't': 'g', 's': 'h', 'r': 'i', 'q': 'j',
            'p': 'k', 'o': 'l', 'n': 'm', 'm': 'n'
        }
        
        result = ''
        for char in decoded:
            result += replacements.get(char, char)
        
        return result
    except:
        return encrypted_url

def extract_hq_stream(pid):
    """方法1：解析网页获取高质量源"""
    try:
        # 从网页中提取播放信息
        webpage_url = f"https://www.miguvideo.com/mgs/website/prd/redirectToTVPlayUrl.html?contId={pid}"
        response = requests.get(webpage_url, headers=hq_headers, timeout=10)
        
        if response.status_code == 200:
            html_content = response.text
            
            # 尝试不同方式提取播放链接
            patterns = [
                r'"playUrl":"([^"]+)"',
                r'播放地址.*?(http[^\s"]+)',
                r'src="([^"]+\.m3u8[^"]*)"',
                r'video_url.*?"([^"]+)"'
            ]
            
            for pattern in patterns:
                import re
                match = re.search(pattern, html_content)
                if match:
                    url = match.group(1)
                    # 解码可能的加密链接
                    if 'b64:' in url or len(url) > 200:
                        url = decode_migu_url(url)
                    
                    # 验证是否为720P或更高清晰度
                    if any(q in url.lower() for q in ['720', '1080', '4k', 'hdr', 'high']):
                        return url
        
        return None
    except Exception as e:
        print(f"网页解析失败（pid={pid}）：{e}")
        return None

def get_hq_stream_alternate(pid, channel_name=""):
    """方法2：使用备用接口获取高质量源"""
    current_date = format_date_ymd()
    
    # 备用API参数（不同接口需要不同格式）
    alternate_params_list = [
        {
            "contId": pid,
            "rateType": "4",  # 4: 高清, 5: 超清, 6: 4K
            "timestamp": str(int(time.time() * 1000)),
            "appId": "miguvideo",
            "appVersion": appVersion
        },
        {
            "cid": pid,
            "quality": "high",  # high, super, ultra
            "platform": "h5",
            "_": str(int(time.time() * 1000))
        }
    ]
    
    for api_url in ALTERNATE_API_URLS:
        for params in alternate_params_list:
            try:
                response = requests.get(
                    api_url, 
                    headers=hq_headers, 
                    params=params, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 不同接口可能返回不同格式
                    urls_to_check = []
                    
                    # 尝试从不同字段提取URL
                    possible_paths = [
                        ["data", "url"],
                        ["body", "urlInfo", "url"],
                        ["result", "streamUrl"],
                        ["playUrl"],
                        ["url"],
                        ["m3u8_url"]
                    ]
                    
                    for path_list in possible_paths:
                        current = data
                        found = True
                        for key in path_list:
                            if isinstance(current, dict) and key in current:
                                current = current[key]
                            else:
                                found = False
                                break
                        if found and isinstance(current, str) and current.startswith("http"):
                            urls_to_check.append(current)
                    
                    # 检查是否为高质量源
                    for url in urls_to_check:
                        if any(q in url.lower() for q in ['720', '1080', '4k', 'hdr', 'high', 'super', 'ultra']):
                            return url
                    
                    # 如果接口返回URL列表，检查每个URL
                    if "urls" in str(data).lower():
                        import re
                        all_urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', str(data))
                        for url in all_urls:
                            if any(q in url.lower() for q in ['720', '1080', '4k', 'hdr']):
                                return url
                            
            except Exception as e:
                continue
    
    return None

def get_hq_stream_enhanced(pid, channel_name=""):
    """增强版高质量源获取（优先顺序）"""
    
    # 方案1：尝试备用接口
    hq_url = get_hq_stream_alternate(pid, channel_name)
    if hq_url:
        return hq_url
    
    # 方案2：尝试网页解析
    hq_url = extract_hq_stream(pid)
    if hq_url:
        return hq_url
    
    # 方案3：修改原始请求参数获取高清
    try:
        timestamp = str(int(time.time() * 1000))
        random_num = random.randint(0, 999999)
        salt = f"{random_num:06d}25"
        suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
        
        # 尝试不同的rateType
        for rate_type in ["4", "5", "6", "7"]:  # 4: 高清, 5: 超清, 6: 4K, 7: HDR
            app_t = timestamp + pid + appVersion[:8]
            sign = md5(md5(app_t) + suffix)
            
            params = {
                "sign": sign,
                "rateType": rate_type,
                "contId": pid,
                "timestamp": timestamp,
                "salt": salt,
                "appVersion": appVersion
            }
            
            url = "https://play.miguvideo.com/playurl/v1/play/playurl"
            response = requests.get(url, headers=hq_headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "200" and "body" in data:
                    url_info = data["body"].get("urlInfo", {})
                    stream_url = url_info.get("url")
                    if stream_url:
                        return stream_url
    except:
        pass
    
    return None

def get_content(pid):
    """修复版：直接请求咪咕接口获取播放链接（包含高质量源）"""
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Referer": "https://m.miguvideo.com/",
        "Origin": "https://m.miguvideo.com",
        "appCode": "miguvideo_default_h5",
        "appId": "miguvideo",
        "terminalId": "h5"
    }
   
    # 首先尝试获取高质量源
    hq_url = get_hq_stream_enhanced(pid)
    if hq_url:
        print(f"成功获取高质量源（pid={pid}）")
        # 模拟原始接口返回格式
        return {
            "code": "200",
            "body": {
                "urlInfo": {
                    "url": hq_url
                }
            }
        }
   
    # 如果高质量源失败，使用原始方法
    result = getSaltAndSign(pid)
    rateType = "2" if pid == "608831231" else "3"  # 这里可以尝试改为"4"获取高清
   
    # 尝试更高的rateType获取高质量
    for rt in ["4", "3", "2"]:
        params = {
            "sign": result['sign'],
            "rateType": rt,
            "contId": pid,
            "timestamp": result['timestamp'],
            "salt": result['salt']
        }
       
        url = "https://play.miguvideo.com/playurl/v1/play/playurl"
        try:
            resp = requests.get(url, headers=req_headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == "200":
                return data
        except:
            continue
    
    return None

def getddCalcu720p(url, pID):
    """对播放链接进行解密/拼接处理（增强版）"""
    try:
        # 检查是否已经是高质量源
        quality_indicators = ['720p', '1080p', '4k', 'hdr', 'high', 'hd']
        if any(indicator in url.lower() for indicator in quality_indicators):
            print(f"链接已是高质量源（pID={pID}）")
            return url
        
        # 尝试获取高质量源
        hq_url = get_hq_stream_enhanced(pID)
        if hq_url:
            return hq_url
        
        # 如果无法获取高质量源，使用原始处理
        if "&puData=" in url:
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
            result_url = f'{url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android'
            
            # 尝试修改参数获取高质量
            result_url = result_url.replace('rateType=2', 'rateType=4')
            result_url = result_url.replace('rateType=3', 'rateType=4')
            
            return result_url
        else:
            return url
    except Exception as e:
        print(f"链接解密失败（pID={pID}）：{e}")
        return url

def append_All_Live(live, flag, data):
    """处理单个频道的链接获取与格式化（增强版）"""
    try:
        pid = data.get("pID")
        name = data.get("name", "未知频道")
        pics = data.get("pics", {})
        logo = pics.get("highResolutionH", "")
       
        print(f"开始处理频道：{name} (PID: {pid})")
       
        # 获取播放链接
        respData = get_content(pid)
        if not respData or "body" not in respData:
            print(f'频道 [{name}] 获取播放链接失败：接口返回异常')
            # 尝试备用方案
            hq_url = get_hq_stream_enhanced(pid, name)
            if hq_url:
                content = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{live}",{name}\n{hq_url}\n'
                All_Live[flag] = content
                print(f'频道 [{name}] 备用方案更新成功！')
            return
       
        url_info = respData["body"].get("urlInfo", {})
        raw_url = url_info.get("url")
        if not raw_url:
            print(f'频道 [{name}] 无播放链接')
            # 尝试备用接口
            alternate_url = get_hq_stream_alternate(pid, name)
            if alternate_url:
                content = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{live}",{name}\n{alternate_url}\n'
                All_Live[flag] = content
                print(f'频道 [{name}] 备用接口更新成功！')
            return
       
        # 解密链接
        playurl = getddCalcu720p(raw_url, pid)
       
        # 处理302重定向，获取真实播放地址
        z = 1
        final_url = playurl
        while z <= 6:
            try:
                obj = requests.get(playurl, allow_redirects=False, timeout=5)
                location = obj.headers.get("Location")
                if location and location.startswith("http://hlsz"):
                    final_url = location
                    break
                time.sleep(0.15)
                z += 1
            except Exception as e:
                print(f"获取真实播放地址中间失败（{name}）：{e}")
                z += 1
                time.sleep(0.15)
       
        # 检查是否为高质量源
        if any(q in final_url.lower() for q in ['720', '1080', '4k', 'hdr', 'hd']):
            quality = "高清"
        elif '480' in final_url.lower():
            quality = "标清"
        else:
            quality = "未知"
            
        # 格式化M3U条目
        content = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{live}",{name} [{quality}]\n{final_url}\n'
        if z == 7:
            print(f'频道 [{name}] 更新失败：重定向次数超限')
        else:
            All_Live[flag] = content
            print(f'频道 [{name}] 更新成功！质量：{quality}')
    except Exception as e:
        print(f'频道 [{data.get("name", "未知")}] 更新失败！错误：{e}')

def update(live, url):
    """多线程处理单个分类下的所有频道"""
    global FLAG, All_Live
    pool = ThreadPoolExecutor(thread_num)
    try:
        print(f"获取分类 {live} 的频道列表...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        resp_json = response.json()
        dataList = resp_json["body"].get("dataList", [])
       
        if not dataList:
            print(f"分类 [{live}] 无频道数据")
            return
        
        print(f"分类 [{live}] 发现 {len(dataList)} 个频道")
       
        for flag, data in enumerate(dataList):
            All_Live.append("")
            pool.submit(append_All_Live, live, FLAG + flag, data)
        pool.shutdown(wait=True)
        FLAG += len(dataList)
    except Exception as e:
        print(f"分类 [{live}] 获取频道列表失败：{e}")
        pool.shutdown(wait=False)

def main():
    """主函数"""
    print("开始获取咪咕高清直播源...")
    
    # 初始化M3U文件
    writefile(path, '#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/erw.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n')
   
    # 遍历所有分类
    for live in lives:
        print(f"\n{'='*50}")
        print(f"分类 ----- [{live}] ----- 开始更新...")
        print(f"{'='*50}")
        
        if live in LIVE:
            url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
            update(live, url)
            time.sleep(1.5)  # 增加延迟避免请求过快
        else:
            print(f"分类 [{live}] 无对应ID，跳过")
   
    # 将所有频道写入文件
    print(f"\n{'='*50}")
    print(f"开始写入文件：{path}")
    valid_channels = [c for c in All_Live if c]
    
    for content in valid_channels:
        appendfile(path, content)
    
    print(f"文件写入完成！")
    print(f"共获取 {len(valid_channels)} 个有效频道")
    print(f"文件位置：{path}")
    print(f"{'='*50}")

def test_single_channel():
    """测试单个频道获取高清源"""
    test_pid = "608831231"  # CGTN测试
    test_name = "测试频道"
    
    print(f"测试获取高质量源 (PID: {test_pid})...")
    
    # 方法1：备用接口
    url1 = get_hq_stream_alternate(test_pid, test_name)
    print(f"备用接口结果: {url1[:100] if url1 else '无结果'}")
    
    # 方法2：网页解析
    url2 = extract_hq_stream(test_pid)
    print(f"网页解析结果: {url2[:100] if url2 else '无结果'}")
    
    # 方法3：增强获取
    url3 = get_hq_stream_enhanced(test_pid, test_name)
    print(f"增强获取结果: {url3[:100] if url3 else '无结果'}")

if __name__ == "__main__":
    # 测试单个频道
    # test_single_channel()
    
    # 运行主程序
    main()
