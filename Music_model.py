import discord
import youtube_dl

from discord import PCMVolumeTransformer
from Config import PREFIX, VOLUME, COUNT_HISTORY, FILE_NAME_QUEUE, FILE_NAME_HISTORY
from Library import *

ListSong = dict()
SearchListSong = dict()
SearchMessageIds = dict()
MusicChannelConnection = dict()
History = dict()


def start():
    global ListSong
    global History
    ListSong = load_file(FILE_NAME_QUEUE)
    History = load_file(FILE_NAME_HISTORY)


def play(url, guild_id, voice):
    output = add_song(guild_id, url)
    start_play(guild_id, voice)

    return output


def start_play(guild_id, voice):
    if not voice.is_playing():
        if ListSong and ListSong.get(str(guild_id)) and len(ListSong[str(guild_id)]['songs']) > 0:
            play_song(guild_id, voice, 0)
            return ''
        else:
            return 'Очередь пустая'
    else:
        return 'Бот уже играет'


def start_play_seek(guild_id, voice, seek):
    if voice:
        ListSong[str(guild_id)]['is_skip'] = 'true'
        voice.stop()

    if ListSong and ListSong.get(str(guild_id)) and len(ListSong[str(guild_id)]['songs']) > 0:
        play_song(guild_id, voice, seek)
        return None
    else:
        return 'Очередь пустая'


def play_song(guild_id, voice, seek: int):
    try:
        if isinstance(ListSong[str(guild_id)]['songs'][0], dict):
            num = ListSong[str(guild_id)]['songs'][0]['num_song']
            with youtube_dl.YoutubeDL({'format': 'bestaudio/best', 'playliststart': num, 'playlistend': num,
                                       'ignoreerrors': 'True'}) as ydl:
                info = ydl.extract_info(ListSong[str(guild_id)]['songs'][0]['url'], download=False)

            url = str(info['entries'][0]['formats'][0]['url'])
            time = int(info['entries'][0]['duration'])
        else:
            with youtube_dl.YoutubeDL({'format': 'bestaudio/best', 'ignoreerrors': 'True'}) as ydl:
                info = ydl.extract_info(ListSong[str(guild_id)]['songs'][0], download=False)
            url = info['formats'][0]['url']
            time = info['duration']

        if seek < 0:
            seek = 0
        elif seek > time:
            seek = time - 1

        voice.play(discord.FFmpegPCMAudio(url, **dict(
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options=f'-vn -ss {seek}')),
                   after=lambda e: play_next(url, guild_id, voice))
        voice.source = PCMVolumeTransformer(voice.source, volume=VOLUME)
    except Exception as ex:
        logs(ex)


