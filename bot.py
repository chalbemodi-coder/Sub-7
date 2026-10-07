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

import re
from traceback import format_exc

from telethon import Button, events
from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeEmptyError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from core.bot import Bot
from core.executors import Executors
from database import DataBase
from functions.info import AnimeInfo
from functions.schedule import ScheduleTasks, Var
from functions.session_store import SessionStoreError, get_session_key
from functions.tools import Tools, asyncio
from functions.utils import AdminUtils
from libs.ariawarp import Torrent
from libs.logger import LOGS, Reporter
from libs.subsplease import SubsPlease

tools = Tools()
tools.init_dir()
bot = Bot()
dB = DataBase()
bot.run_in_loop(dB.get_channel_settings())
if not Var.SESSION:
    try:
        stored_session = bot.run_in_loop(dB.load_user_session())
        if stored_session and not bot.run_in_loop(
            bot.attach_user_session(stored_session)
        ):
            LOGS.warning("Stored Telegram session is not authorized; use /login.")
    except SessionStoreError as error:
        LOGS.error("Stored Telegram session unavailable (%s).", type(error).__name__)
subsplease = SubsPlease(dB)
torrent = Torrent()
schedule = ScheduleTasks(bot)
admin = AdminUtils(dB, bot)


@bot.on(
    events.NewMessage(
        incoming=True, pattern="^/start ?(.*)", func=lambda e: e.is_private
    )
)
async def _start(event):
    xnx = await event.reply("`Please Wait...`")
    msg_id = event.pattern_match.group(1)
    await dB.add_broadcast_user(event.sender_id)
    force_sub_channels = Var.FORCESUB_CHANNELS or []
    if not force_sub_channels and Var.FORCESUB_CHANNEL and Var.FORCESUB_CHANNEL_LINK:
        force_sub_channels = [
            {
                "channel_id": Var.FORCESUB_CHANNEL,
                "invite_link": Var.FORCESUB_CHANNEL_LINK,
                "temporary": False,
            }
        ]
    missing_channels = []
    for index, channel in enumerate(force_sub_channels, start=1):
        channel_id = channel["channel_id"]
        try:
            is_user_joined = await bot.is_joined(channel_id, event.sender_id)
        except Exception as error:
            LOGS.error("Force-sub membership check failed (%s).", type(error).__name__)
            return await xnx.edit(
                "Could not verify required channel membership. Please contact the bot owner."
            )
        if is_user_joined:
            continue
        if channel.get("temporary"):
            try:
                invite_link = await dB.get_force_sub_invite(
                    event.sender_id, channel_id
                )
                if not invite_link:
                    invite_link, expires_at = await bot.generate_temporary_invite_link(
                        channel_id, minutes=10
                    )
                    await dB.store_force_sub_invite(
                        event.sender_id, channel_id, invite_link, expires_at
                    )
            except Exception as error:
                LOGS.error(
                    "Temporary force-sub link generation failed (%s).",
                    type(error).__name__,
                )
                return await xnx.edit(
                    "Could not create a temporary join link. The bot must be admin with invite-user rights in that channel."
                )
        else:
            invite_link = channel.get("invite_link", "")
        if not invite_link:
            return await xnx.edit(
                "A force-sub channel has no invite link. Please contact the bot owner."
            )
        missing_channels.append(
            [Button.url(f"🚀 JOIN CHANNEL {index}", url=invite_link)]
        )
    if missing_channels:
        missing_channels.append(
            [
                Button.url(
                    "♻️ REFRESH",
                    url=f"https://t.me/{((await bot.get_me()).username)}?start={msg_id}",
                )
            ]
        )
        return await xnx.edit(
            "**Please join all required channels to use this bot.**\nTemporary links expire in 10 minutes and can be used once.",
            buttons=missing_channels,
        )
    if msg_id:
        if msg_id.isdigit():
            msg = await bot.get_messages(Var.BACKUP_CHANNEL, ids=int(msg_id))
            sent_msg = await event.reply(msg)
            notice = await sent_msg.reply(
                "__This file will be automatically deleted after 10 minutes.\nPlease save or forward it immediately.__"
            )
            asyncio.create_task(bot.delete_after([notice, sent_msg], seconds=600))
        else:
            items = await dB.get_store_items(msg_id)
            if items:
                for id in items:
                    msg = await bot.get_messages(Var.CLOUD_CHANNEL, ids=id)
                    if msg:
                        await event.reply(file=[i for i in msg])
    else:
        if event.sender_id == Var.OWNER:
            return await xnx.edit(
                "__Browse Admin Options:__",
                buttons=admin.admin_panel(),
            )
        await event.reply(
            f"**Enjoy Ongoing Anime's Best Encode 24/7 🫡**",
            buttons=[
                [
                    Button.url("👨‍💻 DEV", url="https://t.me/ahjin_anime"),
                    Button.url(
                        "💖 OPEN SOURCE",
                        url="https://github.com/chalbemodi-coder/Sub-7/",
                    ),
                ]
            ],
        )
    await xnx.delete()


