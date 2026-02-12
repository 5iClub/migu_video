import requests
import json
import time
import random
import hashlib
import base64
import gzip
import concurrent.futures
from datetime import datetime
from urllib.parse import urlparse
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AES解密参数（与JS代码保持一致）
KEY_ARRAY = [121, 111, 117, 33, 106, 101, 64, 49, 57, 114, 114, 36, 50, 48, 121, 35]
IV_ARRAY = [65, 114, 101, 121, 111, 117, 124, 62, 127, 110, 54, 38, 13, 97, 110, 63]

# 域名白名单（可根据需要调整）
DOMAIN_WHITE_LIST = [
    "live-play.cctvnews.cctv.com",
    "live-play.cctvnews.cctv.cn",
    "cctvts.liveplay.myqcloud.com",
    # 添加更多白名单域名
]

class FengcaizbUpdater:
    def __init__(self, debug_mode=False):
        self.debug = debug_mode
        self.channels_url_m3u = []
        self.channels_url_txt = []
        self.domains_stat = {}
        self.sum_channel = 0
        self.headers = {"Referer": "http://pro.fengcaizb.com"}
        
    def aes_decrypt(self, base_data):
        """AES-128-CBC解密"""
        key = bytes(KEY_ARRAY)
        iv = bytes(IV_ARRAY)
        
        try:
            data = base64.b64decode(base_data)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(data), AES.block_size)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"AES解密失败: {e}")
            return ""
    
    def is_in_white_list(self, domain):
        """检查域名是否在白名单中"""
        return domain in DOMAIN_WHITE_LIST
    
    def check_url_accessible(self, url, timeout=0.3):
        """检查URL是否可访问"""
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            return response.status_code == 200
        except:
            return False
    
    def process_channel(self, channel):
        """处理单个频道"""
        if channel.get('ct'):  # 广告频道过滤
            return []
        
        channel_name = channel.get('title', '').replace('-', '')
        province = channel.get('province', '其他')
        urls = channel.get('urls', [])
        
        valid_urls = []
        
        for url in urls:
            decrypted_url = self.aes_decrypt(url)
            
            # URL清理
            if decrypted_url.startswith("sys_http"):
                decrypted_url = decrypted_url.replace("sys_", "")
            
            if not decrypted_url.startswith("http"):
                continue
            
            # 处理特殊字符
            if "$" in decrypted_url:
                decrypted_url = decrypted_url.split("$")[0]
            
            # 提取域名
            domain = urlparse(decrypted_url).netloc
            
            # 域名验证
            if not self.is_in_white_list(domain):
                if not self.check_url_accessible(decrypted_url):
                    continue
                
                # 统计域名使用次数（调试模式）
                if self.debug:
                    self.domains_stat[domain] = self.domains_stat.get(domain, 0) + 1
            
            valid_urls.append({
                'name': channel_name,
                'url': decrypted_url,
                'province': province,
                'domain': domain
            })
        
        return valid_urls
    
    def fetch_and_process(self):
        """获取并处理所有数据"""
        try:
            # 第一步：获取压缩数据
            logger.info("开始获取fengcaizb直播源数据...")
            response = requests.get(
                "http://pro.fengcaizb.com/channels/pro.gz",
                headers=self.headers
            )
            
            if response.status_code != 200:
                logger.error("请求失败，状态码: %d", response.status_code)
                return None
            
            # 第二步：解压数据
            logger.info("开始解压缩数据...")
            decompressed = gzip.decompress(response.content)
            logger.info(f"解压缩完成: {len(response.content)}字节 -> {len(decompressed)}字节")
            
            # 第三步：解析JSON
            data = json.loads(decompressed.decode('utf-8'))
            
            # 检查是否需更新（这里简化处理，实际可根据时间戳判断）
            timestamp = data.get('timestamp', 0)
            # timestamp_check = self.check_timestamp(timestamp) # 可添加时间戳检查逻辑
            
            # 第四步：处理所有频道
            logger.info("开始处理频道数据...")
            last_province = ""
            
            # 添加M3U文件头
            self.channels_url_m3u.append(
                '#EXTM3U x-tvg-url="https://gh-proxy.com/https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml,'
                'https://hk.gh-proxy.org/raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml,'
                'https://develop202.github.io/migu_video/playback.xml,'
                'https://raw.githubusercontents.com/develop202/migu_video/refs/heads/main/playback.xml" '
                'catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"'
            )
            
            # 处理每个频道
            for idx, channel in enumerate(data.get('data', [])):
                valid_urls = self.process_channel(channel)
                
                for url_info in valid_urls:
                    # 分组处理
                    if url_info['province'] != last_province:
                        self.channels_url_txt.append(f"{url_info['province']},#genre#")
                        last_province = url_info['province']
                    
                    # M3U格式
                    m3u_entry = (
                        f'#EXTINF:-1 tvg-id="{url_info["name"]}" '
                        f'tvg-name="{url_info["name"]}" tvg-logo="" '
                        f'group-title="{url_info["province"]}",{url_info["name"]}\n'
                        f'{url_info["url"]}'
                    )
                    
                    # TXT格式
                    txt_entry = f'{url_info["name"]},{url_info["url"]}'
                    
                    # 如果是第一个有效频道，添加更新时间信息
                    if self.sum_channel == 0:
                        update_time = datetime.fromtimestamp(timestamp/1000 + 8*3600)
                        time_str = update_time.strftime("%Y-%m-%d %H:%M:%S")
                        update_entry = f'更新日期: {time_str}'
                        
                        self.channels_url_m3u.append(
                            f'#EXTINF:-1 tvg-id="更新时间" tvg-name="更新时间" '
                            f'tvg-logo="" group-title="信息",{update_entry}\n'
                            f'http://example.com'
                        )
                        self.channels_url_txt.append(f'{update_entry},http://example.com')
                    
                    self.channels_url_m3u.append(m3u_entry)
                    self.channels_url_txt.append(txt_entry)
                    self.sum_channel += 1
                    
                    logger.info(f"频道处理成功: {url_info['name']} ({self.sum_channel}个)")
            
            logger.info(f"总共处理 {self.sum_channel} 个有效频道")
            
            return {
                'm3u': '\n'.join(self.channels_url_m3u),
                'txt': '\n'.join(self.channels_url_txt),
                'timestamp': timestamp,
                'channel_count': self.sum_channel
            }
            
        except Exception as e:
            logger.error(f"处理过程中出错: {e}")
            return None
    
    def save_files(self):
        """保存到文件"""
        result = self.fetch_and_process()
        
        if result:
            with open('fengcaizb.m3u', 'w', encoding='utf-8') as f:
                f.write(result['m3u'])
            
            with open('fengcaizb.txt', 'w', encoding='utf-8') as f:
                f.write(result['txt'])
            
            # 调试信息
            if self.debug:
                logger.info("域名统计:")
                for domain, count in sorted(self.domains_stat.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"  {domain}: {count}次")
            
            return result['channel_count']
        return 0


