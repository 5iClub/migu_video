import requests
import time
import json
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor

# 保持原线程命名
thread_mum = 10  # 线程

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
        # 提取puData
        if "&puData=" not in url:
            return url
            
        puData_part = url.split("&puData=")[1]
        puData = puData_part.split("&")[0]
        
        # 生成日期相关参数
        now = datetime.now()
        day_str = str(now.day).zfill(2)
        month_str = str(now.month).zfill(2)
        
        # 基础密钥（调整后的）
        keys = "cdabyzwxklnmopqrstuvwxyz0123456789"
        
        ddCalcu_chars = []
        puData_len = len(puData)
        
        # 改进的交叉算法
        # 先取末尾的几个字符
        start_pos = max(0, puData_len - 8)
        for i in range(min(8, puData_len)):
            pos = start_pos + i
            if pos < puData_len:
                ddCalcu_chars.append(puData[pos])
            
            # 在特定位置插入特殊字符
            if i == 1:
                ddCalcu_chars.append('v')
            elif i == 3:
                day_last = int(day_str[-1])
                key_idx = (day_last + int(pID[0]) if pID and len(pID) > 0 else day_last) % len(keys)
                ddCalcu_chars.append(keys[key_idx])
            elif i == 5 and len(pID) > 2:
                pID_idx = (int(pID[2]) if pID[2].isdigit() else 5) % len(keys)
                ddCalcu_chars.append(keys[pID_idx])
        
        # 补全到适当长度
        target_length = min(12, max(8, puData_len // 2))
        while len(ddCalcu_chars) < target_length:
            idx = (len(ddCalcu_chars) * 7) % len(keys)
            ddCalcu_chars.append(keys[idx])
        
        ddCalcu = "".join(ddCalcu_chars[:target_length])
        
        # 清理已有ddCalcu参数
        if "&ddCalcu=" in url:
            base_url = url.split("&ddCalcu=")[0]
        else:
            base_url = url
            
        new_url = f'{base_url}&ddCalcu={ddCalcu}&sv=10004&ct=android'
        return new_url
        
    except Exception as e:
        return url

def getddCalcu720p_fix2(url, pID):
    """
    修复方案2：尝试md5摘要算法
    """
    try:
        if "&puData=" not in url:
            return url
            
        puData_part = url.split("&puData=")[1]
        puData = puData_part.split("&")[0]
        
        # 使用MD5生成固定长度的字符串
        now = datetime.now()
        input_str = f"{puData}_{pID}_{now.strftime('%Y%m%d%H')}"
        
        md5_hash = hashlib.md5(input_str.encode()).hexdigest()
        
        # 取前12个字符作为ddCalcu
        ddCalcu = md5_hash[:12]
        
        # 清理已有ddCalcu参数
        if "&ddCalcu=" in url:
            base_url = url.split("&ddCalcu=")[0]
        else:
            base_url = url
            
        new_url = f'{base_url}&ddCalcu={ddCalcu}&sv=10004&ct=android'
        return new_url
        
    except Exception as e:
        return url

def getddCalcu720p_fix3(url, pID):
    """
    修复方案3：简单反转+固定字符
    """
    try:
        if "&puData=" not in url:
            return url
            
        puData_part = url.split("&puData=")[1]
        puData = puData_part.split("&")[0]
        
        # 简单反转puData
        reversed_part = puData[::-1]
        
        # 取前8个字符
        base_part = reversed_part[:8]
        
        # 添加固定字符
        fixed_chars = ['v', '2', 'a', '5']
        
        # 构建ddCalcu
        ddCalcu_list = []
        for i in range(12):
            if i < len(base_part):
                ddCalcu_list.append(base_part[i])
            else:
                fix_idx = (i - len(base_part)) % len(fixed_chars)
                ddCalcu_list.append(fixed_chars[fix_idx])
        
        ddCalcu = "".join(ddCalcu_list)[:12]
        
        # 清理已有ddCalcu参数
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
            
            # 测试修复后的URL
            response = requests.head(fixed_url, timeout=3, allow_redirects=True)
            
            if response.status_code < 400:
                return fixed_url
                
        except Exception:
            continue
    
    # 如果所有算法都失败，尝试降级到480P
    if "rateType=3" in url:
        # 移除ddCalcu参数并降级到480P
        if "&ddCalcu=" in url:
            base_url = url.split("&ddCalcu=")[0]
        else:
            base_url = url
            
        # 替换rateType为2 (480P)
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
        
        # 使用智能修复算法
        playurl_resp = respData.get("body", {}).get("urlInfo", {}).get("url", "")
        if playurl_resp:
            # 使用智能修复算法
            playurl = smart_getddCalcu720p(playurl_resp, data["pID"])
        else:
            playurl = playurl_resp
        
        if not playurl:
            return
            
        # 后续重定向逻辑保持不变
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
            # 获取频道名称和logo
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

def get_channel_list(vomsID):
    """
    修复：获取分类下的频道列表 - 尝试多种API
    """
    try:
        # 方案1：尝试原来的API
        url1 = f"https://program-sc.miguvideo.com/live/v2/tv-channel-list/{vomsID}/1/1000"
        response1 = requests.get(url1, headers=headers, timeout=5)
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"API方案1响应: {json.dumps(data1, ensure_ascii=False)[:100]}...")
            if data1.get("code") == 200:
                channel_list = data1.get("body", {}).get("channelList", [])
                if channel_list:
                    return channel_list
        
        # 方案2：尝试不同的API格式
        url2 = f"https://program-sc.miguvideo.com/live/v2/tv-channel-list?categoryId={vomsID}&pageNum=1&pageSize=1000"
        response2 = requests.get(url2, headers=headers, timeout=5)
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"API方案2响应: {json.dumps(data2, ensure_ascii=False)[:100]}...")
            if data2.get("code") == 200:
                channel_list = data2.get("body", {}).get("list", data2.get("body", {}).get("data", []))
                if channel_list:
                    return channel_list
        
        # 方案3：尝试搜索API
        url3 = f"https://program-sc.miguvideo.com/live/v2/search-channel?category={vomsID}&page=1&size=1000"
        response3 = requests.get(url3, headers=headers, timeout=5)
        
        if response3.status_code == 200:
            data3 = response3.json()
            print(f"API方案3响应: {json.dumps(data3, ensure_ascii=False)[:100]}...")
            if data3.get("code") == 200:
                channel_list = data3.get("body", {}).get("channels", [])
                if channel_list:
                    return channel_list
                
        return None
            
    except Exception as e:
        print(f"获取频道列表失败: {e}")
        return None

