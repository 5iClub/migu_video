import requests
import json
import time
import random
import hashlib
import re
import base64
from datetime import datetime

# 基本配置
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.miguvideo.com/",
    "Origin": "https://www.miguvideo.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

# 所有分类配置
lives = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']

# 分类ID配置（可能已更新）
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

# 备用分类ID（以防原ID失效）
LIVE_BACKUP = {
    '热门': 'all',
    '央视': 'cctv',
    '卫视': 'ws',
    '地方': 'local',
    '体育': 'sports',
    '影视': 'movie',
    '综艺': 'variety',
    '少儿': 'children',
    '新闻': 'news',
    '教育': 'education',
    '熊猫': 'panda',
    '纪实': 'documentary'
}

path = 'migu.txt'
appVersion = "2600034600"

def md5(text):
    """MD5加密"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def getSaltAndSign(pid):
    """生成salt和sign"""
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + pid + appVersion[:8]
    sign = md5(md5(app_t) + suffix)
    return {"salt": salt, "sign": sign, "timestamp": timestamp}

def simple_request(url, headers=None, timeout=10, retry=2):
    """简化的请求函数"""
    for i in range(retry):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            elif i < retry - 1:
                time.sleep(1)
        except Exception as e:
            if i < retry - 1:
                time.sleep(1)
    return None

def get_play_url_v1(pid):
    """原始方法获取播放URL"""
    try:
        result = getSaltAndSign(pid)
        rateType = "2" if pid == "608831231" else "3"
        
        params = {
            "sign": result["sign"],
            "rateType": rateType,
            "contId": pid,
            "timestamp": result["timestamp"],
            "salt": result["salt"]
        }
        
        api_url = "https://play.miguvideo.com/playurl/v1/play/playurl"
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "000000" and "body" in data:
                return data["body"]["urlInfo"]["url"]
    except Exception as e:
        print(f"原始接口异常: {e}")
    
    return None

def get_play_url_v2(pid):
    """方法2：使用新版API"""
    try:
        # 新版API接口
        api_url = "https://webapi.miguvideo.com/gateway/playurl/v3/play/playurl"
        
        params = {
            "contId": pid,
            "rateType": "3",
            "playerType": "3",
            "clientType": "1",
            "platform": "2",
            "deviceid": "",
            "usertype": "",
            "version": "2.0"
        }
        
        custom_headers = headers.copy()
        custom_headers.update({
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
        })
        
        response = requests.get(api_url, params=params, headers=custom_headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # 多层尝试获取URL
            url_paths = [
                data.get("body", {}).get("urlInfo", {}).get("url"),
                data.get("data", {}).get("urlInfo", {}).get("url"),
                data.get("body", {}).get("playUrl"),
                data.get("data", {}).get("playUrl"),
                data.get("urlInfo", {}).get("url"),
                data.get("url"),
            ]
            
            for url in url_paths:
                if url and isinstance(url, str) and url.startswith("http"):
                    return url
                    
    except Exception as e:
        print(f"新版API异常: {e}")
    
    return None

def get_play_url_v3(pid):
    """方法3：使用移动端接口"""
    try:
        url = f"https://wap.miguvideo.com/migu/liveroom/room/queryLiveInfo?liveId={pid}"
        
        mobile_headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Referer": "https://wap.miguvideo.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9"
        }
        
        response = requests.get(url, headers=mobile_headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "0":
                return data.get("data", {}).get("liveUrl")
                
    except Exception as e:
        print(f"移动接口异常: {e}")
    
    return None

def get_play_url_v4(pid):
    """方法4：使用公开直播接口"""
    try:
        url = f"https://webapi.miguvideo.com/front/mobile/livePlay/getLivePlayUrl?liveChannelId={pid}"
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "0":
                streams = data.get("data", {}).get("streams", [])
                if streams:
                    return streams[0].get("playUrl")
                    
    except Exception as e:
        print(f"公开接口异常: {e}")
    
    return None

def get_play_url_v5(pid):
    """方法5：使用页面解析"""
    try:
        # 访问播放页面
        page_url = f"https://www.miguvideo.com/mgs/website/prd/play.html?cid={pid}"
        
        page_headers = headers.copy()
        page_headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1"
        })
        
        response = requests.get(page_url, headers=page_headers, timeout=15)
        
        if response.status_code == 200:
            html = response.text
            
            # 在HTML中搜索播放URL
            url_patterns = [
                r'http[s]?://[^\s"\'<>]+\.m3u8[^\s"\']*',
                r'"url"\s*:\s*"([^"]+)"',
                r'playUrl\s*=\s*["\']([^"\']+)["\']',
                r'src="(http[^"]+\.m3u8)"',
                r'https?://\S+?miguvideo\.com\S+?\.m3u8\S*'
            ]
            
            for pattern in url_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    url = matches[0]
                    if url.startswith('//'):
                        url = 'https:' + url
                    return url
                    
            # 搜索JSON数据
            json_pattern = r'window\.__PRELOADED_STATE__\s*=\s*({.*?});'
            matches = re.findall(json_pattern, html, re.DOTALL)
            if matches:
                try:
                    data = json.loads(matches[0])
                    # 尝试在JSON中查找播放地址
                    def find_url(obj):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if isinstance(v, str) and ('.m3u8' in v or 'playurl' in v.lower()):
                                    if v.startswith('http') or v.startswith('//'):
                                        return v
                                elif isinstance(v, (dict, list)):
                                    result = find_url(v)
                                    if result:
                                        return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_url(item)
                                if result:
                                    return result
                        return None
                    
                    url = find_url(data)
                    if url:
                        if url.startswith('//'):
                            url = 'https:' + url
                        return url
                except:
                    pass
                    
    except Exception as e:
        print(f"页面解析异常: {e}")
    
    return None

def get_play_url(pid):
    """综合获取播放URL，尝试多种方法"""
    if not pid or not pid.strip():
        return None
    
    # 如果pid是数字，尝试多种格式
    if pid.isdigit():
        formats_to_try = [pid, f"LIVE_{pid}", f"live-{pid}", pid.zfill(9)]
    else:
        formats_to_try = [pid]
    
    # 所有可用方法
    methods = [
        get_play_url_v5,  # 页面解析（最可能有效）
        get_play_url_v4,  # 公开接口
        get_play_url_v3,  # 移动端接口
        get_play_url_v2,  # 新版API
        get_play_url_v1,  # 原始方法
    ]
    
    for pid_format in formats_to_try:
        for method_idx, method in enumerate(methods, 1):
            try:
                url = method(pid_format)
                if url and url.startswith('http'):
                    # 验证URL是否有效
                    if any(ext in url.lower() for ext in ['.m3u8', 'playurl', 'miguvideo']):
                        print(f"    方法{method_idx}成功获取到URL")
                        return url
            except Exception as e:
                continue
            time.sleep(0.5)
        time.sleep(1)
    
    return None

def process_single_channel(category, channel_data, retry=2):
    """处理单个频道"""
    try:
        name = channel_data.get("name", "未知频道")
        pid = channel_data.get("pID", channel_data.get("contId", ""))
        
        if not pid:
            # 尝试从其他字段获取ID
            pid = channel_data.get("liveId", channel_data.get("channelId", ""))
        
        if not pid:
            print(f"  {name}: ✗ 无有效ID")
            return None
        
        print(f"  处理: {name}")
        
        # 获取播放URL
        play_url = None
        for attempt in range(retry):
            play_url = get_play_url(pid)
            if play_url:
                break
            if attempt < retry - 1:
                time.sleep(1)
        
        if not play_url:
            print(f"  {name}: ✗ 获取URL失败")
            return None
        
        # 处理URL格式
        if play_url.startswith('//'):
            play_url = 'https:' + play_url
        
        # 验证URL
        if not play_url.startswith('http'):
            print(f"  {name}: ✗ URL格式无效")
            return None
        
        # 获取logo
        logo = ""
        if "pics" in channel_data:
            pics = channel_data["pics"]
            logo = pics.get("highResolutionH", 
                          pics.get("smallResolutionH", 
                                  pics.get("picUrl", "")))
        elif "imageUrl" in channel_data:
            logo = channel_data["imageUrl"]
        elif "logo" in channel_data:
            logo = channel_data["logo"]
        
        # 生成M3U条目
        channel_line = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{category}",{name}\n{play_url}\n'
        print(f"  {name}: ✓")
        return channel_line
        
    except Exception as e:
        print(f"  {name}: ✗ 处理异常 ({str(e)[:30]})")
        return None

def process_category(category, category_id, max_channels=20):
    """处理一个分类"""
    print(f"━ 处理分类: {category}")
    
    channels = []
    
    # 尝试多种API接口获取频道列表
    api_endpoints = [
        # 原始接口
        f'https://program-sc.miguvideo.com/live/v2/tv-data/{category_id}',
        # 新版接口
        f'https://webapi.miguvideo.com/front/mobile/liveChannel/queryLiveChannel?channelType={category_id}',
        # 移动端接口
        f'https://wap.miguvideo.com/migu/liveroom/channel/queryChannelList?channelType={category_id}',
        # 通用接口
        f'https://webapi.miguvideo.com/gateway/live/v2/channel/list?type={category_id}',
    ]
    
    channel_list = []
    
    for api_url in api_endpoints:
        try:
            data = simple_request(api_url, headers=headers)
            if data:
                # 尝试不同数据格式
                if "body" in data and "dataList" in data["body"]:
                    channel_list = data["body"]["dataList"]
                    break
                elif "data" in data and isinstance(data["data"], list):
                    channel_list = data["data"]
                    break
                elif "list" in data:
                    channel_list = data["list"]
                    break
        except:
            continue
    
    # 如果原始接口失败，尝试备用接口
    if not channel_list and category in LIVE_BACKUP:
        backup_id = LIVE_BACKUP[category]
        backup_urls = [
            f'https://webapi.miguvideo.com/front/mobile/liveChannel/queryLiveChannel?channelType={backup_id}',
            f'https://wap.miguvideo.com/migu/liveroom/channel/queryChannelList?channelType={backup_id}',
        ]
        
        for api_url in backup_urls:
            try:
                data = simple_request(api_url, headers=headers)
                if data:
                    if "data" in data and isinstance(data["data"], list):
                        channel_list = data["data"]
                        break
                    elif "list" in data:
                        channel_list = data["list"]
                        break
            except:
                continue
    
    if not channel_list:
        print(f"  获取频道列表失败")
        return channels
    
    # 限制处理数量
    if len(channel_list) > max_channels:
        if category == "热门":
            limit = max_channels * 2
        else:
            limit = max_channels
        channel_list = channel_list[:limit]
    
    print(f"  发现 {len(channel_list)} 个频道")
    
    # 处理每个频道
    success_count = 0
    for idx, channel in enumerate(channel_list, 1):
        result = process_single_channel(category, channel)
        if result:
            channels.append(result)
            success_count += 1
        
        # 控制处理速度
        if idx % 3 == 0:
            time.sleep(0.5)
    
    print(f"  完成 {success_count}/{len(channel_list)} 个频道")
    return channels

def main():
    """主函数"""
    print("=" * 60)
    print("开始更新咪咕直播源")
    print("当前时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    start_time = time.time()
    
    # 写入M3U文件头
    m3u_header = '''#EXTM3U x-tvg-url="https://raw.githubusercontent.com/develop202/migu_video/main/playback.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"

'''
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(m3u_header)
    except Exception as e:
        print(f"写入文件失败: {e}")
        return
    
    all_channels = []
    category_stats = {}
    
    # 处理每个分类
    for category in lives:
        if category not in LIVE:
            continue
            
        print(f"\n▶ 开始处理: {category}")
        
        # 尝试多种ID格式
        category_ids = [LIVE[category]]
        if category in LIVE_BACKUP:
            category_ids.append(LIVE_BACKUP[category])
        
        category_channels = []
        for cat_id in category_ids:
            channels = process_category(category, cat_id, max_channels=15)
            if channels:
                category_channels = channels
                break
        
        if category_channels:
            # 添加分类分隔标识
            all_channels.append(f'\n# 分类: {category}\n')
            all_channels.extend(category_channels)
            category_stats[category] = len(category_channels)
        else:
            category_stats[category] = 0
        
        # 分类间延时
        if category != "纪实":
            time.sleep(1)
    
    # 写入所有频道到文件
    if all_channels:
        try:
            with open(path, 'a', encoding='utf-8') as f:
                for channel in all_channels:
                    f.write(channel)
            
            # 统计结果
            print(f"\n" + "="*60)
            print("更新完成！统计结果：")
            print("-"*60)
            
            total_success = 0
            for cat in lives:
                if cat in category_stats:
                    count = category_stats[cat]
                    if count > 0:
                        bar_length = min(count // 2, 20)
                        bar = "█" * bar_length
                        print(f"{cat:5} | {bar:20} {count:3d} 个")
                        total_success += count
                    else:
                        print(f"{cat:5} | {'×':20} 0   个")
            
            print("-"*60)
            bar_length = min(total_success // 5, 20)
            bar = "█" * bar_length
            print(f"总计 | {bar:20} {total_success:3d} 个频道")
            
            # 计算文件大小
            import os
            file_size = os.path.getsize(path)
            print(f"\n文件大小: {file_size / 1024:.1f} KB")
            print(f"保存到: {os.path.abspath(path)}")
            
        except Exception as e:
            print(f"\n写入文件失败: {e}")
    else:
        print(f"\n" + "="*60)
        print("更新失败，未获取到任何频道")
        print("可能原因：")
        print("1. 网络连接问题")
        print("2. API接口已更新")
        print("3. 需要验证或Cookie")
        print("=" * 60)
    
    end_time = time.time()
    print(f"\n总运行时间: {end_time - start_time:.1f} 秒")
    print("=" * 60)

def test_individual_channels():
    """测试几个关键频道"""
    print("开始测试关键频道...")
    print("-" * 60)
    
    test_channels = [
        {"name": "CCTV1", "pID": "608831231", "category": "央视"},
        {"name": "湖南卫视", "pID": "608831232", "category": "卫视"},
        {"name": "CCTV5", "pID": "608834000", "category": "体育"},
    ]
    
    success_count = 0
    for test in test_channels:
        print(f"测试: {test['name']} (ID: {test['pID']})")
        url = get_play_url(test['pID'])
        if url:
            print(f"  成功: {url[:80]}...")
            success_count += 1
        else:
            print(f"  失败")
        print("-" * 40)
        time.sleep(1)
    
    print(f"\n测试结果: {success_count}/{len(test_channels)} 个频道成功")
    return success_count > 0

if __name__ == "__main__":
    # 设置全局超时
    import socket
    socket.setdefaulttimeout(20)
    
    # 先测试单个频道
    if test_individual_channels():
        print("\n测试成功，开始完整更新...")
        main()
    else:
        print("\n单个频道测试失败，直接尝试完整更新...")
        print("如果仍然失败，请检查网络或API接口状态")
        main()
