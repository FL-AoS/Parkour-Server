# reset parkour by tool change ;)
# copy from https://github.com/VierEck/aos-stuff/blob/main/pique/Parkour.py
from piqueserver.commands import command
from pyspades.constants import SPADE_TOOL, BLOCK_TOOL, WEAPON_TOOL, GRENADE_TOOL
from pyspades.contained import WeaponReload
from pyspades.packet import register_packet_handler

@command("resetgesture", "rg")
def res_gesture(c, gesture=None):
	if c.parkour_reset_gesture is not None and gesture is None:
		c.parkour_reset_gesture = None
		return "Gesture reset disabled"

	elif gesture is None:
		return "Available gestures: Spade, Block, Weapon, Grenade and Reload"

	gesture = gesture.lower()

	if "spade" in gesture:
		c.parkour_reset_gesture = SPADE_TOOL
	elif "block" in gesture:
		c.parkour_reset_gesture = BLOCK_TOOL
	elif "weap" in gesture:
		c.parkour_reset_gesture = WEAPON_TOOL
		gesture = "weapon"
	elif "gren" in gesture or "nade" in gesture:
		c.parkour_reset_gesture = GRENADE_TOOL
		gesture = "grenade"
	elif "r" in gesture:
		c.parkour_reset_gesture = 5
		send_low_ammo(c)
		gesture = "reload"
	else:
		return "Available gestures: Spade, Block, Weapon, Grenade and Reload"

	return "Set gesture reset to " + gesture

def send_low_ammo(p):
	wr = WeaponReload()
	wr.clip_ammo = 4
	wr.reserve_ammo = 10
	wr.player_id = p.player_id

	p.send_contained(wr)

def apply_script(protocol, connection, config):
	class toolConnec(connection):
		parkour_reset_gesture = None

		@register_packet_handler(WeaponReload)
		def on_reload_recieved(self, contained):
			if self.parkour_reset_gesture == 5:
				self.isresetting = True
				self.kill()

				return False

			return connection.on_reload_recieved(self, contained)

		def on_spawn(self, pos):
			if self.parkour_reset_gesture == 5:
				send_low_ammo(self)

			return connection.on_spawn(self, pos)

		def on_tool_set_attempt(self, tool):
			if self.parkour_reset_gesture is tool:
				self.isresetting = True
				self.kill()

				return False

			return connection.on_tool_set_attempt(self, tool)

	return protocol, toolConnec