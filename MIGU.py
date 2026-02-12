#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
咪咕视频抓取脚本
更新日期: 2024-12-08
"""

import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 咪咕视频配置 ====================
THREAD_NUM = 10
MIGU_HEADERS = {
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

# 频道分类
LIVES = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']
LIVE_IDS = {
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

APP_VERSION = "2600034600"
MIGU_TXT = 'migu.txt'

# ==================== 通用工具函数 ====================
def print_colored(text, color="white"):
    """彩色打印输出"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m"
    }
    end = "\033[0m"
    print(f"{colors.get(color, '')}{text}{end}")


def write_file(filepath, content):
    """写入文件"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print_colored(f"文件已保存: {filepath}", "green")
        return True
    except Exception as e:
        print_colored(f"保存文件失败 {filepath}: {e}", "red")
        return False


def md5_hash(text):
    """生成MD5哈希值"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


# ==================== 咪咕视频部分 ====================
class MiguTV:
    def __init__(self):
        self.all_channels = []
       
    def get_salt_and_sign(self, pid):
        """生成加密所需的salt和sign"""
        timestamp = str(int(time.time() * 1000))
        random_num = random.randint(0, 999999)
        salt = f"{random_num:06d}25"
        suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
        app_t = timestamp + pid + APP_VERSION[:8]
        sign = md5_hash(md5_hash(app_t) + suffix)
       
        return {"salt": salt, "sign": sign, "timestamp": timestamp}
   
    def get_content(self, pid):
        """获取频道播放信息"""
        try:
            result = self.get_salt_and_sign(pid)
            rate_type = "2" if pid == "608831231" else "3"
           
            # 构造URL
            url = f"https://play.miguvideo.com/playurl/v1/play/playurl"
            params = {
                "sign": result["sign"],
                "rateType": rate_type,
                "contId": pid,
                "timestamp": result["timestamp"],
                "salt": result["salt"]
            }
           
            # 添加必要头部
            headers = {
                "User-Agent": MIGU_HEADERS["User-Agent"],
                "Referer": "https://m.miguvideo.com/",
                "Origin": "https://m.miguvideo.com"
            }
           
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
           
        except Exception as e:
            print_colored(f"获取内容失败: {e}", "red")
       
        return None
   
    def process_play_url(self, url, pid):
        """处理播放URL"""
        if "&puData=" not in url:
            return url
       
        try:
            pu_data = url.split("&puData=")[1]
            keys = "cdabyzwxkl"
            dd_calcu = []
           
            # 获取当前日期
            current_date = datetime.now()
            date_str = f"{current_date.year}{current_date.month:02d}{current_date.day:02d}"
           
            for i in range(0, int(len(pu_data) / 2)):
                dd_calcu.append(pu_data[len(pu_data) - i - 1])
                dd_calcu.append(pu_data[i])
                if i == 1:
                    dd_calcu.append("v")
                if i == 2:
                    dd_calcu.append(keys[int(date_str[2])])
                if i == 3:
                    dd_calcu.append(keys[int(pid[6]) if len(pid) > 6 else 0])
                if i == 4:
                    dd_calcu.append("a")
           
            result = f'{url}&ddCalcu={"".join(dd_calcu)}&sv=10004&ct=android'
            return result
           
        except Exception as e:
            print_colored(f"URL处理失败: {e}", "red")
            return url
   
    def follow_redirects(self, url, max_redirects=6):
        """跟踪重定向"""
        current_url = url
       
        for i in range(max_redirects):
            try:
                response = requests.get(current_url, allow_redirects=False, timeout=5)
                location = response.headers.get("Location", "")
                if location and location.startswith("http://hlsz"):
                    current_url = location
                    break
                time.sleep(0.15)
            except:
                break
       
        return current_url
   
    def process_channel(self, live_category, channel_data, index):
        """处理单个频道"""
        try:
            channel_name = channel_data.get("name", f"频道{index}")
            pid = channel_data.get("pID", "")
           
            if not pid:
                return None
           
            # 获取播放信息
            content_data = self.get_content(pid)
            if not content_data or "body" not in content_data:
                return None
           
            url_info = content_data.get("body", {}).get("urlInfo", {})
            if not url_info or "url" not in url_info:
                return None
           
            # 处理播放URL
            play_url = self.process_play_url(url_info["url"], pid)
            final_url = self.follow_redirects(play_url)
           
            if not final_url:
                return None
           
            # 构建M3U条目
            logo = channel_data.get("pics", {}).get("highResolutionH", "")
            m3u_entry = f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" tvg-logo="{logo}" group-title="{live_category}",{channel_name}\n{final_url}\n'
           
            print_colored(f"✓ {channel_name}", "green")
            return m3u_entry
           
        except Exception as e:
            print_colored(f"✗ 频道处理失败: {e}", "yellow")
            return None
   
    def update_category(self, live_category):
        """更新单个分类的所有频道"""
        try:
            category_id = LIVE_IDS.get(live_category)
            if not category_id:
                return []
           
            url = f"https://program-sc.miguvideo.com/live/v2/tv-data/{category_id}"
            response = requests.get(url, headers=MIGU_HEADERS, timeout=10)
           
            if response.status_code != 200:
                return []
           
            data = response.json()
            data_list = data.get("body", {}).get("dataList", [])
           
            if not data_list:
                return []
           
            print_colored(f"处理分类: {live_category} ({len(data_list)}个频道)", "cyan")
           
            results = []
            with ThreadPoolExecutor(max_workers=THREAD_NUM) as executor:
                futures = []
                for index, channel_data in enumerate(data_list):
                    future = executor.submit(self.process_channel, live_category, channel_data, index)
                    futures.append(future)
               
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)
           
            return results
           
        except Exception as e:
            print_colored(f"分类更新异常: {e}", "red")
            return []
   
    def generate_m3u(self, entries):
        """生成完整的M3U文件"""
        m3u_header = '#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/erw.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n'
        return m3u_header + "".join(entries)


