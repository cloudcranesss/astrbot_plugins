import asyncio
import hashlib
import json
import random
import time
import aiohttp
from typing import Dict, Optional, LiteralString
from astrbot.core import logger


class BaiduTranslator():
    """
    百度翻译API封装类

    功能:
    - 支持多种语言互译
    - 自动签名生成
    - 错误处理
    - 结果解析

    使用示例:
    translator = BaiduTranslator()
    result = translator.translate("hello", from_lang="en", to_lang="zh")
    print(result)
    """

    # 支持的语言代码映射
    LANGUAGE_MAP = {
        'auto': '自动检测',
        'zh': '中文',
        'en': '英语',
        'jp': '日语',
        'kor': '韩语',
        'fra': '法语',
        'spa': '西班牙语',
        'th': '泰语',
        'ara': '阿拉伯语',
        'ru': '俄语',
        'pt': '葡萄牙语',
        'de': '德语',
        'it': '意大利语',
        'el': '希腊语',
        'nl': '荷兰语',
        'pl': '波兰语',
        'bul': '保加利亚语',
        'est': '爱沙尼亚语',
        'dan': '丹麦语',
        'fin': '芬兰语',
        'cs': '捷克语',
        'rom': '罗马尼亚语',
        'slo': '斯洛文尼亚语',
        'swe': '瑞典语',
        'hu': '匈牙利语',
        'cht': '繁体中文',
        'vie': '越南语'
    }

    # 错误代码映射
    ERROR_MESSAGES = {
        52000: '成功',
        52001: '请求超时',
        52002: '系统错误',
        52003: '未授权用户',
        54000: '必填参数为空',
        54001: '签名错误',
        54003: '访问频率受限',
        54004: '账户余额不足',
        54005: '长query请求频繁',
        58000: '客户端IP非法',
        58001: '译文语言方向不支持',
        58002: '服务当前已关闭',
        90107: '认证未通过或未生效'
    }

    def __init__(self, appid: str, secret_key: str):
        """初始化翻译器"""
        self.api_url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'

        # 获取API凭证
        self.appid = appid
        self.secret_key = secret_key
        
        # 用于Google翻译的等待时间变量
        self._google_trans_wait = 60

        logger.info(f"appid: {self.appid} secret_key: {self.secret_key}")

        if not all([self.appid, self.secret_key]):
            logger.error("百度翻译API配置不完整，请检查config.ini文件")
            raise ValueError("百度翻译API配置不完整")

    async def _generate_sign(self, query: str, salt: str) -> str:
        """
        生成API请求签名

        参数:
            query: 要翻译的文本
            salt: 随机盐值

        返回:
            MD5签名字符串
        """
        sign_str = f"{self.appid}{query}{salt}{self.secret_key}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    async def translate_by_baidu(
            self,
            query: str,
            from_lang: str = 'auto',
            to_lang: str = 'jp',
            **kwargs
    ) -> Optional[str]:
        """异步翻译方法"""
        if not query:
            logger.warning("翻译请求为空")
            return None

        if from_lang not in self.LANGUAGE_MAP:
            logger.warning(f"不支持的源语言代码: {from_lang}")
            return None

        if to_lang not in self.LANGUAGE_MAP:
            logger.warning(f"不支持的目标语言代码: {to_lang}")
            return None

        salt = str(random.randint(32768, 65536))
        sign = await self._generate_sign(query, salt)

        params = {
            'q': query,
            'from': from_lang,
            'to': to_lang,
            'appid': self.appid,
            'salt': salt,
            'sign': sign,
            **kwargs
        }

        try:
            logger.info(f"发送翻译请求: {query[:50]}... (from {from_lang} to {to_lang})")

            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, params=params, timeout=10) as response:
                    response.raise_for_status()
                    result = await response.json()

                    if 'error_code' in result:
                        error_code = result.get('error_code')
                        error_msg = self.ERROR_MESSAGES.get(error_code, '未知错误')
                        logger.error(f"API返回错误: {error_code} - {error_msg}")
                        return None

                    return ''.join(item['dst'] for item in result.get('trans_result', []))

        except aiohttp.ClientError as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return None

    async def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.LANGUAGE_MAP.copy()

    async def translate_by_google(self, text, to="ja"):
        """使用Google翻译文本（默认翻译为简体中文）异步版本"""
        logger.info(f"开始调用谷歌翻译API，输入: {text}")
        start_time = time.time()

        # 构建请求URL
        url = f"https://translate.google.com/translate_a/single?client=gtx&dt=t&dj=1&ie=UTF-8&hl=zh-CN&sl=auto&tl={to}&q={text}"
        logger.info(f"请求地址: {url}")

        # 使用异步会话
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(url) as response:
                        # 处理429错误（请求过多）
                        if response.status == 429:
                            logger.warning(f"HTTP 429: Google翻译请求超限，将等待{self._google_trans_wait}秒后重试")
                            await asyncio.sleep(self._google_trans_wait)
                            self._google_trans_wait += random.randint(60, 90)
                            continue

                        # 检查其他错误状态
                        response.raise_for_status()

                        # 解析响应
                        result = await response.json()
                        sentences = result["sentences"]

                        end_time = time.time()
                        logger.info(f"翻译完成，耗时 {end_time - start_time:.2f} 秒")

                        return "".join([sentence["trans"] for sentence in sentences])

                except aiohttp.ClientError as e:
                    logger.error(f"谷歌翻译请求失败: {str(e)}")
                    raise
                except json.JSONDecodeError:
                    logger.error("谷歌翻译响应解析失败")
                    raise

    async def translate(self, text: str) -> Optional[str]:
        """统一翻译接口
        
        Args:
            text: 要翻译的文本
            
        Returns:
            翻译后的文本，失败则返回None
        """
        logger.info(f"开始翻译文本，内容: {text[:50]}...")
        
        if self.appid and self.secret_key:
            logger.info("使用百度翻译API")
            result = await self.translate_by_baidu(text)
        else:
            logger.warning("百度翻译API配置不完整，将使用Google翻译")
            result = await self.translate_by_google(text)
        
        logger.info(f"翻译完成，结果: {result[:50]}...")
        return result