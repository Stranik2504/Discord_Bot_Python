import datetime
import json
import os.path
import requests
import validators

from Config import API_KEY_GOOGLE


def logs(text):
    if isinstance(text, str):
        print('[' + str(datetime.datetime.now()) + ']' + text)


def load_file(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as json_data:
                return json.load(json_data)

        except Exception as ex:
            logs(ex)
            return None
    else:
        return None


def save_file(filename, save_object):
    with open(filename, 'w', encoding='utf-8') as json_data:
        json.dump(save_object, json_data)


def search_song(name_song: str):
    response = requests.get('https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&fields=items(id,'
                            'snippet)&' + name_song + '&key= '
                            + API_KEY_GOOGLE)

    list_songs = list()

    for song in response.json()['items']:
        list_songs.append(dict(title=song['snippet']['title'], id=song['id']['videoId']))

    return list_songs


def is_valid(text: str):
    if not validators.url(text):
        return False
    else:
        return True