def play_next(url, guild_id, voice):
    global ListSong

    if voice and ListSong[str(guild_id)]['is_skip'] == 'false':
        if ListSong and ListSong.get(str(guild_id)) and len(ListSong[str(guild_id)]['songs']) > 0:
            if not isinstance(ListSong[str(guild_id)]['songs'][0], dict):
                if ListSong[str(guild_id)]['looping'] == 'off':
                    add_song_history(guild_id, ListSong[str(guild_id)]['songs'].pop(0))
                    save_file(FILE_NAME_HISTORY, History)
                elif ListSong[str(guild_id)]['looping'] == 'all':
                    song = ListSong[str(guild_id)]['songs'].pop(0)
                    add_song_history(guild_id, song)
                    if ListSong[str(guild_id)]['skipping'] == 'false':
                        ListSong[str(guild_id)]['songs'].append(song)
                    save_file(FILE_NAME_HISTORY, History)
                elif ListSong[str(guild_id)]['looping'] == 'all/reset':
                    ListSong[str(guild_id)]['looping'] = 'all'
            elif ListSong[str(guild_id)]['skipping'] == 'true':
                ListSong[str(guild_id)]['songs'].pop(0)
            else:
                num = ListSong[str(guild_id)]['songs'][0]['num_song'] + 1
                with youtube_dl.YoutubeDL({'format': 'bestaudio/best', 'playliststart': num, 'playlistend': num,
                                           'ignoreerrors': 'True'}) as ydl:
                    info = ydl.extract_info(ListSong[str(guild_id)]['songs'][0]['url'], download=False)

                if not info.get('entries') or info.get('entries') == '' or info.get('entries') == ' ':
                    if ListSong[str(guild_id)]['looping'] == 'off':
                        ListSong[str(guild_id)]['songs'].pop(0)
                    elif ListSong[str(guild_id)]['looping'] == 'all':
                        lists = ListSong[str(guild_id)]['songs'].pop(0)
                        ListSong[str(guild_id)]['songs'].append(lists)
                    elif ListSong[str(guild_id)]['looping'] == 'all/reset':
                        ListSong[str(guild_id)]['looping'] = 'all'
                else:
                    ListSong[str(guild_id)]['songs'][0]['num_song'] += 1
                    add_song_history(guild_id, url)
                    save_file(FILE_NAME_QUEUE, ListSong)
                    save_file(FILE_NAME_HISTORY, History)

            ListSong[str(guild_id)]['skipping'] = 'false'

            save_file(FILE_NAME_QUEUE, ListSong)

            if ListSong and ListSong.get(str(guild_id)):
                play_song(guild_id, voice, 0)
    else:
        ListSong[str(guild_id)]['is_skip'] = 'false'


def add_song(guild_id, url):
    global ListSong

    if not ListSong:
        ListSong = {str(guild_id): dict(songs=list(), looping='off', is_skip='false', skipping='false')}
    else:
        if not ListSong.get(str(guild_id)):
            ListSong.update({str(guild_id): dict(songs=list(), looping='off', is_skip='false', skipping='false')})

    try:
        is_playlist = False

        with youtube_dl.YoutubeDL({'ignoreerrors': 'True', 'playliststart': 1, 'playlistend': 1}) as ydl:
            info = ydl.extract_info(url, download=False)

        if info:
            if info.get('entries'):
                is_playlist = True
                ListSong[str(guild_id)]['songs'].append({'url': url, 'num_song': 1})
            else:
                ListSong[str(guild_id)]['songs'].append(url)

            save_file(FILE_NAME_QUEUE, ListSong)

            if is_playlist:
                return 'Плейлист успешно добавлен'
            else:
                return 'Песня успешно добавлена'
        else:
            return 'Ошибка в добавлении песни/плейлиста'
    except Exception as ex:
        logs(ex)
        return 'Ошибка в добавлении песни/плейлиста'


def add_song_history(guild_id, url):
    global History

    if not History:
        History = {str(guild_id): list()}
    elif not History.get(str(guild_id)):
        History[str(guild_id)] = list()

    History[str(guild_id)].insert(0, url)

    if len(History[str(guild_id)]) > COUNT_HISTORY:
        History[str(guild_id)].pop(COUNT_HISTORY)


def leave(guild_id, voice):
    if ListSong:
        if ListSong.get(str(guild_id)):
            ListSong[str(guild_id)]['is_skip'] = 'true'
    voice.stop()


def pause(voice):
    if voice:
        if voice.is_playing():
            voice.pause()
            return 'Музыка приостановленна'
        else:
            return 'Бот уже остановлен'
    else:
        return 'Бот не подключен к голосовому каналу'


def resume(voice):
    if voice:
        if voice.is_paused():
            voice.resume()
            return 'Музыка продолжает воспроизведение'
        else:
            return 'Уже играет'
    else:
        return 'Бот не подключен к голосовому каналу'


