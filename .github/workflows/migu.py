import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ====================== 配置参数 ======================
thread_num = 10
appVersion = "2600034600"
appVersionID = f"{appVersion}-99000-201600010010028"

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
    "sec-ch-ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "terminalId": "h5"
}

All_Live = []
FLAG = 0

# 常见两字地方分类（若咪咕返回更多，可在此扩展）
TWO_CHAR_LOCATIONS = {
    '北京', '上海', '天津', '重庆', '江苏', '浙江', '广东', '山东', '四川', '湖北',
    '湖南', '福建', '安徽', '河北', '河南', '陕西', '山西', '江西', '广西', '云南',
    '贵州', '甘肃', '青海', '宁夏', '新疆', '西藏', '海南', '辽宁', '吉林', '黑龙江'
}

def format_date_ymd():
    return datetime.now().strftime("%Y%m%d")

def writefile(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def md5(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def getSaltAndSign(pid):
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + pid + appVersion[:8]
    sign = md5(md5(app_t) + suffix)
    return {"salt": salt, "sign": sign, "timestamp": timestamp}

def get_content(pid):
    """通过 Apipost 代理获取播放地址（保留原有有效方式）"""
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
    result = getSaltAndSign(pid)
    rateType = "3"
    URL = f"https://play.miguvideo.com/playurl/v1/play/playurl?sign={result['sign']}&rateType={rateType}&contId={pid}&timestamp={result['timestamp']}&salt={result['salt']}"
    params = URL.split("?")[1].split("&")

    body = {
        "option": {
            "scene": "http_request",
            "lang": "zh-cn",
            "globals": {},
            "project": {
                "request": {
                    "header": {"parameter": [
                        {"key": "Accept", "value": "*/*", "is_checked": 1, "field_type": "String", "is_system": 1},
                        {"key": "Accept-Encoding", "value": "gzip, deflate, br", "is_checked": 1, "field_type": "String", "is_system": 1},
                        {"key": "User-Agent", "value": "PostmanRuntime-ApipostRuntime/1.1.0", "is_checked": 1, "field_type": "String", "is_system": 1},
                        {"key": "Connection", "value": "keep-alive", "is_checked": 1, "field_type": "String", "is_system": 1}
                    ]},
                    "query": {"parameter": []},
                    "body": {"parameter": []},
                    "cookie": {"parameter": []},
                    "auth": {"type": "noauth"},
                    "pre_tasks": [],
                    "post_tasks": []
                }
            },
            "env": {
                "env_id": "1",
                "env_name": "默认环境",
                "env_pre_url": "",
                "env_pre_urls": {"1": {"server_id": "1", "name": "默认服务", "sort": 1000, "uri": ""}, "default": {"server_id": "1", "name": "默认服务", "sort": 1000, "uri": ""}},
                "environment": {}
            },
            "cookies": {"switch": 1, "data": []},
            "system_configs": {
                "send_timeout": 0,
                "auto_redirect": -1,
                "max_redirect_time": 5,
                "auto_gen_mock_url": -1,
                "request_param_auto_json": -1,
                "proxy": {"type": 2, "envfirst": 1, "bypass": [], "protocols": ["http"], "auth": {"authenticate": -1, "host": "", "username": "", "password": ""}},
                "ca_cert": {"open": -1, "path": "", "base64": ""},
                "client_cert": {}
            },
            "custom_functions": {},
            "collection": [{
                "target_id": "3c5fd6a9786002",
                "target_type": "api",
                "parent_id": "0",
                "name": "MIGU",
                "request": {
                    "auth": {"type": "inherit"},
                    "body": {"mode": "None", "parameter": [], "raw": "", "raw_parameter": [], "raw_schema": {"type": "object"}, "binary": None},
                    "pre_tasks": [],
                    "post_tasks": [],
                    "header": {"parameter": [
                        {"description": "", "field_type": "string", "is_checked": 1, "key": " AppVersion", "value": "2600034600", "not_None": 1, "schema": {"type": "string"}, "param_id": "3c60653273e0b3"},
                        {"description": "", "field_type": "string", "is_checked": 1, "key": "TerminalId", "value": "android", "not_None": 1, "schema": {"type": "string"}, "param_id": "3c6075c1f3e0e1"},
                        {"description": "", "field_type": "string", "is_checked": 1, "key": "X-UP-CLIENT-CHANNEL-ID", "value": "2600034600-99000-201600010010028", "not_None": 1, "schema": {"type": "string"}, "param_id": "3c60858bb3e10c"}
                    ]},
                    "query": {"parameter": [
                        {"param_id": "3c5fd74233e004", "field_type": "string", "is_checked": 1, "key": "sign", "not_None": 1, "value": params[0].split("=")[1], "description": ""},
                        {"param_id": "3c6022f433e030", "field_type": "string", "is_checked": 1, "key": "rateType", "not_None": 1, "value": params[1].split("=")[1], "description": ""},
                        {"param_id": "3c60354133e05b", "field_type": "string", "is_checked": 1, "key": "contId", "not_None": 1, "value": params[2].split("=")[1], "description": ""},
                        {"param_id": "3c605e4bf860b1", "field_type": "String", "is_checked": 1, "key": "timestamp", "not_None": 1, "value": params[3].split("=")[1], "description": ""},
                        {"param_id": "3c605e4c3860b2", "field_type": "String", "is_checked": 1, "key": "salt", "not_None": 1, "value": params[4].split("=")[1], "description": ""}
                    ], "query_add_equal": 1},
                    "cookie": {"parameter": [], "cookie_encode": 1},
                    "restful": {"parameter": []},
                    "tabs_default_active_key": "query"
                },
                "parents": [],
                "method": "POST",
                "protocol": "http/1.1",
                "url": URL,
                "pre_url": ""
            }],
            "database_configs": {}
        },
        "test_events": [{"type": "api", "data": {"target_id": "3c5fd6a9786002", "project_id": "57a21612a051000", "parent_id": "0", "target_type": "api"}}]
    }
    body_json = json.dumps(body, separators=(",", ":"))
    proxy_url = "https://workspace.apipost.net/proxy/v2/http"
    for retry in range(3):
        try:
            resp = requests.post(proxy_url, headers=_headers, data=body_json, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            return json.loads(result["data"]["data"]["response"]["body"])
        except Exception as e:
            if retry == 2:
                raise
            time.sleep(1)

def getddCalcu720p(url, pID):
    if not url or "&puData=" not in url:
        return url
    try:
        puData = url.split("&puData=")[1]
        keys = "cdabyzwxkl"
        ddCalcu = []
        length = len(puData)
        for i in range(0, length // 2):
            ddCalcu.append(puData[length - i - 1])
            ddCalcu.append(puData[i])
            if i == 1:
                ddCalcu.append("v")
            if i == 2:
                ddCalcu.append(keys[int(format_date_ymd()[2])])
            if i == 3:
                ddCalcu.append(keys[int(pID[6])])
            if i == 4:
                ddCalcu.append("a")
        return f"{url}&ddCalcu={''.join(ddCalcu)}&sv=10004&ct=android"
    except Exception:
        return url

def append_All_Live(live, flag, data):
    global All_Live
    channel_name = data.get("name", "未知")
    success = False
    playurl = ""
    try:
        respData = get_content(data["pID"])
        if "body" not in respData or "urlInfo" not in respData["body"]:
            raise ValueError("无urlInfo")
        playurl = respData["body"]["urlInfo"].get("url", "")
        if not playurl:
            raise ValueError("空链接")
        playurl = getddCalcu720p(playurl, data["pID"])
        for z in range(1, 7):
            try:
                obj = requests.get(playurl, allow_redirects=False, timeout=10)
                location = obj.headers.get("Location", "")
                if location and location.startswith("http://hlsz"):
                    playurl = location
                    success = True
                    break
            except Exception:
                pass
            time.sleep(0.15)
        if not success:
            raise Exception("未获取到hlsz地址")
        logo = data.get("pics", {}).get("highResolutionH", "")
        line = (f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" '
                f'tvg-logo="{logo}" group-title="{live}",{channel_name}\n{playurl}\n')
        All_Live[flag] = line
        print(f'✅ [{channel_name}] 成功')
    except Exception as e:
        print(f'❌ [{channel_name}] 失败: {e}')

def update(category_name, url):
    """处理一个分类下的所有频道"""
    global FLAG, All_Live
    print(f"\n📺 分类 【{category_name}】 开始...")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        dataList = resp.json()["body"]["dataList"]
    except Exception as e:
        print(f"❌ 获取列表失败: {e}")
        return

    start_idx = FLAG
    All_Live.extend([""] * len(dataList))
    with ThreadPoolExecutor(max_workers=thread_num) as executor:
        futures = [executor.submit(append_All_Live, category_name, start_idx + idx, data) for idx, data in enumerate(dataList)]
        for future in as_completed(futures):
            future.result()
    FLAG += len(dataList)
    print(f"📺 完成 {len(dataList)} 个频道")

def get_all_categories():
    """获取咪咕所有分类，并规范分类名称"""
    url = "https://program-sc.miguvideo.com/live/v2/category/list"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    raw_cats = resp.json()["body"]["categoryList"]
    normalized = []
    for cat in raw_cats:
        name = cat["name"]
        cid = cat["categoryId"]
        # 1. 数字频道统一为“数字”
        if "数字" in name:
            name = "数字"
        # 2. 地方分类：只保留两字地名（如北京、上海），其余跳过（如“地方”）
        elif name == "地方":
            continue   # 模糊分类，实际频道已在具体省份分类中
        elif name in TWO_CHAR_LOCATIONS:
            pass   # 保留原名
        # 3. 其他分类（热门、央视等）保持不变
        normalized.append({"name": name, "categoryId": cid})
    # 去重（可能多个数字分类合并为同一个“数字”）
    seen = set()
    unique = []
    for cat in normalized:
        key = (cat["name"], cat["categoryId"])
        if key not in seen:
            seen.add(key)
            unique.append(cat)
    return unique

def main():
    # M3U 头部及温馨提示频道
    m3u_content = '#EXTM3U x-tvg-url="https://itv.sspai.pp.ua/erw.xml.gz" catchup="append" catchup-source="?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"\n'
    tip_channels = [
        ("温馨提示", "https://icloud.ifanr.pp.ua/温馨提示.mp4", "https://logo.jsdelivr.dpdns.org/tv/温馨提示.png"),
        ("谨防诈骗", "https://icloud.ifanr.pp.ua/温馨提示.mp4", "https://logo.jsdelivr.dpdns.org/tv/谨防诈骗.png"),
        ("禁止蕉绿", "https://icloud.ifanr.pp.ua/温馨提示.mp4", "https://logo.jsdelivr.dpdns.org/tv/禁止蕉绿.png"),
        ("Cloudflare TV", "https://cloudflare.tv/hls/live.m3u8", "https://logo.jsdelivr.dpdns.org/tv/CloudflareTV.png"),
    ]
    for name, url, logo in tip_channels:
        m3u_content += f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="🦧温馨提示",{name}\n{url}\n'

    # 获取并遍历所有规范后的分类
    try:
        categories = get_all_categories()
        print(f"获取到 {len(categories)} 个分类")
    except Exception as e:
        print(f"获取分类失败: {e}，使用默认12分类")
        # 保底分类（原有12个）
        default_cats = [
            ("热门", "e7716fea6aa1483c80cfc10b7795fcb8"),
            ("央视", "1ff892f2b5ab4a79be6e25b69d2f5d05"),
            ("卫视", "0847b3f6c08a4ca28f85ba5701268424"),
            ("体育", "7538163cdac044398cb292ecf75db4e0"),
            ("影视", "10b0d04cb23d4ac5945c4bc77c7ac44e"),
            ("新闻", "c584f67ad63f4bc983c31de3a9be977c"),
            ("教育", "af72267483d94275995a4498b2799ecd"),
            ("熊猫", "e76e56e88fff4c11b0168f55e826445d"),
            ("综艺", "192a12edfef04b5eb616b878f031f32f"),
            ("少儿", "fc2f5b8fd7db43ff88c4243e731ecede"),
            ("纪实", "e1165138bdaa44b9a3138d74af6c6673")
        ]
        categories = [{"name": name, "categoryId": cid} for name, cid in default_cats]

    for cat in categories:
        cat_name = cat["name"]
        cat_id = cat["categoryId"]
        print(f"\n========== 分类 [{cat_name}] ==========")
        url = f"https://program-sc.miguvideo.com/live/v2/tv-data/{cat_id}"
        update(cat_name, url)

    # 写入 M3U 文件
    for line in All_Live:
        if line:
            m3u_content += line
    writefile("MiGu.m3u", m3u_content)
    print("\n✨ MiGu.m3u 生成完毕")

    # 生成 TXT 格式
    txt_lines = ["🦧温馨提示,#genre#"]
    for name, url, _ in tip_channels:
        txt_lines.append(f"{name},{url}")
    current_group = ""
    for line in All_Live:
        if not line:
            continue
        parts = line.strip().split('\n')
        for i in range(0, len(parts), 2):
            if i+1 >= len(parts):
                break
            inf = parts[i]
            url_line = parts[i+1]
            try:
                group = inf.split('group-title="')[1].split('"')[0]
                name = inf.split(',')[-1].strip()
                if group != current_group:
                    current_group = group
                    txt_lines.append(f"{current_group},#genre#")
                txt_lines.append(f"{name},{url_line}")
            except Exception:
                continue
    writefile("MiGu.txt", "\n".join(txt_lines) + "\n")
    print("✨ MiGu.txt 生成完毕")

if __name__ == "__main__":
    main()
