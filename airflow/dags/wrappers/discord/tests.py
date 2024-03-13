import argparse
from io import BytesIO

from discord_client import DiscordClient

parser = argparse.ArgumentParser()
parser.add_argument('test', nargs=1)
parser.add_argument("--token", required=False)
parser.add_argument("--channel", required=False)


def test_send_message(token: str, channel: str):
    discord = DiscordClient(token=token)
    discord.create_message(channel, content='Test message 👌')

def test_send_message_with_attach(token: str, channel: str):
    discord = DiscordClient(token=token)
    discord.create_message(channel, 'Test message with attachments 🔥', files=["dags/wrappers/discord/the-big-short-margot-robbie.gif"])


def main():
    args = parser.parse_args()
    if args.test[0] == 'send_message':
        test_send_message(
             args.token
            ,args.channel
        )
    elif args.test[0] == 'send_message_with_attach':
        test_send_message_with_attach(
             args.token
            ,args.channel
        )


if __name__ == '__main__':
    main()
