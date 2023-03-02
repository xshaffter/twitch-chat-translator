# Install

- open your console and go to the project directory
- make sure you have python >= 3.9
- create your virtual environment for this project with

```shell
python -m venv twitch-translator
```

- activate the virtual environment using

Linux/macOS

````shell
source twitch-translator/bin/activate
````

Windows

```shell
twitch-translator/Scripts/activate
```

- install all the dependencies

```shell
pip install -r requirements.txt
```

- create a .env file with the following parameters:

```
token=<TOKEN>  # got from https://twitchapps.com/tmi/
nickname=<USERNAME>
channel=<WATCHED_CHANNEL>
```

- then you can run the script with

```shell
python main.py
```