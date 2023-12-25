# reverse invisible by sbyte
# pretty tricky

from piqueserver.commands import command
from pyspades.contained import KillAction, CreatePlayer
from pyspades.constants import FALL_KILL
from pyspades.bytes import ByteWriter
import enet

@command("hideplayers", "hp")
def hideplayers(p):
	"""
	Hide players for you, like a reverse invisible
	/hideplayers or /hp
	"""
	p.reverse_invisible = not p.reverse_invisible

	if p.reverse_invisible:
		p.hide_players()
		return "Players are hidden for you"
	else:
		p.show_players()
		return "Now you can see players again"

def apply_script(protocol, connection, config):
	class rProtocol(protocol):
		def broadcast_contained(self, contained, unsequenced=False, sender=None,
							team=None, save=False, rule=None):
			if unsequenced:
				flags = enet.PACKET_FLAG_UNSEQUENCED
			else:
				flags = enet.PACKET_FLAG_RELIABLE
			writer = ByteWriter()
			contained.write(writer)
			data = bytes(writer)
			packet = enet.Packet(data, flags)
			for player in self.connections.values():
				if player is sender or player.player_id is None:
					continue
				if team is not None and player.team is not team:
					continue
				if rule is not None and not rule(player):
					continue
				if player.saved_loaders is not None:
					if save:
						player.saved_loaders.append(data)
				else:
					if player.reverse_invisible and data[1] != player.player_id:
						if (data[0] == 3 or data[0] == 4  or data[0] == 7  or
							data[0] == 8 or data[0] == 12 or data[0] == 16 or
							data[0] == 28):
							continue

					player.peer.send(0, packet)

	class rInvConnec(connection):
		reverse_invisible = False

		def on_login(self, name):
			create_player = CreatePlayer()
			create_player.player_id = self.player_id
			create_player.name = self.name
			create_player.weapon = self.weapon if self.weapon else 0
			create_player.team = self.team.id

			if self.world_object:
				x,y,z = self.world_object.position.get()
				create_player.x = x
				create_player.y = y
				create_player.z = z
			else:
				create_player.x = 0
				create_player.y = 0
				create_player.z = 0

			for player in self.protocol.players.values():
				if player.reverse_invisible:
					player.send_contained(create_player)
					player.hide_player(self)

			return connection.on_login(self, name)

		def hide_player(self, player):
			kill_action = KillAction()
			kill_action.player_id = player.player_id
			kill_action.killer_id = player.player_id
			kill_action.kill_type = FALL_KILL
			kill_action.respawn_time = -1

			self.send_contained(kill_action)

		def hide_players(self):
			for player in self.protocol.players.values():
				if not player.world_object or player.team.spectator:
					continue

				if player == self:
					continue

				self.hide_player(player)

		def show_players(self):
			for player in self.protocol.players.values():
				if not player.world_object or player.team.spectator:
					continue

				if player == self:
					continue

				x,y,z = player.world_object.position.get()

				create_player = CreatePlayer()
				create_player.player_id = player.player_id
				create_player.name = player.name
				create_player.weapon = player.weapon
				create_player.x = x
				create_player.y = y
				create_player.z = z
				create_player.team = player.team.id

				self.send_contained(create_player)

	return rProtocol, rInvConnec