@bot.on(
    events.NewMessage(incoming=True, pattern="^/about", func=lambda e: e.is_private)
)
async def _(e):
    await admin._about(e)


@bot.on(
    events.NewMessage(
        incoming=True,
        pattern=r"^/channels(?:@\w+)?$",
        func=lambda e: e.is_private,
    )
)
async def _show_channels(event):
    if not Var.OWNER or event.sender_id != Var.OWNER:
        return await event.reply("This command is only available to the configured owner.")
    settings = await dB.get_channel_settings()
    main = ", ".join(str(item) for item in settings["main_channels"]) or "not set"
    force_sub_lines = [
        f"`{item['channel_id']}` — {'10-minute, one-use link' if item['temporary'] else 'fixed link'}"
        for item in settings["force_sub_channels"]
    ] or ["not set"]
    text = (
        "**Channel settings**\n"
        f"Main (max 2): `{main}`\n"
        f"Logs: `{settings['log_channel'] or 'not set'}`\n"
        f"Backup: `{settings['backup_channel'] or 'not set'}`\n"
        f"Cloud: `{settings['cloud_channel'] or 'not set'}`\n"
        f"Force-sub (max 6):\n" + "\n".join(force_sub_lines) + "\n\n"
        "Set: `/setchannel main|log|backup|cloud <channel_id>`\n"
        "Temp force-sub: `/setchannel forcesub <channel_id> temp`\n"
        "Fixed force-sub: `/setchannel forcesub <channel_id> fixed <invite_link>`\n"
        "Add the bot as admin; temporary links need invite-user rights.\n"
        "Switching to temp does not revoke any old fixed invite link; revoke that link in Telegram if needed.\n"
        "Remove force-sub: `/unsetchannel forcesub [channel_id]`; other roles: `/unsetchannel main [channel_id]` or `/unsetchannel log|backup|cloud`."
    )
    await event.reply(text)


@bot.on(
    events.NewMessage(
        incoming=True,
        pattern=r"^/setchannel(?:@\w+)?(?:\s|$)",
        func=lambda e: e.is_private,
    )
)
async def _set_channel(event):
    if not Var.OWNER or event.sender_id != Var.OWNER:
        return await event.reply("This command is only available to the configured owner.")
    parts = event.raw_text.split(maxsplit=4)
    if len(parts) < 3:
        return await event.reply("Use `/channels` to see channel setup commands.")
    role = parts[1].lower().replace("-", "")
    aliases = {"logs": "log", "fsub": "forcesub", "mainchannel": "main"}
    role = aliases.get(role, role)
    if role not in {"main", "log", "backup", "cloud", "forcesub"}:
        return await event.reply("Unknown channel type. Use `/channels` for help.")
    try:
        channel_id = int(parts[2])
    except ValueError:
        return await event.reply("Send a numeric Telegram channel ID, such as `-1001234567890`.")
    if channel_id == 0:
        return await event.reply("Channel ID cannot be 0.")
    if channel_id > 0:
        return await event.reply("Use the channel's negative numeric ID, for example `-1001234567890`.")
    invite_link = ""
    temporary = False
    if role == "forcesub":
        if len(parts) == 4 and parts[3].lower() in {"temp", "temporary", "10m"}:
            temporary = True
        elif len(parts) >= 5 and parts[3].lower() in {"fixed", "permanent"}:
            invite_link = parts[4].strip()
        elif len(parts) == 4 and parts[3].startswith(("https://t.me/", "http://t.me/")):
            # Backward-compatible syntax: /setchannel forcesub <id> <invite_link>
            invite_link = parts[3].strip()
        else:
            return await event.reply(
                "Use `/setchannel forcesub <id> temp` or `/setchannel forcesub <id> fixed <invite_link>`."
            )
        if not temporary and not invite_link.startswith(("https://t.me/", "http://t.me/")):
            return await event.reply("Fixed mode needs a valid `https://t.me/` invite link.")
    try:
        settings = await dB.set_channel(
            role, channel_id, invite_link, temporary=temporary
        )
    except ValueError as error:
        return await event.reply(str(error))
    except Exception as error:
        LOGS.error("Could not save channel settings (%s).", type(error).__name__)
        return await event.reply("Could not save that channel setting. Check the database connection.")
    if role == "main":
        targets = ", ".join(str(item) for item in settings["main_channels"])
        return await event.reply(f"Main channel configured. Posts will go to: `{targets}`")
    if role == "forcesub":
        mode = "10-minute, one-use temporary link" if temporary else "fixed invite link"
        note = " Revoke any old fixed invite in Telegram if you switched to temp." if temporary else ""
        return await event.reply(f"Force-sub channel `{channel_id}` saved with {mode}.{note}")
    return await event.reply(f"`{role}` channel configured as `{channel_id}`.")


