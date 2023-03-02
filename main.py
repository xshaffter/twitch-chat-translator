import logging
import os
import socket

from beepy import beep
from dotenv import load_dotenv
from emoji import demojize
from googletrans import Translator
import platform


def create_toast(title, text):
    _platform = platform.platform().lower().split("-")[0]
    if _platform == "macos":
        os.system("""
                  osascript -e 'display notification "{}" with title "{}"'
                  """.format(text, title))
    elif _platform == "windows":
        from windows_toasts import WindowsToaster, ToastText1
        wintoaster = WindowsToaster(title)
        newToast = ToastText1()
        newToast.SetBody(text)
        wintoaster.show_toast(newToast)
    elif _platform == "linux":
        os.system(f'notify-send "{title}" "{text}"')
    else:
        print(f"{_platform=}")


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
        create_toast("Translator", "translator activated")
        while True:
            resp = sock.recv(2048).decode('utf-8')
            if channel in resp:
                clear_message = demojize(resp.split(f"{channel} :")[-1].strip())
                sender = resp.split("!")[0].replace(":", "")
                if sender.lower() not in ignored_users and clear_message:
                    detected = translator.detect(text=clear_message).lang
                    if detected != "es":
                        translated = translator.translate(clear_message, dest="es").text

                        beep(sound="error")
                        create_toast(f"{sender}(es) from ({detected}) in {channel}", translated)


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

    main()
