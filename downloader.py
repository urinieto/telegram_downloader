#!/usr/bin/env python
import asyncio
import datetime
import emoji
import os
import shutil
import sys
import time

from tqdm import tqdm
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument
from telethon.tl.types import MessageMediaPhoto
from telethon.tl.types import MessageMediaWebPage
from config import API_ID, API_HASH, PHONE_NUM, SESSION_ID, CHAT_ID

MEDIA_DIR = "media"
AUDIO_DIR = "audio"
VIDEO_DIR = "video"
IMG_DIR = "image"
WEB_DIR = "web"
MONTHS_DICT = {
    1: "Gener",
    2: "Febrer",
    3: "Març",
    4: "Abril",
    5: "Maig",
    6: "Juny",
    7: "Juliol",
    8: "Agost",
    9: "Setembre",
    10: "Octubre",
    11: "Novembre",
    12: "Desembre"
}


class Message(object):
    def __init__(self, message):
        self.message = message


def create_session(session_id, phone_num, api_id, api_hash):
    """Creates a Telegram session."""
    client = TelegramClient(session_id, api_id, api_hash)
    client.start()
    return client


def format_media_path(msg, name, new_dir, extension):
    """Formats the file containing the media."""
    new_path = "{}-{}-{} {}:{:02d}:{:02d}_{}.{}".format(
        msg.date.year, msg.date.month, msg.date.day,
        msg.date.hour, msg.date.minute, msg.date.second, name,
        extension)
    return os.path.join(new_dir, new_path)


def download_media(msg, name, client, media_dir=MEDIA_DIR, audio_dir=AUDIO_DIR,
                   video_dir=VIDEO_DIR, img_dir=IMG_DIR, web_dir=WEB_DIR):
    """Downloads media, if any."""
    os.makedirs(media_dir, exist_ok=True)
    audio_dir = os.path.join(media_dir, audio_dir)
    os.makedirs(audio_dir, exist_ok=True)
    img_dir = os.path.join(media_dir, img_dir)
    os.makedirs(img_dir, exist_ok=True)
    video_dir = os.path.join(media_dir, video_dir)
    os.makedirs(video_dir, exist_ok=True)
    web_dir = os.path.join(media_dir, web_dir)
    os.makedirs(web_dir, exist_ok=True)

    out_msg = ""

    if isinstance(msg.media, MessageMediaWebPage):
        import ipdb; ipdb.set_trace()
        path = format_media_path(msg, name, web_dir, "html")
        wait_fun(client.download_media, message=msg,
                 file="{}".format(path))
        out_msg = "Web: {}".format(msg)
    elif isinstance(msg.media, MessageMediaPhoto):
        import ipdb; ipdb.set_trace()
        path = format_media_path(msg, name, img_dir, "jpg")
        wait_fun(client.download_media, message=msg,
                 file="{}.jpg".format(path))
        out_msg = "\myfigure{0.6}{%s}{%s}" % (
            path, get_message_string(msg, name, None))
    elif isinstance(msg.media, MessageMediaDocument):
        return out_msg
        if msg.media.document.mime_type == "video/mp4":
            path = format_media_path(msg, name, video_dir, "mp4")
            wait_fun(client.download_media, message=msg,
                     file="{}".format(path))
            out_msg = "Video: {}".format(path)
        else:
            print("CACA DOCUMENT")
            print(msg)
            print(msg.media)
            sys.exit()

    else:
        print(msg)
        print(msg.media)
        sys.exit()

    return out_msg


def get_message_string(msg, name, content):
    """Gets the actual string, customly formatted."""
    if content is None:
        content = ""
    else:
        content = ": " + parse_emojis(content)
    return '[{}/{}/{} {}:{num:02d}] \\textbf{{{}}}{}'.format(
        msg.date.day, msg.date.month, msg.date.year, msg.date.hour, name,
        content.replace("_", "\_"), num=msg.date.minute)


def parse_emojis(in_str):
    """Adds the DejaSans prefix for LaTeX parsing."""
    out_str = ""
    for c in in_str:
        if c in emoji.UNICODE_EMOJI:
            out_str += "{\DejaSans " + c + "}"
        else:
            out_str += c
    return out_str


