from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import re

@register("astrbot_plugin_jm_domain", "TraeAI", "检测JM国内域名", "v1.0", "https://github.com/YourName/astrbot_plugin_jm_domain")
class JMDomain(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.target_url = "https://jmcomicne.net/"
        # 匹配规则：查找"国内域名"附近的链接
        # 匹配规则：查找 class="china" 后的链接
        # HTML示例: <div class="china"><span>https://jm18c-oec.cc</span></div>
        self.pattern = re.compile(r'class=["\']china["\'].*?(https?://[\w.-]+)', re.DOTALL | re.IGNORECASE)

    @filter.command("jm")
    async def check_jm_domain(self, event: AstrMessageEvent):
        """获取JM最新的国内域名"""
        yield event.plain_result("正在检测最新的国内域名，请稍候...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # 设置User-Agent避免被简单的反爬拦截
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                async with session.get(self.target_url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        yield event.plain_result(f"无法访问发布页，状态码: {resp.status}")
                        return
                    
                    html = await resp.text()
                    match = self.pattern.search(html)
                    
                    if match:
                        domain = match.group(1)
                        yield event.plain_result(f"✅ 检测成功！\n目前最新的国内域名为：\n{domain}")
                    else:
                        yield event.plain_result("⚠️ 未能在页面中找到国内域名信息，请检查发布页结构是否变更。")
                        
        except Exception as e:
            logger.error(f"JM插件出错: {e}")
            yield event.plain_result(f"❌ 检测过程中发生错误: {str(e)}")
