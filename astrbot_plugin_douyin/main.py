import re
import asyncio
import aiohttp
from aiohttp import ClientSession, ClientTimeout
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69"
}

DEFAULT_TIMEOUT = ClientTimeout(total=15)

DOUYIN_PATTERN = re.compile(r"https?://v\.douyin\.com/[^/\s]+")

MAX_RETRIES = 3
RETRY_DELAY = 1


@register("douyin", "Trae", "解析抖音链接，提取视频信息、封面、背景音乐等", "1.0.0")
class DouyinPlugin(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.config = config
        self.api_id = self.config.get("api_id", "88888888")
        self.api_key = self.config.get("api_key", "88888888")
        self.timeout = self.config.get("timeout", 30)
        self.api_url = "https://cn.apihz.cn/api/fun/douyin.php"
        self.send_method = self.config.get("send_method", "yield")
        self.trust_env = False
        self._session: aiohttp.ClientSession = None

    async def _get_session(self) -> ClientSession:
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                trust_env=self.trust_env,
                headers=HEADERS,
                timeout=DEFAULT_TIMEOUT,
            )
        return self._session

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        text = event.message_str.strip()
        if not text:
            return

        match = DOUYIN_PATTERN.search(text)
        if not match:
            return

        douyin_url = match.group(0)
        logger.info(f"[DouyinPlugin] 检测到抖音链接: {douyin_url}")

        try:
            session = await self._get_session()
            data = await self.fetch_douyin_info_with_retry(session, douyin_url)
            if not data:
                yield event.plain_result("解析失败，请稍后重试")
                return

            if data.get("code") != 200:
                yield event.plain_result(f"解析失败：{data.get('msg', '未知错误')}")
                return

            info_text = self.build_info_text(data)

            if self.send_method == "nodes":
                result = self.build_nodes_message(event, data, info_text)
                yield event.chain_result(result)
            else:
                chain = []
                cover = data.get("cover")
                if cover:
                    chain.append(Comp.Image.fromURL(cover))
                chain.append(Comp.Plain(info_text))
                yield event.chain_result(chain)

                video = data.get("video")
                if video:
                    yield event.chain_result([Comp.Video.fromURL(video)])

        except Exception as e:
            logger.error(f"[DouyinPlugin] 解析错误: {e}")
            yield event.plain_result(f"解析出错：{str(e)}")

    def build_info_text(self, data: dict) -> str:
        name = data.get("name", "未知")
        title = data.get("title", "无标题")
        video_type = data.get("type", "视频")
        aweme_id = data.get("aweme_id", "")

        info_text = f"👤 作者：{name}\n"
        info_text += f"📝 标题：{title}\n"
        info_text += f"📹 类型：{video_type}\n"
        if aweme_id:
            info_text += f"🆔 ID：{aweme_id}"

        music_title = data.get("musictitle")
        music_author = data.get("musicauthor")
        if music_title:
            music_text = f"🎵 BGM：{music_title}"
            if music_author:
                music_text += f" - {music_author}"
            info_text += f"\n{music_text}"

        return info_text

    def build_nodes_message(self, event: AstrMessageEvent, data: dict, info_text: str) -> list:
        uin = event.get_self_id()
        bot_name = "抖音解析"
        messages = []

        cover = data.get("cover")

        messages.append(
            Comp.Node(
                uin=uin,
                name=bot_name,
                content=[Comp.Plain(info_text), Comp.Image.fromURL(cover) if cover else None]
            )
        )

        video = data.get("video")
        if video:
            messages.append(
                Comp.Node(
                    uin=uin,
                    name=bot_name,
                    content=[Comp.Video.fromURL(video)]
                )
            )

        nodes = Comp.Nodes(messages)
        return [nodes]

    async def fetch_douyin_info_with_retry(self, session: ClientSession, url: str) -> dict:
        params = {
            "id": self.api_id,
            "key": self.api_key,
            "url": url
        }

        for attempt in range(MAX_RETRIES):
            try:
                async with session.get(
                    self.api_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    data = await response.json()
                    if data.get("code") == 200:
                        return data
                    logger.warning(f"[DouyinPlugin] 第 {attempt + 1} 次请求失败: {data.get('msg')}")
            except Exception as e:
                logger.warning(f"[DouyinPlugin] 第 {attempt + 1} 次请求异常: {e}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)

        return None

    async def terminate(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None