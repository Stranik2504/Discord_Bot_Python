import discord

import Music_model
from Library import *
from Config import *
from discord.ext import commands
from discord.utils import get
from discord.ext.commands import has_permissions

client = commands.Bot(command_prefix=PREFIX)


async def join_in_voice(ctx):
    channel = ctx.message.author.voice.channel

    if ctx.voice_client:
        if ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)
            await ctx.send(f'{client.user.name} перемещен к вам: {channel}')
    else:
        await channel.connect()
        await ctx.send(f'{client.user.name} на связи: {channel}')


@client.event  # вход
async def on_ready():
    Music_model.start()
    logs('bot started')


@client.event
async def on_connect():
    logs('bot connected')


@client.event
async def on_disconnect():
    Music_model.disconnected()
    logs('bot disconnected')


@client.command(pass_context=True, aliases=['hi', 'hell', 'hel', 'Hello', 'HELLO', 'Hi', 'HI'],
                help='Поздороваться')
async def hello(ctx):
    await ctx.send(f'{ctx.message.author.mention}, приветствую')


@client.command(pass_context=True, aliases=['rep', 'Rep', 'REP', 'Repeat', 'REPEAT'],
                help='Повторить')
async def repeat(ctx):
    text = ctx.message.content.replace(ctx.message.content.split()[0], '')
    if len(text) <= MAX_LENGTH_TEXT or ctx.author.id in ADMIN_LIST:
        await ctx.send(text)


@client.command(pass_context=True, aliases=['j', 'J', 'Join', 'JOIN'],
                help='Бот присоединяется к голосовому каналу')
async def join(ctx):
    await join_in_voice(ctx)


@client.command(pass_context=True, aliases=['l', 'L', 'Leave', 'LEAVE'],
                help='Бот покидает голосовой канал')
