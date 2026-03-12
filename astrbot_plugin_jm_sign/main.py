from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import aiohttp
import re
import os
import json
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

@register("astrbot_plugin_jm_sign", "cloudcranesss", "JMComic每日签到", "1.0.0", "https://github.com/cloudcranesss/astrbot_plugins")
class JMSign(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.scheduler = AsyncIOScheduler()
        
        # 目标发布页列表
        self.target_urls = [
            "https://jmcomicne.net/",
            "https://jmcomic1.bet/",
            "https://jmcomic.me/"
        ]
        # 匹配规则：查找 class="china" 后的链接
        self.pattern = re.compile(r'class=["\']china["\'].*?(https?://[\w.-]+)', re.DOTALL | re.IGNORECASE)

        # 注册定时任务
        if self.config.get("enable_cron", False):
            # 由于 AstrBot 未直接暴露调度器，使用 on_astrbot_loaded 钩子启动自定义循环
            pass

    @filter.on_astrbot_loaded()
    async def on_start(self):
        """插件加载完成后启动定时任务"""
        if self.config.get("enable_cron", False):
            cron_exp = self.config.get("cron_expression", "0 8 * * *")
            try:
                logger.info(f"JM签到插件：已启用定时任务，Cron: {cron_exp}")
                # 解析 cron 表达式
                # 格式: 分 时 日 月 周
                minute, hour, day, month, day_of_week = cron_exp.split()
                
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                )
                
                # 添加任务
                self.scheduler.add_job(self.run_cron_job, trigger)
                self.scheduler.start()
            except Exception as e:
                logger.error(f"启动定时任务失败: {e}")

    async def run_cron_job(self):
        """定时任务执行入口"""
        logger.info("JM签到定时任务：开始执行...")
        try:
            # 必须使用 async for 消耗生成器
            async for item in self.run_batch_sign(is_cron=True):
                # run_batch_sign 作为生成器，会 yield 消息字符串
                # 我们可以在这里记录日志，方便调试
                logger.info(f"JM签到任务进度: {item}")
        except Exception as e:
            logger.error(f"JM签到定时任务执行异常: {e}")

    async def terminate(self):
        """插件卸载时停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("JM签到插件：定时任务调度器已停止")

    async def run_batch_sign(self, is_cron=False, event: AstrMessageEvent = None):
        """批量执行签到"""
        # 获取配置的账号
        accounts_conf = self.config.get("accounts", [])
        
        task_list = []
        
        for item in accounts_conf:
                # 确保是字符串
                val = str(item).strip()
                if ':' in val:
                    parts = val.split(':', 1)
                    if len(parts) == 2:
                        user = parts[0].strip()
                        pwd = parts[1].strip()
                        if user and pwd:
                            if not any(t["username"] == user for t in task_list):
                                task_list.append({"username": user, "password": pwd})
                elif '@' in val:
                    parts = val.split('@', 1)
                    if len(parts) == 2:
                        user = parts[0].strip()
                        pwd = parts[1].strip()
                        if user and pwd:
                            if not any(t["username"] == user for t in task_list):
                                task_list.append({"username": user, "password": pwd})
    
        
        if not task_list:
            msg = "❌ 未配置任何账号，无法执行签到。"
            if event: yield event.plain_result(msg)
            else: logger.warning(msg)
            return

        # 获取域名
        if event: yield event.plain_result("⏳ 正在获取域名列表...")
        domains = await self.get_domains()
        
        if not domains:
            msg = "❌ 无法获取有效域名，签到中止。"
            if event: yield event.plain_result(msg)
            else: logger.error(msg)
            return
            
        # 结果汇总
        results = []
        
        for account in task_list:
            username = account["username"]
            password = account["password"]
            
            if event: yield event.plain_result(f"⏳ 正在为 {username} 签到...")
            
            # 执行单个账号签到
            res = await self.sign_one_account(username, password, domains)
            # 尝试从结果中提取更友好的用户名
            display_name = username
            if "👤 用户:" in res:
                try:
                    match = re.search(r"👤 用户: (.*?)\n", res)
                    if match:
                        display_name = match.group(1).strip()
                except:
                    pass
            
            results.append(f"用户: {display_name}\n{res}")
            
        final_msg = "=== JMComic 批量签到报告 ===\n\n" + "\n\n".join(results)
        
        # 发送消息 (仅当由指令触发时)
        if event:
            yield event.plain_result(final_msg)
        else:
            # 定时任务触发时，仅记录日志，不再推送通知
            logger.info(final_msg)

    async def sign_one_account(self, username, password, domains):
        """执行单个账号的签到逻辑"""
        success = False
        last_error = None
        result_msg = ""
        
        for domain in domains:
            domain = domain.rstrip('/')
            
            login_url = f"{domain}/login"
            sign_url = f"{domain}/ajax/user_daily_sign"

            logger.info(f"正在为 {username} 签到，域名: {domain}")
            
            try:
                # 禁用SSL验证以绕过自签名证书问题
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Referer": domain
                    }
                    
                    # 1. 登录
                    try:
                        async with session.post(login_url, data={
                            "username": username,
                            "password": password,
                            "submit_login": "1"
                        }, headers=headers, timeout=10) as login_resp:
                            if login_resp.status >= 400:
                                last_error = f"登录失败 {login_resp.status}"
                                continue
                    except Exception as e:
                        last_error = str(e)
                        continue

                    # 2. 签到
                    async with session.post(sign_url, headers=headers, timeout=10) as sign_resp:
                        if sign_resp.status == 200:
                            try:
                                # 指定 content_type=None 以兼容非标准 MIME 类型
                                result = await sign_resp.json(content_type=None)
                                
                                msg = "未知结果"
                                if "msg" in result:
                                    msg = result["msg"]
                                    if not msg:
                                        if result.get("error") == "finished":
                                            msg = "今天已经签到过了 (finished)"
                                        else:
                                            msg = "签到成功"
                                elif "message" in result:
                                    msg = result["message"]
                                else:
                                    msg = str(result)
                                
                                # 3. 获取用户信息
                                user_info = await self.get_user_info(session, domain)
                                info_str = ""
                                if user_info:
                                    info_str = (
                                        f"\n🔰 Lv.{user_info.get('level', '?')} | 💰 {user_info.get('coins', '?')}\n"
                                        f"⭐ 可收藏: {user_info.get('fav_count', '?')} | 📈 经验: {user_info.get('exp', '?')}\n"
                                        f"🏷️ 称号: {user_info.get('title', '无')}"
                                    )
                                    
                                result_msg = f"✅ {msg}{info_str}"
                                success = True
                                break 
                            except Exception as e:
                                result_msg = f"⚠️ 请求成功但解析失败: {e}"
                                success = True
                                break
                        else:
                            last_error = f"接口错误 {sign_resp.status}"
            except Exception as e:
                last_error = str(e)
                
        if not success:
            result_msg = f"❌ 失败: {last_error}"
            
        return result_msg

    async def get_user_info(self, session, domain):
        """获取用户信息"""
        try:
            # 访问用户页面以获取头部信息
            url = f"{domain}/user"
            async with session.get(url, headers={"Referer": domain}, timeout=10) as resp:
                if resp.status != 200:
                    return None
                
                html = await resp.text()
                
                info = {}
                
                # 提取昵称
                name_match = re.search(r'class="header-right-username">@?(.*?)<', html)
                if name_match:
                    info['name'] = name_match.group(1).strip()
                    
                # 提取等级和经验
                # 匹配结构: <div class="header-profile-row-value"> 8 <span class="header-profile-exp">(18603/28350)</span> </div> <div class="header-profile-row-name">等级</div>
                level_match = re.search(r'(\d+)\s*<span class="header-profile-exp">\((.*?)\)</span>[\s\S]*?等级', html)
                if level_match:
                    info['level'] = level_match.group(1)
                    info['exp'] = level_match.group(2)
                    
                # 提取收藏数
                # 结构：<div class="header-profile-row-value">1,200</div> <div class="header-profile-row-name">可收藏数</div>
                fav_match = re.search(r'>([\d,]+)</div>\s*<div class="header-profile-row-name">.*?可收藏数', html)
                if fav_match:
                    info['fav_count'] = fav_match.group(1)

                # 提取等级进度百分比
                # 从经验值计算或直接提取，这里使用已提取的经验值字符串 (18603/28350)
                if 'exp' in info:
                    info['exp_percent'] = info['exp']

                # 提取 J Coins
                # 尝试更简单的正则：在 "J Coins" 之前寻找最近的数字 div
                # ... <div class="header-profile-row-value">23262</div>...J Coins
                try:
                    # 截取 "J Coins" 之前的 500 个字符
                    jcoins_idx = html.find("J Coins")
                    if jcoins_idx != -1:
                        # 从 "J Coins" 往前截取
                        snippet = html[max(0, jcoins_idx-500):jcoins_idx]
                        # 查找最后一个 header-profile-row-value 的内容
                        # <div class="header-profile-row-value">23262</div>
                        # <div class="header-profile-row-name">
                        matches = re.findall(r'class="header-profile-row-value">\s*([\d,]+)\s*</div>', snippet)
                        if matches:
                            # 最后一个匹配项应该是 J Coins 对应的数值
                            info['coins'] = matches[-1]
                except Exception as e:
                    logger.error(f"提取 J Coins 失败: {e}")
                    
                # 提取称号
                title_match = re.search(r'class="header-profile-row-value user-current-title">\s*(.*?)\s*<!--', html)
                if title_match:
                    info['title'] = title_match.group(1).strip()
                    
                return info
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None

    async def get_domains(self):
        """获取JM域名列表，优先使用配置"""
        domains = []
        
        # 1. 配置的域名
        domain_conf = self.config.get("domain")
        if domain_conf:
            logger.info(f"添加配置的域名: {domain_conf}")
            domains.append(domain_conf)
        
        # 2. 自动获取
        # 遍历所有发布页
        for url in self.target_urls:
            try:
                logger.info(f"尝试从发布页获取域名: {url}")
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    async with session.get(url, headers=headers, timeout=5) as resp:
                        if resp.status == 200:
                            html = await resp.text()
                            # 查找所有链接
                            urls = self.pattern.findall(html)
                            
                            if urls:
                                logger.info(f"从 {url} 获取到域名: {urls}")
                                for d in urls:
                                    if d not in domains:
                                        domains.append(d)
                                # 如果成功获取到，就不再尝试其他发布页
                                break
            except Exception as e:
                logger.warning(f"访问发布页 {url} 失败: {e}")
            
        return domains

    @filter.command("jmsign")
    async def jm_sign(self, event: AstrMessageEvent):
        """执行JMComic签到"""
        # 权限检查：如果配置了白名单，仅允许白名单用户执行
        whitelist = self.config.get("whitelist_users", [])
        if whitelist:
            sender = event.get_sender_id()
            if sender not in whitelist and str(sender) not in whitelist:
                yield event.plain_result("🚫 您没有权限执行此指令。")
                return

        # 调用批量签到逻辑
        # 注意：这里需要手动迭代，因为 jm_sign 本身是异步生成器
        async for item in self.run_batch_sign(is_cron=False, event=event):
            yield item


