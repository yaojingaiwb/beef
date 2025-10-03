import asyncio, sys, loguru, os, random, string, time
from curl_cffi.requests import AsyncSession


logger = loguru.logger
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<g>{time:HH:mm:ss:SSS}</g> | <level>{message}</level>",
)


class Twitter2:
    def __init__(self, auth_token: str, proxy: str = None):
        self.auth_token = auth_token
        self.bearer_token = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
        self.defaulf_headers = {
            "authority": "twitter.com",
            "origin": "https://twitter.com",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
            "Authorization": self.bearer_token,
        }
        self.defaulf_cookies = {"auth_token": auth_token}
        self.Twitter = AsyncSession(
            headers=self.defaulf_headers,
            cookies=self.defaulf_cookies,
            timeout=120,
            proxies=proxy,
        )
        self.auth_code = None
        self.csrf_token = None
        self.CreateRetweet_queryId = None
        self.FavoriteTweet_queryId = None

    # 获取auth_code
    async def get_auth_code(self, client_id, state, code_challenge):
        try:
            params = {
                "code_challenge": code_challenge,
                "code_challenge_method": "plain",
                "client_id": client_id,
                "redirect_uri": "https://app.fantv.world/mobile/twitter",
                "response_type": "code",
                "scope": "tweet.read users.read follows.read follows.write offline.access tweet.write",
                "state": f"{state} followTwitter",
            }
            response = await self.Twitter.get(
                "https://x.com/i/api/2/oauth2/authorize", params=params
            )
            if "code" in response.json() and response.json()["code"] == 353:
                self.Twitter.headers.update({"x-csrf-token": response.cookies["ct0"]})
                return await self.get_auth_code(client_id, state, code_challenge)
            elif response.status_code == 429:
                await asyncio.sleep(5)
                return await self.get_auth_code(client_id, state, code_challenge)
            elif "auth_code" in response.json():
                self.auth_code = response.json()["auth_code"]
                return True
            logger.error(f"{self.auth_token} 获取auth_code失败{response.json()}")
            return False
        except Exception as e:
            logger.error(f"{self.auth_token} 获取auth_code异常：{e}")
            return False

    # 获取auth_code
    async def authorize(self, client_id, state, code_challenge):
        try:
            if not await self.get_auth_code(client_id, state, code_challenge):
                return False
            data = {
                "approval": "true",
                "code": self.auth_code,
            }
            response = await self.Twitter.post(
                "https://x.com/i/api/2/oauth2/authorize", data=data
            )
            if "redirect_uri" in response.text:
                logger.info(f"{self.auth_token}  推特授权成功 {response.text}")
                redirect_uri = response.json()
                return redirect_uri["redirect_uri"]
            elif response.status_code == 429:
                await asyncio.sleep(5)
                return await self.authorize(client_id, state, code_challenge)
            logger.error(f"{self.auth_token}  推特授权失败")
            return False
        except Exception as e:
            logger.error(f"{self.auth_token}  推特授权异常：{e}")
            return False

    # 获取CSRF token
    async def get_csrf_token(self):
        try:
            response = await self.Twitter.get(
                "https://x.com/i/api/1.1/friendships/create.json"
            )
            if "ct0" in response.cookies:
                self.csrf_token = response.cookies["ct0"]
                self.Twitter.headers.update({"x-csrf-token": self.csrf_token})
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"{self.auth_token}  获取CSRF token失败: {e}")
            return False

    # 用户名转id
    async def get_user_id(self, screen_name: str):
        try:
            if not self.csrf_token:
                if not await self.get_csrf_token():
                    return False

            res = await self.Twitter.get(
                f"https://x.com/i/api/graphql/-0XdHI-mrHWBQd8-oLo1aA/ProfileSpotlightsQuery?variables=%7B%22screen_name%22%3A%22{screen_name}%22%7D",
            )
            if res.status_code == 200:
                res = res.json()
                user_id = res["data"]["user_result_by_screen_name"]["result"]["rest_id"]
                return user_id
            logger.error(
                f"{self.auth_token}  推特获取用户id失败 {res.status_code}  返回信息{res.text}"
            )
            return False

        except Exception as e:
            logger.error(f"{self.auth_token}  推特获取用户id异常：{e}")
            return False

    # 关注
    async def follow(self, user_id: str):
        try:
            if not self.csrf_token:
                if not await self.get_csrf_token():
                    return False
            data = {
                "include_profile_interstitial_type": 1,
                "include_blocking": 1,
                "include_blocked_by": 1,
                "include_followed_by": 1,
                "include_want_retweets": 1,
                "include_mute_edge": 1,
                "include_can_dm": 1,
                "include_can_media_tag": 1,
                "include_ext_is_blue_verified": 1,
                "include_ext_verified_type": 1,
                "include_ext_profile_image_shape": 1,
                "skip_status": 1,
                "user_id": user_id,
            }

            res = await self.Twitter.post(
                "https://x.com/i/api/1.1/friendships/create.json",
                data=data,
            )
            if res.status_code == 200:
                logger.success(f"{self.auth_token}  推特关注成功")
                return True
            elif res.status_code == 429:
                await asyncio.sleep(5)
                return await self.follow(user_id)
            logger.error(
                f"{self.auth_token}  推特关注失败 {res.status_code}  返回信息{res.text}"
            )
            return False

        except Exception as e:
            logger.error(f"{self.auth_token}  推特关注异常：{e}")
            return False

    # 发推
    async def CreateTweet(self, msg: str):
        try:
            if not self.csrf_token:
                if not await self.get_csrf_token():
                    return False
            data = {
                "variables": {
                    "tweet_text": msg,
                    "dark_request": False,
                    "media": {"media_entities": [], "possibly_sensitive": False},
                    "semantic_annotation_ids": [],
                    "disallowed_reply_options": None,
                },
                "features": {
                    "premium_content_api_read_enabled": False,
                    "communities_web_enable_tweet_community_results_fetch": True,
                    "c9s_tweet_anatomy_moderator_badge_enabled": True,
                    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                    "responsive_web_grok_analyze_post_followups_enabled": True,
                    "responsive_web_jetfuel_frame": False,
                    "responsive_web_grok_share_attachment_enabled": True,
                    "responsive_web_edit_tweet_api_enabled": True,
                    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                    "view_counts_everywhere_api_enabled": True,
                    "longform_notetweets_consumption_enabled": True,
                    "responsive_web_twitter_article_tweet_consumption_enabled": True,
                    "tweet_awards_web_tipping_enabled": False,
                    "responsive_web_grok_analysis_button_from_backend": False,
                    "creator_subscriptions_quote_tweet_preview_enabled": False,
                    "longform_notetweets_rich_text_read_enabled": True,
                    "longform_notetweets_inline_media_enabled": True,
                    "profile_label_improvements_pcf_label_in_post_enabled": True,
                    "rweb_tipjar_consumption_enabled": True,
                    "responsive_web_graphql_exclude_directive_enabled": True,
                    "verified_phone_label_enabled": False,
                    "articles_preview_enabled": True,
                    "rweb_video_timestamps_enabled": True,
                    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                    "freedom_of_speech_not_reach_fetch_enabled": True,
                    "standardized_nudges_misinfo": True,
                    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                    "responsive_web_grok_image_annotation_enabled": True,
                    "responsive_web_graphql_timeline_navigation_enabled": True,
                    "responsive_web_enhance_cards_enabled": False,
                },
                "queryId": "UYy4T67XpYXgWKOafKXB_A",
            }

            res = await self.Twitter.post(
                "https://x.com/i/api/graphql/UYy4T67XpYXgWKOafKXB_A/CreateTweet",
                json=data,
            )
            if res.status_code == 200:
                if "errors" in res.text:
                    logger.error(f"{self.auth_token}  推文发送失败 {res.text}")
                    return False
                else:
                    logger.success(f"{self.auth_token}  推文发送成功")
                    return True
            elif res.status_code == 429:
                await asyncio.sleep(5)
                return await self.CreateTweet(msg)
            logger.error(
                f"{self.auth_token}  推文发送失败 {res.status_code}  返回信息{res.text}"
            )
            return False

        except Exception as e:
            logger.error(f"{self.auth_token}  推文发送异常：{e}")
            return False

    # 验证token
    async def verify_token(self):
        try:
            # 尝试获取用户信息来验证token
            response = await self.Twitter.get(
                "https://x.com/i/api/fleets/v1/fleetline?only_spaces=true"
            )

            if response.status_code == 200:
                logger.info(f"{self.auth_token} Token验证成功")
                return True
            elif response.status_code == 401:
                logger.error(f"{self.auth_token} Token无效")
                return False
            else:
                logger.error(
                    f"{self.auth_token} Token验证失败，状态码：{response.status_code}"
                )

                return await self.verify_token()
        except Exception as e:
            logger.error(f"{self.auth_token} Token验证异常：{e}")
            return await self.verify_token()

    # 获取用户名
    async def get_name(self):
        try:
            if not self.csrf_token:
                if not await self.get_csrf_token():
                    return False
            url = "https://x.com/i/api/2/notifications/all.json?include_profile_interstitial_type=1&include_blocking=1&include_blocked_by=1&include_followed_by=1&include_want_retweets=1&include_mute_edge=1&include_can_dm=1&include_can_media_tag=1&include_ext_is_blue_verified=1&include_ext_verified_type=1&include_ext_profile_image_shape=1&skip_status=1&cards_platform=Web-12&include_cards=1&include_ext_alt_text=true&include_ext_limited_action_results=true&include_quote_count=true&include_reply_count=1&tweet_mode=extended&include_ext_views=true&include_entities=true&include_user_entities=true&include_ext_media_color=true&include_ext_media_availability=true&include_ext_sensitive_media_warning=true&include_ext_trusted_friends_metadata=true&send_error_codes=true&simple_quoted_tweet=true&count=20&requestContext=launch&ext=mediaStats%2ChighlightedLabel%2ChasParodyProfileLabel%2CvoiceInfo%2CbirdwatchPivot%2CsuperFollowMetadata%2CunmentionInfo%2CeditControl%2Carticle"
            response = await self.Twitter.get(url)
            if response.status_code == 200:
                res = response.json()
                users = res["globalObjects"]["users"]
                screen_names = []
                for user_id in users:
                    screen_name = users[user_id][
                        "screen_name"
                    ]  # 这就是获取screen_name的路径
                    screen_names.append(screen_name)
                logger.info(f"{self.auth_token} 获取用户名成功: {screen_names}")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"{self.auth_token} 获取用户名异常: {e}")
            return False

    # 转发
    async def repost(self, tweet_id: str):
        try:
            if not self.CreateRetweet_queryId:
                if not await self.get_queryId():
                    return False
            if not self.csrf_token:
                if not await self.get_csrf_token():
                    return False
            url = f"https://x.com/i/api/graphql/{self.CreateRetweet_queryId}/CreateRetweet"
            data_json = {
                "variables": {"tweet_id": tweet_id, "dark_request": False},
                "queryId": self.CreateRetweet_queryId,
            }
            response = await self.Twitter.post(url, json=data_json)
            if response.status_code == 200:
                await self.favorite(tweet_id)
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"{self.auth_token} 推特转发异常: {e}")
            return False

    # 点赞
    async def favorite(self, tweet_id: str):
        try:
            if not self.FavoriteTweet_queryId:
                if not await self.get_queryId():
                    return False
            url = f"https://x.com/i/api/graphql/{self.FavoriteTweet_queryId}/FavoriteTweet"
            data_json = {
                "variables": {"tweet_id": tweet_id, "dark_request": False},
                "queryId": self.FavoriteTweet_queryId,
            }
            response = await self.Twitter.post(url, json=data_json)
            if response.status_code == 200:
                logger.success(f"{self.auth_token} 点赞成功")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"{self.auth_token} 推特点赞异常: {e}")
            return False

    # 获取queryId
    async def get_queryId(self):
        try:
            url = "https://abs.twimg.com/responsive-web/client-web/main.4a23f9ca.js"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            }
            response = await self.Twitter.get(url, headers=headers)
            if response.status_code == 200:
                res = response.text
                # 用于存储找到的queryId
                favorite_tweet_id = None
                create_retweet_id = None

                # 遍历所有queryId
                current_pos = 0
                while True:
                    # 查找下一个queryId
                    query_index = res.find('queryId:"', current_pos)
                    if query_index == -1:
                        break

                    # 提取queryId
                    query_id_start = query_index + len('queryId:"')
                    query_id_end = res.find('"', query_id_start)
                    if query_id_end == -1:
                        break

                    query_id = res[query_id_start:query_id_end]

                    # 查找这个queryId后面的operationName
                    operation_text = res[
                        query_id_end : query_id_end + 100
                    ]  # 查看后面100个字符

                    if 'operationName:"FavoriteTweet"' in operation_text:
                        favorite_tweet_id = query_id
                    elif 'operationName:"CreateRetweet"' in operation_text:
                        create_retweet_id = query_id

                    if favorite_tweet_id and create_retweet_id:
                        break

                    current_pos = query_id_end + 1

                if not favorite_tweet_id or not create_retweet_id:
                    logger.error(f"{self.auth_token} 未找到所需的queryId")
                    return False

                self.CreateRetweet_queryId = create_retweet_id
                self.FavoriteTweet_queryId = favorite_tweet_id
                # logger.info(
                #     f"{self.auth_token} 获取queryId成功: CreateRetweet_queryId: {create_retweet_id}, FavoriteTweet_queryId: {favorite_tweet_id}"
                # )
                return True
            else:
                logger.error(
                    f"{self.auth_token} 请求失败，状态码: {response.status_code}"
                )
                return False
        except Exception as e:
            logger.error(f"{self.auth_token} 获取queryId异常: {str(e)}")
            return False


