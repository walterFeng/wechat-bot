from BotServer.MainServer import MainServer
from cprint import cprint
import signal
import time
import sys
import requests
import qrcode
import urllib.parse
import json
import os
import subprocess

# 硬编码配置参数
WXAPI_URL = "http://localhost:7123"  # 本地测试URL
WXAPI_WS_URL = "ws://localhost:8899/ws"  # WebSocket URL
DEFAULT_SELFWXID = "wxid_ucndvf3dz8nr121"  # 默认WXID，将在登录成功后更新

# 配置文件路径
CONFIG_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DPbot_config.json")

Bot_Logo = """


 _______  .______   .______     ______   .___________.
|       \ |   _  \  |  |_)  | |  |  |  | `---|  |----`
|  .--.  ||  |_)  | |   _  <  |  |  |  |     |  |     
|  |  |  ||   ___/  |  |_)  | |  `--'  |     |  |     
|  '--'  ||  |      |______/   \______/      |__|     
|_______/ | _|      |______/   \______/      |__|     
                                                      
     Version: V1.0
     Author: 大鹏                                             

"""

# 用于存储登录后的WXID
USER_WXID = None
USER_NICKNAME = None

def save_config_to_json():
    """将配置保存到JSON文件"""
    global USER_WXID, USER_NICKNAME
    
    if not USER_WXID or not USER_NICKNAME:
        cprint.warn("无有效的WXID信息，无法保存配置")
        return False
    
    config_data = {
        "wxapi_url": WXAPI_URL,
        "wxapi_ws_url": WXAPI_WS_URL,
        "user_wxid": USER_WXID,
        "user_nickname": USER_NICKNAME,
        "last_login_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        with open(CONFIG_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        cprint.ok(f"配置已保存到: {CONFIG_JSON_PATH}")
        return True
    except Exception as e:
        cprint.err(f"保存配置失败: {e}")
        return False

def load_config_from_json():
    """从JSON文件加载配置"""
    global USER_WXID, USER_NICKNAME
    
    if not os.path.exists(CONFIG_JSON_PATH):
        cprint.info("未找到配置文件，将使用默认配置")
        return False
    
    try:
        with open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        USER_WXID = config_data.get("user_wxid")
        USER_NICKNAME = config_data.get("user_nickname")
        
        cprint.ok("配置加载成功:")
        cprint.info(f"用户WXID: {USER_WXID}")
        cprint.info(f"用户昵称: {USER_NICKNAME}")
        cprint.info(f"上次登录时间: {config_data.get('last_login_time', '未知')}")
        
        return True if USER_WXID and USER_NICKNAME else False
    except Exception as e:
        cprint.err(f"加载配置失败: {e}")
        return False

class WxApiService:
    def __init__(self, url=WXAPI_URL, timeout=30):  # 使用硬编码的URL
        self.url = url
        self.timeout = timeout
    
    """检查wxapi服务是否可用"""
    def check_service_available(self, max_retries=5, retry_delay=3):
        cprint.info(f"正在检查wxapi服务是否可用 ({self.url})...")
        
        # 添加健康检查端点（如果有的话）
        health_endpoint = f"{self.url}/api/status"  # 假设有这样的端点
        
        for attempt in range(max_retries):
            try:
                # 尝试使用更短的超时时间先测试连接
                response = requests.get(self.url, timeout=min(5, self.timeout))
                
                # 检查状态码和可能的响应内容
                if response.status_code == 200:
                    # 可以增加对响应内容的验证
                    # 例如: if "status" in response.json() and response.json()["status"] == "ok":
                    cprint.ok("wxapi服务连接成功!")
                    return True
                else:
                    cprint.warn(f"API服务返回异常状态码: {response.status_code}")
            except Exception as e:  # 捕获所有可能的异常
                error_type = type(e).__name__
                cprint.warn(f"尝试连接wxapi服务失败 (尝试 {attempt+1}/{max_retries}): {error_type}: {e}")
                
                if attempt < max_retries - 1:
                    cprint.info(f"将在 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
        
        cprint.err("无法连接到wxapi服务，请确保wxapi已正确启动")
        cprint.info("您可以:")
        cprint.info("1. 检查wxapi服务是否正常运行")
        cprint.info("2. 检查网络连接")
        cprint.info("3. 验证配置中的URL是否正确")
        cprint.info("4. 重新启动程序")
        
        return False
     
    """调用 /Login/GetQRCar 提交参数并显示二维码，并轮询等待登录"""    
    def post_login_qr(self):
        """获取新的二维码"""
        def get_qr_code():
            try:
                url = f"{self.url}/api/Login/GetQRCar"
                payload = {
                    "DeviceID": "123456",
                    "DeviceName": "Dpbot",
                    "Proxy": {
                        "ProxyIp": "",
                        "ProxyPassword": "",
                        "ProxyUser": ""
                    }
                }
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }
                response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                cprint.err(f"获取二维码失败: {e}")
                raise

        """在控制台打印二维码并自动弹出图片"""
        def display_qr_code(real_url):
            # 先在控制台显示二维码
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=2,
                border=1
            )
            qr.add_data(real_url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
            
            # 生成图片二维码并保存
            try:
                # 二维码图片路径
                qr_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_qr.png")
                
                # 创建更高质量的二维码图片
                img_qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=10,
                    border=4
                )
                img_qr.add_data(real_url)
                img_qr.make(fit=True)
                
                img = img_qr.make_image(fill_color="black", back_color="white")
                img.save(qr_img_path)
                
                cprint.ok(f"二维码图片已保存到: {qr_img_path}")
                
                # 自动打开图片
                try:
                    cprint.info("正在自动打开二维码图片...")
                    if sys.platform == 'win32':
                        os.startfile(qr_img_path)
                    elif sys.platform == 'darwin':  # macOS
                        subprocess.call(['open', qr_img_path])
                    else:  # Linux
                        subprocess.call(['xdg-open', qr_img_path])
                except Exception as e:
                    cprint.warn(f"无法自动打开图片: {e}")
                    cprint.info(f"请手动打开二维码图片: {qr_img_path}")
            except Exception as e:
                cprint.err(f"生成二维码图片失败: {e}")

        try:
            max_retries = 3
            for qr_attempt in range(max_retries):
                try:
                    # Step 1: 获取二维码
                    qr_data = get_qr_code()

                    uuid = qr_data["Data"]["Uuid"]
                    qr_url = qr_data["Data"]["QrUrl"]

                    # 提取真正的微信登录地址
                    parsed = urllib.parse.urlparse(qr_url)
                    real_qr_data = urllib.parse.parse_qs(parsed.query)["data"][0]

                    # 打印提示信息
                    cprint.err("\n==================================")
                    cprint.warn("==> 等待手机扫描二维码以登录微信...")
                    cprint.err("==================================")

                    # Step 2: 显示二维码
                    display_qr_code(real_qr_data)

                    # Step 3: 开始轮询检测登录状态
                    check_url = f"{self.url}/api/Login/CheckQR"
                    headers = {
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    }
                    
                    inner_max_checks = 10
                    for attempt in range(inner_max_checks):
                        try:
                            check_response = requests.post(check_url, params={"uuid": uuid}, headers=headers, timeout=self.timeout)
                            if check_response.status_code == 200:
                                check_result = check_response.json()
                                if check_result.get("Code") == 0 and check_result.get("Success") == True:
                                    acct_sect_resp = (check_result.get("Data") or {}).get("acctSectResp")
                                    
                                    if acct_sect_resp and acct_sect_resp.get("userName"):
                                        cprint.ok("\n==================================")
                                        cprint.ok("恭喜，登录成功！")
                                        print(f"用户昵称: {acct_sect_resp.get('nickName')}")
                                        print(f"微信号: {acct_sect_resp.get('alias')}")
                                        print(f"手机号: {acct_sect_resp.get('bindMobile')}")
                                        
                                        # 更新全局变量
                                        global USER_WXID, USER_NICKNAME
                                        USER_WXID = acct_sect_resp.get('userName')
                                        USER_NICKNAME = acct_sect_resp.get('nickName')
                                        
                                        # 保存配置到JSON文件
                                        save_config_to_json()
                                        
                                        # 登录成功后清理临时文件
                                        try:
                                            qr_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_qr.png")
                                            if os.path.exists(qr_img_path):
                                                os.remove(qr_img_path)
                                        except:
                                            pass
                                        
                                        return  # 登录成功，跳出循环
                                    else:
                                        print(f"⌛ 等待用户扫码登录... {attempt+1}/{inner_max_checks}", end="\r", flush=True)
                                else:
                                    cprint.err("获取登录状态时出错...")
                            else:
                                cprint.err("连接服务器获取登录状态时出错...")
                        except requests.RequestException as e:
                            cprint.err(f"检查登录状态请求出错: {e}")
                            print(f"⌛ 等待片刻后重试... {attempt+1}/{inner_max_checks}", end="\r", flush=True)
                            
                        # 每隔3秒检测一次
                        time.sleep(3)
                    
                    # 如果内部循环结束后仍未登录成功，则重试获取二维码
                    if qr_attempt < max_retries - 1:
                        cprint.warn(f"扫码登录超时或失败，将重新获取二维码 (尝试 {qr_attempt+2}/{max_retries})...")
                        time.sleep(1)
                        
                    break  # 跳出二维码获取循环
                
                except requests.RequestException as e:
                    if qr_attempt < max_retries - 1:
                        cprint.err(f"获取二维码失败: {e}")
                        cprint.info(f"将在3秒后重试... (尝试 {qr_attempt+2}/{max_retries})")
                        time.sleep(3)
                    else:
                        raise

            # 如果所有尝试都失败
            cprint.err("多次尝试后仍未能完成登录，请检查网络和服务状态")

        except requests.RequestException as e:
            cprint.err(f"请求出错: {e}")
            cprint.info("请检查wxapi服务是否正常运行，网络是否正常连接。")
        except Exception as e:
            cprint.err(f"发生异常: {e}")
            cprint.info("请尝试重新启动程序并检查配置。")
            
    def run(self):
        """实现自动扫码登录功能"""
        cprint.info("开始自动扫码登录流程...")
        
        # 先检查服务是否可用
        if not self.check_service_available():
            choice = input("是否仍要尝试登录？(y/n): ").strip().lower()
            if choice != 'y':
                cprint.warn("已取消登录流程")
                return False
                
        # 调用扫码登录方法
        self.post_login_qr()
        cprint.ok("登录成功，准备启动主服务...")
        return True

