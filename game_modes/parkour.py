"""
parkour.py by IAmYourFriend https://twitter.com/1AmYF

parkour.py is a parkour gamemode with highscores. Players spawn on the same
team at the same location and have to make it to their base to complete the
parkour. Example: https://youtu.be/CIvmWNBpfi8

Setup:

	Set game_mode in your server config to "parkour" and add parkour maps to the
	rotation.

	To create a new parkour map, map txt metadata is required. Example:

		extensions = {
			'water_damage' : 100,
			'parkour_start' : (127, 256, 50),
			'parkour_end' : (382, 256, 50),
			'parkour_checkpoints' : [(187, 256, 50), (240, 256, 39), (289, 256, 50)]
		}

	'parkour_start' marks the coordinate for spawn, 'parkour_end' for the base
	location. 'parkour_checkpoints' is optional. If used, and a player dies during
	the parkour, he will respawn at the closest checkpoint coordinate behind him
	(the parkour direction needs to be from left to right on the map view).

Config Options:

	[parkour]
	# Every parkour completion will be saved into a csv file and the top scores will
	# be listed with the /highscore command (the csv file will be written into the
	# map folder as mapname_scores.csv).
	save_highscores = true

	# How many of the top scores to show when using the /highscore command.
	show_scores = 10

Commands:

	/highscore
		List the top highscores (if enabled).
	/reset
		Reset your time/score and retry the parkour from start.


Customizations by sByte:
- ~~SQLite3 database~~ Mariadb database
- Practice mode
- ShadowMode support (custom)
- Timer (custom, optional)
- on_parkour_finish event (depends on parkour api)
- Parkour categorizer (custom, WIP)
- support for 3d checkpoints with ext: parkour_3d_checkpoints (bool) & parkour_checkpoints_size (tuple)
"""

import time
import operator
from pyspades.constants import *
from pyspades.collision import vector_collision
from piqueserver.commands import command
from piqueserver.config import config
from math import floor
import os.path
from twisted.internet.reactor import callLater
import asyncio

PARKOUR_CONFIG = config.section("parkour")
SAVE_HIGHSCORES = PARKOUR_CONFIG.option("save_highscores", default=True, cast=bool)
SHOW_SCORES = PARKOUR_CONFIG.option("show_scores", default=10, cast=int)

HIDE_COORD = (0, 0, 63)

def get_shadow_filename(connection):
	return (os.path.join(config.config_dir, "maps",
			connection.protocol.map_info.rot_info.name + "_shadowinputs.txt"))

def get_shadow_filename_pro(protocol):
	return (os.path.join(config.config_dir, "maps",
			protocol.map_info.rot_info.name + "_shadowinputs.txt"))
@command()
def k(p):
	p.kill()

@command()
def highscore(connection):
	"""
	List the top highscores
	/highscore
	"""

	displayscores = connection.protocol.get_top_ten()

	i = 1
	strscores = []
	for displayvalues in displayscores:
		if i > 10:
			break

		username = displayvalues[1]
		f_time = get_formatted_parkour_time(displayvalues[3])
		deaths = displayvalues[4]

		place = str(i) + ". "
		if i < 10:
			place += " "
		strscores.append(place + str(username) + "  (" + f_time +
						 " mins, deaths: " + str(deaths) + ")")
		i += 1


	connection.send_lines(strscores)

@command("reset", "r")
def reset(connection):
	"""
	Reset your time/score and retry the parkour from start
	/reset
	"""
	if connection.team is connection.protocol.blue_team:
		connection.isresetting = True
		connection.kill()

@command("practicehelp")
def practicehelp(p):
	lines = [
		"Use /practice to join in practice mode or leave from it.",
		"Use /setrespawn to set a custom respawn.",
		"Use /nextcp to teleport between checkpoints.",
		"Use /pfly to enable fly mode."
	]

	p.send_lines(lines)

