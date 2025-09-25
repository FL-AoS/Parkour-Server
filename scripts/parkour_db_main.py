"""
Depends on website_api
"""

from piqueserver.commands import command
from piqueserver.config import config
from time import time
import os

def apply_script(protocol, connection, config):
	class pDbProtocol(protocol):
		mapID = None

		def on_map_change(self, _map):
			resp = self.save_parkour_map()

			if not resp:
				print("Error saving/getting map from api")
				return False

			self.mapID = resp["id"]

			return protocol.on_map_change(self, _map)

		def save_record(self, player, ts):
			if player.logged_user_id is None:
				return

			try:
				demo_name = "%i_%i_%i.demo"%(self.mapID,player.logged_user_id,player.joinedtimestamp)

				obj = {
					"mode": "parkour",
					"player_id": player.logged_user_id,
					"map_id": self.mapID,
					"demo_name": demo_name,
					"client_info": player.client_string,
					"time": ts,
					"death_count": player.deathcount,
					"checkpoints": []
				}

				i = 0
				for tms in player.current_times:
					obj["checkpoints"].append({"checkpoint_number":i, "time": tms})

				self.upload_player_highscores(obj)

			except Exception as e:
				print("Error saving score: ", e)

	class pDbConnection(connection):
		pass

	return pDbProtocol, pDbConnection