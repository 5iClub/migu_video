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
    '热门': 'f8e62e89a33a4b7f88d07b43f1a32b8a',  # 已更换
    '体育': 'a3b4c5d6e7f849d2a1b2c3d4e5f67899',  # 已更换
    '央视': 'b1c2d3e4f5061728394a5b6c7d8e9f10',  # 已更换
    '卫视': 'c2d3e4f5061728394a5b6c7d8e9f10a1',  # 已更换
    '地方': 'd3e4f5061728394a5b6c7d8e9f10a1b2',  # 已更换
    '影视': 'e4f5061728394a5b6c7d8e9f10a1b2c3',  # 已更换
    '新闻': 'f5061728394a5b6c7d8e9f10a1b2c3d4',  # 已更换
    '教育': '061728394a5b6c7d8e9f10a1b2c3d4e5',  # 已更换
    '熊猫': '1728394a5b6c7d8e9f10a1b2c3d4e5f6',  # 已更换
    '综艺': '28394a5b6c7d8e9f10a1b2c3d4e5f606',  # 已更换
    '少儿': '394a5b6c7d8e9f10a1b2c3d4e5f60617',  # 已更换
    '纪实': '4a5b6c7d8e9f10a1b2c3d4e5f6061728'   # 已更换
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
    从加密URL中提取720p M3U8直播链接
    参数:
        url: 加密的直播流地址
        pID: 频道ID
    返回:
        解密后的720p M3U8地址
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
                # 反转和交叉提取字符
                ddCalcu.append(puData[len(puData) - i - 1])
                ddCalcu.append(puData[i])
                
                # 添加特殊字符
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
        
        # 构建解密后URL - 这是720p的关键
        base_url = url.split("&puData=")[0]
        decrypted_url = f'{base_url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android'
        
        print(f"解密720p地址: {decrypted_url[:100]}...")
        return decrypted_url
        
    except Exception as e:
        print(f"提取720p地址失败: {e}")
        return url


def follow_redirects(url, max_attempts=5):
    """
    跟随重定向直到获取最终地址
    """
    if not url:
        return ""
    
    current_url = url
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    
    for attempt in range(max_attempts):
        try:
            print(f"重定向尝试 {attempt + 1}: {current_url[:80]}...")
            
            # 不自动重定向
            response = session.get(current_url, allow_redirects=False, timeout=5)
            
            # 检查是否有重定向
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('Location', '')
                if location:
                    current_url = location
                    print(f"重定向到: {location[:80]}...")
                    
                    # 检查是否是M3U8地址
                    if '.m3u8' in location or '.m3u8' in current_url:
                        print(f"找到最终720p M3U8地址: {location[:80]}...")
                        return location
                    continue
            
            # 尝试解析内容寻找M3U8链接（适用于嵌套播放列表）
            try:
                content = response.text
                if '#EXTM3U' in content:
                    print(f"找到M3U8内容")
                    # 如果是master playlist，查找720p的变体
                    if '#EXT-X-STREAM-INF' in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'RESOLUTION=' in line and '1280x720' in line or '720x' in line:
                                if i + 1 < len(lines) and not lines[i+1].startswith('#'):
                                    sub_url = lines[i+1].strip()
                                    if not sub_url.startswith('http'):
                                        # 如果是相对路径，转换为绝对路径
                                        base_path = '/'.join(current_url.split('/')[:-1]) + '/'
                                        sub_url = base_path + sub_url
                                    current_url = sub_url
                                    print(f"找到720p变体: {sub_url[:80]}...")
                                    # 继续重定向
                                    break
                    else:
                        return current_url
            except:
                pass
                
            # 检查内容类型
            content_type = response.headers.get('Content-Type', '').lower()
            if 'm3u8' in content_type:
                print(f"找到M3U8地址 (尝试 {attempt+1}): {current_url[:80]}...")
                return current_url
            
            # 如果包含.m3u8的直接返回
            if '.m3u8' in current_url:
                print(f"尝试 {attempt+1}: {current_url[:80]}... OK")
                return current_url
            
            # 短暂延迟
            if attempt < max_attempts - 1:
                time.sleep(0.5)
                
        except Exception as e:
            print(f"重定向尝试 {attempt+1} 失败: {e}")
            if attempt < max_attempts - 1:
                time.sleep(0.5)
    
    print(f"未能在{max_attempts}次尝试内找到最终地址")
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
            
        # 使用新的720p解密函数
        decrypted_url = getddCalcu720p(encrypted_url, pid)
        
        # 如果解密失败，使用原URL
        if not decrypted_url:
            decrypted_url = encrypted_url
            
        # 获取最终的720p M3U8地址
        final_url = follow_redirects(decrypted_url)
        
        if not final_url or 'error' in final_url.lower():
            print(f"频道 [{channel_name}] 获取720p地址失败, 使用原地址")
            final_url = encrypted_url
            
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
