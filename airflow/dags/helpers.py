
import io
import os
import logging
import tempfile
import json
import re
from datetime import date, datetime

from airflow.models import Variable

from wrappers.discord.discord_client import DiscordClient


DISCORD_BOT_TOKEN = Variable.get('discord_airflow_bot_token')
DISCORD_ETL_ALERT_CHANNEL_ID = Variable.get('discord_etl_alerts_channel_id')


def discord_alert_file(context):
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # open your files here
        error_file_name = temp_dir + '/error.json'
        error_file = open(error_file_name, 'w')
        error_file.write(str(context['exception']))
        error_file.close()
        
        discord_alert_message_txt = """Airflow Exception Alert\n\nDAG: {}\nTask: {}"""
        message_text = discord_alert_message_txt.format(
            context['task_instance'].dag_id,
            context['task_instance'].task_id,
        )

        discord = DiscordClient(
            token=DISCORD_BOT_TOKEN
        )
        discord.create_message(
            channel_id=DISCORD_ETL_ALERT_CHANNEL_ID, 
            content=message_text,
            files=[error_file_name]
        )

def discord_alert(context):
    discord_alert_message_txt = """Airflow Exception Alert\n\nDAG: {}\nTask: {}\nException: {}"""
    error_message = str(context['exception'])
    message_text = discord_alert_message_txt.format(
        context['task_instance'].dag_id,
        context['task_instance'].task_id,
        error_message[:1900] + ('..' if len(error_message) > 1900 else '') 
    )

    discord = DiscordClient(
        token=DISCORD_BOT_TOKEN
    )
    discord.create_message(
        channel_id=DISCORD_ETL_ALERT_CHANNEL_ID, 
        content=message_text,
    )


def hour_rounder(t):
    # Rounds to nearest hour
    return t.replace(second=0, microsecond=0, minute=0, hour=t.hour)


class BytesIOWrapper(io.BufferedReader):
    """Wrap a buffered bytes stream over TextIOBase string stream."""

    def __init__(self, text_io_buffer, encoding=None, errors=None, **kwargs):
        super(BytesIOWrapper, self).__init__(text_io_buffer, **kwargs)
        self.encoding = encoding or text_io_buffer.encoding or 'utf-8'
        self.errors = errors or text_io_buffer.errors or 'strict'

    def _encoding_call(self, method_name, *args, **kwargs):
        raw_method = getattr(self.raw, method_name)
        val = raw_method(*args, **kwargs)
        return val.encode(self.encoding, errors=self.errors)

    def read(self, size=-1):
        return self._encoding_call('read', size)

    def read1(self, size=-1):
        return self._encoding_call('read1', size)

    def peek(self, size=-1):
        return self._encoding_call('peek', size)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError (f"Type {type(obj)} not serializable")

def datetime_parser(dct):
    for k, v in dct.items():
        if isinstance(v, str) and re.search("^(19|20)\d\d-(0[1-9]|1[012])-([012]\d|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d).*$", v):
            try:
                dct[k] = datetime.fromisoformat(v)
            except:
                pass
    return dct
