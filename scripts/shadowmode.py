"""
ShadowMode made by sByte
"""

from pyspades.contained import InputData, WorldUpdate, CreatePlayer
from pyspades.constants import RIFLE_WEAPON
from piqueserver.commands import command
from enet import Address
from time import time

@command("shadowmode", admin_only=True)
def shadowmodecmd(p):
	p.shadow_mode = not p.shadow_mode

	if not p.shadow_mode:
		p.protocol.exec_shadow(p)
		p.max_items = len(p.shadow_inputs)
	else:
		p.start_shadow_mode = time()
		p.start_position = p.world_object.position.get()

	return "Shadow mode changed to: %s"%p.shadow_mode


class LocalPeer:
	# address = Address(None, 0)
	address = Address(b"localhost", 32886)
	roundTripTime = 0.0

	def send(self, *arg, **kw):
		pass

	def reset(self):
		pass

def apply_script(protocol, connection, config):
	class shadowProtocol(protocol):
		shadow_player = None
		started_new_shadow = 0
		current_input = 0

		def add_shadow(self, name, inputs):
			self.started_new_shadow = time()
			self.shadow_player = self.connection_class(self, None)

			self.shadow_player.name = name
			self.shadow_player.shadow_join()

			self.shadow_player.shadow_inputs = inputs
			self.shadow_player.shadow_mode = False

		def on_world_update(self):
			if self.shadow_player is not None:
				player = self.shadow_player

				"""
				if player.max_items == len(player.shadow_inputs):
					self.started_new_shadow = time()
					player.ShadowClass = self.connection_class(self, None)
					player.ShadowClass.shadow_join()
				"""

				if self.current_input >= len(player.shadow_inputs):
					self.started_new_shadow = time()
					self.current_input = 0

				ts, obj = player.shadow_inputs[self.current_input]

				if time()-self.started_new_shadow>=ts:
					player.handle_shadow(obj)
					self.current_input += 1

			return protocol.on_world_update(self)

		def exec_shadow(self, current_player):
			self.shadow_players.append(current_player)

	class shadowConnection(connection):
		shadow_mode = False
		start_shadow_mode = 0

		shadow_inputs = []
		local = False

		def __init__(self, protocol, peer):
			if peer is not None:
				connection.__init__(self, protocol, peer)
				return

			self.local = True
			connection.__init__(self, protocol, LocalPeer())
			self.on_connect()
			# ~ self.saved_loaders = None
			self._send_connection_data()
			self.send_map()

		def handle_shadow(self, obj):
			types = {
				"animation": self.handle_shadowanim,
				"walk": self.handle_shadowwalk,
				"orientation": self.handle_shadowori,
				"position": self.handle_shadowpos,
				"world_update": self.handle_wu,
				"checkpoint": self.handle_checkpoint,
				"finish": self.handle_finish
			}

			types[obj["type"]](obj["inputs"])

		def handle_shadowanim(self, obj):
			jump, crouch, sneak, sprint = obj
			self.world_object.set_animation(jump, crouch, sneak, sprint)
			self.world_object.set_crouch(crouch)

			self.send_shadowinputs()

		def handle_wu(self, obj):
			pass

		def handle_checkpoint(self, obj):
			pass

		def handle_finish(self, obj):
			pass

		def handle_shadowwalk(self, obj):
			self.world_object.set_walk(*obj)
			self.send_shadowinputs()

		def handle_shadowori(self, obj):
			self.world_object.set_orientation(*obj)

		def handle_shadowpos(self, obj):
			x,y,z = obj
			self.world_object.set_position(x,y,z)

		def send_shadowinputs(self):
			obj = self.world_object

			inp_data = InputData()
			inp_data.player_id = self.player_id
			inp_data.jump = obj.jump
			inp_data.crouch = obj.crouch
			inp_data.sneak = obj.sneak
			inp_data.sprint = obj.sprint
			inp_data.up = obj.up
			inp_data.right = obj.right
			inp_data.left = obj.left
			inp_data.down = obj.down

			self.protocol.broadcast_contained(inp_data)

		def shadow_join(self):
			self.team = self.protocol.green_team
			self.set_weapon(RIFLE_WEAPON, True)
			self.protocol.players[self.player_id] = self
			self.on_login(self.name)
			self.spawn()

		def on_animation_update(self, jump, crouch, sneak, sprint):
			if self.shadow_mode:
				self.shadow_inputs.append((time()-self.start_shadow_mode, {
					"type": "animation",
					"inputs": (jump, crouch, sneak, sprint)
				}))
			return connection.on_animation_update(self, jump, crouch, sneak, sprint)

		def on_walk_update(self, up, down, left, right):
			if self.shadow_mode:
				self.shadow_inputs.append((time()-self.start_shadow_mode, {
					"type": "walk",
					"inputs": (up, down, left, right)
				}))
			return connection.on_walk_update(self, up, down, left, right)

		def on_orientation_update(self, x, y, z):
			if self.shadow_mode:
				self.shadow_inputs.append((time()-self.start_shadow_mode, {
					"type": "orientation",
					"inputs": (x, y, z)
				}))
			return connection.on_orientation_update(self, x, y, z)

		def on_position_update(self):
			if self.shadow_mode:
				x,y,z = self.world_object.position.get()
				self.shadow_inputs.append((time()-self.start_shadow_mode, {
					"type": "position",
					"inputs": (x, y, z)
				}))
			return connection.on_position_update(self)

		def save_world_update(self):
			if self.shadow_mode:
				self.shadow_inputs.append((time()-self.start_shadow_mode, {
					"type": "world_update",
					"inputs": [(self.world_object.position.get(), self.world_object.orientation.get())]
				}))

		def save_checkpoint_reach(self, formatted_time, cp, maxcps):
			if self.shadow_mode:
				self.shadow_inputs.append((time()-self.start_shadow_mode, {
					"type": "checkpoint",
					"inputs": (formatted_time, cp, maxcps)
				}))

		def save_finish_time(self, formatted_time):
			if self.shadow_mode:
				self.shadow_inputs.append((time()-self.start_shadow_mode, {
					"type": "finish",
					"inputs": (formatted_time)
				}))

		def disconnect(self, data=0):
			if not self.local:
				return connection.disconnect(self)
			if self.disconnected:
				return

			self.protocol.current_input = 0
			self.protocol.shadow_player = None
			self.disconnected = True
			self.on_disconnect()

	return shadowProtocol, shadowConnection