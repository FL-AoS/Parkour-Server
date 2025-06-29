"""
Depends on mariadb


Config:
[parkour_db]
user = "aos_u"
password = "123"
host = "127.0.0.1"
port = 3306
database = "parkour"
"""

from piqueserver.commands import command
from piqueserver.config import config
from time import time
import sqlite3
import os
import mariadb

PARKOUR_DB_CFG = config.section("parkour_db")

PARKOUR_DB_USER = PARKOUR_DB_CFG.option("user").get()
PARKOUR_DB_PASSWORD = PARKOUR_DB_CFG.option("password").get()
PARKOUR_DB_HOST = PARKOUR_DB_CFG.option("host").get()
PARKOUR_DB_PORT = PARKOUR_DB_CFG.option("port").get()
PARKOUR_DB_DB = PARKOUR_DB_CFG.option("database").get()

@command("register")
def register(p, user=None, password=None):
	if not p.admin:
		p.send_chat("Want to register? Join on our discord and get the Parkour role.")
		p.send_chat("https://discord.gg/BJkMA49UQt")
	else:
		if user is None:
			return "You need to specify an user to be registered."

		if password is None:
			return "You need to specify a password to be registered to '%s' user."%(user)

		p.protocol.dbCursor.execute("""
			INSERT INTO players (login, password, last_ip) VALUES (?, ?, ?)
		""", (user, password, '0.0.0.0'))
		
		p.protocol.dbConnection.commit()

		return "Successfuly registered User '%s', with password '%s'. Please ask the user to use /changepassword when login."%(user, password)

@command("changepassword")
def changepassword(p, oldpass=None, newpass=None):
	if p.logged_user_id is None:
		return "You need to login to change your password."

	if oldpass is None or newpass is None:
		return "Wrong usage, please use: /changepassword <old_password> <new_password>"

	p.protocol.dbCursor.execute("""
		SELECT * FROM players
		WHERE id=? and password=?
	""", (p.logged_user_id,oldpass))
	check = p.protocol.dbCursor.fetchone()

	if not check:
		return "Wrong password, please try again."

	p.protocol.dbCursor.execute("""
		UPDATE players
		SET password=?
		WHERE id=?
	""", (newpass,p.logged_user_id))
	p.protocol.dbConnection.commit()

	return "Your password changed to %s"%(newpass)

@command("login")
def login(p, user=None, passw=None):
	if not passw:
		for user_type, passwords in p.protocol.passwords.items():
			#yes isnt actually the user, but yes
			if user in passwords:
				if user_type in p.user_types:
					return "You're already logged in as %s" % user_type
				return p.on_user_login(user_type, True)

		if p.login_retries is None:
			p.login_retries = p.protocol.login_retries - 1
		else:
			p.login_retries -= 1

		if not p.login_retries:
			p.kick('Ran out of login attempts')
			return

		return 'Use /login <user> <password>. If you not has an account use /register'

	p.protocol.dbCursor.execute("SELECT * FROM players WHERE login=? and password=?", (user, passw))
	loginfos = p.protocol.dbCursor.fetchone()

	if not loginfos:
		return "Wrong infos for login..."

	p.protocol.dbCursor.execute("""
		UPDATE players
		SET last_ip=?
		WHERE id=?
	""", (p.address[0],loginfos[0]))
	p.protocol.dbConnection.commit()

	p.logged_user_id = loginfos[0]

	return "Welcome back %s!"%(user)

def create_player_table(protocol):
	protocol.dbCursor.execute("""
		CREATE TABLE IF NOT EXISTS players
		(id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
		 login VARCHAR(255) NOT NULL UNIQUE,
		 password VARCHAR(255) NOT NULL,
		 last_ip VARCHAR(255) DEFAULT NULL,
		 created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
		 updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP()
		);
	""")

	protocol.dbConnection.commit()

def create_map_table(protocol):
	protocol.dbCursor.execute("""
		CREATE TABLE IF NOT EXISTS prk_maps
		(id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
		 name VARCHAR(255) NOT NULL UNIQUE,
		 creator VARCHAR(255) NOT NULL,
		 description VARCHAR(255) NOT NULL,
		 type VARCHAR(255) NOT NULL,
		 checkpoints INT(11) NOT NULL,
		 created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
		 updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP()
		);
	""")

	protocol.dbConnection.commit()

