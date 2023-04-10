import logging
import os
import platform
import re
import socket
import sys
import time
from threading import Thread

import beepy
import pandas as pd
from dotenv import load_dotenv
from emoji import demojize
from googletrans import Translator


class Message(object):
    __slots__ = ["sender", "channel", "message", "clear_message", "indexer", "no_emotes_txt", "do_ignore", "connection"]

    def __init__(self, channel, message_txt, connection):
        regex = re.findall(f":tmi.twitch.tv \\d{{3}} {channel} :", message_txt)
        try:
            separator = regex[0]
        except IndexError:
            separator = f"{channel} :"

        try:
            components, self.message = message_txt.split(separator)
        except ValueError:
            print(separator)
            print(message_txt)
            raise
        self.connection = connection
        self.do_ignore = -1
        self.no_emotes_txt = ""
        self.indexer = {}
        self.message = self.message.strip()
        self.channel = channel
        self.sender = components.split("!")[0][1:]
        self.clear_message = demojize(self.message.strip())

    def no_emotes(self):
        if self.no_emotes_txt:
            return self.no_emotes_txt
        index = 0
        result: str = self.message
        for segment in self.message.split(" "):
            if self.connection.is_emote(segment):
                result = result.replace(segment, f"{{{index}}}")
                self.indexer[index] = segment
                index += 1

        self.no_emotes_txt = result
        return result

    def rebuild(self, text):
        result = text
        for index, value in self.indexer.items():
            result.replace(index, value)
        self.indexer = dict()

        return result

    def translate(self):
        global translator
        detected = translator.detect(self.message)
        brute_translation = translator.translate(self.message, dest="es").text
        rebuilt_translate = self.rebuild(brute_translation)
        return detected, rebuilt_translate

    def is_ignore_message(self):
        if self.do_ignore == -1:
            self.do_ignore = re.findall(r"cheer[a-zA-Z]*\d+", self.clear_message) \
                             or self.sender.lower() in ignored_users \
                             or self.clear_message.startswith("!") \
                             or self.connection.is_emote(self.clear_message) \
                             or self.connection.is_emote_sequence(self.clear_message)
        return self.do_ignore

    def __str__(self):
        return f"{self.sender=}\n{self.message=}\n{self.channel=}"

    def is_valid_language(self):
        VALID_LANGUAGES = ["es", "en"]
        detected = translator.detect(self.no_emotes()).lang
        if isinstance(detected, list):
            return any([lang in VALID_LANGUAGES for lang in detected])
        else:
            return detected in VALID_LANGUAGES

    def log(self):
        self.connection.logger.info(f"{self.sender}: {self.clear_message}")
        create_toast(f"{self.sender}#{channel}", self.clear_message)

    def notify_tag(self):
        if f"@{self.connection.nickname}" in self.clear_message or (
                check_agv("--mod") and ("@mod" in self.clear_message or "@mods" in self.clear_message)
        ):
            beepy.beep()
            create_toast(f"{self.sender}#{channel}", self.clear_message)

    def log_translation(self):
        detected, translated = self.translate()
        self.connection.logger.info(f"{self.sender}({detected}): {self.clear_message}")
        self.connection.logger.info(f"{self.sender}(es): {translated}")

        create_toast(f"{self.sender}(es) from ({detected}) in {channel}", translated)

    def do_count(self):
        return any([len(re.findall(f"\\b{word}\\b", self.clear_message)) >= 1 for word in self.connection.words])