@bot.on(
    events.NewMessage(
        incoming=True,
        pattern=r"^/unsetchannel(?:@\w+)?(?:\s|$)",
        func=lambda e: e.is_private,
    )
)
async def _unset_channel(event):
    if not Var.OWNER or event.sender_id != Var.OWNER:
        return await event.reply("This command is only available to the configured owner.")
    parts = event.raw_text.split(maxsplit=2)
    if len(parts) < 2:
        return await event.reply("Use `/unsetchannel forcesub [channel_id]` to remove one or all force-sub channels.")
    role = parts[1].lower().replace("-", "")
    aliases = {"logs": "log", "fsub": "forcesub", "mainchannel": "main"}
    role = aliases.get(role, role)
    if role not in {"main", "log", "backup", "cloud", "forcesub"}:
        return await event.reply("Unknown channel type. Use `/channels` for help.")
    channel_id = None
    if role in {"main", "forcesub"} and len(parts) > 2:
        try:
            channel_id = int(parts[2])
        except ValueError:
            return await event.reply("Channel ID must be numeric.")
    settings = await dB.unset_channel(role, channel_id)
    if role == "main":
        main = ", ".join(str(item) for item in settings["main_channels"]) or "none"
        return await event.reply(f"Main channel removed. Remaining main channels: `{main}`")
    if role == "forcesub":
        count = len(settings["force_sub_channels"])
        return await event.reply(f"Force-sub channel setting removed. `{count}` force-sub channels remain.")
    return await event.reply(f"`{role}` channel removed.")


async def _delete_login_input(message):
    """Best-effort removal of owner-entered phone/code/password messages."""
    try:
        await message.delete()
    except Exception:
        pass


