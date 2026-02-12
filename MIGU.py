#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩直播抓取脚本
包含AES解密功能
更新日期: 2024-12-08
"""

import requests
import json
import time
from datetime import datetime
import hashlib
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

# ==================== 彩直播配置 ====================
FENGCAI_M3U = 'fengcai.m3u'
FENGCAI_TXT = 'fengcai.txt'


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
    print_colored("彩直播抓取工具", "cyan")
    print_colored(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "cyan")
    print_colored("=" * 60, "blue")
    
    start_time = time.time()
    
    # 抓取彩直播
    print_colored("\n开始抓取彩直播...", "magenta")
    
    if not AES_AVAILABLE:
        print_colored("AES解密不可用，无法处理彩直播数据", "red")
        print_colored("请安装: pip install pycryptodome", "yellow")
        return False
    
    fengcai = FengCaiTV()
    fengcai_result = fengcai.fetch_fengcai_channels()
    
    if fengcai_result:
        write_file(FENGCAI_M3U, fengcai_result["m3u"])
        write_file(FENGCAI_TXT, fengcai_result["txt"])
        print_colored(f"彩直播: {fengcai.success_count}/{fengcai.total_count} 个频道", "green")
    else:
        print_colored("彩直播: 无数据", "yellow")
    
    # 统计信息
    end_time = time.time()
    elapsed = end_time - start_time
    
    print_colored("\n" + "=" * 60, "green")
    print_colored("任务完成！", "green")
    print_colored(f"总耗时: {elapsed:.2f} 秒", "green")
    
    print_colored(f"\n文件输出:", "cyan")
    if AES_AVAILABLE and fengcai_result:
        print_colored(f"  彩直播M3U: {FENGCAI_M3U}", "white")
        print_colored(f"  彩直播TXT: {FENGCAI_TXT}", "white")
    
    print_colored(f"\n频道统计:", "cyan")
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