def create_run_history_table(protocol):
	protocol.dbCursor.execute("""
		CREATE TABLE IF NOT EXISTS prk_run_history
		(id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
		 player_id BIGINT(20) UNSIGNED NOT NULL REFERENCES players(id),
		 map_id BIGINT(20) UNSIGNED NOT NULL REFERENCES prk_maps(id),
		 demo_url VARCHAR(255) NOT NULL,
		 client_info VARCHAR(255) NOT NULL,
		 time INT(11) NOT NULL,
		 death_count INT(11) NOT NULL,
		 created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
		 updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP()
		);
	""")

	protocol.dbConnection.commit()

def create_checkpoint_history_table(protocol):
	protocol.dbCursor.execute("""
		CREATE TABLE IF NOT EXISTS prk_checkpoint_history
		(id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
		 checkpoint INT(11) NOT NULL,
		 run_id BIGINT(20) UNSIGNED NOT NULL REFERENCES prk_run_history(id),
		 time INT(11) NOT NULL,
		 created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
		 updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP()
		);
	""")

	protocol.dbConnection.commit()

def apply_script(protocol, connection, config):
	class pDbProtocol(protocol):
		dbConnection = None
		dbCursor = None
		mapID = None

		def __init__(self, *args, **kwargs):
			try:
				self.dbConnection = mariadb.connect(
					user=PARKOUR_DB_USER,
					password=PARKOUR_DB_PASSWORD,
					host=PARKOUR_DB_HOST,
					port=PARKOUR_DB_PORT,
					database=PARKOUR_DB_DB
				)
			except mariadb.Error as e:
				print("Error on database connection, disabling...", e)
				self.dbConnection = None

				return protocol.__init__(self, *args, **kwargs)

			self.dbCursor = self.dbConnection.cursor()

			create_player_table(self)
			create_map_table(self)
			create_run_history_table(self)
			create_checkpoint_history_table(self)

			return protocol.__init__(self, *args, **kwargs)

		def on_map_change(self, _map):
			info = self.map_info

			_type = "line"
			if (info.extensions and "parkour_3d_checkpoints" in info.extensions):
				_type = "checkpoint"

			self.dbCursor.execute("SELECT id FROM prk_maps WHERE name=?", (info.name,))
			res = self.dbCursor.fetchone()

			if res is None:
				try:
					self.dbCursor.execute("INSERT INTO prk_maps (name, creator, description, type, checkpoints) VALUES (?, ?, ?, ?, ?)",
						(info.name, info.author, info.description, _type, len(info.extensions["parkour_checkpoints"])))

					self.dbConnection.commit()

					self.dbCursor.execute("SELECT id FROM prk_maps WHERE name=?", (info.name,))
					self.mapID = self.dbCursor.fetchone()[0]

				except mariadb.Error as e:
					print("Mariadb error:", e)
			else:
				self.mapID = res[0]

			return protocol.on_map_change(self, _map)

		def save_record(self, player, ts):
			if player.logged_user_id is None:
				return

			try:
				demo_name = "%i_%i_%i.demo"%(self.mapID,player.logged_user_id,player.joinedtimestamp)

				self.dbCursor.execute("""
					INSERT INTO prk_run_history (player_id, map_id, demo_url, client_info, time, death_count)
					VALUES (?, ?, ?, ?, ?, ?);
				""", (player.logged_user_id, self.mapID, demo_name, player.client_string, ts, player.deathcount))
				self.dbConnection.commit()

				self.dbCursor.execute("SELECT id FROM prk_run_history WHERE player_id=? ORDER BY created_at DESC LIMIT 1", (player.logged_user_id,))
				runID = self.dbCursor.fetchone()[0]

				i = 0
				for tms in player.current_times:
					self.dbCursor.execute("""
						INSERT INTO prk_checkpoint_history (checkpoint, run_id, time)
						VALUES (?, ?, ?);
					""", (i, runID, tms))
					i+=1

				self.dbConnection.commit()

			except Exception as e:
				print("Error saving score: ", e)

		def get_top_ten(self):
			self.dbCursor.execute("""
				SELECT run.player_id, pl.login, run.map_id, run.time, run.death_count FROM prk_run_history as run
				INNER JOIN players as pl on run.player_id = pl.id
				INNER JOIN (
					SELECT player_id, map_id, min(time) as ts FROM prk_run_history WHERE map_id=? GROUP BY player_id
				) as i ON run.time = i.ts AND run.player_id = i.player_id AND run.map_id = i.map_id ORDER BY time LIMIT 10
			""", (self.mapID,))
			hs = self.dbCursor.fetchall()

			if hs is None:
				hs = []

			return hs

	class pDbConnection(connection):
		logged_user_id = None

	return pDbProtocol, pDbConnection