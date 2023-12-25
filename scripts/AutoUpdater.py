"""
- LICENSE: GPL-3.0
- Made by sByte

Auto update your scripts, its useful when you use the same
script in various servers and need to change something
in a specific server, this is compatible with local files
and web files, like in github.

Always keep this script at the top of all other scripts that
will receive an update.

Add this to your config:

[autoupdater]
  [autoupdater.yourscript]
  url = "../path/to/the/script/yourscript.py"

  [autoupdater.mycoolscript]
  url = "http://myhttpserver/mycoolscript.py"
"""

from piqueserver.config import config
from urllib.request import urlopen
import hashlib
import os

def updateScript(content, scriptname):
	if isinstance(content, bytes):
		content = content.decode("utf-8")

	try:
		f = open("./scripts/%s.py"%scriptname, "w")
		f.write(content)
		f.close()

		return True
	except Exception as e:
		print(e)
		return False

def getScriptContent(configurl):
	content = ""
	if configurl.startswith("."):
		f = open(configurl)
		content = f.read()
		f.close()
	elif configurl.startswith("http"):
		content = urlopen(configurl).read()

	return content

# if True, needs update
def needUpdate(content_url, scriptpath):
	if not os.path.isfile(scriptpath):
		return True

	if not content_url:
		return False

	fscript = open(scriptpath)
	content_script = fscript.read()
	fscript.close()

	if not content_script:
		return True

	return not getfileHash(content_url) == getfileHash(content_script)

def getfileHash(content):
	if isinstance(content, bytes):
		content = content.decode("utf-8")

	_hash = hashlib.sha512()
	_hash.update(content.encode("utf-8"))

	return _hash.hexdigest()

def checkOriginalScriptExists(url_or_path):
	if url_or_path.startswith("."):
		return os.path.isfile(url_or_path)

	elif url_or_path.startswith("http"):
		try:
			code = urlopen(url_or_path).getcode()
			return code == 200
		except:
			return False


config_d = config.get_dict()
if not "autoupdater" in config_d:
	print("\033[93m--------------------------------")
	print("\033[93m!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
	print("\033[91m- PLEASE CREATE THE AUTO UPDATER")
	print("\033[91m-  SECTOR IN YOUR config.TOML")
	print("\033[93m!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
	print("\033[93m--------------------------------\033[0m")

	exit(0)

print("\033[92m--------------------------")
print("\033[92m- STARTING SCRIPTS UPDATE!\033[0m")

for script_name in config_d["autoupdater"]:
	if script_name not in config_d["scripts"]:
		print("\033[94m - Ignoring \033[35m%s\033[94m, script is not enabled in this server.\033[0m"%script_name)
		continue

	script_obj = config_d["autoupdater"][script_name]

	if not checkOriginalScriptExists(script_obj["url"]):
		print("\033[31m - Can't find the script \033[35m%s\033[31m, please check if the URL/PATH: \033[35m%s \033[31mis correctly."%(script_name,script_obj["url"]))
		continue

	content = getScriptContent(script_obj["url"])

	if not needUpdate(content, "./scripts/%s.py"%script_name):
		print("\033[37m - \033[35m%s\033[37m Its already up to date."%script_name)
		continue

	if updateScript(content, script_name):
		print("\033[37m - \033[35m%s\033[37m Got updated."%script_name)
	else:
		print("\033[93m - \033[35m%s\033[93m Cant get updated."%script_name)

print("\033[92m- ALL SCRIPTS GOT UPDATED!")
print("\033[92m--------------------------\033[0m")

def apply_script(protocol, connection, config):
	return protocol, connection