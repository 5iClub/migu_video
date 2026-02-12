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
    
    print(f"修复720P: {pID[:6]}...")
    
    # 尝试的算法列表
    algorithms = [
        ("算法1", getddCalcu720p_fix1),
        ("算法2", getddCalcu720p_fix2),
        ("算法3", getddCalcu720p_fix3),
    ]
    
    # 先检查原始URL是否可用（带已有的ddCalcu）
    try:
        response = requests.head(url, timeout=3, allow_redirects=True)
        if response.status_code < 400:
            return url
    except:
        pass
    
    # 尝试每种算法
    for algo_name, algo_func in algorithms:
        try:
            fixed_url = algo_func(url, pID)
            
            # 测试修复后的URL
            response = requests.head(fixed_url, timeout=3, allow_redirects=True)
            
            if response.status_code < 400:
                return fixed_url
                
        except Exception:
            continue
    
    # 如果所有算法都失败，尝试降级到480P
    print(f"降级480P: {pID[:6]}...")
    if "rateType=3" in url:
        # 移除ddCalcu参数并降级到480P
        if "&ddCalcu=" in url:
            base_url = url.split("&ddCalcu=")[0]
        else:
            base_url = url
            
        # 替换rateType为2 (480P)
        if "rateType=3" in base_url:
            fallback_url = base_url.replace("rateType=3", "rateType=2")
            # 测试一下
            try:
                response = requests.head(fallback_url, timeout=3)
                if response.status_code < 400:
                    return fallback_url
            except:
                pass
    
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
            # print(f'频道 [{data["name"]}] 更新失败！')
            return
            
        # 后续重定向逻辑保持不变
        z = 1
        while z <= 6:
            try:
                obj = requests.get(playurl, allow_redirects=False, timeout=5)
                if obj.status_code == 302:
                    location = obj.headers.get("Location", "")
                    if location and location.startswith("http://hlsz"):
                        # print('重定向成功')
                        playurl = location
                        break
                if z == 6:
                    break
                time.sleep(0.15)
                z += 1
            except Exception as e:
                break
        
        if z <= 6 and playurl:
            content = f'#EXTINF:-1 tvg-id="{data["name"]}" tvg-name="{data["name"]}" tvg-logo="{data["pics"].get("highResolutionH", "")}" group-title="{live}",{data["name"]}\n{playurl}\n'
            All_Live[flag] = content
            print(f'✓ [{data["name"]}]')
            return
        
    except Exception as e:
        # print(f'频道 [{data["name"]}] 更新失败！Error: {e}')
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
    获取分类下的频道列表
    """
    try:
        # 新的API地址 - 获取分类下的频道
        url = f"https://program-sc.miguvideo.com/live/v2/tv-channel-list/{vomsID}/1/1000"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        # 新的数据结构
        if data.get("code") == 200:
            return data.get("body", {}).get("channelList", [])
        else:
            return None
            
    except Exception as e:
        print(f"获取频道列表失败: {e}")
        return None

def main():
    writefile(path, '#EXTM3U\n')
    
    # 先获取可用的直播分类
    print("获取直播分类...")
    categories_url = "https://program-sc.miguvideo.com/live/v2/tv-data/e7716fea6aa1483c80cfc10b7795fcb8"
    
    try:
        response = requests.get(categories_url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("code") != 200:
            print("获取分类失败")
            return
            
        categories = data.get("body", {}).get("liveList", [])
        
        if not categories:
            print("没有找到分类")
            return
            
        print(f"找到 {len(categories)} 个分类")
        
    except Exception as e:
        print(f"获取分类失败: {e}")
        return
    
    # 处理每个分类
    for category in categories:
        category_name = category.get("name", "未命名")
        vomsID = category.get("vomsID")
        
        if not vomsID:
            continue
            
        print(f"开始直播分类 ----- [{category_name}] -----")
        
        # 获取该分类下的频道列表
        channel_list = get_channel_list(vomsID)
        
        if not channel_list:
            print(f"分类 [{category_name}] 没有找到频道")
            continue
            
        print(f"分类 [{category_name}] 共获取 {len(channel_list)} 个频道")
        
        # 过滤有效频道
        valid_channels = []
        for channel in channel_list:
            if isinstance(channel, dict) and channel.get("pID"):
                # 确保频道有必要的字段
                if not channel.get("name"):
                    if channel.get("title"):
                        channel["name"] = channel["title"]
                    else:
                        channel["name"] = "未知频道"
                
                if not channel.get("pics"):
                    channel["pics"] = {"highResolutionH": ""}
                
                valid_channels.append(channel)
        
        print(f"分类 [{category_name}] 有效频道数: {len(valid_channels)}")
        
        if not valid_channels:
            continue
        
        # 线程处理
        with ThreadPoolExecutor(max_workers=thread_mum) as executor:
            futures = []
            for i in range(0, len(valid_channels), thread_mum):
                batch = valid_channels[i:i + thread_mum]
                future = executor.submit(thread_task, category_name, batch)
                futures.append(future)
            
            for future in futures:
                future.result()
    
    # 写文件
    total_channels = len(All_Live)
    if total_channels > 0:
        for key, value in sorted(All_Live.items()):
            writefile(path, value)
        print(f'✓ 更新完成，共获取 {total_channels} 个频道，写入文件 {path}')
    else:
        print(f'✗ 未能获取任何频道')

if __name__ == '__main__':
    main()
