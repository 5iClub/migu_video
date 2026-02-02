import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os

# 基本配置
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Referer": "https://m.miguvideo.com/",
    "Origin": "https://m.miguvideo.com"
}

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


def format_date_ymd():
    """获取当前日期"""
    now = datetime.now()
    return f"{now.year}{now.month:02d}{now.day:02d}"


def get_content(pid):
    """简化的获取播放URL函数"""
    try:
        result = getSaltAndSign(pid)
        rateType = "2" if pid == "608831231" else "3"
        
        # 直接构造PlayURL请求
        params = {
            "sign": result["sign"],
            "rateType": rateType,
            "contId": pid,
            "timestamp": result["timestamp"],
            "salt": result["salt"]
        }
        
        # 使用更简单的User-Agent
        api_headers = {
            "User-Agent": "okhttp/4.9.0",
            "Accept": "application/json, text/plain, */*"
        }
        
        url = "https://play.miguvideo.com/playurl/v1/play/playurl"
        response = requests.get(url, params=params, headers=api_headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "000000" and "body" in data:
                return data["body"]["urlInfo"]["url"]
    except Exception as e:
        print(f"获取播放URL失败 (PID: {pid}): {e}")
    
    return None


def process_channel(live, channel_data):
    """处理单个频道"""
    try:
        name = channel_data.get("name", "未知")
        pid = channel_data.get("pID", "")
        
        if not pid:
            return None
        
        # 获取播放URL
        playurl = get_content(pid)
        if not playurl:
            return None
        
        # 简化重定向逻辑（只尝试1次）
        try:
            resp = requests.get(playurl, allow_redirects=False, timeout=5)
            if "Location" in resp.headers:
                redir_url = resp.headers["Location"]
                if redir_url and redir_url.startswith("http"):
                    playurl = redir_url
        except:
            pass
        
        # 获取logo
        logo = channel_data.get("pics", {}).get("highResolutionH", "")
        if not logo:
            logo = channel_data.get("pics", {}).get("smallResolutionH", "")
        
        # 生成M3U行
        return f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="{live}",{name}\n{playurl}\n'
        
    except Exception as e:
        print(f"处理频道 {channel_data.get('name', '未知')} 失败: {str(e)[:50]}")
        return None


def update_live_category(category_name, category_id):
    """更新单个分类"""
    print(f"开始更新分类: {category_name}")
    results = []
    
    try:
        # 获取频道列表
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{category_id}'
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            print(f"获取分类 {category_name} 失败: HTTP {resp.status_code}")
            return []
        
        data = resp.json()
        if "body" not in data or "dataList" not in data["body"]:
            print(f"分类 {category_name} 数据结构异常")
            return []
        
        channels = data["body"]["dataList"]
        
        # 限制最大处理数量，避免GitHub Actions超时
        max_channels = 50
        if len(channels) > max_channels:
            print(f"分类 {category_name} 频道过多，限制为前 {max_channels} 个")
            channels = channels[:max_channels]
        
        # 单线程处理更稳定
        for channel in channels:
            result = process_channel(category_name, channel)
            if result:
                results.append(result)
        
        print(f"分类 {category_name} 完成，成功 {len(results)} 个频道")
        return results
        
    except Exception as e:
        print(f"更新分类 {category_name} 异常: {e}")
        return []


def main():
    """主函数"""
    print("开始更新咪咕直播源...")
    start_time = time.time()
    
    # 写入M3U文件头
    m3u_header = '''#EXTM3U x-tvg-url="https://raw.githubusercontent.com/develop202/migu_video/main/playback.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"
'''
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(m3u_header)
    
    all_channels = []
    total_success = 0
    
    # 只更新前几个主要分类，避免超时
    main_categories = ['热门', '央视', '卫视', '地方']  # 减少分类数量
    
    for category in main_categories:
        if category in LIVE:
            channels = update_live_category(category, LIVE[category])
            if channels:
                all_channels.extend(channels)
                total_success += len(channels)
        
        # 添加延时，避免请求过快
        time.sleep(1)
    
    # 写入所有频道到文件
    if all_channels:
        with open(path, 'a', encoding='utf-8') as f:
            for channel in all_channels:
                f.write(channel)
        
        print(f"\n更新完成！共成功获取 {total_success} 个频道")
    else:
        print("\n更新失败，未获取到任何频道")
    
    end_time = time.time()
    print(f"总耗时: {end_time - start_time:.2f} 秒")
    
    # 检查文件大小
    try:
        file_size = os.path.getsize(path)
        print(f"生成的文件大小: {file_size / 1024:.1f} KB")
    except:
        pass


if __name__ == "__main__":
    # 设置请求超时和重试
    requests.adapters.DEFAULT_RETRIES = 2
    main()
