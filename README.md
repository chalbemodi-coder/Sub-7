[![Stars](https://img.shields.io/github/stars/chalbemodi-coder/Sub-7?style=flat-square&color=yellow)](https://github.com/chalbemodi-coder/Sub-7/stargazers)
[![Forks](https://img.shields.io/github/forks/chalbemodi-coder/Sub-7?style=flat-square&color=orange)](https://github.com/chalbemodi-coder/Sub-7/forks)
[![Python](https://img.shields.io/badge/Python-v3.12.3-blue)](https://www.python.org/)
[![CodeFactor](https://www.codefactor.io/repository/github/chalbemodi-coder/sub-7/badge)](https://www.codefactor.io/repository/github/chalbemodi-coder/sub-7)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/chalbemodi-coder/Sub-7/graphs/commit-activity)
[![Contributors](https://img.shields.io/github/contributors/chalbemodi-coder/Sub-7?style=flat-square&color=green)](https://github.com/chalbemodi-coder/Sub-7/graphs/contributors)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://makeapullrequest.com)
[![License](https://img.shields.io/badge/license-GPLv3-blue)](https://github.com/chalbemodi-coder/Sub-7/blob/main/LICENSE)
[![Sparkline](https://stars.medv.io/chalbemodi-coder/Sub-7.svg)](https://github.com/chalbemodi-coder/Sub-7)

## Developer Note

- __This repository is not intended or supported for deployment on KOYEB.__
- If Hosted On Heroku Then Make Sure You Are Using Premium Dynos Or Any Above then basic dynos.
- If You Don't Have High End VPS like **8vcpu or 32GiB RAM** So Don't Deploy This Bot.
- You Can Customize FFMPEG Code If You Know What You Are Doing.
- __Ensure that you have adhered to this developer note before reporting any errors.__

## Changelog Of Latest Update

### v0.1
- Shifted To Mongo Database.
- Changed Hashing Algo To SHA256.
- Added About Command.
- Added SS & MediaInfo On/Off
- Added Separate Anime Channel Upload
- <details><summary>Click Here To See How Separate Anime Channel Upload Look.</summary><img src="https://graph.org/file/a0636332545730a4d3d43.jpg" alt="sepul1"/><img src="https://graph.org/file/3eb0b86609469f385f4b5.jpg" alt="sepul2"/></details>
- Added Button Upload Support (File Store)
- <details><summary>Click Here To See How Button Upload Look.</summary><img src="https://graph.org/file/3e9abc9ec7de6a26fd1a1.jpg" alt="btnul"/></details>
- Added Multi Thread Encoding
- Added Progress Bar of Encoding
- Added Option For Logs In Main Channel
- Added ForceSub
- Added 480p Support
- Added Broadcast
- Major Modification In FFMPEG Code.
- Modified Anime Searcher
- Admin Panel Fixed
- ReWritten Whole Program (Fully OOPs Based)
- Optimized Core
- Added Heroku Support
- Added Custom CRF Support

## Contributing

- Any Sort of Contributions are Welcomed!
- Try To Resove Any Task From ToDo List Or Raise A Issue!

## How to deploy?
<p><a href="https://www.youtube.com/live/hWf7DN3nN_c"> <img src="https://img.shields.io/badge/See%20Video-black?style=for-the-badge&logo=YouTube" width="160""/></a></p>

### Fork Repo Then click on below button of ur fork repo.
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Developer Note

- If Hosted On Heroku Then Encoding Of Per Episode Will Take Around 20mins.
- If You Don't Have High End VPS like 8vcpu or 32GiB RAM So Don't Deploy This Bot.
- You Can Customize FFMPEG Code If You Know What You Are Doing.

## Environmental Variable

### REQUIRED VARIABLES

- `BOT_TOKEN` - Get This From @Botfather In Telegram.

- `API_ID` and `API_HASH` - Get these from [my.telegram.org](https://my.telegram.org); required for user-session login.

- `MONGO_SRV` - Get This From mongodb.com .

- `OWNER` - Numeric Telegram user ID allowed to manage channels and use `/login`.

- `SESSION_ENCRYPTION_KEY` - Secret Fernet key used to encrypt the saved user session in MongoDB.

### OPTIONAL VARIABLES

- `SESSION` - Legacy plaintext Telethon session; leave blank to use encrypted `/login` storage.

- `THUMBNAIL` - JPG/PNG Link of Thumbnail FIle.

- `FFMPEG` - You Can Set Custom Path Of ffmpeg if u want, default is `ffmpeg`.

- `LOG_ON_MAIN` - `True/False` It Will Send LOGS in `MAIN_CHANNEL` rather than `LOG_CHANNEL`, default is `False`

- `SEND_SCHEDULE` - `True/False` Send Schedule of Upcoming Anime of that day at 00:30 **IST**, default is `False`.

- `RESTART_EVERDAY` - `True/False` It Will Restart The Bot Everyday At 00:30 **IST**, default is `True`.

- `DELETE_FILES_FROM_PMS` - `True/False` It Will delete the file from pm of user after 10mins if button upload is enabled. default is `True`.

- `CRF` - Less CRF == High Quality, More Size , More CRF == Low Quality, Less Size, CRF Range = 20-51.

### Owner-only Telegram User Login

- Set `OWNER` to your own numeric Telegram user ID. The sample value `0` disables owner-only login until you replace it.
- Generate a Fernet key with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and store it as the secret environment variable `SESSION_ENCRYPTION_KEY`. Never commit or share this key.
- Leave `SESSION` empty. Start the bot, then send `/login` to it from the owner's private chat. Only the exact `OWNER` ID is allowed; up to five incorrect OTP attempts are accepted before the flow stops and the owner must restart it.
- `auto_env_gen.py` may still use a temporary local login once to create the BotFather bot/channels, but it no longer prints or stores that session. Normal runtime user-session login is through `/login`.
- The session is encrypted before it is stored in MongoDB, so it survives normal redeploys. Preserve the same encryption key and protect both the key and database backups; without that key the stored session cannot be decrypted.
- Login codes (and, if requested by Telegram, the 2-Step Verification password) are entered in the bot's private chat and deleted on a best-effort basis. **Bot chats are not end-to-end encrypted**, so Telegram may process or retain messages; do not use this flow if that exposure is unacceptable. Secrets are not written to application logs.

### Owner-only Channel Setup

- Channel IDs are stored in MongoDB; you do not need `MAIN_CHANNEL`, `LOG_CHANNEL`, `BACKUP_CHANNEL`, `CLOUD_CHANNEL`, or force-sub channel environment variables.
- After startup, send `/channels` to see current settings, then `/setchannel main <channel_id>`, `/setchannel log <channel_id>`, `/setchannel backup <channel_id>`, or `/setchannel cloud <channel_id>` in the owner's private chat. The bot must be an administrator with the required posting rights in each channel.
- Add at most two main channels; anime posts, posters, and daily schedules are mirrored to both. Other roles take one channel each. Remove a main channel with `/unsetchannel main <channel_id>` (or clear both with `/unsetchannel main`); remove another role with `/unsetchannel log|backup|cloud`.
- Add up to six force-sub channels, choosing a mode separately for each one: `/setchannel forcesub <channel_id> temp` gives each user a **unique, single-use invite link that expires in 10 minutes**; refresh reuses that user's still-valid link. `/setchannel forcesub <channel_id> fixed <invite_link>` uses the invite link you provide. Repeating `/setchannel` for the same ID changes that channel's mode.
- Temporary links require the bot to be an administrator with permission to invite users in each selected channel. Remove one with `/unsetchannel forcesub <channel_id>` or remove all force-sub channels with `/unsetchannel forcesub`.
- Switching a channel from fixed to temporary mode does not revoke the old fixed invite link; revoke that old link in Telegram if it should no longer work.
- Public anime posts are not automatically deleted. A single temporary progress message is updated in place and removed when processing finishes; error logs remain.

## Deployment In VPS

- `git clone https://github.com/chalbemodi-coder/Sub-7.git`

- `nano .env` configure env as per [this](https://github.com/chalbemodi-coder/Sub-7/blob/main/.sample.env) or  using [this](https://github.com/chalbemodi-coder/Sub-7/blob/main/auto_env_gen.py).

- `sudo docker build . -t ongoing` (make sure to install docker first using `sudo apt install docker.io`)

- `sudo docker run ongoing`

## Commands

[![Comand](https://files.catbox.moe/utcf3f.jpg)](https://github.com/chalbemodi-coder/Sub-7/)

**Uploading of Ongoing Animes Is Automatic**

<!-- ## About

- This Bot Is Currently Running In [This Channel](https://t.me/+q_OBZiXjkBFkYzk0) . -->

## Donate

- [Contact @ahjin_anime on Telegram](https://t.me/ahjin_anime) for support or donations.