def main():
    writefile(path, '#EXTM3U\n')
    
    # 先获取可用的直播分类
    print("获取直播分类...")
    
    # 尝试多个可能的分类API
    category_apis = [
        "https://program-sc.miguvideo.com/live/v2/tv-category",
        "https://program-sc.miguvideo.com/live/v2/tv-data/e7716fea6aa1483c80cfc10b7795fcb8",
        "https://program-sc.miguvideo.com/live/v2/category-list",
    ]
    
    categories = []
    
    for api_url in category_apis:
        try:
            print(f"尝试API: {api_url}")
            response = requests.get(api_url, headers=headers, timeout=10)
            data = response.json()
            
            print(f"API响应: {json.dumps(data, ensure_ascii=False)[:200]}...")
            
            if data.get("code") == 200:
                # 尝试不同的数据结构
                body = data.get("body", {})
                
                # 方案1：直接从liveList获取
                if "liveList" in body:
                    categories = body.get("liveList", [])
                    print(f"从liveList获取到 {len(categories)} 个分类")
                    break
                    
                # 方案2：从categoryList获取
                elif "categoryList" in body:
                    categories = body.get("categoryList", [])
                    print(f"从categoryList获取到 {len(categories)} 个分类")
                    break
                    
                # 方案3：直接返回数组
                elif isinstance(body, list):
                    categories = body
                    print(f"直接获取到 {len(categories)} 个分类")
                    break
        
        except Exception as e:
            print(f"API {api_url} 失败: {e}")
            continue
    
    if not categories:
        print("无法获取分类，使用默认分类")
        # 使用已知的分类vomsID
        categories = [
            {"name": "央视", "vomsID": "1ff892f2b5ab4a79be6e25b69d2f5d05"},
            {"name": "卫视", "vomsID": "0847b3f6c08a4ca28f85ba5701268424"},
            {"name": "地方", "vomsID": "3fdbbd9cdad54f80ae9ff8def9aeb5c4"},
            {"name": "体育", "vomsID": "7538163cdac044398cb292ecf75db4e0"},
            {"name": "影视", "vomsID": "a28ccb4e9d404e3b9a7b2af7bb3a4b1c"},
            {"name": "综艺", "vomsID": "b39ccb4e9d404e3b9a7b2af7bb3a4b1d"},
            {"name": "少儿", "vomsID": "c49ccb4e9d404e3b9a7b2af7bb3a4b1e"},
            {"name": "新闻", "vomsID": "d59ccb4e9d404e3b9a7b2af7bb3a4b1f"},
        ]
    
    print(f"找到 {len(categories)} 个分类")
    
    # 处理每个分类
    for category in categories:
        category_name = category.get("name", "未命名")
        vomsID = category.get("vomsID")
        
        if not vomsID:
            continue
            
        print(f"\n开始直播分类 ----- [{category_name}] -----")
        
        # 直接获取该分类下的所有直播列表（使用搜索API）
        try:
            # 使用搜索API获取该分类下的所有频道
            search_url = f"https://program-sc.miguvideo.com/live/v2/search-channel?keyword=&categoryId={vomsID}&page=1&size=200"
            print(f"搜索URL: {search_url}")
            
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"搜索响应: {json.dumps(data, ensure_ascii=False)[:150]}...")
                
                if data.get("code") == 200:
                    # 尝试不同的数据结构
                    body = data.get("body", {})
                    
                    # 方案1：从channels获取
                    channels = body.get("channels", [])
                    if not channels:
                        # 方案2：从list获取
                        channels = body.get("list", [])
                    
                    if not channels:
                        # 方案3：从data获取（可能是列表）
                        channels_data = body.get("data", [])
                        if isinstance(channels_data, list):
                            channels = channels_data
                    
                    print(f"分类 [{category_name}] 搜索结果: {len(channels)} 个频道")
                    
                    # 处理频道
                    if channels:
                        valid_channels = []
                        
                        for channel in channels:
                            if isinstance(channel, dict):
                                # 获取pID（可能有不同的字段名）
                                pID = channel.get("pID") or channel.get("programId") or channel.get("contId")
                                if pID:
                                    # 确保有必要的字段
                                    channel_copy = channel.copy()
                                    channel_copy["pID"] = str(pID)
                                    
                                    if not channel_copy.get("name"):
                                        channel_copy["name"] = channel.get("title") or channel.get("programName") or "未知频道"
                                    
                                    if not channel_copy.get("pics"):
                                        channel_copy["pics"] = {
                                            "highResolutionH": channel.get("imageH") or channel.get("logo") or ""
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
            
        except Exception as e:
            print(f"处理分类 [{category_name}] 失败: {e}")
    
    # 写文件
    total_channels = len(All_Live)
    if total_channels > 0:
        for key, value in sorted(All_Live.items()):
            writefile(path, value)
        print(f'\n✓ 更新完成，共获取 {total_channels} 个频道，写入文件 {path}')
    else:
        print(f'\n✗ 未能获取任何频道')

if __name__ == '__main__':
    main()
