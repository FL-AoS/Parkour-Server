"""
- LICENSE: GPL-3.0
- Made by sByte

A script for helping with custom messaging (screen messages)
for BetterSpades and OpenSpades.

- How to use?
Put this script on the top of the script list in config.toml,
then the functions "connection.send_cmsg(Message, Type)" and "protocol.broadcast_cmsg(Message, Type)"

Message types:
- Notice
- Status
- Warning
- Error

- Test commands:
/csay Type Message
/cpm Player Type Message
"""
from piqueserver.commands import command, get_player
from pyspades.loaders import Loader
from pyspades.common import encode
from enum import Enum

@command("csay", admin_only=True)
def csay(p, *args):
	if not args:
		return "Usage: /csay MessageType Message"

	p.protocol.broadcast_cmsg(' '.join(args[1:]), args[0])

@command("cpm", admin_only=True)
def cpm(p, *args):
	if not args:
		return "Usage: /cpm Player MessageType Message"
	try:
		player = get_player(p.protocol,args[0])
	except:
		return "Invalid player"
	player.send_cmsg(' '.join(args[2:]), args[1])


class EMsgTypes(Enum):
	Notice = ["N% ", 3]
	Status = ["C% ", 4]
	Warning = ["%% ", 5]
	Error = ["!% ", 6]

class customMsg(Loader):
	id = 17
	text = ""
	msgType = 2

	def read(self, read):
		pass

	def write(self, writer):
		writer.writeByte(self.id, True)
		writer.writeByte(32, True)
		writer.writeByte(self.msgType, True)
		writer.writeString(encode(self.text))

bsMsg = customMsg()
client_supported = ["OpenSpades", "BetterSpades"]

def apply_script(protocol, connection, config):
	class csMsgProtocol(protocol):
		def broadcast_cmsg(self, msg, _type):
			for player in self.players.values():
				player.send_cmsg(msg, _type)

	class csMsgConnection(connection):
		def send_cmsg(self, msg, _type):
			if _type not in EMsgTypes.__members__:
				self.send_chat("(Invalid MessageType) "+msg)
				return
					
			if "client" in self.client_info:
				client = self.client_info["client"]

				getType = EMsgTypes[_type]
				if client not in client_supported:
					self.send_chat(msg)
					return

				elif client == "BetterSpades":
					bsMsg.text = msg
					bsMsg.msgType = getType.value[1]
					self.send_contained(bsMsg)
					return
				self.send_chat(getType.value[0]+msg)

			else:
				self.send_chat(msg)

	return csMsgProtocol, csMsgConnection
