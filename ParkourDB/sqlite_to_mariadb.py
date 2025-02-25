import sqlite3
import os
from time import time
import mariadb
import importlib

dbU = sqlite3.connect("./parkour_users.db")
cursorU = dbU.cursor()

dbH = sqlite3.connect("./parkour_highscores.db")
cursorH = dbH.cursor()

try:
	dbConnection = mariadb.connect(
		user="",
		password="",
		host="",
		port=,
		database=""
	)
except mariadb.Error as e:
	print("Error on database connection, disabling...", e)


dbCursor = dbConnection.cursor()


def create_player_table():
	dbCursor.execute("""
		CREATE TABLE IF NOT EXISTS players
		(id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
		 login VARCHAR(255) NOT NULL UNIQUE,
		 password VARCHAR(255) NOT NULL,
		 last_ip VARCHAR(255) DEFAULT NULL,
		 created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
		 updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP()
		);
	""")

	dbConnection.commit()

def create_map_table():
	dbCursor.execute("""
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

	dbConnection.commit()

def create_run_history_table():
	dbCursor.execute("""
		CREATE TABLE IF NOT EXISTS prk_run_history
		(id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
		 player_id BIGINT(20) UNSIGNED NOT NULL REFERENCES players(id),
		 map_id BIGINT(20) UNSIGNED NOT NULL REFERENCES prk_maps(id),
		 demo_url VARCHAR(255) DEFAULT NULL,
		 client_info VARCHAR(255) DEFAULT NULL,
		 time INT(11) NOT NULL,
		 death_count INT(11) NOT NULL,
		 created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
		 updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP()
		);
	""")

	dbConnection.commit()

def create_checkpoint_history_table():
	dbCursor.execute("""
		CREATE TABLE IF NOT EXISTS prk_checkpoint_history
		(id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
		 checkpoint INT(11) NOT NULL,
		 run_id BIGINT(20) UNSIGNED NOT NULL REFERENCES prk_run_history(id),
		 time INT(11) NOT NULL,
		 created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
		 updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP()
		);
	""")

	dbConnection.commit()

create_player_table()
create_map_table()
create_run_history_table()
create_checkpoint_history_table()

res = cursorU.execute("SELECT * FROM users;").fetchall()

for player in res:
	print(player)

	try:
		dbCursor.execute("INSERT INTO players (id, login, password, last_ip) VALUES (?,?,?,?)",(player[0], player[1], player[2], player[3]))
		dbConnection.commit()
	except Exception as e:
		print(e)

i = 1
for map_name in cursorH.execute("SELECT name FROM sqlite_master;").fetchall():
	loader = importlib.machinery.SourceFileLoader(map_name[0], "../maps/"+map_name[0]+".txt")
	spec = importlib.util.spec_from_loader(loader.name, loader)
	info = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(info)


	name = getattr(info, "name", map_name[0])
	author = getattr(info, "author")
	desc =  getattr(info, "description", "")

	ext = getattr(info, "extensions", {})

	is_3d = ext.get("parkour_3d_checkpoints", False)
	_type = "line"
	if is_3d:
		_type = "checkpoint"

	cps = ext.get("parkour_checkpoints", [])

	print(name)
	try:
		dbCursor.execute("INSERT INTO prk_maps (id, name, creator, description, type, checkpoints) VALUES (?,?,?,?,?,?)", (i,name,author,desc,_type,len(cps)))
		dbConnection.commit()
	except Exception as e:
		print(e)

	for record in cursorH.execute("SELECT * FROM "+map_name[0]).fetchall():
		print(record)
		run_time = record[0]
		run_day = record[1]/1000
		pid = record[2]
		deaths = record[3]

		dbCursor.execute("""
			INSERT INTO prk_run_history
			(player_id, map_id, time, death_count, created_at, updated_at)
			VALUES (?, ?, ?, ?, FROM_UNIXTIME(?), FROM_UNIXTIME(?));
			""", (pid, i, run_time, deaths, run_day, run_day))
		dbConnection.commit()
		print("-----")

	i += 1