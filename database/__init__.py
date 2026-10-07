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

import sys
import time
from datetime import datetime, timezone
from traceback import format_exc

from motor.motor_asyncio import AsyncIOMotorClient

from functions.config import Var
from functions.session_store import decrypt_session, encrypt_session
from libs.logger import LOGS


class DataBase:
    CHANNEL_SETTINGS_ID = "CHANNEL_SETTINGS"
    USER_SESSION_ID = "ENCRYPTED_TELEGRAM_USER_SESSION"

    def __init__(self):
        try:
            LOGS.info("Trying To Connect With MongoDB")
            self.client = AsyncIOMotorClient(Var.MONGO_SRV)
            self.file_info_db = self.client["ONGOINGANIME"]["fileInfo"]
            self.channel_info_db = self.client["ONGOINGANIME"]["animeChannelInfo"]
            self.opts_db = self.client["ONGOINGANIME"]["opts"]
            self.file_store_db = self.client["ONGOINGANIME"]["fileStore"]
            self.broadcast_db = self.client["ONGOINGANIME"]["broadcastInfo"]
            LOGS.info("Successfully Connected With MongoDB")
        except Exception as error:
            LOGS.exception(format_exc())
            LOGS.critical(str(error))
            sys.exit(1)

    def _apply_channel_settings(self, settings):
        main_channels = list(dict.fromkeys(settings.get("main_channels", [])))[:2]
        force_sub_channels = settings.get("force_sub_channels", [])[:6]
        Var.MAIN_CHANNELS = main_channels
        Var.MAIN_CHANNEL = main_channels[0] if main_channels else 0
        Var.LOG_CHANNEL = settings.get("log_channel", 0)
        Var.BACKUP_CHANNEL = settings.get("backup_channel", 0)
        Var.CLOUD_CHANNEL = settings.get("cloud_channel", 0)
        Var.FORCESUB_CHANNELS = force_sub_channels
        Var.FORCESUB_CHANNEL = (
            force_sub_channels[0]["channel_id"] if force_sub_channels else 0
        )
        Var.FORCESUB_CHANNEL_LINK = (
            force_sub_channels[0]["invite_link"] if force_sub_channels else ""
        )

    def _legacy_channel_settings(self):
        main_channels = list(getattr(Var, "MAIN_CHANNELS", []) or [])
        if not main_channels and Var.MAIN_CHANNEL:
            main_channels = [Var.MAIN_CHANNEL]
        force_sub_channels = []
        if Var.FORCESUB_CHANNEL:
            invite_link = Var.FORCESUB_CHANNEL_LINK or ""
            force_sub_channels.append(
                {
                    "channel_id": int(Var.FORCESUB_CHANNEL),
                    "invite_link": invite_link,
                    "temporary": not bool(invite_link),
                }
            )
        return {
            "main_channels": main_channels[:2],
            "log_channel": Var.LOG_CHANNEL or 0,
            "backup_channel": Var.BACKUP_CHANNEL or 0,
            "cloud_channel": Var.CLOUD_CHANNEL or 0,
            "force_sub_channels": force_sub_channels,
        }

    async def get_channel_settings(self):
        data = await self.opts_db.find_one({"_id": self.CHANNEL_SETTINGS_ID})
        if not data:
            data = self._legacy_channel_settings()
            await self.opts_db.update_one(
                {"_id": self.CHANNEL_SETTINGS_ID},
                {"$set": data},
                upsert=True,
            )
        raw_force_sub_channels = data.get("force_sub_channels") or []
        if not raw_force_sub_channels and data.get("force_sub_channel"):
            legacy_link = str(data.get("force_sub_link") or "")
            raw_force_sub_channels = [
                {
                    "channel_id": data["force_sub_channel"],
                    "invite_link": legacy_link,
                    "temporary": not bool(legacy_link),
                }
            ]
        force_sub_channels = []
        seen_force_sub_ids = set()
        for entry in raw_force_sub_channels:
            channel_id = int(entry.get("channel_id") or 0)
            if not channel_id or channel_id in seen_force_sub_ids:
                continue
            seen_force_sub_ids.add(channel_id)
            force_sub_channels.append(
                {
                    "channel_id": channel_id,
                    "invite_link": str(entry.get("invite_link") or ""),
                    "temporary": bool(entry.get("temporary", False)),
                }
            )
            if len(force_sub_channels) == 6:
                break
        settings = {
            "main_channels": [
                int(channel)
                for channel in (data.get("main_channels") or [])
                if int(channel) != 0
            ][:2],
            "log_channel": int(data.get("log_channel") or 0),
            "backup_channel": int(data.get("backup_channel") or 0),
            "cloud_channel": int(data.get("cloud_channel") or 0),
            "force_sub_channels": force_sub_channels,
        }
        first_force_sub = force_sub_channels[0] if force_sub_channels else {}
        settings["force_sub_channel"] = first_force_sub.get("channel_id", 0)
        settings["force_sub_link"] = first_force_sub.get("invite_link", "")
        if data.get("force_sub_channels") != force_sub_channels:
            await self.opts_db.update_one(
                {"_id": self.CHANNEL_SETTINGS_ID},
                {"$set": settings},
                upsert=True,
            )
        self._apply_channel_settings(settings)
        return settings

    async def _save_channel_settings(self, settings):
        await self.opts_db.update_one(
            {"_id": self.CHANNEL_SETTINGS_ID},
            {"$set": settings},
            upsert=True,
        )
        self._apply_channel_settings(settings)

    async def load_user_session(self):
        data = await self.opts_db.find_one({"_id": self.USER_SESSION_ID})
        if not data or not data.get("token"):
            return None
        return decrypt_session(data["token"], Var.SESSION_ENCRYPTION_KEY)

    async def store_user_session(self, session_string):
        token = encrypt_session(session_string, Var.SESSION_ENCRYPTION_KEY)
        await self.opts_db.update_one(
            {"_id": self.USER_SESSION_ID},
            {"$set": {"token": token}},
            upsert=True,
        )

    async def get_force_sub_invite(self, user_id, channel_id):
        key = f"FSUB_INVITE:{int(user_id)}:{int(channel_id)}"
        data = await self.opts_db.find_one({"_id": key})
        if data:
            expires_at = data.get("expires_at")
            if isinstance(expires_at, datetime):
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                is_valid = expires_at.timestamp() > time.time()
            else:
                is_valid = float(expires_at or 0) > time.time()
            if is_valid:
                return data.get("invite_link")
        return None

    async def store_force_sub_invite(
        self, user_id, channel_id, invite_link, expires_at
    ):
        key = f"FSUB_INVITE:{int(user_id)}:{int(channel_id)}"
        if not getattr(self, "_force_sub_ttl_index_ready", False):
            try:
                await self.opts_db.create_index(
                    "expires_at",
                    expireAfterSeconds=0,
                    name="force_sub_invite_expiry",
                )
            except Exception as error:
                LOGS.warning(
                    "Could not create temporary invite cleanup index (%s).",
                    type(error).__name__,
                )
            self._force_sub_ttl_index_ready = True
        await self.opts_db.update_one(
            {"_id": key},
            {
                "$set": {
                    "invite_link": invite_link,
                    "expires_at": datetime.fromtimestamp(
                        float(expires_at), timezone.utc
                    ),
                }
            },
            upsert=True,
        )

    async def set_channel(
        self, role, channel_id, invite_link="", temporary=False
    ):
        settings = await self.get_channel_settings()
        if role == "main":
            channels = settings["main_channels"]
            if channel_id not in channels:
                if len(channels) >= 2:
                    raise ValueError("At most two main channels can be configured.")
                channels.append(channel_id)
            settings["main_channels"] = channels
        elif role in {"log", "backup", "cloud"}:
            settings[f"{role}_channel"] = channel_id
        elif role == "forcesub":
            channels = settings["force_sub_channels"]
            entry = {
                "channel_id": channel_id,
                "invite_link": invite_link,
                "temporary": bool(temporary),
            }
            existing = next(
                (i for i, item in enumerate(channels) if item["channel_id"] == channel_id),
                None,
            )
            if existing is None:
                if len(channels) >= 6:
                    raise ValueError("At most six force-sub channels can be configured.")
                channels.append(entry)
            else:
                channels[existing] = entry
            settings["force_sub_channels"] = channels
            first = channels[0] if channels else {}
            settings["force_sub_channel"] = first.get("channel_id", 0)
            settings["force_sub_link"] = first.get("invite_link", "")
        else:
            raise ValueError("Unknown channel role.")
        await self._save_channel_settings(settings)
        return settings

    async def unset_channel(self, role, channel_id=None):
        settings = await self.get_channel_settings()
        if role == "main":
            if channel_id is None:
                settings["main_channels"] = []
            else:
                settings["main_channels"] = [
                    item for item in settings["main_channels"] if item != channel_id
                ]
        elif role in {"log", "backup", "cloud"}:
            settings[f"{role}_channel"] = 0
        elif role == "forcesub":
            if channel_id is None:
                settings["force_sub_channels"] = []
            else:
                settings["force_sub_channels"] = [
                    item
                    for item in settings["force_sub_channels"]
                    if item["channel_id"] != channel_id
                ]
            first = settings["force_sub_channels"][0] if settings["force_sub_channels"] else {}
            settings["force_sub_channel"] = first.get("channel_id", 0)
            settings["force_sub_link"] = first.get("invite_link", "")
        else:
            raise ValueError("Unknown channel role.")
        await self._save_channel_settings(settings)
        return settings

    async def add_anime(self, uid):
        data = await self.file_info_db.find_one({"_id": uid})
        if not data:
            await self.file_info_db.insert_one({"_id": uid})

    async def toggle_separate_channel_upload(self):
        data = await self.opts_db.find_one({"_id": "SEPARATE_CHANNEL_UPLOAD"})
        _data = not (data or {}).get("switch", False)
        await self.opts_db.update_one(
            {"_id": "SEPARATE_CHANNEL_UPLOAD"}, {"$set": {"switch": _data}}, upsert=True
        )

    async def is_separate_channel_upload(self):
        data = await self.opts_db.find_one({"_id": "SEPARATE_CHANNEL_UPLOAD"})
        return (data or {}).get("switch", False)

    async def toggle_original_upload(self):
        data = await self.opts_db.find_one({"_id": "OG_UPLOAD"})
        _data = not (data or {}).get("switch", False)
        await self.opts_db.update_one(
            {"_id": "OG_UPLOAD"}, {"$set": {"switch": _data}}, upsert=True
        )

    async def is_original_upload(self):
        data = await self.opts_db.find_one({"_id": "OG_UPLOAD"})
        return (data or {}).get("switch", False)

    async def toggle_button_upload(self):
        data = await self.opts_db.find_one({"_id": "BUTTON_UPLOAD"})
        _data = not (data or {}).get("switch", False)
        await self.opts_db.update_one(
            {"_id": "BUTTON_UPLOAD"}, {"$set": {"switch": _data}}, upsert=True
        )

    async def is_button_upload(self):
        data = await self.opts_db.find_one({"_id": "BUTTON_UPLOAD"})
        return (data or {}).get("switch", False)

    async def is_anime_uploaded(self, uid):
        data = await self.file_info_db.find_one({"_id": uid})
        if data:
            return True
        return False

    async def add_anime_channel_info(self, title, _data):
        await self.channel_info_db.update_one(
            {"_id": title}, {"$set": {"data": _data}}, upsert=True
        )

    async def get_anime_channel_info(self, title):
        data = await self.channel_info_db.find_one({"_id": title})
        if (data or {}).get(title):
            return data["data"]
        return {}

    async def store_items(self, _hash, _list):
        # in case
        await self.file_store_db.update_one(
            {"_id": _hash}, {"$set": {"data": _list}}, upsert=True
        )

    async def get_store_items(self, _hash):
        data = await self.file_store_db.find_one({"_id": _hash})
        if (data or {}).get("data"):
            return data["data"]
        return []

    async def add_broadcast_user(self, user_id):
        data = await self.broadcast_db.find_one({"_id": user_id})
        if not data:
            await self.broadcast_db.insert_one({"_id": user_id})

    async def get_broadcast_user(self):
        data = self.broadcast_db.find()
        return [i["_id"] for i in (await data.to_list(length=None))]

    async def toggle_ss_upload(self):
        data = await self.opts_db.find_one({"_id": "SS_UPLOAD"})
        _new = not (data or {}).get("switch", True)
        await self.opts_db.update_one(
            {"_id": "SS_UPLOAD"},
            {"$set": {"switch": _new}},
            upsert=True,
        )

    async def is_ss_upload(self):
        data = await self.opts_db.find_one({"_id": "SS_UPLOAD"})
        return (data or {}).get("switch", True)
