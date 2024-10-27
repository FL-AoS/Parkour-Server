def apply_script(protocol, connection, config):
	class papiConnec(connection):
		def on_parkour_finish(self, timestamp):
			pass

	return protocol, papiConnec