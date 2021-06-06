import datetime
import json
import os.path
import requests
import validators

from Config import API_KEY_GOOGLE, MAX_COUNT_SONGS_FROM_SEARCH, MAX_SEARCH_ITERATION


def logs(text):
    print('[' + str(datetime.datetime.now()) + ']' + str(text))


def load_file(filename):
    try:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as json_data:
                    return json.load(json_data)

            except Exception as ex:
                logs(ex)
                return None
        else:
            return None
    except Exception as ex:
        logs('[Library][load_file]: ' + str(ex))


def save_file(filename, save_object):
    try:
        with open(filename, 'w', encoding='utf-8') as json_data:
            json.dump(save_object, json_data)
    except Exception as ex:
        logs('[Library][save_file]: ' + str(ex))


def get_time(time: str):
    try:
        D = 0
        H = 0
        M = 0
        S = 0

        if time.find('D') != -1:
            D = time.replace('D', ' ').split()[0]
            time = time.replace(D + 'D', '')

        if time.find('H') != -1:
            H = time.replace('H', ' ').split()[0]
            time = time.replace(H + 'H', '')

        if time.find('M') != -1:
            M = time.replace('M', ' ').split()[0]
            time = time.replace(M + 'M', '')

        if time.find('S') != -1:
            S = time.replace('S', ' ').split()[0]

        results = ''

        if D:
            results += D + ':'

        if H:
            if results and len(H) == 1:
                results += '0' + H + ':'
            else:
                results += H + ':'

        if M:
            if results and len(M) == 1:
                results += '0' + M + ':'
            else:
                results += M + ':'

        if S:
            if results and len(S) == 1:
                results += '0' + S
            else:
                results += S

        return results
    except Exception as ex:
        logs('[Library][get_time]: ' + str(ex))
        return 0


#Venv google
def search_song(name_song: str):
    try:
        list_songs = list()
        num = 0
        next_page_token = None

        while num < MAX_SEARCH_ITERATION:
            if next_page_token:
                response = requests.get(
                    f'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&pageToken={next_page_token}&q=' + name_song +
                    '&key=' + API_KEY_GOOGLE)
            else:
                response = requests.get(
                    'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q=' + name_song +
                    '&key=' + API_KEY_GOOGLE)

            next_page_token = response.json()['nextPageToken']

            for song in response.json()['items']:
                if song['snippet']['liveBroadcastContent'] == 'none':
                    response = requests.get('https://www.googleapis.com/youtube/v3/videos?id=' + song['id'][
                        'videoId'] + '&part=contentDetails&key=' + API_KEY_GOOGLE)

                    list_songs.append(dict(title=song['snippet']['title'] + '. (' + get_time(
                        response.json()['items'][0]['contentDetails']['duration'].replace('PT', '')) + ')',
                                           id=song['id']['videoId']))
                    if len(list_songs) == MAX_COUNT_SONGS_FROM_SEARCH:
                        break

            if len(list_songs) == MAX_COUNT_SONGS_FROM_SEARCH:
                break

            num += 1

        return list_songs
    except Exception as ex:
        logs('[Library][search_song]: ' + str(ex))
        return list()


def is_valid(text: str):
    try:
        return False if not validators.url(text) else True
    except Exception as ex:
        logs('[Library][is_valid]: ' + str(ex))
        return False
