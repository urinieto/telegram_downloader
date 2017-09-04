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


client = create_session(SESSION_ID, PHONE_NUM, API_ID, API_HASH)
chat = InputPeerChat(GROUP_ID)

date = datetime.datetime.today()
date = date.replace(day=21)
date = date.replace(year=2016)

total_count, messages, senders = client.get_message_history(
    chat, offset_date=date, limit=100, max_id=143408)
print(total_count)

# dialogs, entities = client.get_dialogs(10)
# print('\n'.join('{}. {}'.format(i, str(e)) for i, e in enumerate(entities)))

for msg, sender in zip(reversed(messages), reversed(senders)):
    # Get the name of the sender if any
    if sender:
        name = getattr(sender, 'first_name', None)
        if not name:
            name = getattr(sender, 'title')
            if not name:
                name = '???'
        else:
            name += ' ' + getattr(sender, 'last_name', None)
    else:
        name = '???'

    # Format the message content
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

    print('[{}/{}/{} {}:{}] (ID={}) {}: {}'.format(
        msg.date.day, msg.date.month, msg.date.year, msg.date.hour,
        msg.date.minute, msg.id, name, content))

print("TOTAL:", len(messages))
