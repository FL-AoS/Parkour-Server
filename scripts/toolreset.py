# reset parkour by tool change ;)
# copy from https://github.com/VierEck/aos-stuff/blob/main/pique/Parkour.py
from piqueserver.commands import command
from pyspades.constants import SPADE_TOOL, BLOCK_TOOL, WEAPON_TOOL, GRENADE_TOOL

@command("resetgesture", "rg")
def res_gesture(c, gesture=None):
	if "spade" in gesture:
		c.parkour_reset_gesture = SPADE_TOOL
	elif "block" in gesture:
		c.parkour_reset_gesture = BLOCK_TOOL
	elif "weap" in gesture:
		c.parkour_reset_gesture = WEAPON_TOOL
	elif "nade" in gesture:
		c.parkour_reset_gesture = GRENADE_TOOL
	else:
		c.parkour_reset_gesture = None
		return "Gesture reset disabled"

	return "Set gesture reset to " + gesture

def apply_script(protocol, connection, config):
	class toolConnec(connection):
		parkour_reset_gesture = None

		def on_tool_set_attempt(self, tool):
			if self.parkour_reset_gesture is tool:
				self.isresetting = True
				self.kill()

				return False

			return connection.on_tool_set_attempt(self, tool)

	return protocol, toolConnec