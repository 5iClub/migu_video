import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

thread_num = 10  # 线程数
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

lives = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']
LIVE = {'热门': 'e7716fea6aa1483c80cfc10b7795fcb8', '体育': '7538163cdac044398cb292ecf75db4e0',
        '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05', '卫视': '0847b3f6c08a4ca28f85ba5701268424',
        '地方': '855e9adc91b04ea18ef3f2dbd43f495b', '影视': '10b0d04cb23d4ac5945c4bc77c7ac44e',
        '新闻': 'c584f67ad63f4bc983c31de3a9be977c', '教育': 'af72267483d94275995a4498b2799ecd',
        '熊猫': 'e76e56e88fff4c11b0168f55e826445d', '综艺': '192a12edfef04b5eb616b878f031f32f',
        '少儿': 'fc2f5b8fd7db43ff88c4243e731ecede', '纪实': 'e1165138bdaa44b9a3138d74af6c6673'}

path = 'migu.txt'
appVersion = "2600034600"
appVersionID = appVersion + "-99000-201600010010028"
All_Live = []
FLAG = 0


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


def getSaltAndSign(contId):
    """生成salt和sign"""
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + contId + appVersion[:8]
    sign = md5(md5(app_t) + suffix)
    return {
        "salt": salt,
        "sign": sign,
        "timestamp": timestamp
    }


def get_content(contId):
    """获取直播流地址"""
    try:
        result = getSaltAndSign(contId)
        
        url = f"https://play.miguvideo.com/playurl/v1/play/playurl"
        params = {
            "sign": result['sign'],
            "rateType": "3",  # 3表示720p
            "contId": contId,
            "timestamp": result['timestamp'],
            "salt": result['salt']
        }
        
        # 简化请求头
        req_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "appCode": "miguvideo_default_h5",
            "appId": "miguvideo",
            "channel": "H5",
            "terminalId": "h5"
        }
        
        response = requests.get(url, headers=req_headers, params=params, timeout=10)
        data = response.json()
        
        if data.get("code") == 200 and "body" in data and "urlInfo" in data["body"]:
            return data["body"]["urlInfo"]["url"]
        else:
            print(f"获取流地址失败: {data.get('message', '未知错误')}")
            return None
            
    except Exception as e:
        print(f"请求异常: {e}")
        return None


def get_720p_stream(stream_url):
    """获取最终的720p流地址"""
    try:
        # 直接请求获取重定向地址
        response = requests.get(stream_url, headers=headers, allow_redirects=False, timeout=10)
        
        if response.status_code in [301, 302] and 'Location' in response.headers:
            location = response.headers['Location']
            
            # 如果已经是hls地址，直接返回
            if location.startswith("http://hlsz") or location.endswith('.m3u8'):
                return location
            
            # 继续跟随重定向
            for _ in range(5):  # 最多跟随5次重定向
                resp = requests.get(location, headers=headers, allow_redirects=False, timeout=10)
                if resp.status_code in [301, 302] and 'Location' in resp.headers:
                    location = resp.headers['Location']
                    if location.startswith("http://hlsz") or location.endswith('.m3u8'):
                        return location
                else:
                    break
        
        # 如果没有重定向，直接返回原地址
        return stream_url
        
    except Exception as e:
        print(f"获取流地址异常: {e}")
        return None


def append_All_Live(live, flag, data):
    """处理单个频道"""
    try:
        channel_name = data.get("name", "未知频道")
        contId = data.get("contId") or data.get("pID")
        
        if not contId:
            print(f'频道 [{channel_name}] 没有contId，跳过')
            return
        
        # 获取流地址
        stream_url = get_content(contId)
        
        if stream_url:
            # 获取最终的720p流地址
            final_url = get_720p_stream(stream_url)
            
            if final_url:
                # 获取频道图标
                logo = ""
                if "pics" in data:
                    logo = data["pics"].get("highResolutionH", "")
                
                content = f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" tvg-logo="{logo}" group-title="{live}",{channel_name}\n{final_url}\n'
                All_Live[flag] = content
                print(f'频道 [{channel_name}] 更新成功！')
            else:
                print(f'频道 [{channel_name}] 获取流地址失败！')
        else:
            print(f'频道 [{channel_name}] 获取流地址失败！')
            
    except Exception as e:
        print(f'频道 [{channel_name}] 更新失败！错误: {str(e)}')


def update(live, url):
    """更新某个分类下的所有频道"""
    global FLAG, All_Live
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "body" in data and "dataList" in data["body"]:
            dataList = data["body"]["dataList"]
            
            if not dataList:
                print(f"分类 [{live}] 没有频道数据")
                return
            
            # 扩展All_Live列表
            for i in range(len(dataList)):
                All_Live.append("")
            
            # 使用线程池处理
            with ThreadPoolExecutor(max_workers=thread_num) as pool:
                futures = []
                for idx, channel_data in enumerate(dataList):
                    future = pool.submit(append_All_Live, live, FLAG + idx, channel_data)
                    futures.append(future)
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
            
            FLAG += len(dataList)
            print(f"分类 [{live}] 更新完成，共{len(dataList)}个频道")
        else:
            print(f"分类 [{live}] 数据格式错误")
            
    except Exception as e:
        print(f"更新分类 [{live}] 失败: {str(e)}")


def main():
    """主函数"""
    print("开始更新Migu直播源...")
    
    # 写入M3U文件头
    header = '#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/epg.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n'
    writefile(path, header)
    
    total_channels = 0
    
    # 遍历所有分类
    for live in lives:
        print(f"\n分类 [{live}] 开始更新...")
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
        update(live, url)
        
        # 统计已获取的频道数
        channels_count = len([c for c in All_Live if c])
        print(f"已获取 {channels_count} 个频道")
    
    # 写入所有频道信息
    print("\n写入文件...")
    for content in All_Live:
        if content:  # 只写入成功获取的频道
            appendfile(path, content)
    
    print(f"\n完成！共获取 {len([c for c in All_Live if c])} 个频道")
    print(f"结果已保存到 {path}")


if __name__ == "__main__":
    main()
