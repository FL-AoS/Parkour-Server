from pyspades.contained import PositionData
from pyspades.packet import register_packet_handler
from time import time
from math import fabs

MESSAGE_NOCLIP = "Looks someone is trying to hack here :DDDDDDDDDDDDD, if you believe this is a mistake, please report on discord"
NOCLIP_BLOCKS_TELEPORT = 8 #blocks
NOCLIP_TELEPORT_TIME = 3 # sec

MESSAGE_WATERGLITCH = "Looks like your run is using the water glitch, if you believe thats a mistake, please report on discord."
CATEGORY_AS_WATERGLITCHER_TIME = 3 #sec

def apply_script(protocol, connection, config):
	class categoryConnec(connection):
		start_water_time = 0
		is_onwater = False

		water_glitcher = False
		nocliper = False

		def on_kill(self, killer, _type, grenade):
			if self.isresetting:
				self.start_water_time = 0
				self.is_onwater = False

				self.water_glitcher = False

			return connection.on_kill(self, killer, _type, grenade)

		def check_waterglitch(self):
			if self.water_glitcher:
				return

			x,y,z = self.world_object.position.get()
			real_pos = z+2 if not self.world_object.crouch else z+1
			if real_pos > 62 and self.is_onwater == False:
				self.start_water_time = time()
				self.is_onwater = True
				self.send_chat("Its water time, Z: %i"%z)

			elif real_pos < 62 and self.is_onwater == True and (
				time()-self.start_water_time>=CATEGORY_AS_WATERGLITCHER_TIME
			 ):
				self.is_onwater = False
				self.start_water_time = 0
				self.water_glitcher = True
			elif real_pos<62 and self.is_onwater == True:
				self.is_onwater = False
				self.start_water_time = 0

			if self.water_glitcher:
				self.send_chat(MESSAGE_WATERGLITCH)

		@register_packet_handler(PositionData)
		def on_position_update_recieved(self, contained):
			if self.local or not self.world_object or self.nocliper:
				return connection.on_position_update_recieved(self, contained)				

			if not self.last_position_update:
				return connection.on_position_update_recieved(self, contained)

			if time()-self.last_position_update > NOCLIP_TELEPORT_TIME:
				return connection.on_position_update_recieved(self, contained)

			xC, yC, zC = self.world_object.position.get()

			if fabs(contained.x-xC) > NOCLIP_BLOCKS_TELEPORT:
				self.nocliper = True

			if self.nocliper:
				self.send_chat(MESSAGE_NOCLIP)

			return connection.on_position_update_recieved(self, contained)


	return protocol, categoryConnec