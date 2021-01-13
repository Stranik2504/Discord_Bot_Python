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

    try:
        ListSong = load_file(FILE_NAME_QUEUE)
        History = load_file(FILE_NAME_HISTORY)
    except Exception as ex:
        logs('[Music_model][start]: ' + str(ex))


def play(url, guild_id, voice):
    try:
        output = add_song(guild_id, url)
        start_play(guild_id, voice)

        return output
    except Exception as ex:
        logs('[Music_model][play]: ' + str(ex))
        return 'Ошибка'


def start_play(guild_id, voice):
    try:
        if not voice.is_playing():
            if ListSong and ListSong.get(str(guild_id)) and len(ListSong[str(guild_id)]['songs']) > 0:
                play_song(guild_id, voice, 0)
                return ''
            else:
                return 'Очередь пустая'
        else:
            return 'Бот уже играет'
    except Exception as ex:
        logs('[Music_model][start_play]: ' + str(ex))
        return 'Ошибка'


def start_play_seek(guild_id, voice, seek):
    try:
        if voice:
            ListSong[str(guild_id)]['is_skip'] = 'true'
            voice.stop()

        if ListSong and ListSong.get(str(guild_id)) and len(ListSong[str(guild_id)]['songs']) > 0:
            play_song(guild_id, voice, seek)
            return None
        else:
            return 'Очередь пустая'
    except Exception as ex:
        logs('[Music_model][start_play_seek]: ' + str(ex))
        return 'Ошибка'


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
        logs('[Music_model][play_song]: ' + str(ex))


def play_next(url, guild_id, voice):
    global ListSong

    try:
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
    except Exception as ex:
        logs('[Music_model][play_next]: ' + str(ex))


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
        logs('[Music_model][add_song]: ' + str(ex))
        return 'Ошибка в добавлении песни/плейлиста'


def add_song_history(guild_id, url):
    global History

    try:
        if not History:
            History = {str(guild_id): list()}
        elif not History.get(str(guild_id)):
            History[str(guild_id)] = list()

        History[str(guild_id)].insert(0, url)

        if len(History[str(guild_id)]) > COUNT_HISTORY:
            History[str(guild_id)].pop(COUNT_HISTORY)
    except Exception as ex:
        logs('[Music_model][add_song_history]: ' + str(ex))


def leave(guild_id, voice):
    try:
        if ListSong:
            if ListSong.get(str(guild_id)):
                ListSong[str(guild_id)]['is_skip'] = 'true'
        voice.stop()
    except Exception as ex:
        logs('[Music_model][leave]: ' + str(ex))


def pause(voice):
    try:
        if voice:
            if voice.is_playing():
                voice.pause()
                return 'Музыка приостановленна'
            else:
                return 'Бот уже остановлен'
        else:
            return 'Бот не подключен к голосовому каналу'
    except Exception as ex:
        logs('[Music_model][pause]: ' + str(ex))
        return 'Ошибка'


def resume(voice):
    try:
        if voice:
            if voice.is_paused():
                voice.resume()
                return 'Музыка продолжает воспроизведение'
            else:
                return 'Уже играет'
        else:
            return 'Бот не подключен к голосовому каналу'
    except Exception as ex:
        logs('[Music_model][resume]: ' + str(ex))
        return 'Ошибка'


def stop(guild_id, voice):
    try:
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
    except Exception as ex:
        logs('[Music_model][stop]: ' + str(ex))
        return 'Ошибка'


def clear(guild_id, voice):
    try:
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
    except Exception as ex:
        logs('[Music_model][clear]: ' + str(ex))
        return 'Ошибка'


def skip(guild_id, voice):
    try:
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
    except Exception as ex:
        logs('[Music_model][skip]: ' + str(ex))
        return 'Ошибка'


def get_history(guild_id):
    try:
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
    except Exception as ex:
        logs('[Music_model][get_history]: ' + str(ex))
        return list()


def get_current_cong(guild_id):
    try:
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
    except Exception as ex:
        logs('[Music_model][get_current_cong]: ' + str(ex))
        return {'name': 'Ошибка', 'url': 'Ошибка'}


def set_looping(guild_id, looping: str):
    try:
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
    except Exception as ex:
        logs('[Music_model][set_looping]: ' + str(ex))
        return 'Ошибка'