# NAME = [
#     "1870996459644149761",
#     "1658385599395696643",
#     "1549289212075442176",
#     "1774124248161976320",
# ]
# # user-kl020543-sessid-YB8yJw7p-sesstime-1-keep-true:3832985b4e0964d96596c87000353d36:pr.roxlabs.cn:4600
# nstproxy_Channel = "5A9CF1703859A242"
# nstproxy_Password = "qqqq1111"
# session = "".join(random.choices(string.digits + string.ascii_letters, k=9))
# nstproxy = f"http://user-kl020543-sessid-{session}-sesstime-1-keep-true:3832985b4e0964d96596c87000353d36@pr.roxlabs.cn:4600"
# proxies = {"http": nstproxy, "https": nstproxy}
# words = [
#     "PIAN token has shown remarkable growth potential in the crypto market.",
#     "The innovative technology behind PIAN token sets it apart from other cryptocurrencies.",
#     "Investing in PIAN token could be a smart move for long-term gains.",
#     "PIAN token's community support is strong and growing every day.",
#     "The transparency and security features of PIAN token are highly commendable.",
#     "PIAN token's roadmap is clear and well-structured, promising a bright future.",
#     "The team behind PIAN token is dedicated and highly skilled, ensuring continuous development.",
#     "PIAN token offers unique utility that makes it a valuable asset in the blockchain ecosystem.",
#     "The market performance of PIAN token has been impressive, attracting many investors.",
#     "PIAN token's low transaction fees make it an attractive option for users.",
#     "The partnerships and collaborations of PIAN token are expanding its reach and influence.",
#     "PIAN token's innovative use cases are driving its adoption across various industries.",
#     "The scalability of PIAN token's blockchain technology is a significant advantage.",
#     "PIAN token's user-friendly interface makes it accessible to both beginners and experts.",
#     "The consistent updates and improvements to PIAN token's platform show a commitment to excellence.",
#     "PIAN token's potential for mass adoption is evident given its strong fundamentals.",
#     "The community-driven approach of PIAN token fosters trust and engagement among users.",
#     "PIAN token's ability to integrate with other platforms enhances its versatility and utility.",
#     "The long-term vision of PIAN token's development team is inspiring and promising.",
#     "PIAN token's resilience in volatile market conditions demonstrates its stability and reliability.",
# ]
# random_words = random.sample(words, 1)
# msg = f"{' '.join(random_words)}\n#Painfession @Pain"
# print(msg)
# with open(os.path.join(os.path.dirname(__file__), "tw_token.txt"), "r") as f:
#     twtoekns = f.read().splitlines()
# with open(os.path.join(os.path.dirname(__file__), "proxy.txt"), "r") as f:
#     proxys = f.read().splitlines()
# for i, twtoken in enumerate(twtoekns):
#     # for i in NAME:
#     #     logger.info(f"{twtoken} 开始关注: {i}")
#     #     res = asyncio.run(Twitter2(twtoken).follow(i))
#     proxies = {"http": proxys[i], "https": proxys[i]}
#     res = asyncio.run(Twitter2(twtoken, proxies).CreateTweet(msg))
#     time.sleep(3)


async def main(twtoken, proxies) -> None:
    zxc = Twitter2(twtoken, proxies)
    gz = await zxc.follow("1629692601317330945")
    dz = await zxc.favorite("1874893754269905320")


with open(os.path.join(os.path.dirname(__file__), "tw_token.txt"), "r") as f:
    twtoekns = f.read().splitlines()

with open(os.path.join(os.path.dirname(__file__), "proxy.txt"), "r") as f:
    proxys = f.read().splitlines()
for i, twtoken in enumerate(twtoekns):
    # for i in NAME:
    #     logger.info(f"{twtoken} 开始关注: {i}")
    #     res = asyncio.run(Twitter2(twtoken).follow(i))
    proxies = {"http": proxys[i], "https": proxys[i]}
    res = asyncio.run(main(twtoken, proxies))
    time.sleep(1)