# ==================== 主程序 ====================
def main():
    """主函数"""
    print_colored("=" * 60, "blue")
    print_colored("咪咕视频抓取工具", "cyan")
    print_colored(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "cyan")
    print_colored("=" * 60, "blue")
   
    start_time = time.time()
   
    # 抓取咪咕视频
    print_colored("\n开始抓取咪咕视频...", "magenta")
    migu_count = 0
   
    migu = MiguTV()
    migu_entries = []
   
    for category in LIVES:
        category_entries = migu.update_category(category)
        migu_entries.extend(category_entries)
        migu_count += len(category_entries)
        time.sleep(0.5)  # 避免请求过快
   
    if migu_entries:
        migu_content = migu.generate_m3u(migu_entries)
        write_file(MIGU_TXT, migu_content)
        print_colored(f"咪咕视频: {migu_count} 个频道", "green")
    else:
        print_colored("咪咕视频: 无数据", "yellow")
   
    # 统计信息
    end_time = time.time()
    elapsed = end_time - start_time
   
    print_colored("\n" + "=" * 60, "green")
    print_colored("任务完成！", "green")
    print_colored(f"总耗时: {elapsed:.2f} 秒", "green")
   
    print_colored(f"\n文件输出:", "cyan")
    print_colored(f"  咪咕视频: {MIGU_TXT}", "white")
   
    print_colored(f"\n频道统计:", "cyan")
    print_colored(f"  咪咕视频: {migu_count} 个", "white")
   
    print_colored("=" * 60, "green")
   
    return True


if __name__ == "__main__":
    try:
        success = main()
        if not success:
            exit(1)
    except KeyboardInterrupt:
        print_colored("\n程序被用户中断", "yellow")
        exit(0)
    except Exception as e:
        print_colored(f"\n程序运行出错: {e}", "red")
        exit(1)