@command("practicemode", "practice")
def practicemode(p):
	if not p.world_object:
		return "Looks like you isnt in the world, please join in a team."

	p.practicemode = not p.practicemode
	if p.practicemode:
		p.send_chat("You entered in the practice mode.")
		return "Use /practicehelp to understand how to use this."
	else:
		p.practice_respawn = None
		p.fly = False
		p.isresetting = True
		p.kill()

	return "You left from practice mode."

@command("pfly")
def pfly(p):
	if not p.practicemode:
		return "You need to be in practicemode to use this, check /practicehelp"

	if not p.world_object:
		return "Looks like you isnt in the world, please join in a team."

	p.fly = not p.fly

	message = 'now flying' if p.fly else 'no longer flying'
	p.send_chat("You're %s" % message)

@command("setrespawn")
def setrespawn(p):
	if not p.practicemode:
		return "You need to be in practicemode to use this, check /practicehelp"

	if not p.world_object:
		return "Looks like you isnt in the world, please join in a team."

	if p.practice_respawn is not None:
		p.practice_respawn = None
		return "Respawn removed, now you is respawning on checkpoints."

	x,y,z = p.world_object.position.get()
	x=int(x)
	y=int(y)
	z=int(z)

	p.practice_respawn = (x,y,z)
	p.set_location((x,y,z))

	return "You setted your respawn to (%i,%i,%i)"%(x,y,z)

@command("nextcheckpoint", "nextcp")
def nextcheckpoint(p):
	if not p.practicemode:
		return "You need to be in practicemode to use this, check /practicehelp"

	if not p.world_object:
		return "Looks like you isnt in the world, please join in a team."

	p.reachedcheckpoint += 1

	if p.reachedcheckpoint >= len(p.protocol.map_info.extensions["parkour_checkpoints"]):
		p.reachedcheckpoint = 0

	x,y,z = p.protocol.map_info.extensions["parkour_checkpoints"][p.reachedcheckpoint]

	p.set_location((x,y,z))
	return "Advanced to checkpoint: %i"%(p.reachedcheckpoint)

async def checking_loop(protocol):
	last_update_network = 0
	while True:
		try:
			if time.time()-last_update_network >= 1/20:
				protocol.update_network()
				protocol.on_world_update()
				last_update_network = time.time()

			player_list = list(protocol.players.values())
			for player in player_list:
				if player.local:
					continue

				if not player.world_object:
					continue

				if player.team.id == -1 or player.team.id == 1:
					continue

				if player.practicemode:
					continue

				if player.isresetting:
					continue

				if vector_collision(player.world_object.position, player.team.base) or vector_collision(player.world_object.position, player.team.other.base):
					player.check_refill()

				if "parkour_3d_checkpoints" in protocol.map_info.extensions and protocol.map_info.extensions["parkour_3d_checkpoints"]:
					checkpoints = protocol.map_info.extensions["parkour_checkpoints"]
					checkpoints_size = protocol.map_info.extensions["parkour_checkpoints_size"]

					x, y, z = player.world_object.position.get()
					index = player.reachedcheckpoint
					maxCps = len(checkpoints)

					if index < maxCps:
						xCp, yCp, zCp = checkpoints[index]
						xCs, yCs, zCs = checkpoints_size[index]

						if ((x >= xCp and x <= xCp+xCs) and (y >= yCp and y <= yCp+yCs) and (z <= zCp and z >= zCp-zCs)):
							player.current_times.append(get_now_in_ms() - player.joinedtimestamp)
							time_msg = "Time %s"%(get_formatted_parkour_time(player.current_times[player.reachedcheckpoint]))

							if len(player.pb_times) > 0:
								time_msg += " - PB: %s"%(get_formatted_parkour_time(player.pb_times[player.reachedcheckpoint]))

							if len(player.last_run_times) > player.reachedcheckpoint:
								time_msg += " - Last: %s"%(get_formatted_parkour_time(player.last_run_times[player.reachedcheckpoint]))

							player.reachedcheckpoint += 1
							player.send_chat("You reached checkpoint %i/%i!"%(player.reachedcheckpoint, maxCps))
							player.send_chat_warning(time_msg)

							if player.reachedcheckpoint == maxCps:
								player.send_chat("FINISH!!!")


				player.check_waterglitch()
		except Exception as e:
			print("Error in check loop: ",e)

		await asyncio.sleep(0.001)

