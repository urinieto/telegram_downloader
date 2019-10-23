#!/usr/bin/env python
import asyncio
import datetime
import emoji
import os
import sys

from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument
from telethon.tl.types import MessageMediaPhoto
from telethon.tl.types import MessageMediaWebPage
from telethon.tl.types import MessageMediaGeo
from telethon.tl.types import MessageMediaUnsupported
from telethon.tl.types import MessageMediaContact
from telethon.tl.types import WebPageEmpty
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

    out_msg = ""

    if isinstance(msg.media, MessageMediaWebPage):
        content = msg.message
        if not isinstance(msg.media.webpage, WebPageEmpty):
            content = "\\url{{{}}} ".format(msg.media.webpage.url)
        out_msg = get_message_string(msg, name, content)
    elif isinstance(msg.media, MessageMediaGeo):
        content = "Geolocation({}, {})".format(
            msg.media.geo.long,
            msg.media.geo.lat)
        out_msg = get_message_string(msg, name, content)
    elif isinstance(msg.media, MessageMediaPhoto):
        path = format_media_path(msg, name, img_dir, "jpg")
        wait_fun(client.download_media, message=msg,
                 file="{}.jpg".format(path))
        horizontal = msg.media.photo.sizes[0].w > msg.media.photo.sizes[0].h
        latex_size = 0.5 if horizontal else 0.35
        out_msg = "\myfigure{%f}{%s}{%s}" % (
            latex_size, path, get_message_string(msg, name, msg.message))
    elif isinstance(msg.media, MessageMediaDocument):
        if msg.media.document.mime_type == "video/mp4" or \
                msg.media.document.mime_type == "video/3gpp":
            ext = msg.media.document.mime_type.split("/")[1]
            path = format_media_path(msg, name, video_dir, ext)
            wait_fun(client.download_media, message=msg,
                     file="{}".format(path))
            content = "(video a {})".format(path)
            try:
                # Try to download a thumbnail of the video
                path_thumb = format_media_path(msg, name, video_dir, "jpg")
                wait_fun(client.download_media, message=msg,
                        thumb=-1, file=path_thumb)
                out_msg = "\myfigure{0.3}{%s}{%s}" % (
                    path_thumb, get_message_string(msg, name,
                                                content + msg.message))
            except TypeError:
                out_msg = get_message_string(msg, name, msg.message)
        elif msg.media.document.mime_type == "audio/ogg":
            path = format_media_path(msg, name, audio_dir, "ogg")
            wait_fun(client.download_media, message=msg,
                     file="{}".format(path))
            content = "(\`audio a {})".format(path)
            out_msg = get_message_string(msg, name,
                                         content + msg.message)
        elif msg.media.document.mime_type == "image/jpeg":
            # Not sure why some images are stored as such instead of MessageMediaPhoto
            path = format_media_path(msg, name, img_dir, "jpg")
            wait_fun(client.download_media, message=msg,
                    file="{}.jpg".format(path))
            horizontal = msg.media.document.thumbs[0].w > msg.media.document.thumbs[0].h
            latex_size = 0.5 if horizontal else 0.35
            out_msg = "\myfigure{%f}{%s}{%s}" % (
                latex_size, path, get_message_string(msg, name, msg.message))
        else:
            import ipdb; ipdb.set_trace()
            print("CACA DOCUMENT")
            print(msg)
            print(msg.media)
            sys.exit()
    elif isinstance(msg.media, MessageMediaContact):
        out_msg = get_message_string(msg, name, "(Contacte: {} {})".format(
            msg.media.first_name, msg.media.phone_number))
    elif isinstance(msg.media, MessageMediaUnsupported):
        out_msg = get_message_string(msg, name, "(Message not parsed) " + msg.message)
    else:
        import ipdb; ipdb.set_trace()
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
    return '[{}:{:02d}h] \\textbf{{{}}}{}'.format(
        msg.date.hour, msg.date.minute, name,
        content.replace("_", "\_"))


def parse_emojis(in_str):
    """Adds the DejaSans prefix for LaTeX parsing."""
    out_str = ""
    for c in in_str:
        if c in emoji.UNICODE_EMOJI:
            out_str += "{\DejaSans " + c + "}"
        else:
            out_str += c
    return out_str


def add_new_day(date):
    return "\\textbf{{{}/{}/{}}}\n\n".format(
        date.day, date.month, date.year)


def add_new_month(date):
    return "\mychapter{%s del %d}\n\n" % \
        (MONTHS_DICT[date.month], date.year)


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
    """Returns name from the given message."""
    # Remove middle name if any
    try:
        first_name = ps_dict[msg.from_id].first_name.split(" ")[0]
    except KeyError:
        import ipdb; ipdb.set_trace()
        pass

    # Get only initial of last name
    last_initial = ps_dict[msg.from_id].last_name[0]
    return "{} {}".format(first_name, last_initial)


def get_participants(client, chat):
    """Gets a dictionary of participants in the given chat."""
    participants = {}
    for p in client.iter_participants(chat):
        participants[p.id] = p
        if p.first_name == "Bernat":
            # Bernat switched phone numbers, so let's hack the old one in
            participants[2390325] = p
    return participants


def process():
    """Main process."""
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
    date = date.replace(day=26)
    date = date.replace(month=8)
    date = date.replace(year=2014)

    prev_month = None
    prev_day = None

    # Parse each message, from oldest to newest
    for message in client.iter_messages(chat, offset_date=date, reverse=True):
        # Empty string
        out_str = ""

        # Start a chapter for every new month
        if prev_month is None or prev_month != date.month:
            out_str += add_new_month(message.date)
            prev_month = date.month

        # Start a subsection for every new day
        if prev_day is None or prev_day != date.day:
            out_str += add_new_day(message.date)
            prev_day = date.day

        name = get_name(message, ps)
        if message.media:
            out_str += download_media(message, name, client)
        else:
            out_str += get_message_string(message, name, message.message)

        # Write to latex
        print(out_str)
        with open("latex/content.tex", "a") as f:
            f.write(out_str + '\n\n')
    print("Done")


if __name__ == "__main__":
    process()