class Connection(object):

    def __init__(self, channel_name):
        self.server = "irc.chat.twitch.tv"
        self.port = 6667
        self.token = os.environ.get("token", False)
        self.nickname = os.environ.get("nickname")
        self.words = os.environ.get("searched_words").split(",")
        self.channel_name = channel_name
        self.channel = f"#{channel_name}"
        self.first_buffer = 2
        self.bttv_emotes = self.__get_bttv_channel_emotes()
        self.word_counter = 0
        self.logger = self.__configure_logger()

    def __configure_logger(self):

        logger = logging.getLogger(f"{self.channel_name}_logger")
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(f"{self.channel_name}-chat.log", encoding='utf-8')
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(asctime)s — %(message)s', datefmt='[%Y-%m-%d %H:%M:%S]'))
        logger.addHandler(handler)
        return logger
    def __get_bttv_channel_emotes(self):
        dataframe = pd.read_csv("emotes/channel-emotes.csv")
        dataframe = dataframe.loc[(dataframe["type"] == "BTTV") & (dataframe["owner"] == self.channel_name)]
        return dataframe

    def __receive_first(self):
        while True:
            try:
                resp = self.sock.recv(2048).decode('utf-8')
                if self.channel in resp:
                    break
            except ConnectionResetError:
                continue

    def begin(self):
        with socket.socket() as self.sock:
            self.sock.connect((self.server, self.port))

            self.sock.send(f"PASS {self.token}\n".encode('utf-8'))
            self.sock.send(f"NICK {self.nickname}\n".encode('utf-8'))
            self.sock.send(f"JOIN {self.channel}\n".encode('utf-8'))
            print(f"listening to {self.channel}")
            self.__listen()

    def __check_response(self, resp):

        if resp.startswith('PING'):
            self.sock.send("PONG\n".encode('utf-8'))
            return

        if f"{channel} :" in resp:
            message = Message(channel, resp, self)

            if check_agv("--notify"):
                message.notify_tag()

            if check_agv("--count"):
                if message.do_count():
                    self.word_counter += 1
                    print(f"{message.sender} ({self.word_counter}): {message.message}")
                    self.logger.info(f"{message.sender} ({self.word_counter}): {message.message}")

            if check_agv("--translate") and not message.is_ignore_message() and not message.is_valid_language():
                message.log_translation()

    def __listen(self):
        create_toast("twitch-chat", f"listener activated in #{self.channel_name}")
        while True:
            general_resp = self.sock_recv()
            clean_resp = general_resp.strip()
            responses = clean_resp.split("\n")

            for response in responses:
                self.__check_response(response.strip())

    def is_bttv_emote(self, segment):
        return segment in self.bttv_emotes['name'].unique()

    def is_streamer_emote(self, segment):
        return segment in channel_emotes['name'].unique() or self.is_bttv_emote(segment)

    def is_normal_emote(self, text):
        return text in general_emotes_df["name"].unique()

    def is_emote(self, text):
        if " " in text:
            return False

        return self.is_normal_emote(text) or self.is_streamer_emote(text)

    def is_emote_sequence(self, clear_message):
        sequence = clear_message.split(" ")
        diffs = set(sequence)
        for item in diffs:
            if not self.is_emote(item):
                return False

        return True

    def sock_recv(self):
        while True:
            try:
                return self.sock.recv(4096).decode('utf-8')
            except ConnectionResetError:
                time.sleep(1)


def create_toast(title, text):
    _platform = platform.platform().lower().split("-")[0]
    if _platform == "macos":
        os.system("""
              osascript -e 'display notification "{}" with title "{}"'
              """.format(text, title))
    elif _platform == "windows":
        windows_toasts = __import__("windows_toasts")
        wintoaster = windows_toasts.WindowsToaster(title)
        newToast = windows_toasts.ToastText1()
        newToast.SetBody(text)
        wintoaster.show_toast(newToast)
    elif _platform == "linux":
        os.system(f'notify-send "{title}" "{text}"')
    else:
        print(f"{_platform=}")


def configure_logger():
    try:
        os.mkdir("logs")
    except FileExistsError:
        pass


def check_agv(argv):
    return argv in sys.argv
    

def get_channel_emotes():
    dataframe: pd.DataFrame = pd.read_csv(f"emotes/channel-emotes.csv")
    dataframe: pd.DataFrame = dataframe.loc[(dataframe["type"] == "twitch")]
    return dataframe


if __name__ == "__main__":
    load_dotenv()
    ignored_users_str = os.environ.get("IGNORED_USERS", "streamelements,nightbot").lower()

    global translator
    translator = Translator()
    ignored_users = ignored_users_str.split(",")
    channels = os.getenv("channels", "").split(",")

    channel_emotes = get_channel_emotes()
    general_emotes_df = pd.read_csv("emotes/general-emotes.csv")

    configure_logger()
    print(channels)
    for channel in channels:
        connection = Connection(channel)
        t = Thread(target=connection.begin, daemon=True, name=f"{connection.channel_name}-t")
        t.start()

    while True:
        pass
