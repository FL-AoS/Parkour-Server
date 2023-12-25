"""
- LICENSE: GPL-3.0
- Made by Deleted User

Add a vote map for your server! With this players can start a vote writing
"rtv" on the chat, and voting. Also the map vote will start when the map ends!

Commands:
- /votemap
- /suggestmap
"""

from random import choice
from piqueserver.map import RotationInfo
from piqueserver.commands import command
from twisted.internet.reactor import callLater

RTV_PLAYERS_MIN = 70
LIMIT_SUGGESTION_PER_PLAYER = 1
VOTE_TIMEOUT = 15 # In seconds

@command("votemap", "rtv")
def votemap_cmd(p):
	"""
	Vote for change the map
	/votemap (Alias: /rtv)
	"""
	if not p.already_rtv:
		p.do_rtv()
	else:
		return "You already voted!"
	return "RTV computed successfully! %i Votes left"%p.protocol.rtv_left()

@command("suggestmap", "addmap")
def suggestmap_cmd(p, args=None):
	"""
	Suggest a map for the RTV (Map vote)
	/suggestmap <map name> (Alias: /addmap)
	"""
	if p.suggestions >= LIMIT_SUGGESTION_PER_PLAYER:
		return "You already suggested a map."

	if not args:
		return "Please type the map name when executating the command..."

	if args not in p.protocol.get_map_rotation():
		return "Invalid map name, check the map names with /showrotation"

	try:
		get_map = p.protocol.vote_maps[args]
		return "Map already on the options, please choose another one."
	except KeyError:
		pass

	if len(p.protocol.vote_maps) >= 3:
		to_remove = list(p.protocol.vote_maps)[0]
		del p.protocol.vote_maps[to_remove]

	p.suggestions += 1
	p.protocol.vote_maps[args] = 0
	say(p.protocol, "Map %s added to Vote Options."%args, "Notice")

# We need this in case server not have CustomMessages script
def say(p, msg, _type):
	try:
		p.broadcast_cmsg(msg, _type)
	except:
		p.broadcast_chat(msg)

def apply_script(protocol, connection, config):
	class rtvProtoc(protocol):
		rtv_votes = 0
		vote_maps = {}
		voting = False

		def on_map_change(self, _map):
			self.voting = False
			self.rtv_votes = 0
			self.vote_maps = {}
			for player in self.players.values():
				player.already_voted = False
				player.already_rtv = False
				player.suggestions = 0

			av_maps = self.get_map_rotation()
			while(len(self.vote_maps) < 3 if len(av_maps) > 2 else len(self.vote_maps) != len(av_maps)):
				choosed = choice(av_maps)
				if len(av_maps) > 3:				
					if choosed not in self.vote_maps.keys():
						self.vote_maps[choosed] = 0
				else:
					self.vote_maps[choosed] = 0

			return protocol.on_map_change(self, _map)

		def on_game_end(self):
			self.start_mapvote()

		def start_mapvote(self):
			for player in self.players.values():
				player.already_rtv = True

			self.voting = True
			self.broadcast_votes()
			callLater(VOTE_TIMEOUT, self.end_mapvote)

		def end_mapvote(self):
			map_choosed = max(self.vote_maps, key = self.vote_maps.get)
			say(self, "%s won with %i Votes!"%(map_choosed, self.vote_maps[map_choosed]), "Error")

			self.planned_map = RotationInfo(map_choosed)
			callLater(5, self.advance_rotation)

		def broadcast_votes(self):
			self.broadcast_chat("---------------")
			for i,map_name in enumerate(self.vote_maps):
				self.broadcast_chat("[ %i ] %s (%i Votes)"%(len(self.vote_maps)-i, map_name, self.vote_maps[map_name]))
			self.broadcast_chat("Type the number to vote.")
			self.broadcast_chat("---------------")

		def count_rtv(self):
			self.rtv_votes += 1
			if self.rtv_left() <= 0:
				self.start_mapvote()

		def rtv_left(self):
			percentage = len(self.players)*RTV_PLAYERS_MIN/100
			return percentage-self.rtv_votes


	class rtvConec(connection):
		already_rtv = False
		already_voted = False
		suggestions = 0

		def do_rtv(self):
			self.already_rtv = True
			say(self.protocol, "[RTV] %s voted to advance map (%i Votes left)"%
				(self.printable_name, self.protocol.rtv_left()), "Notice")
			self.protocol.count_rtv()

		def on_chat(self, msg, global_msg):
			if msg.lower() == "rtv" and not self.already_rtv:
				self.do_rtv()

			elif msg.lower() == "rtv" and self.already_rtv:
				self.send_chat("You already voted!")

			elif (msg == "1" or msg == "2" or msg == "3") and self.protocol.voting and not self.already_voted:
				msgInt = int(msg)
				vote_maps = self.protocol.vote_maps
				vote_maps[list(vote_maps)[len(vote_maps)-msgInt]] += 1
				self.protocol.broadcast_votes()
				self.already_voted = True

			return connection.on_chat(self, msg, global_msg)

		def on_disconnect(self):
			if self.already_rtv:
				self.protocol.rtv_votes -= 1

			return connection.on_disconnect(self)

	return rtvProtoc, rtvConec