"""
made by sByte

Dependencies:
- Parkour Gamemode
- Custom Messages
"""
from piqueserver.commands import command
from pyspades.contained import WeaponReload
from time import time

@command("timer")
def timer(p):
	p.timer = not p.timer
	msg = "enabled" if p.timer else "disabled"

	return "Timer is %s now!"%(msg)

def apply_script(protocol, connection, config):
	class timeProtocol(protocol):
		last_update_timer = 0

		def on_world_update(self):
			if time()-self.last_update_timer >= 1:
				for player in self.players.values():
					if player.timer:
						player.update_timer()

				self.last_update_timer = time()

			return protocol.on_world_update(self)

	class timeConnec(connection):
		timer = True

		def update_timer(self):
			if not self.timer or self.local:
				return

			imdumbaf = time()-(self.joinedtimestamp/1000)
			secs = imdumbaf%60
			mins = imdumbaf/60

			if not "client" in self.client_info:
				wr = WeaponReload()
				wr.clip_ammo = mins
				wr.reserve_ammo = secs if secs > 1 else 1 # stop auto switch after death
				wr.player_id = self.player_id
				self.send_contained(wr)
			else:
				mins_msg = "%i"%mins
				secs_msg = "%i"%secs

				if mins < 10:
					mins_msg = "0%i"%(mins)

				if secs < 10:
					secs_msg = "0%i"%(secs)

				self.send_chat_status("Current Time")
				self.send_chat_status("%s:%s"%(mins_msg, secs_msg))

	return timeProtocol, timeConnec