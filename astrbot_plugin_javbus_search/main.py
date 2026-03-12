import random
import re
from typing import AsyncGenerator, Any, List, Optional, Dict, Coroutine
import aiohttp
from astrbot.core.message.message_event_result import MessageEventResult
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as comp


from .utils.translate import BaiduTranslator


@register("JavBus Serach", "cloudcranesss", "一个基于JavBus API的搜索服务", "v1.0.1",
          "https://github.com/cloudcranesss/astrbot_plugin_javbus_search")
class JavBusSerach(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.javbus_api_url = config.get("javbus_api_url", "")
        self.forward_url = config.get("forward_url", "")
        self.javbus_image_proxy = config.get("javbus_image_proxy", "")
        self.baidu_api_key = config.get("baidu_api_key", "")
        self.baidu_secret_key = config.get("baidu_secret_key", "")
        self.qq_access_token = config.get("qq_access_token", "")
        logger.info(
            f"初始化JavBus搜索插件，API地址: {self.javbus_api_url}\n"
            f"转发地址配置: {'已配置' if self.forward_url else '未配置'}\n"
            f"JavBus 图片代理地址: {self.javbus_image_proxy}")
        self.api = JavBusAPI(self.javbus_api_url)
        self.trans = BaiduTranslator(self.baidu_api_key, self.baidu_secret_key)


    async def send_reply(
            self,
            event: AstrMessageEvent,
            content: List[str],
            screenshots: List[str] = None,
            use_forward: bool = True
    ) -> AsyncGenerator[MessageEventResult, Any]:
        """统一消息发送方法"""
        sender_id = event.get_sender_id()
        group_id = event.get_group_id()
        screenshots = screenshots or []
        logger.info(f"准备发送回复，发送者: {sender_id}, 接收方: {group_id or '私聊'}, 内容条数: {len(content)}, 截图数: {len(screenshots)}")
        
        if use_forward:
            logger.info("使用AstrBot自带合并转发功能")
            # 无论群组还是私聊，都使用合并转发功能
            async for msg in self._send_forward_messages(event, content[:10], screenshots[:10]):
                yield msg
            if len(content) > 10:
                logger.info(f"结果过多，已显示前10条，共 {len(content)} 条结果")
        else:
            logger.info("使用普通消息回复模式")
            async for msg in self._send_normal_messages(event, content):
                yield msg
        
        logger.info(f"消息发送完成，共 {len(content)} 条内容")
        
    async def _send_normal_messages(
            self,
            event: AstrMessageEvent,
            content: List[str]
    ) -> AsyncGenerator[MessageEventResult, Any]:
        """发送普通消息"""
        for idx, message in enumerate(content, 1):
            logger.debug(f"发送第 {idx}/{len(content)} 条消息: {message[:50]}...")
            yield event.plain_result(message)
        
    async def _send_forward_messages(
            self,
            event: AstrMessageEvent,
            content: List[str],
            screenshots: List[str]
    ) -> AsyncGenerator[MessageEventResult, Any]:
        """使用AstrBot自带合并转发功能发送消息"""
        uin = int(event.get_self_id())
        bot_name = "CloudCrane Bot"
        messages = []
        
        # 为每个搜索结果创建一个独立的消息
        for idx, message in enumerate(content):
            # 创建一条消息，包含文本和图片
            message_content = [comp.Plain(str(message))]
            if idx < len(screenshots):
                url = screenshots[idx]
                message_content.append(comp.Image.fromURL(url))
            
            # 将这条消息添加到列表中
            messages.append(
                comp.Node(
                    uin=uin,
                    name=bot_name,
                    content=message_content
                )
            )
        
        # 使用Nodes组件创建一个合并转发，包含所有消息
        merged_forward = comp.Nodes(messages)
        
        logger.info(f"创建了1个合并转发，包含 {len(messages)} 条消息")
        yield event.chain_result([merged_forward])

    # 将 www.javbus.com 替换为 self.javbus_image_proxy
    async def proxy_image(self, image_url: str):
        """将图片URL替换为代理地址"""
        logger.debug(f"原始图片URL: {image_url}")
        if self.javbus_image_proxy:
            proxy_url = image_url.replace("https://www.javbus.com", self.javbus_image_proxy)
            logger.debug(f"代理后图片URL: {proxy_url}")
            return proxy_url
        else:
            logger.warning("未配置图片代理，使用原始URL")
            return image_url

    async def _extract_keyword(self, event: AstrMessageEvent, command: str) -> str:
        """从消息中提取关键词
        
        Args:
            event: 消息事件
            command: 命令前缀（如"搜关键词"、"搜演员"、"搜磁力"）
            
        Returns:
            提取的关键词
        """
        logger.info(f"开始提取关键词，命令: {command}")
        messages = event.get_messages()
        result1 = str(messages[0])
        logger.debug(f"原始消息内容: {result1}")
        result2 = re.findall(r"text='(.*?)'", result1)[0]
        logger.debug(f"提取的文本部分: {result2}")
        keyword = result2.split(command)[1]
        keyword = keyword.strip()
        logger.info(f"提取完成，关键词: {keyword}")
        return keyword

    @filter.regex(r"^搜关键词(.+)", flags=re.IGNORECASE, priority=1)
    async def search_movies(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, Any]:
        try:
            keyword = await self._extract_keyword(event, "搜关键词")
            if not keyword:
                logger.warning("搜索关键词为空")
                yield event.plain_result("请输入搜索关键词")
                return

            logger.info(f"用户 {event.get_sender_id()} 在群组 {event.get_group_id()} 搜索影片: {keyword}")

            logger.info(f"开始调用搜索API，关键词: {keyword}")
            datas = await self.api.search_movies(keyword=keyword)
            logger.info(f"搜索完成，找到 {len(datas.get('movies', []))} 个结果")

            if not datas.get("movies"):
                logger.info("未找到匹配的影片")
                yield event.plain_result("没有找到相关影片")
                return

            movies_info = []
            screenshots = []
            for idx, data in enumerate(datas["movies"]):
                logger.info(f"处理第 {idx + 1}/{len(datas['movies'])} 个结果: {data.get('id')}")
                title = data['title'][:20] + "..." if len(data['title']) > 20 else data['title']
                movies_info.append(
                    f"番号: {data['id']}\n"
                    f"标题: {title}\n"
                    f"日期: {data['date']}\n"
                    f"标签: {', '.join(data['tags'])}\n"
                )
                screenshots.append(await self.proxy_image(data['img']))

            movies_info.append(f"找到 {len(datas['movies'])} 个结果")
            logger.info(f"准备返回 {len(movies_info)} 条消息")

            # 使用统一的send_reply方法发送消息，包含截图
            async for msg in self.send_reply(event, movies_info, screenshots):
                yield msg
                
        except IndexError as e:
            logger.error(f"消息格式错误: {str(e)}")
            yield event.plain_result("消息格式错误，请按照正确格式输入")
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}", exc_info=True)
            yield event.plain_result("搜索服务暂时不可用")

    @filter.regex(r"^搜演员(.+)")
    async def search_star(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, Any]:
        try:
            keyword = await self._extract_keyword(event, "搜演员")
            if not keyword:
                logger.warning("演员搜索关键词为空")
                yield event.plain_result("请输入演员名称")
                return

            logger.info(f"用户 {event.get_sender_id()} 在群组 {event.get_group_id()} 搜索演员: {keyword}")

            logger.info(f"开始调用演员搜索API: {keyword}")
            translated_keyword = await self.trans.translate(keyword)
            data = await self.api.get_star_by_name(translated_keyword)
            logger.info(f"演员搜索结果: {data}")

            if not data:
                logger.info("未找到演员信息")
                yield event.plain_result("未找到该演员信息")
                return

            star_info = []
            screenshots = []

            star_info = [
                f"姓名: {data['name']}\n"
                f"生日: {data['birthday']}\n"
                f"年龄: {data['age']}\n"
                f"身高: {data['height']}\n"
                f"三维: {data['bust']} - {data['waistline']} - {data['hipline']}\n"
            ]
            screenshots.append(await self.proxy_image(data['avatar']))
            logger.info(f"演员信息已构建: {data['name']}")

            # 使用统一的send_reply方法发送消息，包含截图
            async for msg in self.send_reply(event, star_info, screenshots):
                yield msg
                
        except IndexError as e:
            logger.error(f"消息格式错误: {str(e)}")
            yield event.plain_result("消息格式错误，请按照正确格式输入")
        except Exception as e:
            logger.error(f"演员搜索失败: {str(e)}", exc_info=True)
            yield event.plain_result("演员查询服务异常")

    @filter.regex(r"^搜磁力([a-zA-Z0-9-]+)")
    async def search_magnet(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, Any]:
        try:
            keyword = await self._extract_keyword(event, "搜磁力")
            logger.info(f"用户 {event.get_sender_id()} 在群组 {event.get_group_id()} 搜索磁力: {keyword}")

            logger.info(f"开始获取影片详情: {keyword}")
            detail = await self.api.get_movie_detail(keyword)
            logger.info(f"影片详情获取完成，结果: {'找到' if detail else '未找到'}")

            if not detail:
                logger.info("未找到影片详情")
                yield event.plain_result("没有找到该影片")
                return

            if isinstance(detail.get("videoLength"), int):
                try:
                    hours = detail["videoLength"] // 60
                    minutes = detail["videoLength"] % 60
                    videoLength = f"{hours}小时{minutes}分钟"
                    logger.info(f"计算影片时长: {detail['videoLength']}分钟 -> {videoLength}")
                except Exception as e:
                    logger.error(f"时长计算错误: {str(e)}")
                    videoLength = str(detail.get("videoLength", "未知"))
            else:
                videoLength = str(detail.get("videoLength", "未知"))

            stars_str = "暂无演员信息"
            if detail.get("stars"):
                try:
                    stars = [s["name"] if isinstance(s, dict) else str(s) for s in detail["stars"][:3]]
                    stars_str = "、".join(stars)
                    if len(detail["stars"]) > 3:
                        stars_str += f" 等{len(detail['stars'])}人"
                    logger.info(f"处理演员信息完成: {stars_str}")
                except Exception as e:
                    logger.error(f"演员信息处理失败: {str(e)}")
                    stars_str = "演员信息解析错误"

            director_str = "未知"
            if isinstance(detail.get("director"), dict):
                director_str = detail["director"].get("name", "未知")
            elif detail.get("director"):
                director_str = str(detail["director"])
            logger.info(f"导演信息: {director_str}")

            screenshots = []

            info_lines = [
                f"【影片详情】\n"
                f"番号：{detail.get('id', 'N/A')}\n"
                f"标题：{detail.get('title', 'N/A')}\n"
                f"日期：{detail.get('date', 'N/A')}\n"
                f"时长：{videoLength}\n"
                f"演员：{stars_str}\n"
                f"导演：{director_str}"
            ]
            screenshots.append(await self.proxy_image(detail['img']))

            magnets = []
            if 'gid' in detail and 'uc' in detail:
                try:
                    logger.info(f"开始获取磁力链接: gid={detail['gid']}, uc={detail['uc']}")
                    all_magnets = await self.api.get_magnets(
                        movie_id=keyword,
                        gid=detail['gid'],
                        uc=detail['uc']
                    )
                    magnets = all_magnets[:5]  # 获取前5条磁力链接
                    logger.info(f"获取到 {len(magnets)} 条磁力链接")
                except Exception as e:
                    logger.error(f"磁力链接获取失败: {str(e)}", exc_info=True)
            else:
                logger.warning("缺少获取磁力链接的必要参数")

            if magnets:
                info_lines.append("【磁力链接】")
                for idx, magnet in enumerate(magnets, 1):
                    title = magnet['title']
                    size = magnet['size']
                    share_date = magnet['shareDate']
                    is_hd = magnet['isHD']
                    link = magnet['link']
                    has_sub = magnet['hasSubtitle']

                    info_lines.append(
                        f"{idx}. {title} {size}\n"
                        f"{share_date}\n"
                        f"{' 高清' if is_hd else ''} 字幕：{'有' if has_sub else '无'}\n"
                        f"{link}"
                    )
            else:
                info_lines.append("【未找到磁力链接】")
                logger.info("未找到磁力链接")

            logger.info(f"准备返回磁力搜索结果，信息行数: {len(info_lines)}")
            # 使用统一的send_reply方法发送消息，包含截图
            async for msg in self.send_reply(event, info_lines, screenshots):
                yield msg
                
        except IndexError as e:
            logger.error(f"消息格式错误: {str(e)}")
            yield event.plain_result("消息格式错误，请按照正确格式输入")
        except Exception as e:
            logger.error(f"磁力搜索失败: {str(e)}", exc_info=True)
            yield event.plain_result("磁力搜索服务异常")


