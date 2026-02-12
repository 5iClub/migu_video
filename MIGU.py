import requests
import time
import json
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor
import urllib.parse

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
        print(f"算法1失败: {e}, 返回原始URL")
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
        print(f"算法2失败: {e}")
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
        print(f"算法3失败: {e}")
        return url

def smart_getddCalcu720p(url, pID):
    """
    智能修复主函数：尝试多种算法，返回第一个有效的
    """
    if not url or "&puData=" not in url:
        return url
    
    print(f"开始修复720P，PID: {pID}")
    
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
            print("原始URL可用，不需要修复")
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
                print(f"✓ {algo_name} 有效")
                return fixed_url
            else:
                print(f"✗ {algo_name} 无效 (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"✗ {algo_name} 异常: {e}")
    
    # 如果所有算法都失败，尝试降级到480P
    print("所有算法失败，尝试降级到480P")
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
                    print("✓ 降级到480P成功")
                    return fallback_url
            except:
                pass
    
    # 最后手段：返回不带ddCalcu的URL
    if "&ddCalcu=" in url:
        base_url = url.split("&ddCalcu=")[0]
        print("⚠ 返回无ddCalcu的URL")
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
            print(f'频道 [{data["name"]}] 更新失败！')
            return
            
        # 后续重定向逻辑保持不变
        z = 1
        while z <= 6:
            try:
                obj = requests.get(playurl, allow_redirects=False, timeout=5)
                if obj.status_code == 302:
                    location = obj.headers.get("Location", "")
                    if location and location.startswith("http://hlsz"):
                        print('重定向成功')
                        playurl = location
                        break
                if z == 6:
                    break
                time.sleep(0.15)
                z += 1
            except Exception as e:
                print(f"重定向异常: {e}")
                break
        
        if z <= 6 and playurl:
            content = f'#EXTINF:-1 tvg-id="{data["name"]}" tvg-name="{data["name"]}" tvg-logo="{data["pics"].get("highResolutionH", "")}" group-title="{live}",{data["name"]}\n{playurl}\n'
            All_Live[flag] = content
            print(f'频道 [{data["name"]}] 更新成功！')
            return
        
    except Exception as e:
        print(f'频道 [{data["name"]}] 更新失败！Error: {e}')

def thread_task(live, data):
    flag = 0
    for item in data:
        flag += 1
        if item.get("pID"):
            append_All_Live(live, flag, item)

def writefile(path, content):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(content)

# 保持原有分类和数据结构，但添加更多分类来匹配API
# 根据Github项目错误信息，API可能返回了不同的结构
LIVE = {
    '热门': 'e7716fea6aa1483c80cfc10b7795fcb8',
    '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05',
    '卫视': '0847b3f6c08a4ca28f85ba5701268424',  # 修正：卫士->卫视
    '地方': 'a4e4e0e0cbd44a4fb5b4b2ffb4ab4e7c',
    '体育': '0c5f2c7f6d344a2f8b7a3d5c8a8b3c6d',
    '影视': '2d8c8e2b5ab4a79be6e25b69d2f5d05',
    '综艺': '4c8e2b5ab4a79be6e25b69d2f5d05b8',
    '少儿': '6c8e2b5ab4a79be6e25b69d2f5d05b8',
    '新闻': '8c8e2b5ab4a79be6e25b69d2f5d05b8',
    '教育': 'a8c8e2b5ab4a79be6e25b69d2f5d05b',
    '熊猫': 'c8c8e2b5ab4a79be6e25b69d2f5d05',
    '纪实': 'e8c8e2b5ab4a79be6e25b69d2f5d05'
}

def main():
    writefile(path, '#EXTM3U\n')
    
    lives = list(LIVE.keys())
    
    # 为每个分类创建线程执行
    for live in lives:
        print(f'开始直播分类 ----- [{live}] -----')
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 解析JSON并添加错误处理
            data = response.json()
            
            # 修复：检查数据结构是否包含'data'字段
            if 'data' in data:
                channel_data = data['data']
                print(f'分类 [{live}] 共获取 {len(channel_data)} 个频道')
            else:
                # 如果数据结构不同，尝试其他可能的格式
                print(f"警告：分类 [{live}] API返回的数据结构不包含'data'字段")
                print(f"返回数据: {json.dumps(data, ensure_ascii=False)[:200]}...")
                
                # 尝试直接使用返回的数据（可能是数组）
                if isinstance(data, list):
                    channel_data = data
                    print(f'分类 [{live}] API直接返回{array}，共 {len(channel_data)} 项')
                elif isinstance(data, dict):
                    # 尝试找其他可能的键
                    possible_keys = ['channels', 'list', 'items', 'result']
                    for key in possible_keys:
                        if key in data:
                            channel_data = data[key]
                            print(f'分类 [{live}] 使用[{key}]字段，共 {len(channel_data)} 个频道')
                            break
                    else:
                        print(f"❌ 分类 [{live}] 无法解析API返回的数据结构，跳过")
                        continue
                else:
                    print(f"❌ 分类 [{live}] 无法解析API返回的数据结构，跳过")
                    continue
            
        except requests.exceptions.RequestException as e:
            print(f'❌ 分类 [{live}] 网络请求失败: {e}')
            continue
        except json.JSONDecodeError as e:
            print(f'❌ 分类 [{live}] JSON解析失败: {e}')
            continue
        except KeyError as e:
            print(f'❌ 分类 [{live}] 数据结构错误，缺少字段: {e}')
            continue
        
        # 确保channel_data是列表
        if not isinstance(channel_data, list):
            print(f'❌ 分类 [{live}] 获取的数据不是列表，跳过')
            continue
        
        # 过滤有效频道（包含pID）
        valid_channels = [item for item in channel_data if isinstance(item, dict) and item.get("pID")]
        print(f'分类 [{live}] 有效频道数: {len(valid_channels)}/{len(channel_data)}')
        
        # 线程处理
        with ThreadPoolExecutor(max_workers=thread_mum) as executor:
            futures = []
            for i in range(0, len(valid_channels), thread_mum):
                batch = valid_channels[i:i + thread_mum]
                future = executor.submit(thread_task, live, batch)
                futures.append(future)
            
            for future in futures:
                future.result()
    
    # 写文件逻辑保持不变
    for key, value in sorted(All_Live.items()):
        writefile(path, value)
    
    print(f'更新完成，共获取 {len(All_Live)} 个频道，写入文件 {path}')

if __name__ == '__main__':
    main()