def get_looping(guild_id):
    try:
        if ListSong and ListSong.get(str(guild_id)):
            return 'Повторение(off/single/all): ' + ListSong[str(guild_id)]['looping']
        else:
            return 'Очередь не найдена'
    except Exception as ex:
        logs('[Music_model][get_looping]: ' + str(ex))
        return 'Ошибка'


def get_queue(guild_id, count):
    try:
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
    except Exception as ex:
        logs('[Music_model][get_queue]: ' + str(ex))
        return None


def restart(guild_id, voice):
    try:
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
    except Exception as ex:
        logs('[Music_model][restart]: ' + str(ex))
        return 'Ошибка'


def search(guild_id, name_song: str):
    try:
        list_songs = search_song(name_song)
        SearchListSong[str(guild_id)] = list_songs
        results = f'Пожалуйста, выберите дорожку с командой «{PREFIX}p n»:\n'

        for i in range(len(list_songs)):
            results += str(i + 1) + ') ' + list_songs[i]['title'] + '\n'

        return results
    except Exception as ex:
        logs('[Music_model][search]: ' + str(ex))
        return 'Ошибка'


def add_message(guild_id, message_id):
    try:
        SearchMessageIds[str(guild_id)] = message_id
    except Exception as ex:
        logs('[Music_model][add_message]: ' + str(ex))


def pop_message(guild_id):
    try:
        return SearchMessageIds.pop(str(guild_id))
    except Exception as ex:
        logs('[Music_model][pop_message]: ' + str(ex))
        return None


def is_songs_in_search(guild_id):
    try:
        return bool(SearchListSong.get(str(guild_id)))
    except Exception as ex:
        logs('[Music_model][is_songs_in_search]: ' + str(ex))
        return False


def add_song_in_playlist(guild_id, num: int):
    try:
        if num > 5 or num < 1:
            return [False, 'Не правильный номер']

        add_song(guild_id, 'https://www.youtube.com/watch?v=' + SearchListSong.pop(str(guild_id))[num - 1]['id'])

        return [True, 'Песня успешно добавленна в плейлист']
    except Exception as ex:
        logs('[Music_model][add_song_in_playlist]: ' + str(ex))
        return [False, 'Ошибка']


def join(guild_id, voice_channel_id, channel_id):
    try:
        if not MusicChannelConnection.get(str(guild_id)):
            MusicChannelConnection[str(guild_id)] = dict(voice_channel_id=voice_channel_id, channel_id=channel_id)
        else:
            MusicChannelConnection[str(guild_id)]['voice_channel_id'] = voice_channel_id
            MusicChannelConnection[str(guild_id)]['channel_id'] = channel_id
    except Exception as ex:
        logs('[Music_model][join]: ' + str(ex))


def rejoin(guild_id, voice_channel_id):
    try:
        if MusicChannelConnection.get(str(guild_id)):
            MusicChannelConnection[str(guild_id)]['voice_channel_id'] = voice_channel_id
    except Exception as ex:
        logs('[Music_model][rejoin]: ' + str(ex))


def is_connect_in_this_guild(guild_id):
    try:
        if MusicChannelConnection.get(str(guild_id)):
            return bool(MusicChannelConnection.get(str(guild_id)))

        return None
    except Exception as ex:
        logs('[Music_model][is_connect_in_this_guild]: ' + str(ex))
        return None


def get_voice_connection(guild_id):
    try:
        if MusicChannelConnection.get(str(guild_id)):
            return MusicChannelConnection[str(guild_id)]['voice_channel_id'], MusicChannelConnection[str(guild_id)]['channel_id']

        return None
    except Exception as ex:
        logs('[Music_model][get_voice_connection]: ' + str(ex))
        return None


def voice_disconnected(guild_id):
    try:
        if MusicChannelConnection.get(str(guild_id)):
            MusicChannelConnection.pop(str(guild_id))
    except Exception as ex:
        logs('[Music_model][voice_disconnected]: ' + str(ex))


def disconnected():
    try:
        for guild_id in ListSong.keys():
            ListSong[str(guild_id)]['is_skip'] = 'true'
    except Exception as ex:
        logs('[Music_model][disconnected]: ' + str(ex))