class JavBusAPI:
    def __init__(self, base_url: str = None):
        self.base_url = base_url.rstrip('/') if base_url else ""
        logger.info(f"JavBus API初始化成功，基础URL为：{self.base_url}")
        
        # 默认headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 创建一个可复用的session
        self.session = aiohttp.ClientSession(headers=self.headers)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """关闭session"""
        if hasattr(self, 'session') and not self.session.closed:
            await self.session.close()

    async def _request(self, url: str, params: Dict = None) -> Dict:
        """统一的异步请求方法"""
        logger.info(f"开始API请求，URL: {url}")
        logger.debug(f"请求参数: {params}")
        try:
            async with self.session.get(url, params=params) as response:
                logger.info(f"请求响应状态: {response.status}")
                response.raise_for_status()
                data = await response.json()
                logger.debug(f"响应数据: {data}")
                return data
        except aiohttp.ClientResponseError as e:
            logger.error(f"请求失败 {e.status}: {e.message}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}")
            raise

    async def get_movies(
            self,
            page: int = 1,
            magnet: str = "exist",
            filter_type: Optional[str] = None,
            filter_value: Optional[str] = None,
            movie_type: str = "normal"
    ) -> Dict[str, Any]:
        params = {
            'page': page,
            'magnet': magnet,
            'type': movie_type
        }

        if filter_type and filter_value:
            params.update({
                'filterType': filter_type,
                'filterValue': filter_value
            })

        url = f"{self.base_url}/api/movies"
        return await self._request(url, params)

    async def search_movies(
            self,
            keyword: str,
            page: int = 1,
            magnet: str = "exist",
            movie_type: str = "normal"
    ) -> Dict[str, Any]:
        params = {
            'keyword': keyword,
            'page': page,
            'magnet': magnet,
            'type': movie_type
        }

        url = f"{self.base_url}/api/movies/search"
        return await self._request(url, params)

    async def get_movie_detail(self, movie_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/movies/{movie_id}"
        return await self._request(url)

    async def get_magnets(
            self,
            movie_id: str,
            gid: str,
            uc: str,
            sort_by: str = "size",
            sort_order: str = "desc"
    ) -> List[Dict]:
        params = {
            'gid': gid,
            'uc': uc,
            'sortBy': sort_by,
            'sortOrder': sort_order
        }

        url = f"{self.base_url}/api/magnets/{movie_id}"
        return await self._request(url, params)

    async def get_star_detail(
            self,
            star_id: str,
            star_type: str = "normal"
    ) -> Dict[str, Any]:
        params = {'type': star_type}
        url = f"{self.base_url}/api/stars/{star_id}"
        return await self._request(url)

    async def get_star_by_name(self, star_name: str) -> Optional[Dict[str, Any]]:
        """通过演员名称搜索演员信息"""
        if not star_name:
            return None
            
        try:
            # 先搜索包含该演员的影片
            movie_lists = await self.search_movies(star_name)
            movies = movie_lists.get("movies", [])
            
            if not movies:
                logger.info(f"未找到包含演员 {star_name} 的影片")
                return None

            # 从影片中提取演员信息
            star_ids = set()
            for movie in movies:
                if not movie.get("stars"):
                    continue
                    
                for star in movie["stars"]:
                    if isinstance(star, dict) and "name" in star and "id" in star:
                        if star_name in star["name"]:
                            star_ids.add(star["id"])

            if not star_ids:
                logger.info(f"未找到演员 {star_name} 的ID信息")
                return None

            # 获取第一个演员的详细信息
            star_id = list(star_ids)[0]
            return await self.get_star_detail(star_id)
            
        except Exception as e:
            logger.error(f"搜索演员 {star_name} 失败: {str(e)}")
            return None