def get_now_in_ms():
	return round(time.time()*1000)


def get_formatted_parkour_time(completedms):
	completedformatmin = str(int(floor(completedms / 60 / 1000)))
	if len(completedformatmin) == 1:
		completedformatmin = "0" + completedformatmin

	completedformatsec = str(int(completedms/1000 % 60))
	if len(completedformatsec) == 1:
		completedformatsec = "0" + completedformatsec

	completedformatms = str(int(completedms % 1000))
	if len(completedformatms) == 1:
		completedformatms = "0"+completedformatms

	return completedformatmin + ":" + completedformatsec + ":" + completedformatms


def reset_player_stats(self):
	self.joinedtimestamp = get_now_in_ms()
	self.completedparkour = False
	self.reachedcheckpoint = 0
	self.deathcount = 0

	if not self.local:
		self.shadow_inputs = []
		self.shadow_mode = True
		self.start_shadow_mode = time.time()

ev_loop = asyncio.get_event_loop()
def apply_script(protocol, connection, config):
	class ParkourConnection(connection):
		joinedtimestamp = None
		completedparkour = False
		reachedcheckpoint = 0
		deathcount = 0
		isresetting = False

		practicemode = False
		practice_respawn = None

		current_times = []
		last_run_times = []
		pb_times = []
		pb_time = 0

		def shadowinputSave(self, newtime):
			cansaveinputs = False

			if not os.path.exists(get_shadow_filename(self)):
				cansaveinputs = True

			if not cansaveinputs:
				currentscore = open(get_shadow_filename(self), "r")
				currentscore_i = int(currentscore.readline())
				if newtime<currentscore_i:
					cansaveinputs = True

				currentscore.close()

			if not cansaveinputs:
				return

			f = open(get_shadow_filename(self), "w")
			stringtowrite = ""

			stringtowrite += "%i\n"%newtime
			for inputr in self.shadow_inputs:
				stringtowrite += "%s\n"%str(inputr)

			f.write(stringtowrite)
			f.close()

			self.protocol.spawn_shadow_runner()

		def on_team_join(self, team):
			if team is self.protocol.blue_team:
				reset_player_stats(self)
			return connection.on_team_join(self, team)

		def on_flag_take(self):
			return False

		def on_spawn_location(self, pos):
			if self.team is self.protocol.blue_team and self.practice_respawn is None:
				if self.isresetting:
					self.last_run_times = self.current_times
					self.current_times = []

					reset_player_stats(self)
				self.isresetting = False
				ext = self.protocol.map_info.extensions
				if self.reachedcheckpoint > 0:
					if "parkour_3d_checkpoints" in ext and ext["parkour_3d_checkpoints"]:
						x,y,z = ext["parkour_checkpoints"][self.reachedcheckpoint-1]
						xs,ys,zs = ext["parkour_checkpoints_size"][self.reachedcheckpoint-1]

						return (x+xs/2, y+ys/2, z-1)
					else:
						return ext["parkour_checkpoints"][self.reachedcheckpoint - 1]
				else:
					reset_player_stats(self)
					return ext["parkour_start"]

			elif self.practicemode and self.practice_respawn is not None:
				return self.practice_respawn

			return connection.on_spawn_location(self, pos)

		def on_kill(self, killer, _type, grenade):
			if self.team is self.protocol.blue_team and not self.isresetting:
				self.deathcount += 1
				if "parkour_checkpoints" in self.protocol.map_info.extensions and "parkour_3d_checkpoints" not in self.protocol.map_info.extensions:
					checkpoints = self.protocol.map_info.extensions["parkour_checkpoints"]
					i = len(checkpoints)
					self.reachedcheckpoint = 0
					for cp in reversed(checkpoints):
						if self.world_object.position.x >= cp[0]:
							self.reachedcheckpoint = i
							break
						i -= 1
			return connection.on_kill(self, killer, _type, grenade)

		def on_refill(self):
			if "parkour_3d_checkpoints" in self.protocol.map_info.extensions and self.protocol.map_info.extensions["parkour_3d_checkpoints"]:
				if self.reachedcheckpoint < len(self.protocol.map_info.extensions["parkour_checkpoints"]):
					self.send_chat("You need to reach all checkpoints in order to finish")

					return connection.on_refill(self)

			if self.team is self.protocol.blue_team and not self.completedparkour and not self.practicemode:
				self.completedparkour = True
				if self.joinedtimestamp is not None:
					ts = get_now_in_ms() - self.joinedtimestamp
					displaytime = get_formatted_parkour_time(ts)
					msg = "Congratulations, %s completed the parkour! Stats: %s mins, %s deaths"

					if self.pb_time == 0 or ts < self.pb_time:
						msg+=" (PERSONAL BEST!!)"
						self.pb_time = ts
						self.pb_times = self.current_times

					completedmessage = msg % (self.name, displaytime, self.deathcount)
					self.protocol.broadcast_chat(completedmessage)
					self.protocol.irc_say(completedmessage)

					self.on_parkour_finish(ts)

					if SAVE_HIGHSCORES.get() and self.logged_user_id is not None:
						self.protocol.save_record(self, ts)
						self.shadowinputSave(ts)

					if self.logged_user_id is None:
						self.send_chat("To save your scores on /highscore, please use /register or /login")

					if self.team is self.protocol.blue_team:
						self.isresetting = True
						self.kill()
			elif self.practicemode:
				self.send_chat("You is on practice mode, you cant save your score.")

			return connection.on_refill(self)

		def on_disconnect(self):
			if self.team is self.protocol.blue_team and not self.completedparkour:
				if self.joinedtimestamp is not None:
					displaytime = get_formatted_parkour_time(get_now_in_ms() -
															 self.joinedtimestamp)
					msg = "%s ragequit after %s mins, %s deaths"
					failmessage = msg % (self.name, displaytime, self.deathcount)
					self.protocol.broadcast_chat(failmessage)
					self.protocol.irc_say(failmessage)
			connection.on_disconnect(self)

		def check_speedhack(self, x,y,z, distance=None):
			return True

	class ParkourProtocol(protocol):
		game_mode = CTF_MODE
		parkour_loop = None

		def __init__(self, *args, **kwargs):
			if self.parkour_loop is None:
				self.parkour_loop = ev_loop.create_task(checking_loop(self))

			return protocol.__init__(self, *args, **kwargs)

		def on_base_spawn(self, x, y, z, base, entity_id):
			if entity_id == BLUE_BASE:
				return self.map_info.extensions["parkour_end"]
			return HIDE_COORD

		def on_flag_spawn(self, x, y, z, flag, entity_id):
			return HIDE_COORD

		def on_map_change(self, _map):
			extensions = self.map_info.extensions
			for must_have in ("parkour_start", "parkour_end"):
				if must_have not in extensions:
					raise Exception("Missing parkour map metadata: %s" % must_have)
			self.green_team.locked = True
			self.balanced_teams = 0
			self.building = False
			self.fall_damage = False
			self.killing = False
			self.spawn_shadow_runner()

			return protocol.on_map_change(self, _map)

		def spawn_shadow_runner(self):
			if self.shadow_player is not None:
				self.shadow_player.disconnect()

			if os.path.exists(get_shadow_filename_pro(self)):
				f = open(get_shadow_filename_pro(self), 'r')
				content = f.read().split("\n")
				timer = get_formatted_parkour_time(int(content.pop(0)))

				real_content = []
				del content[-1]

				for line in content:
					real_content.append(eval(line))

				callLater(2, self.add_shadow,timer, real_content)
				f.close()

	return ParkourProtocol, ParkourConnection