class MIGUUpdater:
    """原有的咪咕更新器"""
    def __init__(self, thread_num=10):
        self.thread_num = thread_num
        self.headers = {
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
            "appCode": "miguvideo_default_h5",
            "appId": "miguvideo",
            "channel": "H5",
            "terminalId": "h5"
        }
        
        self.lives = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']
        self.LIVE = {
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
        
        self.appVersion = "2600034600"
        self.All_Live = []
        self.FLAG = 0
    
    def md5(self, text):
        """MD5加密"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def getSaltAndSign(self, pid):
        """获取salt和sign"""
        timestamp = str(int(time.time() * 1000))
        random_num = random.randint(0, 999999)
        salt = f"{random_num:06d}25"
        suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
        app_t = timestamp + pid + self.appVersion[:8]
        sign = self.md5(self.md5(app_t) + suffix)
        
        return {
            "salt": salt,
            "sign": sign,
            "timestamp": timestamp
        }
    
    def getddCalcu720p(self, url, pID):
        """生成ddCalcu参数（原逻辑）"""
        puData = url.split("&puData=")[1]
        keys = "cdabyzwxkl"
        ddCalcu = []
        
        for i in range(0, int(len(puData) / 2)):
            ddCalcu.append(puData[int(len(puData)) - i - 1])
            ddCalcu.append(puData[i])
            
            if i == 1:
                ddCalcu.append("v")
            if i == 2:
                date_str = datetime.now().strftime("%Y%m%d")
                ddCalcu.append(keys[int(date_str[2])])
            if i == 3:
                ddCalcu.append(keys[int(pID[6])])
            if i == 4:
                ddCalcu.append("a")
        
        return f'{url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android'
    
    def get_play_url(self, pid):
        """获取播放URL"""
        try:
            result = self.getSaltAndSign(pid)
            rateType = "2" if pid == "608831231" else "3"
            
            url = f"https://play.miguvideo.com/playurl/v1/play/playurl?sign={result['sign']}&rateType={rateType}&contId={pid}&timestamp={result['timestamp']}&salt={result['salt']}"
            
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                return ""
            
            data = response.json()
            play_url = self.getddCalcu720p(data["body"]["urlInfo"]["url"], pid)
            
            # 尝试获取最终播放地址
            for _ in range(6):
                try:
                    resp = requests.get(play_url, allow_redirects=False, timeout=5)
                    location = resp.headers.get("Location", "")
                    
                    if location and location.startswith("http://hlsz"):
                        play_url = location
                        break
                    
                    time.sleep(0.15)
                except:
                    continue
            
            return play_url
        except Exception as e:
            logger.error(f"获取播放URL失败: {e}")
            return ""
    
    def process_migu_channel(self, live, data):
        """处理单个咪咕频道"""
        try:
            channel_name = data.get("name", "")
            pid = data.get("pID", "")
            logo = data.get("pics", {}).get("highResolutionH", "")
            
            play_url = self.get_play_url(pid)
            
            if play_url:
                content = (
                    f'#EXTINF:-1 tvg-id="{channel_name}" '
                    f'tvg-name="{channel_name}" '
                    f'tvg-logo="{logo}" '
                    f'group-title="{live}",{channel_name}\n{play_url}\n'
                )
                logger.info(f"咪咕频道 [{channel_name}] 更新成功！")
                return content
            else:
                logger.warning(f"咪咕频道 [{channel_name}] 更新失败！")
                return None
                
        except Exception as e:
            logger.error(f"处理咪咕频道失败: {e}")
            return None
    
    def update(self, live, url):
        """更新指定分类"""
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"获取分类 {live} 失败")
                return
            
            data = response.json()
            data_list = data.get("body", {}).get("dataList", [])
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_num) as executor:
                futures = []
                for data_item in data_list:
                    future = executor.submit(self.process_migu_channel, live, data_item)
                    futures.append(future)
                    time.sleep(0.1)  # 避免请求过快
                
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        self.All_Live.append(result)
            
        except Exception as e:
            logger.error(f"更新分类 {live} 出错: {e}")
    
    def run(self):
        """运行咪咕更新"""
        logger.info("开始更新咪咕直播源...")
        
        # 写入文件头
        with open('migu.m3u', 'w', encoding='utf-8') as f:
            f.write('#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/erw.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n')
        
        # 更新所有分类
        for live in self.lives:
            logger.info(f"分类 ----- [{live}] ----- 开始更新")
            url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{self.LIVE[live]}'
            self.update(live, url)
            time.sleep(1)  # 避免请求过快
        
        # 写入内容
        with open('migu.m3u', 'a', encoding='utf-8') as f:
            for content in self.All_Live:
                if content:
                    f.write(content)
        
        logger.info(f"咪咕更新完成，共 {len([c for c in self.All_Live if c])} 个频道")


class UnifiedUpdater:
    """统一更新器"""
    def __init__(self, debug_mode=False):
        self.migu_updater = MIGUUpdater()
        self.fengcaizb_updater = FengcaizbUpdater(debug_mode)
        
    def merge_sources(self):
        """合并所有源到一个文件"""
        try:
            # 读取咪咕源
            try:
                with open('migu.m3u', 'r', encoding='utf-8') as f:
                    migu_content = f.read()
            except FileNotFoundError:
                migu_content = "# 咪咕源获取失败\n"
            
            # 读取fengcaizb源
            try:
                with open('fengcaizb.m3u', 'r', encoding='utf-8') as f:
                    fengcaizb_content = f.read().split('\n', 1)
                    if len(fengcaizb_content) > 1:
                        fengcaizb_content = fengcaizb_content[1]  # 跳过文件头
                    else:
                        fengcaizb_content = ""
            except FileNotFoundError:
                fengcaizb_content = "# fengcaizb源获取失败\n"
            
            # 合并并去重
            all_channels = self.deduplicate_channels(migu_content, fengcaizb_content)
            
            # 生成统一的M3U文件头
            unified_header = (
                '#EXTM3U x-tvg-url="https://itv.5iclub.dpdns.org/erw.xml" '
                'catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"\n'
                '# 更新时间: ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n'
            )
            
            # 写入统一文件
            unified_content = unified_header + '\n'.join(all_channels)
            with open('all_live.m3u', 'w', encoding='utf-8') as f:
                f.write(unified_content)
            
            logger.info(f"合并完成，总共 {len(all_channels)} 个频道")
            
            # 生成统计信息
            self.generate_stats(len(all_channels))
            
            return len(all_channels)
            
        except Exception as e:
            logger.error(f"合并源文件失败: {e}")
            return 0
    
    def deduplicate_channels(self, migu_content, fengcaizb_content):
        """去重频道"""
        channels = []
        channel_names = set()
        
        # 处理咪咕源
        if migu_content:
            lines = migu_content.split('\n')
            for i in range(len(lines)):
                if lines[i].startswith('#EXTINF'):
                    channel_info = lines[i]
                    if i + 1 < len(lines) and lines[i + 1].startswith('http'):
                        url = lines[i + 1]
                        # 提取频道名
                        channel_name = channel_info.split('tvg-name="')[1].split('"')[0] if 'tvg-name="' in channel_info else channel_info.split(',')[1]
                        
                        if channel_name not in channel_names:
                            channel_names.add(channel_name)
                            channels.append(channel_info)
                            channels.append(url)
        
        # 处理fengcaizb源
        if fengcaizb_content:
            lines = fengcaizb_content.split('\n')
            for i in range(len(lines)):
                if lines[i].startswith('#EXTINF'):
                    channel_info = lines[i]
                    if i + 1 < len(lines) and lines[i + 1].startswith('http'):
                        url = lines[i + 1]
                        # 提取频道名
                        channel_name = channel_info.split('tvg-name="')[1].split('"')[0] if 'tvg-name="' in channel_info else channel_info.split(',')[1]
                        
                        if channel_name not in channel_names:
                            channel_names.add(channel_name)
                            channels.append(channel_info)
                            channels.append(url)
        
        return channels
    
    def generate_stats(self, total_channels):
        """生成统计信息文件"""
        stats = {
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_channels": total_channels,
            "migu_channels": len(self.migu_updater.All_Live),
            "fengcaizb_channels": self.fengcaizb_updater.sum_channel,
            "sources": ["咪咕视频", "fengcaizb"]
        }
        
        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    
    def run_all(self, run_migu=True, run_fengcaizb=True):
        """运行所有更新"""
        logger.info("=== 开始更新所有直播源 ===\n")
        
        # 更新咪咕源
        if run_migu:
            logger.info("[1/2] 更新咪咕直播源")
            self.migu_updater.run()
            time.sleep(2)
        
        # 更新fengcaizb源
        if run_fengcaizb:
            logger.info("[2/2] 更新fengcaizb直播源")
            count = self.fengcaizb_updater.save_files()
            logger.info(f"fengcaizb源处理完成，共 {count} 个频道")
            time.sleep(2)
        
        # 合并源
        logger.info("[3/3] 合并所有直播源")
        total_channels = self.merge_sources()
        
        logger.info(f"\n=== 所有更新完成！ ===")
        logger.info(f"总计频道数: {total_channels}")
        
        return total_channels


def main():
    """主函数"""
    try:
        # 安装依赖检查
        try:
            import requests
            from Crypto.Cipher import AES
        except ImportError:
            logger.error("缺少依赖，请安装：")
            logger.error("pip install requests pycryptodome")
            return
        
        # 初始化统一更新器
        updater = UnifiedUpdater(debug_mode=False)  # 设置为True可查看调试信息
        
        # 运行所有更新
        total = updater.run_all(run_migu=True, run_fengcaizb=True)
        
        logger.info(f"\n生成的文件:")
        logger.info(f"  - migu.m3u (咪咕源)")
        logger.info(f"  - fengcaizb.m3u (fengcaizb源)")
        logger.info(f"  - fengcaizb.txt (TXT格式源)")
        logger.info(f"  - all_live.m3u (合并所有源)")
        logger.info(f"  - stats.json (统计信息)")
        
    except KeyboardInterrupt:
        logger.info("\n用户中断操作")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()
