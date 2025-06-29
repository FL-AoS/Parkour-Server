"""
Depends on shadowmode.py
Depends on parkour_db_main.py
Depends on parkour gamemode
"""
from pyspades.contained import InputData, MapStart, MapChunk, StateData, CTFState, ExistingPlayer, WorldUpdate, ChatMessage
from pyspades.bytes import ByteWriter
import enet
import struct
from pyspades.mapgenerator import ProgressiveMapGenerator
import time

def save_packet(fd, contained, _t):
	bw = ByteWriter()
	contained.write(bw)
	packet = enet.Packet(bytes(bw), enet.PACKET_FLAG_RELIABLE)

	fd.write(struct.pack("fH", _t, len(packet.data)))
	fd.write(packet.data)

def apply_script(protocol, connection, config):
	class demConnec(connection):
		def save_to_demo(self):
			f = open("demos/%i_%i_%i.demo"%(self.protocol.mapID,self.logged_user_id,self.joinedtimestamp), "wb")

			f.write(struct.pack("BB", 1, 3))

			map_data = ProgressiveMapGenerator(self.protocol.map)

			mp_start = MapStart()
			mp_start.size = map_data.get_size()
			save_packet(f, mp_start, 0.0)

			for i in range(35):
				if not map_data.data_left():
					break
				map_ck = MapChunk()
				map_ck.data = map_data.read(8192)
				save_packet(f, map_ck, 0.0)

			blue = self.protocol.blue_team
			green = self.protocol.green_team

			st_data = StateData()
			st_data.player_id = 1
			st_data.fog_color = self.protocol.fog_color
			st_data.team1_color = blue.color
			st_data.team1_name = blue.name
			st_data.team2_color = green.color
			st_data.team2_name = green.name

			blue_base = blue.base
			blue_flag = blue.flag
			green_base = green.base
			green_flag = green.flag
			ctf_data = CTFState()
			ctf_data.cap_limit = self.protocol.max_score
			ctf_data.team1_score = blue.score
			ctf_data.team2_score = green.score

			ctf_data.team1_base_x = blue_base.x
			ctf_data.team1_base_y = blue_base.y
			ctf_data.team1_base_z = blue_base.z

			ctf_data.team2_base_x = green_base.x
			ctf_data.team2_base_y = green_base.y
			ctf_data.team2_base_z = green_base.z

			ctf_data.team1_has_intel = 0
			ctf_data.team2_flag_x = green_flag.x
			ctf_data.team2_flag_y = green_flag.y
			ctf_data.team2_flag_z = green_flag.z
			ctf_data.team2_has_intel = 0
			ctf_data.team1_flag_x = blue_flag.x
			ctf_data.team1_flag_y = blue_flag.y
			ctf_data.team1_flag_z = blue_flag.z

			st_data.state = ctf_data
			save_packet(f, st_data, 0.0)


			ep = ExistingPlayer()
			ep.player_id = 0
			ep.team = 0
			ep.weapon = 0
			ep.tool = 3
			ep.kills = 0
			ep.color = 0xffffffff
			ep.name = self.name

			save_packet(f, ep, 0.0)

			inp_data = InputData()
			inp_data.player_id = 0
			inp_data.up = 0
			inp_data.down = 0
			inp_data.left = 0
			inp_data.right = 0
			inp_data.jump = 0
			inp_data.crouch = 0
			inp_data.sneak = 0
			inp_data.sprint = 0

			for packet in self.shadow_inputs:
				_time, inp = packet

				if inp["type"] == "world_update":
					wu = WorldUpdate()
					wu.items = inp["inputs"]

					save_packet(f, wu, _time)

				elif inp["type"] == "walk":
					up, down, left, right = inp["inputs"]
					inp_data.up = 1 if up else 0
					inp_data.down = 1 if down else 0
					inp_data.left = 1 if left else 0
					inp_data.right = 1 if right else 0

					save_packet(f, inp_data, _time)
				elif inp["type"] == "animation":
					jump, crouch, sneak, sprint = inp["inputs"]
					inp_data.jump = 1 if jump else 0
					inp_data.crouch = 1 if crouch else 0
					inp_data.sneak = 1 if sneak else 0
					inp_data.sprint = 1 if sprint else 0

					save_packet(f, inp_data, _time)

				elif inp["type"] == "checkpoint":
					formatted_time, cp, maxcps = inp["inputs"]

					msg = ChatMessage()
					msg.player_id = 32
					msg.chat_type = 2
					msg.value = "Reached checkpoint %i/%i in: %s"%(cp, maxcps, formatted_time)

					save_packet(f, msg, _time)

				elif inp["type"] == "finish":
					formatted_time = inp["inputs"]

					msg = ChatMessage()
					msg.player_id = 32
					msg.chat_type = 2
					msg.value = "Finished the run in: %s"%(formatted_time)

					save_packet(f, msg, _time)

			f.close()


	return protocol, demConnec