def shutdown(signum, frame):
    global Ms
    try:
        if Ms and hasattr(Ms, 'Pms') and hasattr(Ms.Pms, 'stopPushServer'):
            Ms.Pms.stopPushServer()
    except Exception as e:
        print(f"关闭服务时出错: {e}")
    finally:
        time.sleep(2)
        sys.exit(0)

# 全局变量
Ms = None

def main():
    global Ms, USER_WXID, USER_NICKNAME
    cprint.info(Bot_Logo.strip())
    
    # 加载保存的配置
    config_loaded = load_config_from_json()
    
    # 询问是否需要登录
    cprint.info("\n==================================")
    if config_loaded:
        cprint.info(f"检测到已保存的登录信息: {USER_NICKNAME}")
    cprint.info("是否需要重新登录？(y/n): ")
    cprint.info("输入y进行扫码登录，输入n跳过登录直接启动")
    cprint.info("==================================")
    
    # 处理命令行参数，如果有--force参数则强制登录
    force_login = False
    if len(sys.argv) > 1 and sys.argv[1].lower() in ['-f', '--force']:
        cprint.warn("检测到强制登录参数，将执行登录流程...")
        force_login = True
    
    if not force_login:
        while True:
            choice = input().strip().lower()
            if choice == 'y':
                do_login = True
                break
            elif choice == 'n':
                if not config_loaded:
                    cprint.err("未检测到有效的登录信息，必须进行登录")
                    do_login = True
                else:
                    do_login = False
                break
            else:
                cprint.warn("无效输入，请输入y或n")
    else:
        do_login = True
    
    # 根据选择决定是否执行登录流程
    login_success = True
    if do_login:
        Wxapi_service = WxApiService(url=WXAPI_URL)
        login_success = Wxapi_service.run()
    else:
        cprint.ok("跳过登录，直接启动主服务...")
        cprint.info(f"使用保存的配置 - WXID: {USER_WXID}, 昵称: {USER_NICKNAME}")
    
    # 启动主服务
    if login_success or not do_login:
        try:
            # 创建MainServer时传入必要的配置信息
            Ms = MainServer(self_wxid=USER_WXID, base_url=WXAPI_URL, ws_url=WXAPI_WS_URL)
            
            # 为MainServer设置wxid和其他属性
            if hasattr(Ms, 'wcf'):
                Ms.wcf.self_wxid = USER_WXID
                Ms.wcf.base_url = WXAPI_URL
                Ms.wcf.ws_url = WXAPI_WS_URL
                cprint.ok(f"已设置MainServer配置: WXID={USER_WXID}")
            
            try:
                Ms.processMsg()
            except KeyboardInterrupt:
                shutdown(signal.SIGINT, None)
        except Exception as e:
            cprint.err(f"启动主服务失败: {e}")
            cprint.info("请检查服务配置并重新启动程序。")
    else:
        cprint.err("登录未成功完成，无法启动主服务")
        cprint.info("请重新启动程序并尝试登录")

if __name__ == '__main__':
    # 注册信号处理器，以便优雅退出
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    main()