@bot.on(
    events.NewMessage(
        incoming=True,
        pattern=r"^/login(?:@\w+)?$",
        func=lambda e: e.is_private,
    )
)
async def _owner_login(event):
    if not Var.OWNER or event.sender_id != Var.OWNER:
        return await event.reply("This login command is only available to the configured owner.")

    if bot.user_client is not None:
        try:
            if bot.user_client.is_connected():
                return await event.reply(
                    "A Telegram user session is already connected."
                )
        except Exception:
            pass

    try:
        Var.SESSION_ENCRYPTION_KEY = get_session_key(
            Var.SESSION_ENCRYPTION_KEY, create=True
        )
    except SessionStoreError:
        return await event.reply(
            "Session storage is not ready. Ensure the persistent Docker .state volume is mounted and writable, or set SESSION_ENCRYPTION_KEY."
        )

    await _delete_login_input(event.message)
    login_client = TelegramClient(StringSession(), Var.API_ID, Var.API_HASH)
    saved = False
    try:
        await login_client.connect()
        async with bot.conversation(event.chat_id, timeout=180, exclusive=True) as conv:
            await conv.send_message(
                "Security notice: Telegram bot chats are not end-to-end encrypted. "
                "Telegram and this bot process these login details; phone, OTP, and optional 2-step password messages "
                "are deleted from chat on a best-effort basis only. Send `continue` to proceed or `/cancel` to stop."
            )
            consent_message = await conv.get_response()
            consent = (consent_message.raw_text or "").strip().lower()
            await _delete_login_input(consent_message)
            if consent == "/cancel":
                return await conv.send_message("Login cancelled; no session was saved.")
            if consent != "continue":
                return await conv.send_message(
                    "Login cancelled. Run /login again and send `continue` if you want to proceed."
                )

            await conv.send_message(
                "Send your phone number in international format (for example, +1234567890).\n"
                "Your message will be deleted on a best-effort basis. Send /cancel to stop."
            )
            phone_message = await conv.get_response()
            phone = re.sub(r"[\s()\-]", "", phone_message.raw_text or "")
            await _delete_login_input(phone_message)
            if phone.lower() == "/cancel":
                return await conv.send_message("Login cancelled; no session was saved.")
            if not re.fullmatch(r"\+[1-9]\d{6,14}", phone):
                return await conv.send_message(
                    "That phone number format is invalid. Run /login again and use international format."
                )

            try:
                sent_code = await login_client.send_code_request(phone)
            except PhoneNumberInvalidError:
                return await conv.send_message(
                    "Telegram rejected that phone number. Run /login again and check the number."
                )

            authorized = False
            for attempt in range(1, 6):
                await conv.send_message(
                    f"Enter the Telegram login code ({attempt}/5). Do not forward it to anyone."
                )
                code_message = await conv.get_response()
                code = re.sub(r"\s+", "", code_message.raw_text or "")
                await _delete_login_input(code_message)
                if code.lower() == "/cancel":
                    return await conv.send_message("Login cancelled; no session was saved.")

                try:
                    await login_client.sign_in(
                        phone=phone,
                        code=code,
                        phone_code_hash=sent_code.phone_code_hash,
                    )
                    authorized = True
                    break
                except (PhoneCodeEmptyError, PhoneCodeInvalidError):
                    await conv.send_message("Wrong OTP. Please enter the code again.")
                except PhoneCodeExpiredError:
                    sent_code = await login_client.send_code_request(phone)
                    await conv.send_message(
                        "That OTP expired. Telegram sent a new code; enter the new code."
                    )
                except SessionPasswordNeededError:
                    for password_attempt in range(1, 4):
                        await conv.send_message(
                            "Telegram 2-Step Verification is enabled. Send its password to continue; "
                            "it will be deleted on a best-effort basis. Send /cancel to stop."
                        )
                        password_message = await conv.get_response()
                        password = password_message.raw_text or ""
                        await _delete_login_input(password_message)
                        if password.lower() == "/cancel":
                            return await conv.send_message(
                                "Login cancelled; no session was saved."
                            )
                        try:
                            await login_client.sign_in(password=password)
                            authorized = True
                            break
                        except PasswordHashInvalidError:
                            await conv.send_message(
                                f"Wrong 2-Step Verification password ({password_attempt}/3). Try again."
                            )
                    if authorized:
                        break
                    return await conv.send_message(
                        "Too many incorrect 2-Step Verification passwords. Run /login again later."
                    )

            if not authorized:
                return await conv.send_message(
                    "Too many incorrect OTP attempts. Run /login again to request a fresh code."
                )

            session_string = login_client.session.save()
            try:
                await dB.store_user_session(session_string)
            except Exception as error:
                LOGS.error(
                    "Could not persist encrypted Telegram session (%s).",
                    type(error).__name__,
                )
                try:
                    await login_client.log_out()
                except Exception:
                    pass
                return await conv.send_message(
                    "Could not securely save the session to the database. Login was not retained; check MongoDB and SESSION_ENCRYPTION_KEY."
                )

            Var.SESSION = session_string
            bot.user_client = login_client
            saved = True
            return await conv.send_message(
                "Telegram user session connected and stored encrypted."
            )
    except asyncio.TimeoutError:
        await event.reply("Login timed out; no session was saved. Run /login to try again.")
    except Exception as error:
        # Never log Telegram codes, passwords, phone numbers, or session strings.
        LOGS.error("Owner Telegram login failed (%s).", type(error).__name__)
        await event.reply("Telegram login failed. Check the phone/API settings and try again.")
    finally:
        if not saved:
            try:
                await login_client.disconnect()
            except Exception:
                pass