def stop(guild_id, voice):
    if voice and not isinstance(voice, int):
        if voice.is_playing() or voice.is_paused():
            ListSong[str(guild_id)]['is_skip'] = 'true'
            voice.stop()
            if ListSong and ListSong.get(str(guild_id)):
                if len(ListSong[str(guild_id)]['songs']) > 0:
                    add_song_history(guild_id, ListSong[str(guild_id)]['songs'][0])
                ListSong.pop(str(guild_id))
                save_file(FILE_NAME_QUEUE, ListSong)
                save_file(FILE_NAME_HISTORY, History)
                return 'Воспроизведение остановленно и очередь отчищена'
            else:
                return 'Воспроизведение остановленно, но очередь не найдена'
        else:
            return 'Бот уже остановлен'
    else:
        return 'Бот не подключен к голосовому каналу'


def clear(guild_id, voice):
    if voice:
        ListSong[str(guild_id)]['is_skip'] = 'true'
        voice.stop()
    else:
        return 'Ошибка очищения(музыка проигрывается)'

    if ListSong and ListSong.get(str(guild_id)):
        if len(ListSong[str(guild_id)]['songs']) > 0:
            add_song_history(guild_id, ListSong[str(guild_id)]['songs'][0])
        ListSong.pop(str(guild_id))
        save_file(FILE_NAME_QUEUE, ListSong)
        save_file(FILE_NAME_HISTORY, History)
        return 'Очередь отчищена'
    else:
        return 'Очередь не найдена'


def skip(guild_id, voice):
    if ListSong and ListSong.get(str(guild_id)):
        if voice and (voice.is_playing() or voice.is_paused()):
            ListSong[str(guild_id)]['skipping'] = 'true'
            voice.stop()
        else:
            if len(ListSong[str(guild_id)]['songs']) > 0:
                add_song_history(guild_id, ListSong[str(guild_id)]['songs'].pop(0))
            else:
                return 'Очередь пустая'

            save_file(FILE_NAME_QUEUE, ListSong)
            save_file(FILE_NAME_HISTORY, History)
    else:
        return 'Очередь не найдена'

    return 'Песня пропущена'


def get_history(guild_id):
    output = None

    for i in History[str(guild_id)]:
        with youtube_dl.YoutubeDL({'format': 'bestaudio'}) as ydl:
            info = ydl.extract_info(i, download=False)
        name = info['title']

        if not output:
            output = list({'name': name, 'url': History[str(guild_id)]})
        else:
            output.append({'name': name, 'url': History[str(guild_id)]})

    return output


def get_current_cong(guild_id):
    if ListSong[str(guild_id)]['songs'][0] is dict:
        with youtube_dl.YoutubeDL({'format': 'bestaudio', 'ignoreerrors': 'True', 'playliststart':
            ListSong[str(guild_id)]['songs'][0]['num_song'],
                                   'playlistend': ListSong[str(guild_id)]['songs'][0]['num_song']}) \
                as ydl:
            info = ydl.extract_info(ListSong[str(guild_id)]['songs'][0]['url'], download=False)
    else:
        with youtube_dl.YoutubeDL({'format': 'bestaudio', 'ignoreerrors': 'True'}) as ydl:
            info = ydl.extract_info(ListSong[str(guild_id)]['songs'][0], download=False)
    name = info['title']
    return {'name': name, 'url': ListSong[str(guild_id)]['songs'][0]}


def set_looping(guild_id, looping: str):
    if ListSong and ListSong.get(str(guild_id)):
        if ListSong[str(guild_id)]['looping'] != looping:
            ListSong[str(guild_id)]['looping'] = looping
            save_file(FILE_NAME_QUEUE, ListSong)

            if looping == 'single':
                return 'Повторение изменено на повторение одной песни'
            elif looping == 'all':
                return 'Повторение изменено на повторения всех песен'
            else:
                ListSong[str(guild_id)]['looping'] = 'off'
                return 'Повторение отключено'
        else:
            return 'Такое повторение уже включено'
    else:
        return 'Очередь не найдена'


def get_looping(guild_id):
    if ListSong and ListSong.get(str(guild_id)):
        return 'Повторение(off/single/all): ' + ListSong[str(guild_id)]['looping']
    else:
        return 'Очередь не найдена'


