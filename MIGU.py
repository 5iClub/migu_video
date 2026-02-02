import requests
import json
import time
import random
import hashlib
from datetime import datetime

# 基本配置
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Referer": "https://m.miguvideo.com/",
    "Origin": "https://m.miguvideo.com"
}

# 分类配置（只保留主要分类，避免超时）
lives = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']
LIVE = {'热门': 'e7716fea6aa1483c80cfc10b7795fcb8', '体育': '7538163cdac044398cb292ecf75db4e0',
        '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05', '卫视': '0847b3f6c08a4ca28f85ba5701268424',
        '地方': '855e9adc91b04ea18ef3f2dbd43f495b', '影视': '10b0d04cb23d4ac5945c4bc77c7ac44e',
        '新闻': 'c584f67ad63f4bc983c31de3a9be977c', '教育': 'af72267483d94275995a4498b2799ecd',
        '熊猫': 'e76e56e88fff4c11b0168f55e826445d', '综艺': '192a12edfef04b5eb616b878f031f32f',
        '少儿': 'fc2f5b8fd7db43ff88c4243e731ecede', '纪实': 'e1165138bdaa44b9a3138d74af6c6673'}

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
                print(f"请求失败，正在重试... ({e})")
                time.sleep(1)
            else:
                print(f"请求最终失败: {e}")
    return None

def get_play_url(pid):
    """获取播放URL（简化版）"""
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
        response = requests.get(api_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "000000" and "body" in data:
                return data["body"]["urlInfo"]["url"]
    except Exception as e:
        print(f"获取播放URL失败 (PID: {pid}): {e}")
    
    return None

def process_single_channel(category, channel_data):
    """处理单个频道"""
    try:
        name = channel_data.get("name", "未知频道")
        pid = channel_data.get("pID", "")
        
        if not pid:
            return None
        
        print(f"  正在处理: {name}")
        
        # 获取播放URL
        play_url = get_play_url(pid)
        if not play_url:
            return None
        
        # 尝试获取重定向URL（简化逻辑）
        final_url = play_url
        try:
            resp = requests.get(play_url, allow_redirects=False, timeout=5)
            if "Location" in resp.headers:
                location = resp.headers["Location"]
                if location and location.startswith("http"):
                    final_url = location
        except:
            pass  # 保持原URL
        
        # 获取logo
        logo = ""
        if "pics" in channel_data:
            pics = channel_data["pics"]
            logo = pics.get("highResolutionH", pics.get("smallResolutionH", ""))
        
        # 生成M3U条目
        return f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{category}",{name}\n{final_url}\n'
        
    except Exception as e:
        print(f"  处理失败: {name} - {str(e)[:50]}")
        return None

def process_category(category, category_id):
    """处理一个分类"""
    print(f"处理分类: {category}")
    
    channels = []
    try:
        # 获取分类数据
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{category_id}'
        data = simple_request(url, headers=headers)
        
        if not data or "body" not in data or "dataList" not in data["body"]:
            print(f"  获取数据失败")
            return []
        
        channel_list = data["body"]["dataList"]
        print(f"  发现 {len(channel_list)} 个频道")
        
        # 限制处理数量，避免运行时间过长
        max_channels = 30
        if len(channel_list) > max_channels:
            print(f"  限制处理前 {max_channels} 个频道")
            channel_list = channel_list[:max_channels]
        
        # 逐个处理频道
        success_count = 0
        for idx, channel in enumerate(channel_list, 1):
            result = process_single_channel(category, channel)
            if result:
                channels.append(result)
                success_count += 1
            
            # 每处理3个频道休息一下
            if idx % 3 == 0:
                time.sleep(0.5)
        
        print(f"  成功处理 {success_count}/{len(channel_list)} 个频道")
        return channels
        
    except Exception as e:
        print(f"  处理分类异常: {e}")
        return []

def main():
    """主函数"""
    print("=" * 60)
    print("开始更新咪咕直播源")
    print("=" * 60)
    
    start_time = time.time()
    
    # 写入M3U文件头
    m3u_header = '''#EXTM3U x-tvg-url="https://raw.githubusercontent.com/develop202/migu_video/main/playback.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"
'''
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(m3u_header)
        print("已写入M3U文件头")
    except Exception as e:
        print(f"写入文件失败: {e}")
        return
    
    all_channels = []
    total_success = 0
    
    # 处理每个分类
    for category in lives:
        if category not in LIVE:
            continue
            
        category_channels = process_category(category, LIVE[category])
        if category_channels:
            # 添加分类分隔标识
            all_channels.append(f'\n# 分类: {category}\n')
            all_channels.extend(category_channels)
            total_success += len(category_channels)
        
        # 分类间延时
        time.sleep(1.5)
    
    # 写入所有频道到文件
    if all_channels:
        try:
            with open(path, 'a', encoding='utf-8') as f:
                for channel in all_channels:
                    f.write(channel)
            
            print(f"\n{'='*60}")
            print(f"更新成功！")
            print(f"总处理频道数: {total_success}")
            
            # 计算文件大小
            import os
            file_size = os.path.getsize(path)
            print(f"生成文件大小: {file_size / 1024:.1f} KB")
            
        except Exception as e:
            print(f"\n写入文件失败: {e}")
    else:
        print(f"\n{'='*60}")
        print("更新失败，未获取到任何频道")
    
    end_time = time.time()
    print(f"总运行时间: {end_time - start_time:.1f} 秒")
    print("=" * 60)

if __name__ == "__main__":
    # 设置全局超时和重试
    import socket
    socket.setdefaulttimeout(15)
    
    # 执行主函数
    main()
