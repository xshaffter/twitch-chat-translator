import json
import os

import pandas
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

def get_channel_emotes(channel_name):
    response = requests.get(f"http://localhost:8000/emotes/{channel_name}")
    json_response = response.json()
    return json_response


def try_get_dataframe(file_name):
    try:
        data_frame = pd.read_csv(file_name)
    except:
        data_frame = pd.DataFrame()

    return data_frame


if __name__ == "__main__":

    response = requests.get("http://localhost:8000/emotes/general")
    json_data = response.json()

    df = pandas.json_normalize(json_data, sep="_", max_level=0)
    df.to_csv("general-emotes.csv", index=False)

    general_df = try_get_dataframe("channel-emotes.csv")
    already_done_owners = try_get_dataframe("done-owners.csv")
    new_owners = pd.DataFrame()
    try:
        alredy_searched = already_done_owners["name"].unique()
    except:
        alredy_searched = []

    searched_channels = os.environ.get("channels_for_search", "").split(",")
    filtered_owners = [owner for owner in searched_channels if owner not in alredy_searched]

    for channel in filtered_owners:
        json_data = get_channel_emotes(channel)

        json_df = pandas.json_normalize(json_data, sep="_", max_level=0)

        general_df = pd.concat([general_df, json_df])


    new_owners["name"] = filtered_owners

    new_owners.to_csv("done-owners.csv", index=False)
    general_df.to_csv("channel-emotes.csv", index=False)
