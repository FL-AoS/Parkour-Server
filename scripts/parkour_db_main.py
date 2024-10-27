from piqueserver.commands import command
from time import time
import sqlite3
import os

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

		check = p.protocol.dbCursorUsers.execute("""
			SELECT * FROM users
			WHERE name=?
		""", (user,)).fetchall()

		if check:
			return "An user with the name '%s' is already registered!"%(user)

		p.protocol.dbCursorUsers.execute("""
			INSERT INTO users
			VALUES (NULL, ?, ?, '0.0.0.0')
		""", (user, password))
		p.protocol.dbUsers.commit()

		return "Successfuly registered User '%s', with password '%s'. Please ask the user to use /changepassword when login."%(user, password)

@command("changepassword")
def changepassword(p, oldpass=None, newpass=None):
	if p.logged_user_id is None:
		return "You need to login to change your password."

	if oldpass is None or newpass is None:
		return "Wrong usage, please use: /changepassword <old_password> <new_password>"

	check = p.protocol.dbCursorUsers.execute("""
		SELECT * FROM users
		WHERE user_id=? and password=?
	""", (p.logged_user_id,oldpass,)).fetchall()

	if not check:
		return "Wrong password, please try again."

	p.protocol.dbCursorUsers.execute("""
		UPDATE users
		SET password=?
		WHERE user_id=?
	""", (newpass,p.logged_user_id,))
	p.protocol.dbUsers.commit()

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

	loginfos = p.protocol.dbCursorUsers.execute("SELECT * FROM users WHERE name=? and password=?",
		(user, passw,)).fetchall()

	if not loginfos:
		return "Wrong infos for login..."

	p.protocol.dbCursorUsers.execute("""
		UPDATE users
		SET last_ip=?
		WHERE name=? and password=?
	""", (p.address[0],user,passw,))
	p.protocol.dbUsers.commit()

	p.logged_user_id = loginfos[0][0]

	return "Welcome back %s!"%(user)

def create_user_table(protocol):
	protocol.dbCursorUsers.execute("""
		CREATE TABLE users
		(user_id INTEGER PRIMARY KEY,
		 name TEXT,
		 password TEXT,
		 last_ip TEXT
		)
	""")

	protocol.dbUsers.commit()

def apply_script(protocol, connection, config):
	class pDbProtocol(protocol):
		def __init__(self, *args, **kwargs):
			if not os.path.exists("./ParkourDB"):
				os.mkdir("./ParkourDB")

			notexist_usersdb = False

			if not os.path.exists("./ParkourDB/parkour_users.db"):
				notexist_usersdb = True

			self.dbUsers = sqlite3.connect("./ParkourDB/parkour_users.db")
			self.dbCursorUsers = self.dbUsers.cursor()

			self.dbScores = sqlite3.connect("./ParkourDB/parkour_highscores.db")
			self.dbCursorScore = self.dbScores.cursor()

			if notexist_usersdb:
				create_user_table(self)

			return protocol.__init__(self, *args, **kwargs)

		def on_map_change(self, _map):
			name = ''.join(self.map_info.rot_info.name.split(" "))
			variableaaa = "CREATE TABLE IF NOT EXISTS '"+name+"'(run_time INTEGER,run_day INTEGER,user_id INTEGER,deaths INTEGER)"

			self.dbCursorScore.execute(variableaaa)
			self.dbScores.commit()

			return protocol.on_map_change(self, _map)

		def save_record(self, player, wints):
			if player.logged_user_id is None:
				return

			current_map = ''.join(self.map_info.rot_info.name.split(" "))
			fulltimestamp = round(time()*1000)

			scores = self.get_all_records()

			if len(scores) >= 50:
				if scores[49][0] <= wints:
					return

				is_to_remove = None
				for record in scores:
					lotime = record[0]

					if lotime >= wints:
						is_to_remove = record[2]+1
						break

				if is_to_remove is None:
					return

			stop_it = False
			for record in scores:
				u_id = record[2]

				if u_id == player.logged_user_id:
					if record[0] > wints:
						table_check = "DELETE FROM '"+current_map
						where_check = "' WHERE user_id=?"
						self.dbCursorScore.execute(table_check+where_check, (player.logged_user_id,))
					else:
						stop_it = True
						break

			if stop_it:
				return

			tablename = "INSERT INTO '"+current_map
			infos = "' VALUES (?,?,?,?)"

			self.dbCursorScore.execute(tablename+infos,
				(wints, fulltimestamp, player.logged_user_id, player.deathcount))

			self.dbScores.commit()

		def get_all_records(self):
			tablename = "SELECT * FROM '"+''.join(self.map_info.rot_info.name.split(" "))
			infos = "' ORDER BY run_time ASC"
			return self.dbCursorScore.execute(tablename+infos).fetchall()

		def get_top_ten(self):
			to_return = []
			i = 0
			for record in self.get_all_records():
				if i >= 10:
					break

				to_return.append(record)
				i+=1

			return to_return

	class pDbConnection(connection):
		logged_user_id = None

	return pDbProtocol, pDbConnection