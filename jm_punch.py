import logging
import time
from jmcomic import JmOption, JmModuleConfig


class JmPuncher:
    """
    禁漫天堂自动签到类
    基于 jmcomic 库实现，模拟移动端 API 登录 + 签到

    签到流程：
    1. 调用 /login 登录，获取 uid 和 session
    2. 调用 /daily_list/filter 获取当年签到任务列表
    3. 取最新一条任务的 id，调用 /daily_chk 完成签到
    """

    def __init__(self, username, password, proxy=None):
        self.username = username
        self.password = password
        self.proxy = proxy

    def _clear_global_cookies(self):
        """清除 jmcomic 全局 cookies 缓存，避免多账号间 session 复用"""
        if hasattr(JmModuleConfig, 'APP_COOKIES'):
            delattr(JmModuleConfig, 'APP_COOKIES')

    def _get_daily_task_list(self, client):
        """
        获取当年签到任务列表
        接口: POST /daily_list/filter
        参数: data=年份(如 2026)
        返回: {"list": [{"id": "...", "year": "...", "month": "...", "img": "..."}, ...]}
        """
        year = str(time.localtime().tm_year)
        resp = client.req_api(
            '/daily_list/filter',
            get=False,
            data={'data': year},
        )
        return resp.res_data

    def _do_daily_checkin(self, client, user_id, daily_id):
        """
        执行签到
        接口: POST /daily_chk
        参数: user_id=用户ID, daily_id=任务ID
        返回: {"success": bool, "message": "...", "msg": "..."}
        """
        resp = client.req_api(
            '/daily_chk',
            get=False,
            data={'user_id': user_id, 'daily_id': daily_id},
        )
        return resp.res_data

    def run(self):
        try:
            # 清除全局 cookies 缓存，确保每个账号使用独立 session
            self._clear_global_cookies()

            # 构造禁漫配置
            option = JmOption.construct(
                {
                    "client": {
                        "username": self.username,
                        "password": self.password,
                        "proxies": {"http": self.proxy, "https": self.proxy}
                        if self.proxy
                        else None,
                    }
                }
            )
            client = option.build_jm_client()

            # ========== 第一步：登录 ==========
            logging.info(f"正在尝试登录 JM (账号: {self.username})...")
            resp = client.login(self.username, self.password)
            user_data = resp.res_data

            # 验证登录返回的用户名是否与请求账号一致
            actual_username = user_data.get("username", "")
            if actual_username != self.username:
                logging.error("=" * 20)
                logging.error("❌ JM 登录验证失败！")
                logging.error(f"   期望账号: {self.username}")
                logging.error(f"   实际登录: {actual_username}")
                logging.error("   可能原因: 会话缓存导致登录了错误账号")
                logging.error("=" * 20)
                return False

            user_id = user_data.get("uid", "")
            logging.info(f"🎉 JM 登录成功！用户名: {actual_username}，金币: {user_data.get('coin')}")

            # ========== 第二步：获取签到任务列表 ==========
            logging.info("正在获取签到任务列表...")
            daily_list_data = self._get_daily_task_list(client)
            task_list = daily_list_data.get("list", [])

            if not task_list:
                logging.warning("⚠️ 签到任务列表为空，当前无可用签到任务")
                return False

            # 取最新的一条任务（列表末尾）
            latest_task = task_list[-1]
            daily_id = latest_task.get("id", "")

            if not daily_id:
                logging.error("❌ 签到任务 ID 为空")
                return False

            logging.info(f"找到签到任务: id={daily_id}, "
                         f"year={latest_task.get('year')}, month={latest_task.get('month')}")

            # ========== 第三步：执行签到 ==========
            logging.info("正在执行签到...")
            checkin_result = self._do_daily_checkin(client, user_id, daily_id)

            # 解析签到结果
            msg = checkin_result.get("msg", "")
            success = checkin_result.get("success", False)
            message = checkin_result.get("message", "")

            if msg == "今天已经签到过了":
                logging.info("✅ 今天已经签到过了，无需重复签到")
            elif msg:
                logging.info(f"✅ 签到成功！{msg}")
            elif success:
                logging.info(f"✅ 签到成功！{message}")
            else:
                logging.warning(f"⚠️ 签到结果未知，响应: {checkin_result}")

            logging.info("=" * 20)
            logging.info(f"账号: {self.username}")
            logging.info(f"金币余额: {user_data.get('coin')}")
            logging.info("=" * 20)
            return True

        except Exception as e:
            logging.error(f"JM 运行异常: {e}")
            return False