def get_queue(guild_id, count):
    if ListSong and ListSong.get(str(guild_id)) and len(ListSong[str(guild_id)]['songs']) > 0:
        output = []

        for i in ListSong[str(guild_id)]['songs']:
            if len(output) < count:
                if i is dict:
                    with youtube_dl.YoutubeDL({'format': 'bestaudio', 'ignoreerrors': 'True'}) as ydl:
                        info = ydl.extract_info(i['url'], download=False)
                        output.append({'name playlist': info['title'], 'url': i})
                else:
                    with youtube_dl.YoutubeDL({'format': 'bestaudio', 'ignoreerrors': 'True'}) as ydl:
                        info = ydl.extract_info(i, download=False)
                        output.append({'name': info['title'], 'url': i})

        return output
    else:
        return None


def restart(guild_id, voice):
    if voice:
        if ListSong and ListSong.get(str(guild_id)) and len(ListSong[str(guild_id)]['songs']) > 0:
            if ListSong[str(guild_id)]['looping'] == 'off':
                ListSong[str(guild_id)]['songs'].insert(ListSong[str(guild_id)]['songs'][0], 0)
            elif ListSong[str(guild_id)]['looping'] == 'all':
                ListSong[str(guild_id)]['looping'] = 'all/reset'
                ListSong[str(guild_id)]['songs'].insert(ListSong[str(guild_id)]['songs'][0], 0)

            voice.stop()

            return 'Песня перезапущена'
        else:
            return 'Очередь пустая. Не удалось перезапустить песню'
    else:
        return 'Песня не воспроизводиться. Не удалось перезапустить песню'


def search(guild_id, name_song: str):
    list_songs = search_song(name_song)
    SearchListSong[str(guild_id)] = list_songs
    results = f'Пожалуйста, выберите дорожку с командой «{PREFIX}p n»:\n'

    for i in range(len(list_songs)):
        results += str(i + 1) + ') ' + list_songs[i]['title'] + '\n'

    return results


def add_message(guild_id, message_id):
    SearchMessageIds[str(guild_id)] = message_id


def pop_message(guild_id):
    return SearchMessageIds.pop(str(guild_id))


def is_songs_in_search(guild_id):
    return bool(SearchListSong.get(str(guild_id)))


def add_song_in_playlist(guild_id, num: int):
    if num > 5 or num < 1:
        return [False, 'Не правильный номер']

    add_song(guild_id, 'https://www.youtube.com/watch?v=' + SearchListSong.pop(str(guild_id))[num - 1]['id'])

    return [True, 'Песня успешно добавленна в плейлист']


def join(guild_id, voice_channel_id, channel_id):
    if not MusicChannelConnection.get(str(guild_id)):
        MusicChannelConnection[str(guild_id)] = dict(voice_channel_id=voice_channel_id, channel_id=channel_id)
    else:
        MusicChannelConnection[str(guild_id)]['voice_channel_id'] = voice_channel_id
        MusicChannelConnection[str(guild_id)]['channel_id'] = channel_id


def rejoin(guild_id, voice_channel_id):
    if MusicChannelConnection.get(str(guild_id)):
        MusicChannelConnection[str(guild_id)]['voice_channel_id'] = voice_channel_id


def is_connect_in_this_guild(guild_id):
    if MusicChannelConnection.get(str(guild_id)):
        return bool(MusicChannelConnection.get(str(guild_id)))

    return None


def get_voice_connection(guild_id):
    if MusicChannelConnection.get(str(guild_id)):
        return MusicChannelConnection[str(guild_id)]['voice_channel_id'], MusicChannelConnection[str(guild_id)]['channel_id']

    return None


def voice_disconnected(guild_id):
    if MusicChannelConnection.get(str(guild_id)):
        MusicChannelConnection.pop(str(guild_id))


def disconnected():
    for guild_id in ListSong.keys():
        ListSong[str(guild_id)]['is_skip'] = 'true'
