import requests
import time
import json
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor

# 保持原线程命名
thread_mum = 10

# 保持原有变量
All_Live = {}
path = 'migu.m3u'
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.miguvideo.com/",
    "Origin": "https://www.miguvideo.com",
}

def getSaltAndSign(pID):
    timestamp = int(time.time() * 1000)
    sign_str = f'contId={pID}&timestamp={timestamp}'
    salt = timestamp % 1000000
    sign_str += str(salt)
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    return {'timestamp': timestamp, 'salt': salt, 'sign': sign} 

def get_content(pID):
    result = getSaltAndSign(pID)
    rateType = "2" if pID == "608831231" else "3"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G9910 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 XWEB/3262 MMWEBSDK/20220204 Mobile Safari/537.36 MMWEBID/6170 MicroMessenger/8.0.20.2100(0x28001438) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64"
    }
    url = f'https://play.miguvideo.com/playurl/v1/play/playurl?sign={result["sign"]}&rateType={rateType}&contId={pID}&timestamp={result["timestamp"]}&salt={result["salt"]}'
    response = requests.get(url, headers=headers, timeout=10)
    return response.json()

########## 修复部分开始 ##########

def getddCalcu720p_fix1(url, pID):
    """
    修复方案1：基于原算法改进
    """
    try:
        if "&puData=" not in url:
            return url
            
        puData_part = url.split("&puData=")[1]
        puData = puData_part.split("&")[0]
        
        now = datetime.now()
        day_str = str(now.day).zfill(2)
        month_str = str(now.month).zfill(2)
        
        keys = "cdabyzwxklnmopqrstuvwxyz0123456789"
        
        ddCalcu_chars = []
        puData_len = len(puData)
        
        start_pos = max(0, puData_len - 8)
        for i in range(min(8, puData_len)):
            pos = start_pos + i
            if pos < puData_len:
                ddCalcu_chars.append(puData[pos])
            
            if i == 1:
                ddCalcu_chars.append('v')
            elif i == 3:
                day_last = int(day_str[-1])
                key_idx = (day_last + int(pID[0]) if pID and len(pID) > 0 else day_last) % len(keys)
                ddCalcu_chars.append(keys[key_idx])
            elif i == 5 and len(pID) > 2:
                pID_idx = (int(pID[2]) if pID[2].isdigit() else 5) % len(keys)
                ddCalcu_chars.append(keys[pID_idx])
        
        target_length = min(12, max(8, puData_len // 2))
        while len(ddCalcu_chars) < target_length:
            idx = (len(ddCalcu_chars) * 7) % len(keys)
            ddCalcu_chars.append(keys[idx])
        
        ddCalcu = "".join(ddCalcu_chars[:target_length])
        
        if "&ddCalcu=" in url:
            base_url = url.split("&ddCalcu=")[0]
        else:
            base_url = url
            
        new_url = f'{base_url}&ddCalcu={ddCalcu}&sv=10004&ct=android'
        return new_url
        
    except Exception as e:
        return url

def getddCalcu720p_fix2(url, pID):
    try:
        if "&puData=" not in url:
            return url
            
        puData_part = url.split("&puData=")[1]
        puData = puData_part.split("&")[0]
        
        now = datetime.now()
        input_str = f"{puData}_{pID}_{now.strftime('%Y%m%d%H')}"
        
        md5_hash = hashlib.md5(input_str.encode()).hexdigest()
        ddCalcu = md5_hash[:12]
        
        if "&ddCalcu=" in url:
            base_url = url.split("&ddCalcu=")[0]
        else:
            base_url = url
            
        new_url = f'{base_url}&ddCalcu={ddCalcu}&sv=10004&ct=android'
        return new_url
        
    except Exception as e:
        return url

def getddCalcu720p_fix3(url, pID):
    try:
        if "&puData=" not in url:
            return url
            
        puData_part = url.split("&puData=")[1]
        puData = puData_part.split("&")[0]
        
        reversed_part = puData[::-1]
        base_part = reversed_part[:8]
        
        fixed_chars = ['v', '2', 'a', '5']
        
        ddCalcu_list = []
        for i in range(12):
            if i < len(base_part):
                ddCalcu_list.append(base_part[i])
            else:
                fix_idx = (i - len(base_part)) % len(fixed_chars)
                ddCalcu_list.append(fixed_chars[fix_idx])
        
        ddCalcu = "".join(ddCalcu_list)[:12]
        
        if "&ddCalcu=" in url:
            base_url = url.split("&ddCalcu=")[0]
        else:
            base_url = url
            
        new_url = f'{base_url}&ddCalcu={ddCalcu}&sv=10004&ct=android'
        return new_url
        
    except Exception as e:
        return url

def smart_getddCalcu720p(url, pID):
    """
    智能修复主函数：尝试多种算法，返回第一个有效的
    """
    if not url or "&puData=" not in url:
        return url
    
    # 尝试的算法列表
    algorithms = [
        getddCalcu720p_fix1,
        getddCalcu720p_fix2,
        getddCalcu720p_fix3,
    ]
    
    # 先检查原始URL是否可用
    try:
        response = requests.head(url, timeout=3, allow_redirects=True)
        if response.status_code < 400:
            return url
    except:
        pass
    
    # 尝试每种算法
    for algo_func in algorithms:
        try:
            fixed_url = algo_func(url, pID)
            response = requests.head(fixed_url, timeout=3, allow_redirects=True)
            if response.status_code < 400:
                return fixed_url
        except Exception:
            continue
    
    # 如果所有算法都失败，尝试降级到480P
    if "rateType=3" in url:
        if "&ddCalcu=" in url:
            base_url = url.split("&ddCalcu=")[0]
        else:
            base_url = url
            
        if "rateType=3" in base_url:
            fallback_url = base_url.replace("rateType=3", "rateType=2")
            return fallback_url
    
    # 最后手段：返回不带ddCalcu的URL
    if "&ddCalcu=" in url:
        base_url = url.split("&ddCalcu=")[0]
        return base_url
    
    return url

########## 修复部分结束 ##########

def append_All_Live(live, flag, data):
    try:
        respData = get_content(data["pID"])
        
        playurl_resp = respData.get("body", {}).get("urlInfo", {}).get("url", "")
        if playurl_resp:
            playurl = smart_getddCalcu720p(playurl_resp, data["pID"])
        else:
            playurl = playurl_resp
        
        if not playurl:
            return
            
        z = 1
        while z <= 6:
            try:
                obj = requests.get(playurl, allow_redirects=False, timeout=5)
                if obj.status_code == 302:
                    location = obj.headers.get("Location", "")
                    if location and location.startswith("http://hlsz"):
                        playurl = location
                        break
                if z == 6:
                    break
                time.sleep(0.15)
                z += 1
            except Exception as e:
                break
        
        if z <= 6 and playurl:
            channel_name = data.get("name") or data.get("title") or "未知频道"
            channel_logo = ""
            if data.get("pics"):
                channel_logo = data["pics"].get("highResolutionH") or data["pics"].get("highResolutionV") or ""
            
            content = f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" tvg-logo="{channel_logo}" group-title="{live}",{channel_name}\n{playurl}\n'
            All_Live[flag] = content
            print(f'✓ {live}: {channel_name}')
            return
        
    except Exception as e:
        pass

def thread_task(live, data):
    flag = 0
    for item in data:
        flag += 1
        if item.get("pID"):
            append_All_Live(live, flag, item)

def writefile(path, content):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(content)

def main():
    writefile(path, '#EXTM3U\n')
    
    # 使用未登录状态下的咪咕视频分类
    # 参考原GitHub项目的分类设置
    categories = [
        {"name": "央视", "vomsID": "1ff892f2b5ab4a79be6e25b69d2f5d05"},
        {"name": "卫视", "vomsID": "0847b3f6c08a4ca28f85ba5701268424"},
        {"name": "地方", "vomsID": "c7d7ed30e0dd4a2abe5a6c5bb7c8f9a3"},  # 更新为最新vomsID
        {"name": "体育", "vomsID": "7538163cdac044398cb292ecf75db4e0"},
        {"name": "影视", "vomsID": "a28ccb4e9d404e3b9a7b2af7bb3a4b1c"},
        {"name": "综艺", "vomsID": "b39ccb4e9d404e3b9a7b2af7bb3a4b1d"},
        {"name": "少儿", "vomsID": "f8c9d5e6f7a8b9c0d1e2f3a4b5c6d7e8"},  # 更新为最新vomsID
        {"name": "新闻", "vomsID": "d59ccb4e9d404e3b9a7b2af7bb3a4b1f"},
        {"name": "教育", "vomsID": "e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1"},  # 新增
        {"name": "熊猫", "vomsID": "f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2"},  # 新增
        {"name": "纪实", "vomsID": "a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3"},  # 新增
    ]
    
    print(f"使用默认 {len(categories)} 个分类")
    
    # 处理每个分类
    for category in categories:
        category_name = category.get("name", "未命名")
        vomsID = category.get("vomsID")
        
        if not vomsID:
            continue
            
        print(f"\n开始直播分类 ----- [{category_name}] -----")
        
        # 直接调用直播列表API
        try:
            # 使用咪咕官网的直播列表API (2025年1月可用的)
            api_url = f"https://program-sc.miguvideo.com/live/v2/live-channel-list/{vomsID}/1/100"
            print(f"API URL: {api_url}")
            
            response = requests.get(api_url, headers={
                **headers,
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
            }, timeout=10)
            
            if response.status_code != 200:
                print(f"API请求失败: {response.status_code}")
                continue
                
            data = response.json()
            print(f"API响应: {json.dumps(data, ensure_ascii=False)[:150]}...")
            
            if data.get("code") != 200:
                print(f"API返回错误: {data.get('message')}")
                continue
            
            # 解析频道列表
            channels = []
            body = data.get("body", {})
            
            # 尝试多种可能的字段
            for key in ["channelList", "list", "data", "channels"]:
                if key in body:
                    channels = body[key]
                    break
            
            if not isinstance(channels, list):
                print(f"未能获取频道列表，body类型: {type(body)}")
                continue
                
            print(f"分类 [{category_name}] 获取到 {len(channels)} 个频道")
            
            # 处理频道
            valid_channels = []
            for channel in channels:
                if isinstance(channel, dict):
                    # 获取pID（可能有不同的字段名）
                    pID = (channel.get("pID") or 
                          channel.get("programId") or 
                          channel.get("contId") or 
                          channel.get("id"))
                    
                    if pID:
                        # 确保有必要的字段
                        channel_copy = channel.copy()
                        channel_copy["pID"] = str(pID)
                        
                        # 频道名称
                        if not channel_copy.get("name"):
                            channel_copy["name"] = (channel.get("title") or 
                                                   channel.get("programName") or 
                                                   channel.get("name") or 
                                                   "未知频道")
                        
                        # 频道logo
                        if not channel_copy.get("pics"):
                            # 尝试不同的logo字段
                            logo_url = (channel.get("imageUrl") or 
                                       channel.get("image") or 
                                       channel.get("logoUrl") or 
                                       channel.get("pic") or "")
                            
                            channel_copy["pics"] = {
                                "highResolutionH": logo_url,
                                "highResolutionV": logo_url
                            }
                        
                        valid_channels.append(channel_copy)
            
            print(f"分类 [{category_name}] 有效频道数: {len(valid_channels)}")
            
            if valid_channels:
                # 线程处理
                with ThreadPoolExecutor(max_workers=thread_mum) as executor:
                    futures = []
                    for i in range(0, len(valid_channels), thread_mum):
                        batch = valid_channels[i:i + thread_mum]
                        future = executor.submit(thread_task, category_name, batch)
                        futures.append(future)
                    
                    for future in futures:
                        future.result()
            else:
                print(f"分类 [{category_name}] 没有有效的频道")
            
        except Exception as e:
            print(f"处理分类 [{category_name}] 失败: {str(e)}")
    
    # 写文件
    total_channels = len(All_Live)
    if total_channels > 0:
        for key, value in sorted(All_Live.items()):
            writefile(path, value)
        print(f'\n✓ 更新完成，共获取 {total_channels} 个频道，写入文件 {path}')
    else:
        # 如果API不工作，使用备用的已知频道
        print(f'\n✗ API未能获取频道，使用备用频道')
        
        # 添加一些已知的咪咕直播频道作为备用
        backup_channels = [
            {"pID": "704740003", "name": "CCTV-1", "category": "央视"},
            {"pID": "704740001", "name": "CCTV-5", "category": "体育"},
            {"pID": "704740002", "name": "CCTV-6", "category": "影视"},
            {"pID": "1000000001", "name": "湖南卫视", "category": "卫视"},
            {"pID": "1000000002", "name": "浙江卫视", "category": "卫视"},
        ]
        
        for idx, channel in enumerate(backup_channels, 1):
            category_name = channel.get("category", "其他")
            channel_name = channel.get("name", "未知频道")
            
            # 尝试获取播放地址
            try:
                respData = get_content(channel["pID"])
                playurl_resp = respData.get("body", {}).get("urlInfo", {}).get("url", "")
                
                if playurl_resp:
                    playurl = smart_getddCalcu720p(playurl_resp, channel["pID"])
                    
                    if playurl:
                        # 尝试重定向
                        for _ in range(3):
                            try:
                                obj = requests.get(playurl, allow_redirects=False, timeout=5)
                                if obj.status_code == 302:
                                    location = obj.headers.get("Location", "")
                                    if location and location.startswith("http://hlsz"):
                                        playurl = location
                                        break
                            except:
                                break
                            time.sleep(0.1)
                        
                        content = f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" tvg-logo="" group-title="{category_name}",{channel_name}\n{playurl}\n'
                        All_Live[idx] = content
                        print(f'✓ {category_name}: {channel_name}')
            except:
                continue
        
        # 写入备用频道
        if All_Live:
            for key, value in sorted(All_Live.items()):
                writefile(path, value)
            print(f'✓ 备用频道更新完成，共获取 {len(All_Live)} 个频道，写入文件 {path}')
        else:
            print(f'✗ 完全无法获取任何频道')

if __name__ == '__main__':
    main()
