import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

thread_num = 5  # 降低线程数避免被限制

# 基础请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://m.miguvideo.com",
    "Referer": "https://m.miguvideo.com/",
    "appCode": "miguvideo_default_h5",
    "appId": "miguvideo",
    "channel": "H5",
    "terminalId": "h5"
}

# 频道分类ID
LIVE_CATEGORIES = {
    '热门': 'e7716fea6aa1483c80cfc10b7795fcb8',
    '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05',
    '卫视': '0847b3f6c08a4ca28f85ba5701268424',
    '地方': '855e9adc91b04ea18ef3f2dbd43f495b',
    '体育': '7538163cdac044398cb292ecf75db4e0',
    '影视': '10b0d04cb23d4ac5945c4bc77c7ac44e',
    '综艺': '192a12edfef04b5eb616b878f031f32f',
    '少儿': 'fc2f5b8fd7db43ff88c4243e731ecede',
    '新闻': 'c584f67ad63f4bc983c31de3a9be977c',
    '教育': 'af72267483d94275995a4498b2799ecd',
    '熊猫': 'e76e56e88fff4c11b0168f55e826445d',
    '纪实': 'e1165138bdaa44b9a3138d74af6c6673'
}

path = 'migu_live.m3u8'
appVersion = "2600034600"


def md5(text):
    """MD5加密"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def generate_sign(contId):
    """生成签名参数"""
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    
    # 签名算法
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + contId + appVersion[:8]
    sign = md5(md5(app_t) + suffix)
    
    return {
        "timestamp": timestamp,
        "salt": salt,
        "sign": sign
    }


def get_channel_list(category_id):
    """获取频道列表"""
    url = f"https://program-sc.miguvideo.com/live/v2/tv-data/{category_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200 and "body" in data:
                return data["body"].get("dataList", [])
        return []
    except Exception as e:
        print(f"获取频道列表失败: {e}")
        return []


def get_stream_url(contId):
    """获取直播流地址"""
    try:
        # 生成签名
        sign_params = generate_sign(contId)
        
        # 请求参数
        params = {
            "contId": contId,
            "rateType": "3",  # 3=720p, 4=1080p
            "timestamp": sign_params["timestamp"],
            "salt": sign_params["salt"],
            "sign": sign_params["sign"]
        }
        
        # 请求头（添加必要参数）
        stream_headers = {
            "User-Agent": headers["User-Agent"],
            "Accept": "application/json",
            "appCode": "miguvideo_default_h5",
            "appId": "miguvideo",
            "channel": "H5",
            "terminalId": "h5",
            "Support-Pendant": "1"
        }
        
        url = "https://play.miguvideo.com/playurl/v1/play/playurl"
        response = requests.get(url, headers=stream_headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                # 获取流地址
                url_info = data.get("body", {}).get("urlInfo", {})
                stream_url = url_info.get("url", "")
                
                if stream_url:
                    # 解析真正的m3u8地址
                    final_url = resolve_stream_url(stream_url)
                    if final_url:
                        return final_url
        
        return None
        
    except Exception as e:
        print(f"获取流地址异常: {e}")
        return None


def resolve_stream_url(stream_url):
    """解析最终的流地址"""
    try:
        # 第一次请求，获取重定向
        response = requests.get(stream_url, headers=headers, allow_redirects=False, timeout=10)
        
        if response.status_code in [301, 302]:
            location = response.headers.get("Location")
            if location:
                # 如果已经是m3u8地址，直接返回
                if location.endswith('.m3u8') or 'hls' in location:
                    return location
                
                # 继续跟随重定向
                for _ in range(5):
                    resp = requests.get(location, headers=headers, allow_redirects=False, timeout=10)
                    if resp.status_code in [301, 302]:
                        location = resp.headers.get("Location")
                        if location and (location.endswith('.m3u8') or 'hls' in location):
                            return location
                    else:
                        break
        
        # 如果没有重定向或无法获取，尝试直接请求
        resp = requests.get(stream_url, headers=headers, timeout=10)
        if resp.status_code == 200 and resp.text:
            # 检查是否是m3u8内容
            if '#EXTM3U' in resp.text:
                return stream_url
        
        return None
        
    except Exception as e:
        print(f"解析流地址失败: {e}")
        return None


def process_channel(category, channel):
    """处理单个频道"""
    try:
        channel_name = channel.get("name", "")
        cont_id = channel.get("contId") or channel.get("pID")
        
        if not cont_id:
            return None
        
        print(f"正在获取 [{category}] - {channel_name}...")
        
        # 获取流地址
        stream_url = get_stream_url(cont_id)
        
        if stream_url:
            # 获取频道图标
            logo = ""
            if "pics" in channel:
                logo = channel["pics"].get("highResolutionH", "")
            
            # 生成M3U8条目
            m3u8_line = f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" tvg-logo="{logo}" group-title="{category}",{channel_name}\n{stream_url}\n'
            print(f"✓ [{category}] {channel_name} 获取成功")
            return m3u8_line
        else:
            print(f"✗ [{category}] {channel_name} 获取失败")
            return None
            
    except Exception as e:
        print(f"✗ [{category}] {channel_name} 处理异常: {e}")
        return None


def main():
    """主函数"""
    print("=" * 50)
    print("开始获取Migu直播源")
    print("=" * 50)
    
    # 写入M3U8文件头
    m3u_header = '#EXTM3U\n'
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(m3u_header)
    
    all_channels = []
    total = 0
    success = 0
    
    # 遍历所有分类
    for category, category_id in LIVE_CATEGORIES.items():
        print(f"\n正在获取 [{category}] 分类的频道列表...")
        
        # 获取频道列表
        channels = get_channel_list(category_id)
        
        if not channels:
            print(f"[{category}] 分类暂无频道数据")
            continue
        
        print(f"[{category}] 共找到 {len(channels)} 个频道")
        
        # 使用线程池处理频道
        with ThreadPoolExecutor(max_workers=thread_num) as executor:
            futures = []
            for channel in channels:
                future = executor.submit(process_channel, category, channel)
                futures.append(future)
            
            # 收集结果
            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_channels.append(result)
                    success += 1
                total += 1
                
                # 显示进度
                if total % 10 == 0:
                    print(f"进度: {success}/{total} 成功")
        
        print(f"[{category}] 分类完成，成功 {success}/{total}")
    
    # 写入所有频道
    print("\n正在写入文件...")
    with open(path, 'a', encoding='utf-8') as f:
        for channel_line in all_channels:
            f.write(channel_line)
    
    print("\n" + "=" * 50)
    print(f"完成！成功获取 {success}/{total} 个频道")
    print(f"文件保存至: {path}")
    print("=" * 50)
    
    # 输出一些示例
    if all_channels:
        print("\n示例频道地址:")
        for i, line in enumerate(all_channels[:5]):
            print(f"{i+1}. {line.split('\\n')[0]}")


if __name__ == "__main__":
    main()
