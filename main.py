import logging
import os
import socket

from beepy import beep
from dotenv import load_dotenv
from emoji import demojize
from googletrans import Translator


def configure_logger():
    channel_name = channel.replace("#", "")
    try:
        os.mkdir("logs/")
    except:
        pass

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s — %(message)s',
                        datefmt='[%Y-%m-%d %H:%M:%S]',
                        handlers=[logging.FileHandler(f'logs/{channel_name}-chat.log', encoding='utf-8')])


def main():
    translator = Translator()
    with socket.socket() as sock:
        sock.connect((server, port))

        sock.send(f"PASS {token}\n".encode('utf-8'))
        sock.send(f"NICK {nickname}\n".encode('utf-8'))
        sock.send(f"JOIN {channel}\n".encode('utf-8'))

        # ignore the first 2 messages from socket
        sock.recv(2048).decode('utf-8')
        sock.recv(2048).decode('utf-8')
        beep()
        while True:
            resp = sock.recv(2048).decode('utf-8')
            if channel in resp:
                clear_message = demojize(resp.split(f"{channel} :")[-1].strip())
                sender = resp.split("!")[0].replace(":", "")
                if sender.lower() not in ignored_users and clear_message:
                    detected = translator.detect(text=clear_message).lang
                    if detected != "es":
                        beep(sound="error")
                        translated = translator.translate(clear_message, dest="es").text
                        logging.info(f"{sender}({detected}): {clear_message}")
                        logging.info(f"{sender}(es): {translated}")


# run this example
if __name__ == "__main__":
    load_dotenv()

    ignored_users_str = os.environ.get("IGNORED_USERS", "streamelements").lower()
    ignored_users = ignored_users_str.split(",")

    server = os.environ.get("server", "irc.chat.twitch.tv")
    port = int(os.environ.get("port", "6667"))
    token = os.environ.get("token", False)  # get your token from https://twitchapps.com/tmi/
    nickname = os.environ.get("nickname", False)  # your twitch username
    channel = f'#{os.environ.get("channel", nickname)}'  # channel to be spectated

    configure_logger()
    try:
        main()
    except KeyboardInterrupt:
        beep(3)
