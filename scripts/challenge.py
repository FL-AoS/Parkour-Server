"""
Parkour 1v1 system made by sByte
"""

from piqueserver.commands import command, get_player
from twisted.internet.reactor import callLater
from math import floor
from time import time

USER_INVALID_TEAM = "[1V1] You need to be in a valid team for 1v1."
USER_ALREADY_IN_CHALLENGE = "[1V1] You is already in a challenge, use /forfeit to resign."
USER_SELF_CHALLENGE = "[1V1] You can't challenge yourself."
INVITED_INVALID_TEAM = "[1V1] This player needs to be in a valid team for 1v1."
INVITED_ALREADY_IN_CHALLENGE = "[1V1] This player is already in a challenge, please wait."

ALREADY_INVITED_PLAYER = "[1V1] You already invited this player, please wait him accept it."
INVITE_EXPIRED = "[1V1] The 1v1 invite expired or he didn't invited you for 1v1."
NOT_IN_CHALLENGE = "[1V1] You isnt in a challenge."
BLOCK_TEAM_CHANGE = "[1V1] You can't change teams while in 1v1, please use /forfeit to resign."

FORFEITED = "[1V1] %s forfeited"
#1V1_WIN = "[1V1] %s WON AGAINST %s WITH %s!"

@command("challenge", "invite", "x1", "1v1")
def challenge(p, player):
	"""
	Challenge someone to an 1v1 race
	/challenge <player id or name>
	"""
	if not p.world_object or p.team.spectator:
		return USER_INVALID_TEAM

	if p.racing_challenge:
		return USER_ALREADY_IN_CHALLENGE

	player = get_player(p.protocol, player)

	if not player.world_object or player.team.spectator:
		return INVITED_INVALID_TEAM

	if p is player:
		return USER_SELF_CHALLENGE

	if player.racing_challenge:
		return INVITED_ALREADY_IN_CHALLENGE

	if player.player_id in p.sent_invites:
		return ALREADY_INVITED_PLAYER

	p.sent_invites.append(player.player_id)

	player.send_chat("[1V1] %s (#%i) CHALLENGED YOU TO 1v1 USE /accept #%i"%(p.printable_name, p.player_id, p.player_id))
	return "[1V1] You succesfuly invited %s"%player.printable_name

@command("accept")
def accept(p, player):
	"""
	Accept someone's else invite
	/accept <player id or name>
	"""
	player = get_player(p.protocol, player)

	if player.racing_challenge:
		return INVITED_ALREADY_IN_CHALLENGE

	if not p.player_id in player.sent_invites:
		return INVITE_EXPIRED

	p.protocol.start_challenge(p, player)
	player.send_chat("%s accepted the invite, challenge is about to begin!"%p.printable_name)
	return "You accepted %s's invite, challenge is about to begin!"%player.printable_name

@command("forfeit")
def forfeit(p):
	"""
	Forfeit a challenge
	/forfeit
	"""
	if not p.racing_challenge:
		return NOT_IN_CHALLENGE

	p.on_forfeit()

#Stole directly from parkour ;)
def get_now_in_ms():
	return round(time()*1000)

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

def apply_script(protocol, connection, config):
	class challengeProtocol(protocol):
		def start_challenge(self, racer1, racer2):
			racer1.setup_race_start(racer2)
			racer2.setup_race_start(racer1)

			self.challenge_countdown(racer1)

		def challenge_countdown(self, racer):
			enemy = racer.racing_enemy

			for i in range(5):
				msg = "[1V1] CHALLENGE STARTING IN %is"%(5-i)
				callLater(i, racer.send_chat, msg)
				callLater(i, enemy.send_chat, msg)

			callLater(5, self.begin_challenge, racer)

		def begin_challenge(self, racer):
			enemy = racer.racing_enemy

			racer.isresetting = True
			enemy.isresetting = True

			racer.challenge_start_ts = get_now_in_ms()
			enemy.challenge_start_ts = get_now_in_ms()

			racer.kill()
			enemy.kill()

		def end_challenge(self, winner, loser):
			f_time = get_formatted_parkour_time(get_now_in_ms()-winner.challenge_start_ts)
			self.broadcast_chat("%s WON 1v1 AGAINST %s IN %s!"%(winner.printable_name, loser.printable_name, f_time))

			winner.clear_variables()
			loser.clear_variables()

			winner.isresetting = True
			loser.isresetting = True

			winner.kill()
			loser.kill()

	class challengeConnection(connection):
		racing_challenge = False
		racing_enemy = None
		sent_invites = []
		challenge_start_ts = 0

		def __init__(self, *args, **argv):
			self.clear_variables()
			return connection.__init__(self, *args, **argv)

		def setup_race_start(self, enemy):
			self.clear_variables()
			self.racing_challenge = True
			self.racing_enemy = enemy

			if self.team.spectator:
				self.set_team(self.protocol.blue_team)

		def on_forfeit(self):
			if self.racing_enemy:
				self.racing_enemy.send_chat(FORFEITED%(self.printable_name))

			self.protocol.end_challenge(self.racing_enemy, self)

		def clear_variables(self):
			self.racing_challenge = False
			self.racing_enemy = None
			self.sent_invites = []
			self.challenge_start_ts = 0

		def on_team_join(self, old_team):
			if self.racing_challenge:
				self.send_chat(BLOCK_TEAM_CHANGE)
				return False

			return connection.on_team_join(self, old_team)

		def on_disconnect(self):
			if self.racing_challenge:
				self.on_forfeit()

			return connection.on_disconnect(self)

		def on_parkour_finish(self, timestamp):
			if self.racing_challenge:
				self.protocol.end_challenge(self, self.racing_enemy)

			return connection.on_parkour_finish(self, timestamp)

	return challengeProtocol, challengeConnection