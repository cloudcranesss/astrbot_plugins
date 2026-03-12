import socket
import re
from typing import Dict, Set
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig


@register("Wake-on-LAN", "cloudcranesss", "通过发送魔术包唤醒局域网内的设备", "1.0.0",
          "https://github.com/cloudcranesss/astrbot_plugins/astrbot_plugin_wake_on_lan")
class WakeOnLan(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.devices = self._load_devices()
        self.whitelist = self._load_whitelist()
        logger.info(f"Wake-on-LAN 插件初始化完成，已加载 {len(self.devices)} 个设备，白名单用户: {len(self.whitelist)} 人")

    def _load_devices(self) -> Dict[str, Dict[str, str]]:
        devices = {}
        devices_config = self.config.get("devices", [])
        for device in devices_config:
            name = device.get("name", "")
            mac = device.get("mac", "").upper()
            broadcast = device.get("broadcast", "255.255.255.255")
            port = device.get("port", 9)
            if name and mac:
                devices[name] = {"mac": mac, "broadcast": broadcast, "port": port}
        return devices

    def _load_whitelist(self) -> Set[str]:
        whitelist_config = self.config.get("whitelist", [])
        return set(str(uid).strip() for uid in whitelist_config if uid)

    def _is_allowed(self, event: AstrMessageEvent) -> bool:
        if not self.whitelist:
            return True
        user_id = str(event.get_sender_id())
        return user_id in self.whitelist

    def _validate_mac(self, mac: str) -> bool:
        pattern = r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
        return bool(re.match(pattern, mac))

    def _mac_to_bytes(self, mac: str) -> bytes:
        mac_clean = mac.replace(":", "").replace("-", "").replace(" ", "")
        return bytes.fromhex(mac_clean)

    async def _wake_device(self, mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> bool:
        try:
            mac_bytes = self._mac_to_bytes(mac)
            magic_packet = b'\xff' * 6 + mac_bytes * 16

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, (broadcast, port))
            sock.close()
            logger.info(f"成功发送 Wake-on-LAN 魔术包到 {mac}")
            return True
        except Exception as e:
            logger.error(f"发送 Wake-on-LAN 魔术包失败: {e}")
            return False

    def _get_help(self) -> str:
        return """Wake-on-LAN 使用指南:
/wake on <设备名> - 唤醒指定设备
/wake ls - 查看已配置的设备
/wake add <设备名> <MAC> [广播] [端口] - 添加设备 (管理员)
/wake del <设备名> - 删除设备 (管理员)"""

    @filter.command("wake")
    async def wake_command(self, event: AstrMessageEvent, action: str = "", name: str = "", mac: str = "", broadcast: str = "255.255.255.255", port: int = 9):
        if not self._is_allowed(event):
            yield event.plain_result("❌ 您不在白名单中，无法使用此功能")
            return

        action = action.strip().lower() if action else ""
        
        if not action or action == "help":
            yield event.plain_result(self._get_help())
            return

        if action == "ls" or action == "list":
            if not self.devices:
                yield event.plain_result("暂无已配置的设备，请使用 /wake add 添加")
                return
            result = ["已配置的设备:"]
            for dev_name, info in self.devices.items():
                result.append(f"• {dev_name}: {info['mac']} (广播: {info['broadcast']}, 端口: {info['port']})")
            yield event.plain_result("\n".join(result))
            return

        if action == "on":
            if not name:
                yield event.plain_result("用法: /wake on <设备名>")
                return
            name = name.strip()
            if name not in self.devices:
                available = ", ".join(self.devices.keys()) if self.devices else "无"
                yield event.plain_result(f"未找到设备: {name}\n可用设备: {available}")
                return
            device = self.devices[name]
            yield event.plain_result(f"正在唤醒设备: {name} ({device['mac']}) ...")
            success = await self._wake_device(device['mac'], device['broadcast'], device['port'])
            if success:
                yield event.plain_result(f"✅ 设备 {name} 唤醒信号已发送！")
            else:
                yield event.plain_result(f"❌ 设备 {name} 唤醒失败")
            return

        if action == "add":
            if not name or not mac:
                yield event.plain_result("用法: /wake add <设备名> <MAC地址> [广播地址] [端口]\n示例: /wake add 客厅电脑 AA:BB:CC:DD:EE:FF")
                return
            mac = mac.upper()
            if not self._validate_mac(mac):
                yield event.plain_result(f"MAC 地址格式错误: {mac}\n正确格式: AA:BB:CC:DD:EE:FF")
                return
            self.devices[name] = {"mac": mac, "broadcast": broadcast, "port": port}
            logger.info(f"添加设备: {name} - {mac}")
            yield event.plain_result(f"✅ 设备 {name} (MAC: {mac}) 添加成功！")
            return

        if action == "del" or action == "delete" or action == "remove":
            if not name:
                yield event.plain_result("用法: /wake del <设备名称>")
                return
            if name in self.devices:
                del self.devices[name]
                logger.info(f"删除设备: {name}")
                yield event.plain_result(f"✅ 设备 {name} 已删除")
            else:
                yield event.plain_result(f"未找到设备: {name}")
            return

        yield event.plain_result(f"未知指令: {action}\n" + self._get_help())

    async def terminate(self):
        pass
