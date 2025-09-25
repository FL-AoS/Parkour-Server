"""
Dependencies: requests

Website API for updating highscores, login, register, etc

config.toml:
[website_api]
token = ""
url = ""

Events added:
Connection.on_website_login()
"""
from piqueserver.commands import command
from piqueserver.config import config
import requests
import json

WB_CFG = config.section("website_api")
URL = WB_CFG.option("url", default="http://127.0.0.1:8000").get()
TOKEN = WB_CFG.option("token").get()

LOGIN_ENDPOINT = URL+"/api/server/login/validate"
HIGHSCORE_UPLOAD_ENDPOINT = URL+"/api/server/highscores/upload"
SAVE_MAP_ENDPOINT = URL+"/api/server/map/create"

MAP_HIGHSCORES_ENDPOINT = URL+"/api/highscores/"

HEADERS = {
	"Content-Type": 'application/json',
	"Accept": 'application/json',
	"Authorization": "Bearer "+TOKEN
}

@command("register")
def register(p, user=None, password=None):
	return "Want to register? Go to our website: "+URL

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

	login_obj = {
		"login": user,
		"password": passw,
		"ip": p.address[0]
	}

	resp = requests.get(LOGIN_ENDPOINT, headers=HEADERS, json=login_obj)

	if not resp or resp.status_code != 200:
		return "Wrong infos for login..."

	resp_obj = resp.json()
	p.logged_user_id = resp_obj["id"]
	p.logged_user_name = resp_obj["login"]

	p.on_website_login()

	return "Welcome back %s!"%(user)

def apply_script(protocol, connection, config):
	class WebsiteConnection(connection):
		logged_user_id = None
		logged_user_name = None

		def on_website_login(self):
			pass

	class WebsiteProtocol(protocol):
		def upload_player_highscores(self, obj):
			requests.post(HIGHSCORE_UPLOAD_ENDPOINT, headers=HEADERS, json=obj)

		def get_map_highscores(self):
			resp = requests.get(MAP_HIGHSCORES_ENDPOINT+self.map_info.name)

			if not resp or resp.status_code != 200:
				return False

			return resp.json()

		def save_parkour_map(self):
			infos = {}
			infos["name"] = self.map_info.name
			infos["author"] = self.map_info.author
			infos["description"] = self.map_info.description

			infos["type"] = "line"
			if (self.map_info.extensions and "parkour_3d_checkpoints" in self.map_info.extensions):
				infos["type"] = "checkpoint"

			infos["checkpoints"] = len(self.map_info.extensions["parkour_checkpoints"])

			resp = requests.post(SAVE_MAP_ENDPOINT, headers=HEADERS, json=infos)

			if not resp or resp.status_code != 200:
				return False;

			return resp.json();

	return WebsiteProtocol, WebsiteConnection