async def _require_owner_callback(event):
    if not Var.OWNER or event.sender_id != Var.OWNER:
        await event.answer(
            "This admin action is only available to the configured owner.", alert=True
        )
        return False
    return True


@bot.on(events.callbackquery.CallbackQuery(data="slog"))
async def _(e):
    if not await _require_owner_callback(e):
        return
    await admin._logs(e)


@bot.on(events.callbackquery.CallbackQuery(data="sret"))
async def _(e):
    if not await _require_owner_callback(e):
        return
    await admin._restart(e, schedule)


@bot.on(events.callbackquery.CallbackQuery(data="entg"))
async def _(e):
    if not await _require_owner_callback(e):
        return
    await admin._encode_t(e)


@bot.on(events.callbackquery.CallbackQuery(data="sstg"))
async def _(e):
    if not await _require_owner_callback(e):
        return
    await admin._ss_t(e)


@bot.on(events.callbackquery.CallbackQuery(data="butg"))
async def _(e):
    if not await _require_owner_callback(e):
        return
    await admin._btn_t(e)


@bot.on(events.callbackquery.CallbackQuery(data="scul"))
async def _(e):
    if not await _require_owner_callback(e):
        return
    await admin._sep_c_t(e)


@bot.on(events.callbackquery.CallbackQuery(data="cast"))
async def _(e):
    if not await _require_owner_callback(e):
        return
    await admin.broadcast_bt(e)


@bot.on(events.callbackquery.CallbackQuery(data="bek"))
async def _(e):
    if not await _require_owner_callback(e):
        return
    await e.edit(
        "** <                ADMIN PANEL                 > **",
        buttons=admin.admin_panel(),
    )


async def _edit_posters(posters, buttons):
    if not isinstance(posters, list):
        posters = [posters]
    for poster in posters:
        if poster:
            await poster.edit(buttons=buttons)


async def anime(data):
    try:
        torr = [data.get("480p"), data.get("720p"), data.get("1080p")]
        anime_info = AnimeInfo(torr[0].title)
        poster = await tools._poster(bot, anime_info)
        if await dB.is_separate_channel_upload():
            chat_info = await tools.get_chat_info(bot, anime_info, dB)
            await _edit_posters(
                poster,
                [
                    [
                        Button.url(
                            f"EPISODE {anime_info.data.get('episode_number', '')}".strip(),
                            url=chat_info["invite_link"],
                        )
                    ]
                ],
            )
            poster = await tools._poster(bot, anime_info, chat_info["chat_id"])
        btn = [[]]
        original_upload = await dB.is_original_upload()
        button_upload = await dB.is_button_upload()
        for i in torr:
            try:
                filename = f"downloads/{i.title}"
                reporter = Reporter(bot, i.title)
                await reporter.alert_new_file_founded()
                await torrent.download_magnet(i.link, "./downloads/", reporter)
                exe = Executors(
                    bot,
                    dB,
                    {
                        "original_upload": original_upload,
                        "button_upload": button_upload,
                    },
                    filename,
                    AnimeInfo(i.title),
                    reporter,
                )
                result, _btn = await exe.execute()
                if result:
                    if _btn:
                        if len(btn[0]) == 2:
                            btn.append([_btn])
                        else:
                            btn[0].append(_btn)
                        await _edit_posters(poster, btn)
                    asyncio.create_task(exe.further_work())
                    continue
                await reporter.report_error(_btn, log=True)
                if reporter.msg:
                    await reporter.msg.delete()
            except BaseException:
                await reporter.report_error(str(format_exc()), log=True)
                if reporter.msg:
                    await reporter.msg.delete()
    except BaseException:
        LOGS.error(str(format_exc()))


try:
    bot.loop.create_task(subsplease.on_new_anime(anime))
    bot.run()
except KeyboardInterrupt:
    subsplease._exit()
