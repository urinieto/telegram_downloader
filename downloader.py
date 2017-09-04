#!/usr/bin/env python
import datetime
from telethon import TelegramClient
from telethon.tl.types.input_peer_chat import InputPeerChat
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


def parse_message(msg, name):
    """Parses a single message from the given sender's name."""
    if getattr(msg, 'media', None):
        content = '<{}> {}'.format(  # The media may or may not have a caption
            msg.media.__class__.__name__,
            getattr(msg.media, 'caption', ''))
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


def get_parsed_history(messages, senders):
    """Gets the parsed history given a date."""

    parsed_msgs = ""
    for msg, sender in zip(reversed(messages), reversed(senders)):
        name = get_name(sender)
        parsed_msgs += parse_message(msg, name)
    return parsed_msgs


# dialogs, entities = client.get_dialogs(10)
# print('\n'.join('{}. {}'.format(i, str(e)) for i, e in enumerate(entities)))

client = create_session(SESSION_ID, PHONE_NUM, API_ID, API_HASH)
chat = InputPeerChat(GROUP_ID)

date = datetime.datetime.today()
# date = date.replace(day=22)
# date = date.replace(year=2010)
print(date)

parsed_msgs = ""
offset_id = -1
limit = 100
total_msgs = 0
for _ in range(10):
    _, messages, senders = client.get_message_history(
        chat, offset_date=date, limit=limit, offset_id=offset_id)
    offset_id = get_first_msg_id(messages)
    parsed_msgs = get_parsed_history(messages, senders) + parsed_msgs
    total_msgs += len(messages)

print(parsed_msgs)
