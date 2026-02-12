#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
咪咕视频 + 彩直播抓取脚本
包含AES解密功能
更新日期: 2024-12-08
"""

import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64
import gzip
import io

# ==================== AES解密配置 ====================
try:
    from Crypto.Cipher import AES
    AES_AVAILABLE = True
except ImportError:
    print("警告: 未安装pycryptodome，AES解密功能不可用")
    print("请运行: pip install pycryptodome")
    AES_AVAILABLE = False

# AES密钥和IV（与JavaScript一致）
KEY_ARRAY = [121, 111, 117, 33, 106, 101, 64, 49, 57, 114, 114, 36, 50, 48, 121, 35]
IV_ARRAY = [65, 114, 101, 121, 111, 117, 124, 62, 127, 110, 54, 38, 13, 97, 110, 63]

# 域名白名单
DOMAIN_WHITE_LIST = [
    "cdn.gitcdn.top", "cdn.gitcdn.xyz", "tvg.bestvcdn.com",
    "ts.48dn.com", "live-play.cctvnews.cctv.com", "lplay.letv-cdn.com",
    "liveali.cncntv.cn", "livehls1.douyucdn.cn", "livehls3.douyucdn.cn",
    "live.fc.ctripcorp.com", "live.ahstv.com", "lssp.sztv.com.cn",
    "lssp.jxtvcn.com.cn", "live.xmcdn.com", "live.nbtv.cn",
    "gslb.huya.com", "hwltc.tv.cctv.cn", "pull.aliyunlive.com",
    "liveplay-srs.yunnan.gov.cn", "liveshow.gzstv.com", "live.hbtv.com.cn",
    "hls.jstv.com", "live.sdnews.com.cn", "hlslive.hbtv.com.cn",
    "hls.tvming.cn", "live.wifizs.cn", "live.gxtv.cn", "liveplay.gdstv.cn"
]

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
FENGCAI_M3U = 'fengcai.m3u'
FENGCAI_TXT = 'fengcai.txt'
ALL_CHANNELS = 'all_channels.m3u'


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
    print(f"{colors.get(color, colors.get('white', ''))}{text}{end}")


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


# ==================== AES解密函数 ====================
def aes_decrypt(encrypted_data):
    """
    AES解密函数（对应JavaScript的AESdecrypt）
    支持Base64解码和AES-128-CBC解密
    """
    if not AES_AVAILABLE:
        print_colored("AES解密不可用（未安装pycryptodome）", "red")
        return encrypted_data
    
    try:
        # Base64解码
        encrypted_bytes = base64.b64decode(encrypted_data)
        
        # 创建AES解密器
        key = bytes(KEY_ARRAY)
        iv = bytes(IV_ARRAY)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # 解密
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        
        # 去除PKCS7填充
        padding_length = decrypted_bytes[-1]
        if padding_length < 16:
            decrypted_bytes = decrypted_bytes[:-padding_length]
        
        # 解码为字符串
        decrypted_text = decrypted_bytes.decode('utf-8', errors='ignore')
        
        # 处理特殊前缀
        if decrypted_text.startswith("sys_http"):
            decrypted_text = decrypted_text.replace("sys_", "")
        
        return decrypted_text
        
    except Exception as e:
        print_colored(f"AES解密失败: {e}", "yellow")
        return encrypted_data


def is_in_white_list(domain):
    """检查域名是否在白名单中"""
    return domain in DOMAIN_WHITE_LIST


def test_url_availability(url, timeout=2):
    """测试URL是否可用"""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code in [200, 302, 301, 304]
    except:
        return False


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


# ==================== 彩直播部分 ====================
class FengCaiTV:
    def __init__(self):
        self.success_count = 0
        self.total_count = 0
    
    def fetch_fengcai_channels(self):
        """获取彩直播频道数据"""
        print_colored("开始获取彩直播频道数据...", "magenta")
        
        channels_m3u = []
        channels_txt = []
        
        try:
            # 尝试多个源
            sources = [
                "http://pro.fengcaizb.com/channels/pro.gz",
                "http://ds.fengcaizb.com/channels/dszb3.gz"
            ]
            
            response = None
            for source in sources:
                try:
                    headers = {"Referer": "http://pro.fengcaizb.com"}
                    response = requests.get(source, headers=headers, timeout=15)
                    if response.status_code == 200:
                        break
                except:
                    continue
            
            if not response or response.status_code != 200:
                print_colored("彩直播请求失败", "red")
                return None
            
            # 解压gzip数据
            compressed_data = io.BytesIO(response.content)
            with gzip.GzipFile(fileobj=compressed_data, mode='rb') as f:
                decompressed = f.read()
            
            print_colored(f"解压缩完成: {len(response.content)}字节 -> {len(decompressed)}字节", "green")
            
            result = json.loads(decompressed)
            
            # 构建M3U头部
            channels_m3u.append('#EXTM3U x-tvg-url="https://gh-proxy.com/https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml,https://hk.gh-proxy.org/raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml,https://develop202.github.io/migu_video/playback.xml,https://raw.githubusercontents.com/develop202/migu_video/refs/heads/main/playback.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"')
            
            i = 0
            last_province = ""
            
            for channel in result.get("data", []):
                # 过滤广告频道
                if channel.get("ct"):
                    continue
                
                channel_title = channel.get("title", "").replace("-", "")
                
                for url in channel.get("urls", []):
                    i += 1
                    self.total_count += 1
                    
                    # AES解密URL
                    if AES_AVAILABLE:
                        decrypt_url = aes_decrypt(url)
                    else:
                        decrypt_url = url
                    
                    if decrypt_url.startswith("sys_http"):
                        decrypt_url = decrypt_url.replace("sys_", "")
                    
                    if not decrypt_url.startswith("http"):
                        continue
                    
                    # 处理特殊字符
                    if "$" in decrypt_url:
                        decrypt_url = decrypt_url.split("$")[0]
                    
                    # 提取域名
                    try:
                        domain = decrypt_url.split("/")[2]
                    except:
                        continue
                    
                    # 不在白名单的域名需要测试可用性
                    if not is_in_white_list(domain):
                        if not test_url_availability(decrypt_url):
                            continue
                    
                    # 添加频道分类头
                    province = channel.get("province", "")
                    if province != last_province:
                        if last_province:  # 如果不是第一个分类，添加空行
                            channels_txt.append("")
                        channels_txt.append(f"{province},#genre#")
                        last_province = province
                    
                    # 构建M3U条目
                    channel_m3u = f'#EXTINF:-1 tvg-id="{channel_title}" tvg-name="{channel_title}" tvg-logo="" group-title="{province}",{channel_title}\n{decrypt_url}'
                    channel_txt = f'{channel_title},{decrypt_url}'
                    
                    # 添加更新时间（第一条记录）
                    if self.success_count == 0:
                        timestamp = result.get("timestamp", 0) + (8 * 60 * 60 * 1000)
                        update_time = datetime.fromtimestamp(timestamp / 1000)
                        update_time_str = f"更新日期: {update_time.year}-{update_time.month:02d}-{update_time.day:02d} {update_time.hour:02d}:{update_time.minute:02d}:{update_time.second:02d}"
                        channels_m3u.append(f'#EXTINF:-1 tvg-id="{channel_title}" tvg-name="{channel_title}" tvg-logo="" group-title="{province}",{update_time_str}\n{decrypt_url}')
                        channels_txt.append(f'{update_time_str},{decrypt_url}')
                        channels_txt.append("")
                    
                    channels_m3u.append(channel_m3u)
                    channels_txt.append(channel_txt)
                    self.success_count += 1
                    
                    if i % 50 == 0:
                        print_colored(f"已处理 {i} 个频道，成功 {self.success_count} 个", "cyan")
            
            if self.success_count > 0:
                timestamp = result.get("timestamp", 0) + (8 * 60 * 60 * 1000)
                update_time = datetime.fromtimestamp(timestamp / 1000)
                print_colored(f"文件日期: {update_time.year}-{update_time.month:02d}-{update_time.day:02d} {update_time.hour:02d}:{update_time.minute:02d}", "green")
            
            return {
                "m3u": "\n".join(channels_m3u),
                "txt": "\n".join(channels_txt)
            }
            
        except Exception as e:
            print_colored(f"获取彩直播数据失败: {e}", "red")
            return None


# ==================== 主程序 ====================
def main():
    """主函数"""
    print_colored("=" * 60, "blue")
    print_colored("咪咕视频 + 彩直播抓取工具", "cyan")
    print_colored(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "cyan")
    print_colored("=" * 60, "blue")
    
    start_time = time.time()
    
    # 1. 抓取咪咕视频
    print_colored("\n[1/2] 开始抓取咪咕视频...", "magenta")
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
    
    # 2. 抓取彩直播
    print_colored("\n[2/2] 开始抓取彩直播...", "magenta")
    
    if AES_AVAILABLE:
        fengcai = FengCaiTV()
        fengcai_result = fengcai.fetch_fengcai_channels()
        
        if fengcai_result:
            write_file(FENGCAI_M3U, fengcai_result["m3u"])
            write_file(FENGCAI_TXT, fengcai_result["txt"])
            print_colored(f"彩直播: {fengcai.success_count}/{fengcai.total_count} 个频道", "green")
        else:
            print_colored("彩直播: 无数据", "yellow")
    else:
        print_colored("彩直播: AES解密不可用，跳过", "yellow")
    
    # 3. 生成合并文件
    print_colored("\n[3/3] 生成合并文件...", "magenta")
    
    all_content = []
    all_content.append('#EXTM3U x-tvg-url="https://gh-proxy.com/https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n')
    all_content.append('\n# 咪咕视频\n')
    
    if migu_entries:
        # 跳过M3U头部
        migu_lines = migu_content.split('\n', 1)
        if len(migu_lines) > 1:
            all_content.append(migu_lines[1])
    
    if AES_AVAILABLE and fengcai_result:
        all_content.append('\n# 彩直播\n')
        all_content.append(fengcai_result["m3u"].split('\n', 1)[1])
    
    write_file(ALL_CHANNELS, "".join(all_content))
    
    # 4. 统计信息
    end_time = time.time()
    elapsed = end_time - start_time
    
    print_colored("\n" + "=" * 60, "green")
    print_colored("任务完成！", "green")
    print_colored(f"总耗时: {elapsed:.2f} 秒", "green")
    
    print_colored(f"\n文件输出:", "cyan")
    print_colored(f"  咪咕视频: {MIGU_TXT}", "white")
    if AES_AVAILABLE:
        print_colored(f"  彩直播M3U: {FENGCAI_M3U}", "white")
        print_colored(f"  彩直播TXT: {FENGCAI_TXT}", "white")
    print_colored(f"  合并文件: {ALL_CHANNELS}", "white")
    
    print_colored(f"\n频道统计:", "cyan")
    print_colored(f"  咪咕视频: {migu_count} 个", "white")
    
    if AES_AVAILABLE and fengcai_result:
        print_colored(f"  彩直播: {fengcai.success_count} 个", "white")
    
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