async def leave(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        if voice and (voice.is_playing() or voice.is_paused()):
            Music_model.leave(ctx.guild.id, ctx.voice_client)
        await voice.disconnect()
        await ctx.send(f'{client.user.name} отключился от канала')


@client.command(pass_context=True, aliases=['p', 'pla', 'P', 'Pla', 'Play', 'PLAY'],
                help="Найти и/или Возпроизвести песню")
async def play(ctx):
    text = ctx.message.content.replace(ctx.message.content.split()[0], '')

    if text == '' or text == ' ' or not text:
        output = Music_model.start_play(ctx.guild.id, ctx.voice_client)
        if not output == '' and not output == ' ' and output:
            await ctx.send(output)
    else:
        if is_valid(text[1:]):
            await join_in_voice(ctx)
            await ctx.send(Music_model.play(text[1:], ctx.guild.id, ctx.voice_client))
        else:
            if text[1:].isdigit() and Music_model.is_songs_in_search(ctx.guild.id):
                output = Music_model.add_song_in_playlist(ctx.guild.id, int(text[1:]))

                if output[0] and (not ctx.voice_client):
                    await join_in_voice(ctx)
                    await ctx.send(output[1])
                    await ctx.send(Music_model.play(text[1:], ctx.guild.id, ctx.voice_client))
                elif ctx.voice_client:
                    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                        await join_in_voice(ctx)
                        await ctx.send(output[1])
                        await ctx.send(Music_model.play(text[1:], ctx.guild.id, ctx.voice_client))
                else:
                    await ctx.send(output[1])
            else:
                await ctx.send(Music_model.search(ctx.guild.id, text[1:]))


@client.command(pass_context=True, aliases=['Pause', 'PAUSE'], help='Приостановка воспроизведения аудио')
async def pause(ctx):
    await ctx.send(Music_model.pause(ctx.voice_client))


@client.command(pass_context=True, aliases=['Resume', 'RESUME'], help='Возобновление воспроизведения аудио')
async def resume(ctx):
    await ctx.send(Music_model.resume(ctx.voice_client))


@client.command(pass_context=True, aliases=['Stop', 'STOP', 'st', 'St', 'ST'],
                help='Остановка воспроизведения аудио и отчистка очереди воспроизведения')
async def stop(ctx):
    await ctx.send(Music_model.stop(ctx.voice_client, ctx.guild.id))


@client.command(pass_context=True, aliases=['Clear', 'CLEAR'], help='Отчищение очереди')
async def clear(ctx):
    await ctx.send(Music_model.clear(ctx.guild.id, ctx.voice_client))


@client.command(pass_context=True, aliases=['s', 'S', 'Skip', 'SKIP'], help='Пропуск песни')
async def skip(ctx):
    await ctx.send(Music_model.skip(ctx.guild.id, ctx.voice_client))


@client.command(pass_context=True, aliases=['h', 'H', 'History', 'HISTORY'], help='Прошлая песня')
async def history(ctx):
    songs = Music_model.get_history(ctx.guild.id)
    output = ''

    for song in songs:
        output += 'Name song: ' + song['name'] + ', url: ' + song['url'] + '\n'

    await ctx.send(output)


@client.command(pass_context=True, aliases=['np', 'nowplaying', 'NP', 'NowPlaying', 'Nowplaying', 'nowPlaying',
                                            'NOWPLAYING', 'Now_Playing', 'Now_playing', 'now_Playing', 'NOW_PLAYING'],
                help='Песня, котоаря играет')
async def now_playing(ctx):
    song = Music_model.get_current_cong(ctx.guild.id)
    await ctx.send('Name song(playlist): ' + song['name'] + ', url: ' + song['url'])


@client.command(pass_context=True, aliases=['Loop', 'LOOP', 'looping', 'Looping', 'LOOPING'], help='Повторение '
                                                                                                   'песни/песен')
async def loop(ctx):
    looping = ctx.message.content.replace(ctx.message.content.split()[0], '')

    if looping == '' or looping == ' ' or not looping:
        await ctx.send(Music_model.get_looping(ctx.guild.id))
    else:
        looping.replace(' ', '')
        if looping == 'single' or looping == 'all' or looping == 'off':
            await ctx.send(Music_model.set_looping(ctx.guild.id, looping))


@client.command(pass_context=True, aliases=['Queue', 'QUEUE', 'qu', 'Qu', 'QU'], help='Вывод очереди')
async def queue(ctx):
    songs = Music_model.get_queue(ctx.guild.id, MAX_COUNT_SONGS_FROM_QUEUE)

    if songs:
        output = ''

        for song in songs:
            output += 'Name song: ' + song['name'] + ', url: ' + song['url'] + '\n'

        await ctx.send(output)
    else:
        await ctx.send('Нет песен в очереди')


@client.command(pass_context=True, aliases=['rest', 'Rest', 'REST', 'Restart', 'RESTART'], help='Перезапуск '
                                                                                                'воспроизведения '
                                                                                                'песни')
async def restart(ctx):
    await ctx.send(Music_model.restart(ctx.guild.id, ctx.voice_client))


@client.command(pass_context=True, aliases=['Seek', 'SEEK'], help='Перемещения воспроизведение музыки на врема(в '
                                                                  'секундах)')
async def seek(ctx, *, time: int):
    output = Music_model.start_play_seek(ctx.guild.id, ctx.voice_client, time)
    if output == '' or output == ' ' or not output:
        await ctx.send(output)
    else:
        await ctx.send(f'Песня пересена на позицию {time}')


@client.command(pass_context=True, aliases=['eval', 'Exe'], help='')
async def exe(ctx, *, arg: str):
    if ctx.author.id in ADMIN_LIST:
        await ctx.send(eval(arg))
    elif KICK_FOR_ADMIN_COMMAND:
        try:
            await ctx.author.kick(reason='Some')
        except discord.errors.Forbidden:
            await ctx.send(client.user.name + ": I don't have permissions for kick")


@client.command(pass_context=True)
@has_permissions(kick_members=True)
async def voice_kick(ctx, member: discord.Member):
    if ctx.author.id in ADMIN_LIST:
        await member.edit(voice_channel=None)
        logs('Member kicked from voice')
    elif KICK_FOR_ADMIN_COMMAND:
        try:
            await ctx.author.kick(reason='Some')
        except discord.errors.Forbidden:
            await ctx.send(client.user.name + ": I don't have permissions for kick from voice channel")


client.run(TOKEN)
