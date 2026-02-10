import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

thread_num = 10  # 线程数修正
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

# 直播分类
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


def format_date_ymd():
    """
    格式化日期为「年+补0月+补0日」字符串
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
    """生成签名参数"""
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
    """获取直播流信息"""
    _headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "sec-ch-ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
        "Referer": "https://m.miguvideo.com/"
    }
    
    result = getSaltAndSign(pid)
    rateType = "2" if pid == "608831231" else "3"  # 广东卫视特殊处理
    
    # 直接请求咪咕API
    url = f"https://play.miguvideo.com/playurl/v1/play/playurl"
    params = {
        "sign": result['sign'],
        "rateType": rateType,
        "contId": pid,
        "timestamp": result['timestamp'],
        "salt": result['salt'],
        "appVersion": appVersion,
        "terminalId": "h5",
        "appCode": "miguvideo_default_h5"
    }
    
    try:
        response = requests.get(url, headers=_headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"获取内容失败 {pid}: {e}")
    
    return {}


def getddCalcu720p(url, pID):
    """
    核心：从加密URL中提取720p M3U8直播链接
    """
    if not url:
        return ""
    
    try:
        # 提取puData参数
        if '&puData=' not in url:
            return url
            
        puData = url.split("&puData=")[1].split("&")[0]
        keys = "cdabyzwxkl"
        ddCalcu = []
        
        # 解密算法
        for i in range(0, min(10, len(puData) // 2)):
            if i < len(puData):
                # 算法1：反转和交叉
                ddCalcu.append(puData[len(puData) - i - 1])
                ddCalcu.append(puData[i])
                
                # 算法2：特殊字符插入
                if i == 1:
                    ddCalcu.append("v")
                if i == 2:
                    date_str = format_date_ymd()
                    if len(date_str) > 2:
                        ddCalcu.append(keys[int(date_str[2]) % len(keys)])
                if i == 3:
                    if len(pID) > 6:
                        ddCalcu.append(keys[int(pID[6]) % len(keys)])
                    else:
                        ddCalcu.append("k")  # 默认值
                if i == 4:
                    ddCalcu.append("a")
        
        # 构建解密后URL
        base_url = url.split("&puData=")[0]
        decrypted_url = f'{base_url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android'
        
        # 获取720p地址
        print(f"解密URL: {decrypted_url[:100]}...")
        return decrypted_url
        
    except Exception as e:
        print(f"获取720p地址失败: {e}")
        return url


def follow_redirects_to_720p(url, max_attempts=6):
    """
    跟随重定向获取最终720p M3U8地址
    """
    if not url:
        return ""
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    
    current_url = url
    
    for attempt in range(max_attempts):
        try:
            print(f"重定向尝试 {attempt + 1}: {current_url[:80]}...")
            
            # 不自动重定向
            response = session.get(current_url, allow_redirects=False, timeout=5)
            
            # 检查是否有重定向
            if 300 <= response.status_code < 400:
                location = response.headers.get('Location', '')
                if location:
                    current_url = location
                    print(f"重定向到: {location[:80]}...")
                    
                    # 检查是否是720p M3U8地址
                    if '720p' in location.lower() or '.m3u8' in location:
                        print(f"找到720p流地址: {location[:80]}...")
                        return location
                    continue
            
            # 检查响应内容是否为M3U8
            content_type = response.headers.get('Content-Type', '').lower()
            if 'm3u8' in content_type or '.m3u8' in current_url:
                print(f"找到M3U8地址 (尝试 {attempt+1}): {current_url[:80]}...")
                return current_url
            
            # 检查内容是否为M3U8格式
            if response.text.startswith('#EXTM3U'):
                print(f"找到M3U8内容 (尝试 {attempt+1}): {current_url[:80]}...")
                return current_url
            
            # 短暂延迟
            if attempt < max_attempts - 1:
                time.sleep(0.2)
                
        except Exception as e:
            print(f"重定向尝试 {attempt+1} 失败: {e}")
            if attempt < max_attempts - 1:
                time.sleep(0.2)
    
    print(f"未能在{max_attempts}次尝试内找到720p M3U8地址")
    return current_url


def append_All_Live(live, flag, data):
    """处理单个频道"""
    try:
        channel_name = data.get("name", "未知频道")
        pid = data.get("pID", "")
        
        print(f"处理频道: {channel_name} (PID: {pid})")
        
        # 获取直播流信息
        respData = get_content(pid)
        if not respData or respData.get("code") != "2000000":
            print(f"频道 [{channel_name}] 获取信息失败")
            return
            
        # 提取加密URL
        encrypted_url = respData.get("body", {}).get("urlInfo", {}).get("url", "")
        if not encrypted_url:
            print(f"频道 [{channel_name}] 无流地址")
            return
        
        # 获取720p地址
        decrypted_url = getddCalcu720p(encrypted_url, pid)
        if not decrypted_url:
            print(f"频道 [{channel_name}] 720p解密失败")
            return
        
        # 跟随重定向获取最终720p地址
        final_url = follow_redirects_to_720p(decrypted_url)
        if not final_url:
            print(f"频道 [{channel_name}] 获取720p地址失败")
            return
        
        # 生成M3U条目
        logo = data.get("pics", {}).get("highResolutionH", "")
        content = f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" tvg-logo="{logo}" group-title="{live}",{channel_name}\n{final_url}\n'
        
        # 存入列表
        if flag < len(All_Live):
            All_Live[flag] = content
            print(f'✓ 频道 [{channel_name}] 720p更新成功！')
        else:
            All_Live.append(content)
            
    except Exception as e:
        print(f'✗ 频道 [{data.get("name", "未知")}] 更新失败: {e}')


def update(live, url):
    """更新一个分类的所有频道"""
    global FLAG
    global All_Live
    
    print(f"分类 [{live}] 开始更新...")
    
    try:
        # 获取分类下的频道列表
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"分类 [{live}] 数据获取失败")
            return
            
        data = response.json()
        dataList = data.get("body", {}).get("dataList", [])
        
        if not dataList:
            print(f"分类 [{live}] 无可用频道")
            return
            
        print(f"分类 [{live}] 找到 {len(dataList)} 个频道")
        
        # 使用线程池处理每个频道
        with ThreadPoolExecutor(max_workers=thread_num) as executor:
            futures = []
            
            for flag, channel_data in enumerate(dataList):
                # 预留位置
                All_Live.append("")
                
                # 提交任务
                future = executor.submit(
                    append_All_Live, 
                    live, 
                    FLAG + flag, 
                    channel_data
                )
                futures.append(future)
            
            # 等待所有任务完成
            for future in futures:
                future.result()
        
        FLAG += len(dataList)
        print(f"分类 [{live}] 更新完成")
        
    except Exception as e:
        print(f"分类 [{live}] 更新失败: {e}")


def main():
    """主函数"""
    print("开始咪咕直播720p源更新...")
    
    # 写入M3U头
    m3u_header = '#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/erw.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n'
    writefile(path, m3u_header)
    
    # 遍历所有分类
    for live in lives:
        if live in LIVE:
            print(f"\n{'='*50}")
            print(f"处理分类: {live}")
            print('='*50)
            
            url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
            update(live, url)
            
            # 短暂延迟避免请求过快
            time.sleep(1)
    
    # 写入所有有效的直播源
    print(f"\n{'='*50}")
    print("写入M3U文件...")
    valid_count = 0
    
    for content in All_Live:
        if content and content.strip() and "http" in content:
            appendfile(path, content)
            valid_count += 1
    
    print(f"更新完成！共获取 {valid_count} 个有效720p直播源")
    print(f"文件保存至: {path}")


if __name__ == "__main__":
    main()
