#    This file is part of the AutoAnime distribution.
#    Copyright (c) 2026 Kaif_00z
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3.
#
#    This program is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#    General Public License for more details.
#
# License can be found in <
# https://github.com/kaif-00z/AutoAnimeBot/blob/main/LICENSE > .

# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)
# little bit inspired from pyUltroid.BaseClient

import asyncio
import sys
from logging import Logger
from traceback import format_exc

from pyrogram import Client, utils
from telethon import TelegramClient
from telethon.errors import (
    AccessTokenExpiredError,
    AccessTokenInvalidError,
    ApiIdInvalidError,
    AuthKeyDuplicatedError,
)
from telethon.errors.rpcerrorlist import UserNotParticipantError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    EditPhotoRequest,
    GetParticipantRequest,
)
from telethon.tl.functions.messages import ExportChatInviteRequest

from functions.config import Var
from libs.logger import LOGS, TelethonLogger


class Bot(TelegramClient):
    def __init__(
        self,
        api_id=None,
        api_hash=None,
        bot_token=None,
        logger: Logger = LOGS,
        log_attempt=True,
        exit_on_error=True,
        *args,
        **kwargs,
    ):
        self._handle_error = exit_on_error
        self._log_at = log_attempt
        self.logger = logger
        kwargs["api_id"] = api_id or Var.API_ID
        kwargs["api_hash"] = api_hash or Var.API_HASH
        kwargs["base_logger"] = TelethonLogger
        utils.MIN_CHANNEL_ID = -1009147483647
        super().__init__(
            None,
            connection_retries=10,
            retry_delay=5,
            auto_reconnect=True,
            flood_sleep_threshold=60,
            **kwargs,
        )
        self.pyro_client = Client(
            name="pekka",
            api_id=kwargs["api_id"],
            api_hash=kwargs["api_hash"],
            bot_token=bot_token or Var.BOT_TOKEN,
            in_memory=True,
        )
        self.user_client = None
        session_string = Var.SESSION
        if session_string:
            Var.SESSION = session_string
            self.user_client = TelegramClient(
                StringSession(session_string), kwargs["api_id"], kwargs["api_hash"]
            )
        self.run_in_loop(self.start_client(bot_token=bot_token or Var.BOT_TOKEN))

    def __repr__(self):
        return "<AutoAnimeBot.Client :\n bot: {}\n>".format(self._bot)

    async def start_client(self, **kwargs):
        """function to start client"""
        if self._log_at:
            self.logger.info("Trying To login.")
        try:
            await self.start(**kwargs)
            if self.user_client:
                try:
                    await self.user_client.connect()
                    authorized = await self.user_client.is_user_authorized()
                except Exception as error:
                    self.logger.warning(
                        "Could not load configured user session (%s).",
                        type(error).__name__,
                    )
                    authorized = False
                if not authorized:
                    self.logger.warning(
                        "Telegram user session is not authorized; use /login in the owner's private chat."
                    )
                    try:
                        await self.user_client.disconnect()
                    except Exception:
                        pass
                    self.user_client = None
                    Var.SESSION = None
            await self.pyro_client.start()
        except ApiIdInvalidError:
            self.logger.critical("API ID and API_HASH combination does not match!")
            sys.exit(1)
        except (AuthKeyDuplicatedError, EOFError):
            if self._handle_error:
                self.logger.critical("String session expired. Create new!")
                sys.exit(1)
            self.logger.critical("String session expired.")
        except (AccessTokenExpiredError, AccessTokenInvalidError):
            self.logger.critical(
                "Bot token is expired or invalid. Create new from @Botfather and add in BOT_TOKEN env variable!"
            )
            sys.exit(1)
        self.me = await self.get_me()
        if self.me.bot:
            me = f"@{self.me.username}"
        if self._log_at:
            self.logger.info(f"Logged in as {me}")
            if self.user_client:
                user_me = await self.user_client.get_me()
                self.logger.info(f"Logged in as @{user_me.username}")
        self._bot = await self.is_bot()

    async def attach_user_session(self, session_string):
        """Attach an already-authenticated StringSession without interactive prompts."""
        user_client = TelegramClient(
            StringSession(session_string), Var.API_ID, Var.API_HASH
        )
        try:
            await user_client.connect()
            if not await user_client.is_user_authorized():
                await user_client.disconnect()
                return False
        except Exception as error:
            self.logger.error(
                "Could not attach stored Telegram session (%s).", type(error).__name__
            )
            try:
                await user_client.disconnect()
            except Exception:
                pass
            return False
        self.user_client = user_client
        Var.SESSION = session_string
        return True

    async def upload_anime(self, file, caption, thumb=None, is_button=False):
        if not self.pyro_client.is_connected:
            try:
                await self.pyro_client.connect()
            except Exception:
                try:
                    await self.pyro_client.stop()
                except Exception:
                    pass
                await self.pyro_client.start()
        if is_button:
            if not Var.BACKUP_CHANNEL:
                raise RuntimeError("Configure a backup channel before enabling button upload.")
            targets = [Var.BACKUP_CHANNEL]
        else:
            targets = list(
                Var.MAIN_CHANNELS or ([Var.MAIN_CHANNEL] if Var.MAIN_CHANNEL else [])
            )
        if not targets:
            raise RuntimeError("Configure a main channel with /setchannel before uploading.")
        results = await asyncio.gather(
            *(
                self.pyro_client.send_document(
                    channel_id,
                    file,
                    caption=f"`{caption}`",
                    force_document=True,
                    thumb=thumb or "thumb.jpg",
                )
                for channel_id in targets
            ),
            return_exceptions=True,
        )
        posts = [item for item in results if not isinstance(item, BaseException)]
        for result in results:
            if isinstance(result, BaseException):
                self.logger.error("Could not post to one configured channel (%s).", type(result).__name__)
        if not posts:
            error = next((item for item in results if isinstance(item, BaseException)), None)
            raise RuntimeError("Could not upload to any configured channel.") from error
        return posts[0] if len(posts) == 1 else posts

    async def upload_poster(self, file, caption, channel_id=None):
        targets = (
            [channel_id]
            if channel_id
            else list(Var.MAIN_CHANNELS or ([Var.MAIN_CHANNEL] if Var.MAIN_CHANNEL else []))
        )
        if not targets:
            raise RuntimeError("Configure a main channel with /setchannel before posting.")
        results = await asyncio.gather(
            *(
                self.send_file(target, file=file, caption=caption or "")
                for target in targets
            ),
            return_exceptions=True,
        )
        posts = [item for item in results if not isinstance(item, BaseException)]
        for result in results:
            if isinstance(result, BaseException):
                self.logger.error("Could not post a poster to one channel (%s).", type(result).__name__)
        if not posts:
            error = next((item for item in results if isinstance(item, BaseException)), None)
            raise RuntimeError("Could not post the poster to any configured channel.") from error
        return posts[0] if len(posts) == 1 else posts

    async def is_joined(self, channel_id, user_id):
        try:
            await self(GetParticipantRequest(channel=channel_id, participant=user_id))
            return True
        except UserNotParticipantError:
            return False

    async def create_channel(self, title: str, logo=None):
        try:
            r = await self.user_client(
                CreateChannelRequest(
                    title=title,
                    about="Powered by https://t.me/ahjin_anime",
                    megagroup=False,
                )
            )
            created_chat_id = r.chats[0].id
            chat_id = int(f"-100{created_chat_id}")
            await asyncio.sleep(2)
            await self.user_client.edit_admin(
                int(chat_id),
                f"{((await self.get_me()).username)}",
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                pin_messages=True,
                add_admins=True,
            )
            if logo:
                try:
                    await self.user_client(
                        EditPhotoRequest(
                            chat_id, (await self.user_client.upload_file(logo))
                        )
                    )
                except BaseException:
                    pass
            return chat_id
        except BaseException:
            LOGS.error(format_exc())

    async def generate_invite_link(self, channel_id):
        try:
            data = await self.user_client(
                ExportChatInviteRequest(
                    peer=channel_id,
                    title=f"Generated By Ongoing Anime Bot",
                    request_needed=False,
                    usage_limit=None,
                )
            )
            return data.link
        except BaseException:
            LOGS.error(format_exc())

    async def delete_after(self, messages, seconds: int = 600):  # 10 min
        await asyncio.sleep(seconds)
        # maybe floodwait?
        await asyncio.gather(*[msg.delete() for msg in messages])
        # for msg in messages:
        #     try:
        #         await msg.delete()
        #     except Exception:
        #         pass

    def run_in_loop(self, function):
        return self.loop.run_until_complete(function)

    def run(self):
        self.run_until_disconnected()

    def add_handler(self, func, *args, **kwargs):
        if func in [_[0] for _ in self.list_event_handlers()]:
            return
        self.add_event_handler(func, *args, **kwargs)
