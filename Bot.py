import discord

import Music_model
from Library import *
from Config import *
from discord.ext import commands
from discord.utils import get
from discord.ext.commands import has_permissions

client = commands.Bot(command_prefix=PREFIX)


async def join_in_voice(ctx):
	try:
		channel = ctx.message.author.voice.channel

		if ctx.voice_client:
			if ctx.voice_client.channel != channel:
				await ctx.voice_client.move_to(channel)
				Music_model.rejoin(ctx.guild.id, ctx.voice_client.channel.id)
				await ctx.send(f'{client.user.name} перемещен к вам: {channel}')
		else:
			await channel.connect()
			Music_model.join(ctx.guild.id, ctx.voice_client.channel.id, ctx.channel.id)
			await ctx.send(f'{client.user.name} на связи: {channel}')
	except Exception as ex:
		logs('[Bot][join_in_voice]: ' + str(ex))
		await ctx.send('Ошибка')


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


@client.event
async def on_voice_state_update(member, before, after):
	try:
		if after.channel is None and Music_model.is_connect_in_this_guild(member.guild.id) and member.id != ID:
			channel_info = Music_model.get_voice_connection(member.guild.id)
			if len(client.get_channel(channel_info[0]).members) == 1:
				voice = get(client.voice_clients, guild=member.guild)
				if voice:
					Music_model.stop(member.guild.id, voice)
					await voice.disconnect()
				await (await client.fetch_channel(channel_info[1])).send('Бот отключет от голосового канала из-за не наличия юзеров')
				Music_model.voice_disconnected(member.guild.id)
		elif after.channel is not None and Music_model.is_connect_in_this_guild(member.guild.id):
			channel_info = Music_model.get_voice_connection(member.guild.id)
			if len(client.get_channel(channel_info[0]).members) == 1:
				voice = get(client.voice_clients, guild=member.guild)
				if voice:
					Music_model.stop(member.guild.id, voice)
					await voice.disconnect()
				await (await client.fetch_channel(channel_info[1])).send(
					'Бот отключет от голосового канала из-за не наличия юзеров')
	except Exception as ex:
		logs('[Bot][event.on_voice_state_update]: ' + str(ex))


@client.command(pass_context=True, aliases=['hi', 'hell', 'hel', 'Hello', 'HELLO', 'Hi', 'HI'],
				help='Поздороваться')
async def hello(ctx):
	try:
		await ctx.send(f'{ctx.message.author.mention}, приветствую')
	except Exception as ex:
		logs('[Bot][hello]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['rep', 'Rep', 'REP', 'Repeat', 'REPEAT'],
				help='Повторить')
async def repeat(ctx):
	try:
		text = ctx.message.content.replace(ctx.message.content.split()[0], '')
		if len(text) <= MAX_LENGTH_TEXT or ctx.author.id in ADMIN_LIST:
			await ctx.send(text)
	except Exception as ex:
		logs('[Bot][repeat]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['j', 'J', 'Join', 'JOIN'],
				help='Бот присоединяется к голосовому каналу')
async def join(ctx):
	try:
		await join_in_voice(ctx)
	except Exception as ex:
		logs('[Bot][join]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['l', 'L', 'Leave', 'LEAVE'],
				help='Бот покидает голосовой канал')
async def leave(ctx):
	try:
		voice = get(client.voice_clients, guild=ctx.guild)
		if voice and voice.is_connected():
			if voice and (voice.is_playing() or voice.is_paused()):
				Music_model.leave(ctx.guild.id, ctx.voice_client)
			Music_model.voice_disconnected(ctx.guild.id)
			await voice.disconnect()
			await ctx.send(f'{client.user.name} отключился от канала')
	except Exception as ex:
		logs('[Bot][leave]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['p', 'pla', 'P', 'Pla', 'Play', 'PLAY'],
				help="Найти и/или Возпроизвести песню")
