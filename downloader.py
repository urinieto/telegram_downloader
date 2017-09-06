#!/usr/bin/env python
import datetime
import emoji
import os
import shutil
import sys
from tqdm import tqdm
from telethon import TelegramClient
from telethon.tl.types.message_media_photo import MessageMediaPhoto
from config import API_ID, API_HASH, PHONE_NUM, SESSION_ID, CHAT_ID

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


def format_media_path(msg, name, new_dir, prefix, file_extension):
    """Formats the file containing the media."""
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
        new_path = format_media_path(msg, name, audio_dir, "audio", file_extension)
    elif file_extension == ".jpg":
        new_path = format_media_path(msg, name, img_dir, "img", file_extension)
    elif file_extension == ".mp4":
        new_path = format_media_path(msg, name, video_dir, "video", file_extension)

    new_path = tmp_path if new_path is None else new_path
    shutil.move(tmp_path, new_path)

    return new_path


def get_message_string(msg, name, content):
    """Gets the actual string, customly formatted."""
    if content is None:
        content = ""
    else:
        content = ": " + parse_emojis(content)
    return '[{}/{}/{} {}:{num:02d}] \\textbf{{{}}}{}'.format(
        msg.date.day, msg.date.month, msg.date.year, msg.date.hour, name,
        content, num=msg.date.minute)


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
            parsed_msgs += add_new_chapter(prev_date, msg.date)
            prev_date = msg.date
        name = get_name(sender)
        parsed_msgs += parse_message(msg, name, client)

    if prev_batch_date is not None:
        parsed_msgs += add_new_chapter(prev_batch_date, msg.date)
    return parsed_msgs


def get_chat(client, chat_id):
    """Gets the chat with the given id and the open client."""
    dialogs, entities = client.get_dialogs()
    chat = None
    for i, e in enumerate(entities):
        if e.id == CHAT_ID:
            chat = e
            break
    return chat


if __name__ == "__main__":
    client = create_session(SESSION_ID, PHONE_NUM, API_ID, API_HASH)
    chat = get_chat(client, CHAT_ID)

    if chat is None:
        print("Group {} not found!".format(CHAT_ID))
        sys.exit()

    # Download Chat Pic
    _ = client.download_profile_photo(chat, 'media/chat_picture')

    date = datetime.datetime.today()
    # date = date.replace(day=22)
    # date = date.replace(year=2010)

    parsed_msgs = ""
    offset_id = -1
    limit = 100
    total_msgs = 0
    n_batches = 10
    prev_batch_date = None
    for _ in tqdm(range(n_batches)):
        _, messages, senders = client.get_message_history(
            chat, offset_date=date, limit=limit, offset_id=offset_id)
        offset_id = get_first_msg_id(messages)
        curr_msgs = get_parsed_history(messages, senders, client,
                                       prev_batch_date)
        parsed_msgs = curr_msgs + parsed_msgs
        total_msgs += len(messages)
        prev_batch_date = get_first_date(messages)

    # Add first chapter
    parsed_msgs = add_new_chapter(prev_batch_date, None) + parsed_msgs
    print(parsed_msgs)
    with open("latex/content.tex", "w") as f:
        f.write(parsed_msgs)