def parse_message(msg, name, client):
    """Parses a single message from the given sender's name."""
    if getattr(msg, 'media', None):
        media_path = None
        caption = getattr(msg.media, 'caption', '')
        try:
            media_path = download_media(msg, name, client)
        except TypeError:
            print("Couldn't download {}".format(msg))
        if isinstance(msg.media, MessageMediaPhoto) and media_path is not None:
            content = "\myfigure{0.6}{%s}" % ("image/" + os.path.basename(media_path))
            return content + "{" + get_message_string(msg, name, caption) + "}\n\n"
        else:
            content = '<{}> {}'.format(msg.media.__class__.__name__, media_path)
    elif hasattr(msg, 'message'):
        content = msg.message
    elif hasattr(msg, 'action'):
        content = str(msg.action)
    else:
        # Unknown message, simply print its class name
        content = msg.__class__.__name__

    return get_message_string(msg, name, content) + "\n\n"


def get_first_msg_id(messages):
    """Gets the id of the first message."""
    return messages[-1].id if len(messages) > 0 else None


def get_first_date(messages):
    """Gets the date of the first message."""
    return messages[-1].date if len(messages) > 0 else None


def get_last_date(messages):
    """Gets the date of the last message."""
    return messages[0].date if len(messages) > 0 else None


def add_new_chapter(prev, curr):
    """Adds a new LaTeX chapter if needed."""
    return "\mychapter{%s del %d}\n\n" % \
        (MONTHS_DICT[prev.month], prev.year) \
        if curr is None or prev.month != curr.month else ""


def get_parsed_history(messages, senders, client, prev_batch_date):
    """Gets the parsed history given a date."""
    parsed_msgs = ""
    prev_date = get_first_date(messages)
    for i, (msg, sender) in enumerate(zip(reversed(messages),
                                          reversed(senders))):
        if i != 0:
            parsed_msgs += add_new_chapter(msg.date, prev_date)
            prev_date = msg.date
        name = get_name(sender)
        parsed_msgs += parse_message(msg, name, client)

    if prev_batch_date is not None:
        parsed_msgs += add_new_chapter(prev_batch_date, msg.date)
    return parsed_msgs


def get_chat(client, chat_id):
    """Gets the chat with the given id and the open client."""
    chat = None
    for d in client.iter_dialogs():
        if d.entity.id == CHAT_ID:
            chat = d.entity
            break
    return chat


def wait_fun(fun, **args):
    """Run function asynchronously and waits for it to finish."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fun(**args))


def get_name(msg, ps_dict):
    """Returns first + last name from the given message."""
    return "{} {}".format(ps_dict[msg.from_id].first_name,
                          ps_dict[msg.from_id].last_name)


def get_participants(client, chat):
    """Gets a dictionary of participants in the given chat."""
    participants = {}
    for p in client.iter_participants(chat):
        participants[p.id] = p
    return participants


if __name__ == "__main__":
    # Open client and chat
    client = create_session(SESSION_ID, PHONE_NUM, API_ID, API_HASH)
    chat = get_chat(client, CHAT_ID)

    if chat is None:
        print("Group {} not found!".format(CHAT_ID))
        sys.exit()

    # Get all participants
    ps = get_participants(client, chat)

    # Download Chat Pic
    wait_fun(client.download_profile_photo, entity=chat, file='media/chat_pic.jpg')

    date = datetime.datetime.today()
    date = date.replace(day=2)
    # date = date.replace(year=2010)

    # Parse each message, from oldest to newest
    for message in client.iter_messages(chat, offset_date=date, reverse=True):
        name = get_name(message, ps)
        if message.media:
            content = download_media(message, name, client)
            print(get_message_string(message, name, content))
        else:
            print(get_message_string(message, name, message.message))
    sys.exit()
    parsed_msgs = ""
    offset_id = -1
    limit = 100
    total_msgs = 0
    n_batches = 1000000
    prev_batch_date = None
    for _ in tqdm(range(n_batches)):
        import ipdb; ipdb.set_trace()
        _, messages, senders = client.get_message_history(
            chat, offset_date=date, limit=limit, offset_id=offset_id)
        if len(messages) == 0:
            break
        offset_id = get_first_msg_id(messages)
        curr_msgs = get_parsed_history(messages, senders, client,
                                       prev_batch_date)
        parsed_msgs = curr_msgs + parsed_msgs
        total_msgs += len(messages)
        prev_batch_date = get_first_date(messages)
        print(prev_batch_date)
        with open("latex/content.tex", "w") as f:
            f.write(parsed_msgs)

    # Add first chapter
    parsed_msgs = add_new_chapter(prev_batch_date, None) + parsed_msgs
    print(parsed_msgs)
    with open("latex/content.tex", "w") as f:
        f.write(parsed_msgs)