async def play(ctx):
	try:
		text = ctx.message.content.replace(ctx.message.content.split()[0], '')

		if text == '' or text == ' ' or not text:
			await join_in_voice(ctx)
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

					if output[0] and (not ctx.voice_client or (ctx.voice_client and not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused())):
						try:
							await (await ctx.fetch_message(Music_model.pop_message(ctx.guild.id))).delete()
						except Exception as ex:
							logs("Don't have permission for delete search message(" + str(ex) + ')')
						await join_in_voice(ctx)
						await ctx.send(output[1])
						output = Music_model.start_play(ctx.guild.id, ctx.voice_client)
						if not output == '' and not output == ' ' and output:
							await ctx.send(output)
					else:
						await ctx.send(output[1])
				else:
					Music_model.add_message(ctx.guild.id, (await ctx.send(Music_model.search(ctx.guild.id, text[1:]))).id)
	except Exception as ex:
		logs('[Bot][play]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['Pause', 'PAUSE'], help='Приостановка воспроизведения аудио')
async def pause(ctx):
	try:
		await ctx.send(Music_model.pause(ctx.voice_client))
	except Exception as ex:
		logs('[Bot][pause]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['Resume', 'RESUME'], help='Возобновление воспроизведения аудио')
async def resume(ctx):
	try:
		await ctx.send(Music_model.resume(ctx.voice_client))
	except Exception as ex:
		logs('[Bot][resume]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['Stop', 'STOP', 'st', 'St', 'ST'],
				help='Остановка воспроизведения аудио и отчистка очереди воспроизведения')
async def stop(ctx):
	try:
		await ctx.send(Music_model.stop(ctx.voice_client, ctx.guild.id))
	except Exception as ex:
		logs('[Bot][stop]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['Clear', 'CLEAR'], help='Отчищение очереди')
async def clear(ctx):
	try:
		await ctx.send(Music_model.clear(ctx.guild.id, ctx.voice_client))
	except Exception as ex:
		logs('[Bot][clear]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['s', 'S', 'Skip', 'SKIP'], help='Пропуск песни')
async def skip(ctx):
	try:
		await ctx.send(Music_model.skip(ctx.guild.id, ctx.voice_client))
	except Exception as ex:
		logs('[Bot][skip]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['h', 'H', 'History', 'HISTORY'], help='Прошлая песня')
async def history(ctx):
	try:
		songs = Music_model.get_history(ctx.guild.id)
		output = ''

		for song in songs:
			output += 'Name song: ' + song['name'] + ', url: ' + song['url'] + '\n'

		await ctx.send(output)
	except Exception as ex:
		logs('[Bot][history]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['np', 'nowplaying', 'NP', 'NowPlaying', 'Nowplaying', 'nowPlaying',
											'NOWPLAYING', 'Now_Playing', 'Now_playing', 'now_Playing', 'NOW_PLAYING'],
				help='Песня, котоаря играет')
async def now_playing(ctx):
	try:
		song = Music_model.get_current_cong(ctx.guild.id)
		await ctx.send('```Name song(playlist): ' + song['name'] + ', url: ' + song['url'] + '```')
	except Exception as ex:
		logs('[Bot][now_playing]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['Loop', 'LOOP', 'looping', 'Looping', 'LOOPING'], help='Повторение '
																								   'песни/песен')
async def loop(ctx):
	try:
		looping = ctx.message.content.replace(ctx.message.content.split()[0], '')

		if looping == '' or looping == ' ' or not looping:
			await ctx.send(Music_model.get_looping(ctx.guild.id))
		else:
			looping = looping[1:]
			if looping == 'single' or looping == 'all' or looping == 'off':
				await ctx.send(Music_model.set_looping(ctx.guild.id, looping))
	except Exception as ex:
		logs('[Bot][loop]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['Queue', 'QUEUE', 'qu', 'Qu', 'QU'], help='Вывод очереди')
async def queue(ctx):
	try:
		songs = Music_model.get_queue(ctx.guild.id, MAX_COUNT_SONGS_FROM_QUEUE)

		if songs:
			output = ''

			for song in songs:
				output += 'Name song: ' + song['name'] + ', url: ' + song['url'] + '\n'

			await ctx.send(output)
		else:
			await ctx.send('Нет песен в очереди')
	except Exception as ex:
		logs('[Bot][queue]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['rest', 'Rest', 'REST', 'Restart', 'RESTART'], help='Перезапуск '
																								'воспроизведения '
																								'песни')
async def restart(ctx):
	try:
		await ctx.send(Music_model.restart(ctx.guild.id, ctx.voice_client))
	except Exception as ex:
		logs('[Bot][restart]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['Seek', 'SEEK'], help='Перемещения воспроизведение музыки на врема(в '
																  'секундах)')
async def seek(ctx, *, time: int):
	try:
		output = Music_model.start_play_seek(ctx.guild.id, ctx.voice_client, time)
		if output == '' or output == ' ' or not output:
			await ctx.send(output)
		else:
			await ctx.send(f'Песня пересена на позицию {time}')
	except Exception as ex:
		logs('[Bot][seek]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True, aliases=['eval', 'Exe'], help='')
async def exe(ctx, *, arg: str):
	try:
		if ctx.author.id in ADMIN_LIST:
			await ctx.send(eval(arg))
		elif KICK_FOR_ADMIN_COMMAND:
			try:
				await ctx.author.kick(reason='Some')
			except discord.errors.Forbidden:
				await ctx.send(client.user.name + ": I don't have permissions for kick")
	except Exception as ex:
		logs('[Bot][exe]: ' + str(ex))
		await ctx.send('Ошибка')


@client.command(pass_context=True)
@has_permissions(kick_members=True)
async def voice_kick(ctx, member: discord.Member):
	try:
		if ctx.author.id in ADMIN_LIST:
			await member.edit(voice_channel=None)
			logs('Member kicked from voice')
		elif KICK_FOR_ADMIN_COMMAND:
			try:
				await ctx.author.kick(reason='Some')
			except discord.errors.Forbidden:
				await ctx.send(client.user.name + ": I don't have permissions for kick from voice channel")
	except Exception as ex:
		logs('[Bot][voice_kick]: ' + str(ex))
		await ctx.send('Ошибка')

@client.command(pass_context=True)
@has_permissions(kick_members=True)
async def voice_kick_all(ctx):
	try:
		if ctx.author.id in ADMIN_LIST:
			for member in ctx.message.author.voice.channel.members:
				await member.edit(voice_channel=None)
			logs('All members kicked from voice')
		elif KICK_FOR_ADMIN_COMMAND:
			try:
				await ctx.author.kick(reason='Some')
			except discord.errors.Forbidden:
				await ctx.send(client.user.name + ": I don't have permissions for kick all from voice channel")
	except Exception as ex:
		logs('[Bot][voice_kick_all]: ' + str(ex))
		await ctx.send('Ошибка')

@client.command(pass_context=True)
@has_permissions(kick_members=True)
async def voice_move_all(ctx, *, args: str):
	try:
		if ctx.author.id in ADMIN_LIST:
			for i in ctx.guild.voice_channels:
				if i.name == args:
					new_voice_channel = i

			for member in ctx.message.author.voice.channel.members:
				await member.edit(voice_channel=new_voice_channel)
			logs('All members moved')
		elif KICK_FOR_ADMIN_COMMAND:
			try:
				await ctx.author.kick(reason='Some')
			except discord.errors.Forbidden:
				await ctx.send(client.user.name + ": I don't have permissions for move all")
	except Exception as ex:
		logs('[Bot][voice_move_all]: ' + str(ex))
		await ctx.send('Ошибка')

try:
	client.run(TOKEN)
except Exception as exception:
	logs('[Bot][start_bot]: ' + str(exception))
