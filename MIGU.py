import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from Crypto.Cipher import AES
import base64
import gzip
import io
import os
import sys

# ============== 配置部分 ==============
# AES解密常量（与JavaScript一致）
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

# GitHub项目配置
REPO_LINK_UPDATE_TIMESTAMP = 0
DEBUG_MODE = False

# 咪咕视频配置
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

MIGU_CATEGORIES = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']
MIGU_CATEGORY_IDS = {
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
APP_VERSION_ID = APP_VERSION + "-99000-201600010010028"

# ============== 工具函数 ==============
def color_print(text, color="white"):
    """彩色输出（模拟JavaScript的colorOut.js）"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m"
    }
    end_color = "\033[0m"
    print(f"{colors.get(color, colors['white'])}{text}{end_color}")


def write_file(path, content, mode='w'):
    """写入文件"""
    with open(path, mode, encoding='utf-8') as f:
        f.write(content)


def read_file(path):
    """读取文件"""
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def md5_hash(text):
    """MD5加密"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


# ============== JavaScript对应函数 ==============
def aes_decrypt(base_data, key_array=None, iv_array=None):
    """AES解密（对应JavaScript的AESdecrypt函数）"""
    try:
        if key_array is None:
            key_array = KEY_ARRAY
        if iv_array is None:
            iv_array = IV_ARRAY
        
        key = bytes(key_array)
        iv = bytes(iv_array)
        
        # Base64解码
        data = base64.b64decode(base_data)
        
        # AES-CBC解密
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(data)
        
        # 去除PKCS7填充
        padding_length = decrypted[-1]
        if padding_length < 16:
            decrypted = decrypted[:-padding_length]
        
        return decrypted.decode('utf-8', errors='ignore')
    except:
        return base_data


def is_in_white_list(item, white_list=None):
    """检查域名是否在白名单中"""
    if white_list is None:
        white_list = DOMAIN_WHITE_LIST
    return item in white_list


def test_url_availability(url, timeout=0.3):
    """测试URL是否可用"""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code in [200, 302, 301]
    except:
        return False


# ============== 咪咕视频部分 ==============
class MiguVideo:
    def __init__(self):
        self.thread_num = THREAD_NUM
        self.headers = MIGU_HEADERS
        self.all_live = []
        self.flag = 0
    
    def get_salt_and_sign(self, pid):
        """生成salt和sign"""
        timestamp = str(int(time.time() * 1000))
        random_num = random.randint(0, 999999)
        salt = f"{random_num:06d}25"
        suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
        app_t = timestamp + pid + APP_VERSION[:8]
        sign = md5_hash(md5_hash(app_t) + suffix)
        return {
            "salt": salt,
            "sign": sign,
            "timestamp": timestamp
        }
    
    def get_content(self, pid):
        """获取频道内容"""
        _headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "apipost-client-id": "465aea51-4548-495a-8709-7e532dbe3703",
            "apipost-language": "zh-cn",
            "apipost-machine": "3a214a07786002",
            "apipost-platform": "Win",
            "apipost-terminal": "web",
            "apipost-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXlsb2FkIjp7InVzZXJfaWQiOjM5NDY2NDM3MTIyMzAwMzEzNywidGltZSI6MTc2NTYzMjU2NSwidXVpZCI6ImJlNDJjOTMxLWQ4MjctMTFmMC1hNThiLTUyZTY1ODM4NDNhOSJ9fQ.QU0RXa0e-yB-fwJNjYt_OnyM6RteY3L1BaUWqCrdAB4",
            "apipost-version": "8.2.6",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "cookie": "apipost-token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXlsb2FkIjp7InVzZXJfaWQiOjM5NDY2NDM3MTIyMzAwMzEzNywidGltZSI6MTc2NTYzMjU2NSwidXVpZCI6ImJlNDJjOTMxLWQ4MjctMTFmMC1hNThiLTUyZTY1ODM4NDNhOSJ9fQ.QU0RXa0e-yB-fwJNjYt_OnyM6RteY3L1BaUWqCrdAB4; SERVERID=236fe4f21bf23223c449a2ac2dc20aa4|1765632725|1765632691; SERVERCORSID=236fe4f21bf23223c449a2ac2dc20aa4|1765632725|1765632691",
            "Referer": "https://workspace.apipost.net/57a21612a051000/apis",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        result = self.get_salt_and_sign(pid)
        rate_type = "2" if pid == "608831231" else "3"
        url = f"https://play.miguvideo.com/playurl/v1/play/playurl?sign={result['sign']}&rateType={rate_type}&contId={pid}&timestamp={result['timestamp']}&salt={result['salt']}"
        
        body = {
            "option": {
                "scene": "http_request",
                "lang": "zh-cn",
                "globals": {},
                "collection": [
                    {
                        "target_id": "3c5fd6a9786002",
                        "target_type": "api",
                        "parent_id": "0",
                        "name": "MIGU",
                        "request": {
                            "auth": {"type": "inherit"},
                            "method": "POST",
                            "url": url
                        }
                    }
                ]
            },
            "test_events": [{"type": "api", "data": {"target_id": "3c5fd6a9786002"}}]
        }
        
        proxy_url = "https://workspace.apipost.net/proxy/v2/http"
        resp = requests.post(proxy_url, headers=_headers, data=json.dumps(body, separators=(",", ":"))).json()
        return json.loads(resp["data"]["data"]["response"]["body"])
    
    def get_dd_calcu_720p(self, url, pid):
        """计算ddCalcu参数"""
        pu_data = url.split("&puData=")[1]
        keys = "cdabyzwxkl"
        dd_calcu = []
        
        for i in range(0, int(len(pu_data) / 2)):
            dd_calcu.append(pu_data[len(pu_data) - i - 1])
            dd_calcu.append(pu_data[i])
            if i == 1:
                dd_calcu.append("v")
            if i == 2:
                dd_calcu.append(keys[int(datetime.now().strftime("%Y%m%d")[2])])
            if i == 3:
                dd_calcu.append(keys[int(pid[6])])
            if i == 4:
                dd_calcu.append("a")
        
        return f'{url}&ddCalcu={"".join(dd_calcu)}&sv=10004&ct=android'
    
    def process_channel(self, live, flag, data):
        """处理单个频道"""
        try:
            resp_data = self.get_content(data["pID"])
            play_url = self.get_dd_calcu_720p(resp_data["body"]["urlInfo"]["url"], data["pID"])
            
            if play_url:
                z = 1
                while z <= 6:
                    obj = requests.get(play_url, allow_redirects=False)
                    location = obj.headers.get("Location", "")
                    
                    if location.startswith("http://hlsz"):
                        play_url = location
                        break
                    
                    if z <= 6:
                        time.sleep(0.15)
                    z += 1
            
            content = f'#EXTINF:-1 tvg-id="{data["name"]}" tvg-name="{data["name"]}" tvg-logo="{data["pics"]["highResolutionH"]}" group-title="{live}",{data["name"]}\n{play_url}\n'
            
            if z == 7:
                color_print(f'频道 [{data["name"]}] 更新失败！', "yellow")
            else:
                self.all_live[flag] = content
                color_print(f'频道 [{data["name"]}] 更新成功！', "green")
                
        except Exception as e:
            color_print(f'频道 [{data["name"]}] 更新失败！', "red")
            if DEBUG_MODE:
                color_print(f"ERROR: {e}", "red")
    
    def update_category(self, live):
        """更新一个分类的频道"""
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{MIGU_CATEGORY_IDS[live]}'
        
        try:
            response = requests.get(url, headers=self.headers).json()
            data_list = response["body"]["dataList"]
            
            with ThreadPoolExecutor(max_workers=self.thread_num) as executor:
                for flag, data in enumerate(data_list):
                    self.all_live.append("")
                    executor.submit(self.process_channel, live, self.flag + flag, data)
            
            self.flag += len(data_list)
            color_print(f"分类 [{live}] 更新完成，共 {len(data_list)} 个频道", "cyan")
            
        except Exception as e:
            color_print(f"分类 [{live}] 更新失败: {e}", "red")
    
    def generate_m3u(self):
        """生成M3U文件"""
        m3u_header = '#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/erw.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n'
        m3u_content = m3u_header + "".join([c for c in self.all_live if c])
        
        return m3u_content


# ============== 彩直播部分 ==============
class FengCaiLive:
    def __init__(self):
        self.domains_stat = {}
    
    def get_channels(self):
        """获取彩直播频道数据"""
        color_print("开始获取彩直播频道数据...", "magenta")
        
        channels_m3u = []
        channels_txt = []
        sum_channel = 0
        
        headers = {"Referer": "http://pro.fengcaizb.com"}
        
        try:
            # 尝试多个源
            sources = [
                "http://pro.fengcaizb.com/channels/pro.gz",
                "http://ds.fengcaizb.com/channels/dszb3.gz"
            ]
            
            response = None
            for source in sources:
                try:
                    response = requests.get(source, headers=headers, timeout=10)
                    if response.ok:
                        break
                except:
                    continue
            
            if not response or not response.ok:
                color_print("请求失败", "red")
                return 2
            
            color_print("开始解压缩...", "magenta")
            
            # 解压gzip数据
            compressed_data = io.BytesIO(response.content)
            with gzip.GzipFile(fileobj=compressed_data, mode='rb') as f:
                decompressed = f.read()
            
            color_print(f"解压缩完成: {len(response.content)}字节 -> {len(decompressed)}字节", "green")
            
            result = json.loads(decompressed)
            
            # 检查时间戳是否需要更新
            if REPO_LINK_UPDATE_TIMESTAMP > 0 and result.get("timestamp") == REPO_LINK_UPDATE_TIMESTAMP:
                color_print("数据未更新，跳过", "yellow")
                return 1
            
            # 构建M3U头部
            channels_m3u.append('#EXTM3U x-tvg-url="https://gh-proxy.com/https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml,https://hk.gh-proxy.org/raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml,https://develop202.github.io/migu_video/playback.xml,https://raw.githubusercontents.com/develop202/migu_video/refs/heads/main/playback.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"')
            
            i = 0
            last_channel_cate = ""
            
            for channel in result.get("data", []):
                # 过滤广告频道
                if channel.get("ct"):
                    continue
                
                channel_title = channel.get("title", "").replace("-", "")
                
                for url in channel.get("urls", []):
                    i += 1
                    
                    # AES解密URL
                    decrypt_url = aes_decrypt(url)
                    
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
                    
                    # 统计域名使用情况
                    if DEBUG_MODE:
                        self.domains_stat[domain] = self.domains_stat.get(domain, 0) + 1
                    
                    # 添加频道分类头
                    province = channel.get("province", "")
                    if province != last_channel_cate:
                        channels_txt.append(f"{province},#genre#")
                        last_channel_cate = province
                    
                    # 构建M3U条目
                    channel_m3u = f'#EXTINF:-1 tvg-id="{channel_title}" tvg-name="{channel_title}" tvg-logo="" group-title="{province}",{channel_title}\n{decrypt_url}'
                    channel_txt = f'{channel_title},{decrypt_url}'
                    
                    # 添加更新时间（第一条记录）
                    if sum_channel == 0:
                        timestamp = result.get("timestamp", 0) + (8 * 60 * 60 * 1000)
                        update_time = datetime.fromtimestamp(timestamp / 1000)
                        update_time_str = f"更新日期: {update_time.year}-{update_time.month:02d}-{update_time.day:02d} {update_time.hour:02d}:{update_time.minute:02d}:{update_time.second:02d}"
                        channels_m3u.append(f'#EXTINF:-1 tvg-id="{channel_title}" tvg-name="{channel_title}" tvg-logo="" group-title="{province}",{update_time_str}\n{decrypt_url}')
                        channels_txt.append(f'{update_time_str},{decrypt_url}')
                    
                    channels_m3u.append(channel_m3u)
                    channels_txt.append(channel_txt)
                    sum_channel += 1
                    
                    color_print(f"{i} {sum_channel} {channel_title} 添加成功！", "green")
            
            # 显示文件日期
            timestamp = result.get("timestamp", 0) + (8 * 60 * 60 * 1000)
            update_time = datetime.fromtimestamp(timestamp / 1000)
            color_print(f"文件日期: {update_time.year}-{update_time.month:02d}-{update_time.day:02d} {update_time.hour:02d}:{update_time.minute:02d}:{update_time.second:02d}", "cyan")
            
            return {
                "m3u": "\n".join(channels_m3u),
                "txt": "\n".join(channels_txt)
            }
            
        except Exception as e:
            color_print(f"获取彩直播频道数据失败: {e}", "red")
            return None


# ============== 主程序 ==============
def main():
    color_print("=" * 50, "blue")
    color_print("GitHub 电视频道抓取工具", "cyan")
    color_print("=" * 50, "blue")
    
    # 创建输出目录
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 1. 抓取咪咕视频
    color_print("\n[1/2] 开始抓取咪咕视频频道...", "magenta")
    migu = MiguVideo()
    
    for category in MIGU_CATEGORIES:
        color_print(f"分类 [{category}] 开始更新...", "cyan")
        migu.update_category(category)
        time.sleep(1)  # 避免请求过快
    
    # 保存咪咕视频结果
    migu_m3u = migu.generate_m3u()
    migu_file = os.path.join(output_dir, "migu.m3u")
    write_file(migu_file, migu_m3u)
    color_print(f"咪咕视频数据已保存到: {migu_file}", "green")
    
    # 2. 抓取彩直播
    color_print("\n[2/2] 开始抓取彩直播频道...", "magenta")
    fengcai = FengCaiLive()
    fengcai_result = fengcai.get_channels()
    
    if isinstance(fengcai_result, dict):
        # 保存彩直播结果
        fengcai_m3u_file = os.path.join(output_dir, "fengcai.m3u")
        fengcai_txt_file = os.path.join(output_dir, "fengcai.txt")
        
        write_file(fengcai_m3u_file, fengcai_result["m3u"])
        write_file(fengcai_txt_file, fengcai_result["txt"])
        
        # 统计信息
        channel_count = len(fengcai_result["m3u"].split("\n")) - 1
        color_print(f"彩直播数据已保存，共 {channel_count} 个频道", "green")
        
        # 显示域名统计（调试模式）
        if DEBUG_MODE and fengcai.domains_stat:
            color_print("\n域名使用统计:", "cyan")
            sorted_domains = sorted(fengcai.domains_stat.items(), key=lambda x: x[1], reverse=True)
            for domain, count in sorted_domains[:10]:  # 显示前10个
                color_print(f"  {domain}: {count}次", "white")
    
    elif fengcai_result == 1:
        color_print("彩直播数据未更新，使用缓存", "yellow")
    elif fengcai_result == 2:
        color_print("彩直播数据获取失败", "red")
    
    # 3. 合并文件（可选）
    color_print("\n[3/3] 合并所有频道...", "magenta")
    combined_m3u = []
    combined_m3u.append('#EXTM3U x-tvg-url="https://gh-proxy.com/https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n')
    
    # 添加咪咕视频
    combined_m3u.extend([c for c in migu.all_live if c])
    
    # 添加彩直播（如果有）
    if isinstance(fengcai_result, dict):
        combined_m3u.append("\n# 彩直播频道\n")
        combined_m3u.append(fengcai_result["m3u"].split("\n", 1)[1])
    
    # 保存合并文件
    combined_file = os.path.join(output_dir, "all_channels.m3u")
    write_file(combined_file, "".join(combined_m3u))
    color_print(f"合并文件已保存到: {combined_file}", "green")
    
    color_print("\n所有任务完成！", "green")
    color_print(f"输出目录: {output_dir}", "cyan")
    color_print("=" * 50, "blue")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        color_print("\n程序被用户中断", "yellow")
        sys.exit(0)
    except Exception as e:
        color_print(f"\n程序运行出错: {e}", "red")
        sys.exit(1)
