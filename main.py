import asyncio, sys, random, string, datetime, aiofiles, time, os, fake_useragent
from curl_cffi.requests import AsyncSession
from web3 import Web3
from eth_account.messages import encode_defunct
from loguru import logger
from typing import Optional, Dict
from colorama import Fore, Style

# 重试配置
MAX_RETRIES = 3  # 重试次数
RETRY_DELAY = 3  # 重试延迟

# 项目配置参数
INVITE_CODE = ""  # 邀请码 不用填
NSTPROXY_CHANNEL = ""  # 代理通道
NSTPROXY_PASSWORD = ""  # 代理密码
# 并发配置
CONCURRENT_TASKS = 10  # 同时运行的任务数量


logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<g>{time:HH:mm:ss:SSS}</g> | <level>{message}</level>",
)


class zxc:

    def __init__(
        self,
        key: Optional[str] = None,
        proxy: Optional[str] = None,
        invite_code: Optional[str] = None,
        nstproxy_Channel: Optional[str] = None,
        nstproxy_Password: Optional[str] = None,
        index: Optional[int] = None,
        sol_address: Optional[str] = None,
    ):
        if not key:
            raise ValueError("Private key is required")
        if "|" in key:
            self.key = key.split("|")[0]
            self.token = key.split("|")[1]
        else:
            self.key = key
            self.token = None
        self.headers = {
            "User-Agent": fake_useragent.UserAgent().random,
            "Content-Type": "application/json",
        }
        self.w3 = Web3(Web3.HTTPProvider())
        self.address = self.w3.eth.account.from_key(self.key).address
        if proxy:
            proxies = {"http": proxy, "https": proxy}
        elif nstproxy_Channel and nstproxy_Password:
            session = "".join(
                random.choices(string.digits + string.ascii_letters, k=10)
            )
            nstproxy = f"http://{nstproxy_Channel}-residential-country_ANY-r_5m-s_{session}:{nstproxy_Password}@gw-eu.nstproxy.io:24125"
            proxies = {"http": nstproxy, "https": nstproxy}
        else:
            proxies = None
        # self.recaptcha = AsyncTurnstileSolver()
        self.http = AsyncSession(
            timeout=120,
            headers=self.headers,
            impersonate="chrome120",
            proxies=proxies,
        )
        self.invite_code = invite_code
        self.index = index
        self.sol_address = sol_address

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self.http.close()

    async def login(self) -> bool:
        for retry in range(MAX_RETRIES):
            try:
                Timestamp = int(datetime.datetime.now().timestamp() * 1000)
                msg = f"This wallet will be used for staking and farming.\n\nNever gonna give you up\nNever gonna let you down\nNever gonna run around and desert you\nNever gonna make you cry\nNever gonna say goodbye\nNever gonna tell a lie and hurt you\n\nWallet: {self.address[:6]}...{self.address[-4:]}\nTimestamp: {Timestamp}"
                encoded_message = encode_defunct(text=msg)
                message = self.w3.eth.account.sign_message(
                    encoded_message, private_key=self.key
                )
                signature = f"0x{message.signature.hex()}"
                data_json = {
                    "address": self.address,
                    "message": msg,
                    "signature": signature,
                }
                res = await self.http.post(
                    "https://memestaking-api.stakeland.com/wallet/auth", json=data_json
                )

                if res.status_code in [200, 201]:
                    logger.success(f"[{self.index}] 登录成功")
                    res_json = res.json()
                    self.token = res_json["accessToken"]
                    self.http.headers["Authorization"] = f"Bearer {self.token}"
                    return True
                else:
                    logger.error(f"[{self.index}] 登录失败: {res.text}")
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return False
            except Exception as e:
                if retry < MAX_RETRIES - 1:
                    logger.warning(
                        f"[{self.index}] 登录异常, 重试 {retry + 1}/{MAX_RETRIES}: {str(e)}"
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(
                        f"[{self.index}] 登录失败, 已重试{MAX_RETRIES}次: {str(e)}"
                    )
                    return False
        return False

    async def get_total(self) -> bool:
        for retry in range(MAX_RETRIES):
            try:
                res = await self.http.get(
                    f"https://memestaking-api.stakeland.com/wallet/info/{self.address}"
                )

                if res.status_code in [200, 201]:
                    res_json = res.json()
                    logger.success(
                        f"[{self.index}] 查询成功 积分 {res_json['steaks']['total']}"
                    )
                    return True
                else:
                    logger.error(f"[{self.index}] 查询失败: {res.text}")
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return False
            except Exception as e:
                if retry < MAX_RETRIES - 1:
                    logger.warning(
                        f"[{self.index}] 查询异常, 重试 {retry + 1}/{MAX_RETRIES}: {str(e)}"
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(
                        f"[{self.index}] 查询失败, 已重试{MAX_RETRIES}次: {str(e)}"
                    )
                    return False
        return False

    async def share(self, task_id, task_desc) -> bool:
        for retry in range(MAX_RETRIES):
            try:
                data_json = {
                    "questId": task_id,
                }
                res = await self.http.post(
                    "https://memestaking-api.stakeland.com/farming/quest/share",
                    json=data_json,
                )
                if res.status_code in [200, 201]:
                    res_json = res.json()
                    if res_json["success"] == True:
                        logger.success(
                            f"[{self.index}] {task_desc} 完成任务成功✅ 获得牛排 {res_json['earned']}"
                        )
                        return True
                    else:
                        logger.error(
                            f"[{self.index}] {task_desc} 完成任务失败: {res.text}"
                        )
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return False
                else:
                    logger.error(f"[{self.index}] 完成任务失败: {res.text}")
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return False
            except Exception as e:
                if retry < MAX_RETRIES - 1:
                    logger.warning(
                        f"[{self.index}] 完成任务异常, 重试 {retry + 1}/{MAX_RETRIES}: {str(e)}"
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(
                        f"[{self.index}] 完成任务失败, 已重试{MAX_RETRIES}次: {str(e)}"
                    )
                    return False
        return False

    async def submit(self) -> bool:
        for retry in range(MAX_RETRIES):
            try:
                data_json = {
                    "input": self.sol_address,
                    "questId": 66,
                }
                res = await self.http.post(
                    "https://memestaking-api.stakeland.com/farming/quest/submit",
                    json=data_json,
                )
                if res.status_code in [200, 201]:

                    res_json = res.json()
                    if res_json["success"] == True:
                        logger.success(f"[{self.index}] 提交地址成功")
                        return True
                    else:
                        logger.error(f"[{self.index}] 提交地址失败: {res.text}")
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return False
                else:
                    logger.error(f"[{self.index}] 提交地址失败: {res.text}")
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return False
            except Exception as e:
                if retry < MAX_RETRIES - 1:
                    logger.warning(
                        f"[{self.index}] 提交地址异常, 重试 {retry + 1}/{MAX_RETRIES}: {str(e)}"
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(
                        f"[{self.index}] 提交地址失败, 已重试{MAX_RETRIES}次: {str(e)}"
                    )
                    return False
        return False

    TASKS_INFO = {
        66: "submitWallet ✅",
        77: "Follow MemeStrategy ✅",
        76: "Follow MemePay ✅",
        75: "Follow Stakeland ✅",
        67: "Follow Pain ✅",
        78: "Share a Painfession on X✅",
    }

    async def info_quests(self) -> bool:
        quests_list = []
        for retry in range(MAX_RETRIES):
            try:
                res = await self.http.get(
                    f"https://memestaking-api.stakeland.com/farming/info/{self.address}"
                )
                if res.status_code in [200, 201]:
                    res_json = res.json()
                    for quests in res_json["rewards"]:
                        quests_list.append(quests["id"])
                    for task_id, task_desc in self.TASKS_INFO.items():
                        if task_id not in quests_list:
                            if task_id == 66:
                                await self.submit()
                            elif task_id == 78:
                                await self.share(task_id, task_desc)
                            else:
                                await self.follow(task_id, task_desc)
                        else:
                            logger.success(f"[{self.index}] {task_desc} 任务完成✅")
                    return True
                else:
                    logger.error(f"[{self.index}] 获取任务失败: {res.text}")
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return False
            except Exception as e:
                if retry < MAX_RETRIES - 1:
                    logger.warning(
                        f"[{self.index}] 获取任务异常, 重试 {retry + 1}/{MAX_RETRIES}: {str(e)}"
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(
                        f"[{self.index}] 获取任务失败, 已重试{MAX_RETRIES}次: {str(e)}"
                    )
                    return False
        return False

    async def follow(self, task_id, task_desc) -> bool:
        for retry in range(MAX_RETRIES):
            try:
                data_json = {
                    "questId": task_id,
                }
                res = await self.http.post(
                    "https://memestaking-api.stakeland.com/farming/quest/follow",
                    json=data_json,
                )
                if res.status_code in [200, 201]:
                    res_json = res.json()
                    if res_json["success"] == True:
                        logger.success(
                            f"[{self.index}] {task_desc} 完成任务成功✅ 获得牛排 {res_json['earned']}"
                        )
                        return True
                    else:
                        logger.error(
                            f"[{self.index}] {task_desc} 完成任务失败: {res.text}"
                        )
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return False
                else:
                    logger.error(f"[{self.index}] 完成任务失败: {res.text}")
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return False
            except Exception as e:
                if retry < MAX_RETRIES - 1:
                    logger.warning(
                        f"[{self.index}] 完成任务异常, 重试 {retry + 1}/{MAX_RETRIES}: {str(e)}"
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(
                        f"[{self.index}] 完成任务失败, 已重试{MAX_RETRIES}次: {str(e)}"
                    )
                    return False
        return False


async def read_file(file_path: str) -> list[str]:
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return []
    keys = []
    try:
        async with aiofiles.open(file_path, "r") as file:
            async for line in file:
                key = line.strip()
                if key:  # 忽略空行
                    keys.append(key)
        return keys
    except Exception as e:
        logger.error(f"读取文件失败: {str(e)}")
        return []


def print_menu():
    print(
        Fore.GREEN
        + """
╔════════════════════════════════════╗
║           NodeGo 自动化工具        ║
╠════════════════════════════════════╣
║ 1. 注册新账号                      ║
║ 2. 运行每日任务                    ║
║ 0. 退出程序                        ║
╚════════════════════════════════════╝
    """
        + Style.RESET_ALL
    )


def print_proxy_menu():
    print(
        Fore.CYAN
        + """
╔════════════════════════════════════╗
║           代理选择菜单             ║
╠════════════════════════════════════╣
║ 1. 使用本地代理列表                ║
║ 2. 使用动态代理                    ║
╚════════════════════════════════════╝
    """
        + Style.RESET_ALL
    )


async def get_proxy_config():
    while True:
        print_proxy_menu()
        proxy_choice = input(Fore.CYAN + "请选择代理模式 (1-2): " + Style.RESET_ALL)

        if proxy_choice == "1":
            # 使用本地代理
            proxy_file = os.path.join(os.path.dirname(__file__), "proxy.txt")
            proxys = await read_file(proxy_file)
            if not proxys:
                logger.error("未找到有效的本地proxy配置")
                return None
            return {"type": "local", "proxys": proxys}

        elif proxy_choice == "2":
            # 使用动态代理
            return {
                "type": "dynamic",
                "channel": NSTPROXY_CHANNEL,
                "password": NSTPROXY_PASSWORD,
            }

        else:
            logger.error("无效的选择，请重新输入")
            await asyncio.sleep(1)


async def register_accounts() -> None:
    try:
        # 获取代理配置
        proxy_config = await get_proxy_config()
        if not proxy_config:
            return

        # 读取账号配置
        accounts_file = os.path.join(os.path.dirname(__file__), "accounts.txt")
        accounts = await read_file(accounts_file)
        if not accounts:
            logger.error("未找到有效的accounts配置")
            return

        semaphore = CONCURRENT_TASKS
        sem = asyncio.Semaphore(semaphore)

        async def process_register(sem, account, index):
            async with sem:
                while True:
                    try:
                        email, password = account.split(":", 1)

                        # 根据代理配置设置代理
                        if proxy_config["type"] == "local":
                            proxy = proxy_config["proxys"][
                                index % len(proxy_config["proxys"])
                            ]
                            nstproxy_channel = None
                            nstproxy_password = None
                        else:
                            proxy = None
                            nstproxy_channel = proxy_config["channel"]
                            nstproxy_password = proxy_config["password"]

                        xc = zxc(
                            key=None,  # 注册不需要key，随便填
                            email_username=email,
                            email_password="Qqqq1111..",
                            proxy=proxy,
                            index=index + 1,
                            invite_code=INVITE_CODE,
                            nstproxy_Channel=nstproxy_channel,
                            nstproxy_Password=nstproxy_password,
                        )
                    except Exception as e:
                        logger.error(f"[{index + 1}] 注册时发生错误: {str(e)}")

        tasks = []
        if proxy_config["type"] == "local":
            total = min(len(accounts), len(proxy_config["proxys"]))
        else:
            total = len(accounts)

        for index in range(total):
            task = process_register(sem, accounts[index], index)
            tasks.append(task)

        time_start = time.time()
        await asyncio.gather(*tasks)
        time_end = time.time()
        time_cost = datetime.timedelta(seconds=time_end - time_start)
        logger.success(f"所有注册任务执行完成 耗时: {time_cost}")

    except Exception as e:
        logger.error(f"注册过程发生错误: {str(e)}")


async def daily_tasks() -> None:
    retry_count = 0
    max_main_retries = 5

    # 获取代理配置
    proxy_config = await get_proxy_config()
    if not proxy_config:
        return

    while True:
        try:
            # 读取key配置
            keys_file = os.path.join(os.path.dirname(__file__), "keys.txt")
            keys = await read_file(keys_file)
            # 读取sol_address配置
            sol_address_file = os.path.join(
                os.path.dirname(__file__), "sol_address.txt"
            )
            sol_addresss = await read_file(sol_address_file)
            if not keys:
                logger.error("未找到有效的私钥配置")
                await asyncio.sleep(300)
                continue

            semaphore = CONCURRENT_TASKS
            sem = asyncio.Semaphore(semaphore)

            async def process_daily(sem, key, index, sol_address):
                async with sem:
                    try:
                        # 根据代理配置设置代理
                        if proxy_config["type"] == "local":
                            proxy = proxy_config["proxys"][
                                index % len(proxy_config["proxys"])
                            ]
                            nstproxy_channel = None
                            nstproxy_password = None
                        else:
                            proxy = None
                            nstproxy_channel = proxy_config["channel"]
                            nstproxy_password = proxy_config["password"]

                        xc = zxc(
                            key=key,  # 签到不需要key，随便填
                            proxy=proxy,
                            index=index + 1,
                            invite_code=INVITE_CODE,
                            nstproxy_Channel=nstproxy_channel,
                            nstproxy_Password=nstproxy_password,
                            sol_address=sol_address,
                        )
                        if await xc.login():
                            await xc.info_quests()
                            return

                    except Exception as e:
                        logger.error(f"[{index + 1}] 处理账号时发生错误: {str(e)}")

            tasks = []
            if proxy_config["type"] == "local":
                total = min(len(keys), len(proxy_config["proxys"]))
            else:
                total = len(keys)

            # sol_addresss 和 keys 的长度可能不一致，所以需要处理这种情况
            if len(sol_addresss) != total:
                logger.error("私钥和sol_address数量不一致")
                return

            for index in range(total):
                task = process_daily(
                    sem, keys[index], index, sol_address=sol_addresss[index]
                )
                tasks.append(task)

            time_start = time.time()
            await asyncio.gather(*tasks)
            time_end = time.time()
            time_cost = datetime.timedelta(seconds=time_end - time_start)
            logger.success(f"所有日常任务执行完成 耗时: {time_cost}")

            # next_hour = datetime.datetime.now().replace(
            #     minute=0, second=0, microsecond=0
            # ) + datetime.timedelta(hours=24)
            # wait_seconds = (next_hour - datetime.datetime.now()).total_seconds()
            # logger.info(f"等待{wait_seconds/3600:.0f}小时后开始下一轮...")
            # await asyncio.sleep(wait_seconds)
            return True
        except Exception as e:
            retry_count += 1
            if retry_count < max_main_retries:
                logger.warning(
                    f"主循环失败，重试 {retry_count}/{max_main_retries}: {str(e)}"
                )
                await asyncio.sleep(300)
            else:
                logger.error(f"主循环失败，已重试{max_main_retries}次: {str(e)}")
                break


async def main() -> None:
    while True:
        # print_menu()
        choice = "2"
        if choice == "1":
            logger.info("开始执行每日任务...")
            await register_accounts()
        elif choice == "2":
            logger.info("开始执行每日任务...")
            await daily_tasks()
        elif choice == "0":
            logger.info("程序退出...")
            break
        else:
            logger.error("无效的选择，请重新输入")
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常退出: {str(e)}")
