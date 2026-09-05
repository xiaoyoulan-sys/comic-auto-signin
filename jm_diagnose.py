"""
JM 签到接口诊断脚本
用于调试 /daily_list/filter 和 /daily_chk 接口的实际响应
"""
import logging
import json
import time
from jmcomic import JmOption, JmModuleConfig, JmCryptoTool

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def diagnose(username, password):
    # 清除缓存
    if hasattr(JmModuleConfig, 'APP_COOKIES'):
        delattr(JmModuleConfig, 'APP_COOKIES')

    option = JmOption.construct({
        "client": {
            "username": username,
            "password": password,
        }
    })
    client = option.build_jm_client()

    # 登录
    logging.info("=== 登录 ===")
    login_resp = client.login(username, password)
    logging.info(f"登录响应状态码: {login_resp.status_code}")
    logging.info(f"登录响应cookies: {dict(login_resp.cookies)}")

    # 检查 client 的 cookies/postman cookies
    postman = client.get_root_postman()
    if hasattr(postman, 'cookies'):
        logging.info(f"Postman cookies: {postman.cookies}")
    if hasattr(postman, 'session') and hasattr(postman.session, 'cookies'):
        logging.info(f"Session cookies: {dict(postman.session.cookies)}")

    # 获取当前域名
    domain = client.get_domain_list()[0]
    logging.info(f"当前API域名: {domain}")

    # ========== 测试1: 通过 req_api 调用（标准方式）==========
    logging.info("\n=== 测试1: req_api 标准调用 ===")
    year = str(time.localtime().tm_year)
    try:
        resp = client.req_api('/daily_list/filter', get=False, data={'data': year})
        logging.info(f"状态码: {resp.status_code}")
        logging.info(f"JSON响应: {resp.json()}")
        logging.info(f"encoded_data: {resp.encoded_data}")
        try:
            logging.info(f"decoded_data: {resp.decoded_data}")
        except Exception as e:
            logging.info(f"decoded_data 解密失败: {e}")
        try:
            logging.info(f"res_data: {resp.res_data}")
        except Exception as e:
            logging.info(f"res_data 失败: {e}")
    except Exception as e:
        logging.info(f"req_api 失败: {e}")

    # ========== 测试2: 直接 POST（绕过加密）==========
    logging.info("\n=== 测试2: 直接 POST 请求 ===")
    url = f"https://{domain}/daily_list/filter"
    try:
        resp = client.post(url, data={'data': year})
        logging.info(f"状态码: {resp.status_code}")
        logging.info(f"响应头 Content-Type: {resp.headers.get('Content-Type')}")
        text = resp.text[:500]
        logging.info(f"响应文本(前500字符): {text}")
        try:
            j = resp.json()
            logging.info(f"JSON解析: {j}")
        except:
            logging.info("非JSON响应")
    except Exception as e:
        logging.info(f"直接POST失败: {e}")

    # ========== 测试3: 尝试 GET 请求 ==========
    logging.info("\n=== 测试3: GET 请求 ===")
    try:
        resp = client.get(url, params={'data': year})
        logging.info(f"状态码: {resp.status_code}")
        text = resp.text[:500]
        logging.info(f"响应文本(前500字符): {text}")
    except Exception as e:
        logging.info(f"GET请求失败: {e}")

    # ========== 测试4: 尝试不同的参数名 ==========
    logging.info("\n=== 测试4: 不同参数名 ===")
    for param_name in ['year', 'y', 'data']:
        try:
            resp = client.req_api('/daily_list/filter', get=False, data={param_name: year})
            logging.info(f"参数 {param_name}={year}: code={resp.json().get('code')}, data={resp.json().get('data')}")
        except Exception as e:
            logging.info(f"参数 {param_name}={year} 失败: {e}")

    # ========== 测试5: 检查 APP_VERSION ==========
    logging.info(f"\n=== 当前 APP_VERSION: {JmModuleConfig.APP_VERSION} ===")

    # ========== 测试6: 尝试不带参数调用 ==========
    logging.info("\n=== 测试6: 不带参数调用 ===")
    try:
        resp = client.req_api('/daily_list/filter', get=False, data={})
        logging.info(f"无参数: {resp.json()}")
    except Exception as e:
        logging.info(f"无参数失败: {e}")

    # ========== 测试7: 检查 /daily_chk 接口 ==========
    logging.info("\n=== 测试7: 尝试 /daily_chk 接口 ===")
    try:
        resp = client.req_api('/daily_chk', get=False, data={'user_id': '0', 'daily_id': '0'})
        logging.info(f"daily_chk 响应: {resp.json()}")
    except Exception as e:
        logging.info(f"daily_chk 失败: {e}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 3:
        diagnose(sys.argv[1], sys.argv[2])
    else:
        print("用法: python jm_diagnose.py <用户名> <密码>")
