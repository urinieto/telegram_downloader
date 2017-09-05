#!/usr/bin/env python
import datetime
import os
import shutil
import sys
from tqdm import tqdm
from telethon import TelegramClient
from config import API_ID, API_HASH, PHONE_NUM, SESSION_ID, GROUP_ID


def authorize_client(client, phone_num):
    """Authorizes the client if not authorized yet."""
    if not client.is_user_authorized():
        client.send_code_request(phone_num)
        client.sign_in(phone_num, input('Enter code: '))


def create_session(session_id, phone_num, api_id, api_hash):
    """Creates a Telegram session."""
    client = TelegramClient(session_id, api_id, api_hash)
    client.connect()
    authorize_client(client, phone_num)
    return client


def get_name(sender):
    """Gets the first and last names from the given sender, if exist."""
    name = '???'
    if sender:
        name = getattr(sender, 'first_name', None)
        if not name:
            name = getattr(sender, 'title')
            if not name:
                name = '???'
        else:
            name += ' ' + getattr(sender, 'last_name', None)
    return name


def get_new_path(msg, name, new_dir, prefix, file_extension):
    new_path = "{}_{}-{}-{} {}:{min:02d}:{sec:02d}_{}".format(
        prefix, msg.date.year, msg.date.month, msg.date.day,
        msg.date.hour, name, min=msg.date.minute, sec=msg.date.second)
    return os.path.join(new_dir, new_path) + file_extension


def download_media(msg, name, client, media_dir="media", audio_dir="audio",
                   video_dir="video", img_dir="image"):
    """Downloads media, if any."""
    os.makedirs(media_dir, exist_ok=True)
    audio_dir = os.path.join(media_dir, audio_dir)
    os.makedirs(audio_dir, exist_ok=True)
    img_dir = os.path.join(media_dir, img_dir)
    os.makedirs(img_dir, exist_ok=True)
    video_dir = os.path.join(media_dir, video_dir)
    os.makedirs(video_dir, exist_ok=True)

    tmp_path = client.download_media(msg.media, file=media_dir)

    # Move files correctly
    filename, file_extension = os.path.splitext(tmp_path)
    new_path = None
    if file_extension == ".oga":
        new_path = get_new_path(msg, name, audio_dir, "audio", file_extension)
    elif file_extension == ".jpg":
        new_path = get_new_path(msg, name, img_dir, "img", file_extension)
    elif file_extension == ".mp4":
        new_path = get_new_path(msg, name, video_dir, "video", file_extension)

    new_path = tmp_path if new_path is None else new_path
    shutil.move(tmp_path, new_path)

    return new_path


def parse_message(msg, name, client):
    """Parses a single message from the given sender's name."""
    if getattr(msg, 'media', None):
        content = '<{}> {}'.format(  # The media may or may not have a caption
            msg.media.__class__.__name__,
            getattr(msg.media, 'caption', ''))
        try:
            download_media(msg, name, client)
        except TypeError:
            print("Couldn't download {}".format(msg))
    elif hasattr(msg, 'message'):
        content = msg.message
    elif hasattr(msg, 'action'):
        content = str(msg.action)
    else:
        # Unknown message, simply print its class name
        content = msg.__class__.__name__

    return '[{}/{}/{} {}:{num:02d}] (ID={}) {}: {}\n'.format(
        msg.date.day, msg.date.month, msg.date.year, msg.date.hour,
        msg.id, name, content, num=msg.date.minute)


def get_first_msg_id(messages):
    """Gets the id of the first message."""
    return messages[-1].id if len(messages) > 0 else None


def get_parsed_history(messages, senders, client):
    """Gets the parsed history given a date."""

    parsed_msgs = ""
    for msg, sender in zip(reversed(messages), reversed(senders)):
        name = get_name(sender)
        parsed_msgs += parse_message(msg, name, client)
    return parsed_msgs


client = create_session(SESSION_ID, PHONE_NUM, API_ID, API_HASH)

dialogs, entities = client.get_dialogs()
chat = None
for i, e in enumerate(entities):
    if e.id == GROUP_ID:
        chat = e
        break

if chat is None:
    print("Group {} not found!".format(GROUP_ID))
    sys.exit()

# Download Chat Pic
output = client.download_profile_photo(chat, 'media/chat_picture')

date = datetime.datetime.today()
# date = date.replace(day=22)
# date = date.replace(year=2010)
print(date)

parsed_msgs = ""
offset_id = -1
limit = 100
total_msgs = 0
n_batches = 1
for _ in tqdm(range(n_batches)):
    _, messages, senders = client.get_message_history(
        chat, offset_date=date, limit=limit, offset_id=offset_id)
    offset_id = get_first_msg_id(messages)
    parsed_msgs = get_parsed_history(messages, senders, client) + parsed_msgs
    total_msgs += len(messages)

print(parsed_msgs)
