# -*- coding: UTF-8 -*-
# This file is part of the OE-A distribution (https://github.com/xxxx or http://xxx.github.io).
# Copyright (c) 2025 EnigmaWelt
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Special thanks go to @jbleyel, @Mr.Servo, @CommanderData2338 and @stein17 who was and is significantly involved in the realization.

from sys import version_info
from os import mkdir, path, unlink
from os.path import exists, join, splitext
from json import loads
from re import search, S
from requests import get, RequestException
from twisted.internet.reactor import callInThread

from enigma import eServiceReference, ePicLoad, gPixmapPtr, addFont, getDesktop
from Components.ActionMap import ActionMap
from Components.config import ConfigDirectory, ConfigSelection, ConfigSubsection, ConfigYesNo, config
from Components.ConfigList import ConfigListScreen
from Components.FileList import FileList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Plugins.Plugin import PluginDescriptor
from Screens.InfoBar import MoviePlayer
from Screens import InfoBarGenerics
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_FONTS
from Tools.Downloader import downloadWithProgress


PLUGINPATH = resolveFilename(SCOPE_PLUGINS, "Extensions/Enigmawelt/")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"
TMPIC = "/tmp/cover/bild.jpg"
FHD = getDesktop(0).size().height() > 720
FONT = join(resolveFilename(SCOPE_FONTS), "LiberationSans-Regular.ttf")  # /usr/share/fonts/
addFont(FONT, "SRegular", 100, False)
PY2 = version_info[0] == 2
PY3 = version_info[0] == 3

config.plugins.enimaWelt = ConfigSubsection()
config.plugins.enimaWelt.savetopath = ConfigDirectory(default="/media/hdd/movie/")
config.plugins.enimaWelt.SaveResumePoint = ConfigYesNo(default=False)
config.plugins.enimaWelt.COVER_DL = ConfigYesNo(default=False)
config.plugins.enimaWelt.DESC = ConfigYesNo(default=False)
config.plugins.enimaWelt.skinOption = ConfigSelection(default="default", choices=[("default", "Standard"), ("blue", "Blue"), ("gray", "Gray")])


def encode_str(s, encoding="utf-8", errors="strict"):
	if isinstance(s, str):
		return s
#	if PY2 and isinstance(s, unicode):
#		return s.encode(encoding, errors)

	if PY3 and isinstance(s, bytes):
		return s.decode(encoding, errors)
	return s


def geturl(url):
	try:
		r = get(url, timeout=(3.05, 6), headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-us,en;q=0.9,de-DE,de;q=0.8", "Accept-Encoding": "gzip, deflate"})
		r.raise_for_status()
		return r.content
	except RequestException as error:
		print(f"[Enigmawelt] ERROR in module 'geturl': {error}")


def replace_html(txt):
	replacements = {"&#8211;": "-", "&#8218;": ",", "&#8216;": "'", "&#8217;": "'", "&#8220;": "„", "&#8222;": '"', "&amp;": "&"}

	for key, value in replacements.items():
		txt = txt.replace(key, value)
	return txt


class enimaWeltScreen(Screen):
	def __init__(self, session):
		self.loadSkin()
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "ChannelSelectBaseActions", "MenuActions"], {"menu": self.setup, "green": self.ok, "red": self.exit, "yellow": self.search, "blue": self.download, "up": self.up, "down": self.down, "left": self.left, "right": self.right, "nextBouquet": self.p_up, "prevBouquet": self.p_down, "ok": self.ok, "cancel": self.exit}, -1)
		self["movielist"] = List()
		self["cover"] = Pixmap()
		self["description"] = ScrollLabel()
		self["key_red"] = StaticText("EXIT")
		self["key_green"] = StaticText("OK")
		self["key_yellow"] = StaticText("Suche")
		self["key_blue"] = StaticText("Download")
		self["DownloadLabel"] = ScrollLabel()
		self["progress"] = ProgressBar()
		self["progress"].hide()
		self.filteredItems = []
		self.allItems = []
		self.DL_File = ""
		if not exists("/tmp/cover/"):
			mkdir("/tmp/cover/")
		self.filter = ""
		self.onLayoutFinish.append(self.mainMenu)
		self.setTitle("Enigmawelt | Der größte DreamOS/Enigma2 Video Blog")

	def loadSkin(self):
		res = 1080 if FHD else 720
		skinpath = join(PLUGINPATH, config.plugins.enimaWelt.skinOption.value, f"skin_{config.plugins.enimaWelt.skinOption.value}_{res}.xml")
		data = ""
		if exists(skinpath):
			try:
				with open(skinpath, "r") as f:
					data = f.read()
			except OSError as error:
				print(f"[Enigmawelt] ERROR LOAD skin in module 'loadSkin': {skinpath} - {error}")
		self.skin = data

	def setup(self):
		def setupCallback(answer=None):
			if answer:
				self.close(True)

		self.session.openWithCallback(setupCallback, enimaWeltConfig)

	def getUrl(self, data):
		parse = search(r"/embed/(.*)\?cover", data, S)
		if parse:
			return parse.group(1)

	def parseData(self, data):
		self.allItems = []
		try:
			items = loads(data)
			if "items" in items:
				for item in items["items"]:
					title = item.get("title", "").split(" | D")[0]
					url = item.get("content_html", "")
					tags = item.get("tags", "")
					if tags and "Blog" in tags:
						continue
					if url:
						image_url = item.get("image", "")
						content_text = item.get("content_text", "")
						pos = content_text.find("\n\n")
						if pos > 0:
							content_text = content_text[:pos]
						url = self.getUrl(url)
						self.allItems.append((encode_str(title), encode_str(url), (image_url), encode_str(content_text)))
		except Exception as error:
			print(f"[Enigmawelt] ERROR in module 'parseData': {error}")

	def search(self):
		def searchCallback(text):
			self.filter = text.upper() if text else ""
			self.refresh()

		if self.filter:
			self.filter = ""
			self.refresh()
		else:
			self.session.openWithCallback(searchCallback, VirtualKeyBoard, title="Suche...", windowTitle="Suche")

	def mainMenu(self):
		def getList():
			data = geturl("https://enigmawelt.de/feed/json")
			if data:
				self.parseData(data)
				self.refresh()

		callInThread(getList)

	def refresh(self):
		self.filteredItems = self.allItems[:]
		if self.filter:
			self.filteredItems = [i for i in self.filteredItems if self.filter in i[0].upper()]
		if not self.filteredItems:
			self.session.open(MessageBox, "Kein Eintrag gefunden", MessageBox.TYPE_INFO, timeout=5)
			self.filter = ""
			return
		self["movielist"].list = self.filteredItems
		self.infos()

	def ok(self):
		url = self["movielist"].getCurrent()[1]
		url = "https://public-api.wordpress.com/rest/v1.1/videos/%s" % url
		data = geturl(url)
		if data:
			try:
				js = loads(data)
				videourl = js["original"]
				self.Play(videourl, self["movielist"].getCurrent()[0])
			except Exception as error:
				print(f"[Enigmawelt] ERROR in class 'enimaWeltScreen' module 'ok': {error}")

	def exit(self):
		self.close()

	def Play(self, url, title):
		if url:
			sref = eServiceReference(4097, 0, encode_str(url))
			sref.setName(title)
			self.session.open(Player, sref)

	def up(self):
		if self["movielist"]:
			self["movielist"].up()
			self.infos()

	def down(self):
		if self["movielist"]:
			self["movielist"].down()
			self.infos()

	def left(self):
		if self["movielist"]:
			self["movielist"].pageUp()
			self.infos()

	def right(self):
		if self["movielist"]:
			self["movielist"].pageDown()
			self.infos()

	def p_up(self):
		self["description"].pageUp()

	def p_down(self):
		self["description"].pageDown()

	def infos(self):
		if self["movielist"].getCurrent() is not None and isinstance(self["movielist"].getCurrent(), tuple):
			description = self["movielist"].getCurrent()[3]
			self["description"].setText(replace_html(description))
			self.show_cover()

	def show_cover(self):
		if self["movielist"].getCurrent() is not None:
			url = self["movielist"].getCurrent()[2]
			if url.startswith("http"):
				callInThread(self.getimage, url, self["movielist"].getIndex())
			elif url.startswith("/usr/"):
				self.get_cover(url)
			else:
				img = PLUGINPATH + "/img/nocover.png"
				self.get_cover(img)

	def getimage(self, url, index=0):
		try:
			width = str(self["cover"].instance.size().width())
			url = url.replace("?fit=1500", "?fit=" + width)
			data = geturl(url)
			if data:
				with open(TMPIC, "wb") as f:
					f.write(data)
				if self["movielist"].getCurrent() is not None:
					if index == int(self["movielist"].getIndex()):
						self.get_cover(TMPIC)
		except (IOError, KeyError):
			pass

	def get_cover(self, img):
		picload = ePicLoad()
		self["cover"].instance.setPixmap(gPixmapPtr())
		size = self["cover"].instance.size()
		picload.setPara((size.width(), size.height(), 1, 1, False, 1, "#FF000000"))
		if picload.startDecode(img, 0, 0, False) == 0:
			ptr = picload.getData()
			if ptr is not None:
				self["cover"].instance.setPixmap(ptr)
				self["cover"].show()

	def download(self):
		if self.DL_File:
			self.session.openWithCallback(self.DL_Stop, MessageBox, "möchten Sie den Download abbrechen?", default=True, type=MessageBox.TYPE_YESNO)
		else:
			if not self["movielist"].getCurrent():
				return
			url = self["movielist"].getCurrent()[1]
			url = "https://public-api.wordpress.com/rest/v1.1/videos/%s" % url
			data = geturl(url)
			if data:
				try:
					js = loads(data)
					videourl = js["original"]
					self.DL_Start(videourl, self["movielist"].getCurrent()[0])
				except Exception as error:
					print(f"[Enigmawelt] ERROR in class 'enimaWeltScreen' module 'download': {error}")

	def DL_Start(self, url, title):
		title = "".join(i for i in title if i not in r'\/":*?<>|')
		self.DL_File = str(config.plugins.enimaWelt.savetopath.value) + str(title) + ".mp4"
		if exists(self.DL_File):
			n = self.DL_File
			root, ext = splitext(self.DL_File)
			i = 0
			while exists(n):
				i += 1
				n = "%s_(%i)%s" % (root, i, ext)
			self.DL_File = n

		if config.plugins.enimaWelt.COVER_DL.value:
			downloader = downloadWithProgress(str(self["movielist"].getCurrent()[2]), self.DL_File[:-3] + "jpg")
			if hasattr(downloadWithProgress, "setAgent"):
				downloader.setAgent(UA)
			downloader.start()
		if config.plugins.enimaWelt.DESC.value:
			desc = self["movielist"].getCurrent()[3]
			if desc:
				with open(self.DL_File[:-3] + "txt", "w") as f:
					f.write(desc)

		self["progress"].show()
		self["DownloadLabel"].show()
		self.downloader = downloadWithProgress(str(url), str(self.DL_File))
		if hasattr(downloadWithProgress, "setAgent"):
			self.downloader.setAgent(UA)
		self.downloader.addProgress(self.DL_progress)
		self.downloader.addEnd(self.DL_finished)
		self.downloader.addError(self.DL_failed)
		self.downloader.start()

	def fileClean(self):
		filename = self.DL_File.rsplit(".", 1)[0]
		for ext in [".jpg", ".txt"]:
			fileext = filename + ext
			if path.exists(fileext):
				unlink(fileext)
		self.DL_File = ""

	def DL_Stop(self, answer):
		if answer:
			self.downloader.stop()
			self.fileClean()
			self["progress"].hide()
			self["DownloadLabel"].hide()

	def DL_finished(self, s=""):
		self["progress"].hide()
		self["DownloadLabel"].hide()
		self.DL_File = ""
		self.session.open(MessageBox, "Download erfolgreich %s" % s, MessageBox.TYPE_INFO, timeout=5)

	def DL_failed(self, error):
		self["progress"].hide()
		self["DownloadLabel"].hide()
		self.downloader.stop()
		self.fileClean()
		self.session.open(MessageBox, "Download-Fehler %s" % error, MessageBox.TYPE_INFO)

	def DL_progress(self, recvbytes, totalbytes):
		try:
			self["DownloadLabel"].setText(str(recvbytes // 1024 // 1024) + "MB/" + str(totalbytes // 1024 // 1024) + "MB")
			self["progress"].setValue(int(100 * recvbytes // totalbytes))
		except KeyError:
			pass


class Player(MoviePlayer):
	ENABLE_RESUME_SUPPORT = True

	def __init__(self, session, service):
		MoviePlayer.__init__(self, session, service)
		self.skinName = "MoviePlayer"

	def up(self):
		pass

	def down(self):
		pass

	def leavePlayer(self):
		if config.plugins.enimaWelt.SaveResumePoint.value and hasattr(InfoBarGenerics, "setResumePoint"):
			InfoBarGenerics.setResumePoint(self.session)
		self.close()

	def leavePlayerOnExit(self):
		self.leavePlayer()

	def doEofInternal(self, playing):
		if not playing or not self.execing:
			return
		self.close()


class enimaWeltConfig(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.title = "Einstellungen"
		self.session = session
		self.skinName = ["Setup"]
		self["key_red"] = StaticText("Abbrechen")
		self["key_green"] = StaticText("Speichern")
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
			{"cancel": self.cancel,
			 "red": self.cancel,
			"ok": self.ok,
			"green": self.save}, -2)
		ConfigListScreen.__init__(self, [], session=session)
		self.list = [
			("Download-Verzeichnis:", config.plugins.enimaWelt.savetopath),
			("Cover Downloaden", config.plugins.enimaWelt.COVER_DL),
			("Handlung Downloaden", config.plugins.enimaWelt.DESC),
			("Skin", config.plugins.enimaWelt.skinOption)
			]
		if hasattr(InfoBarGenerics, "setResumePoint"):
			self.list.append(("Letzte Abspielposition speichern", config.plugins.enimaWelt.SaveResumePoint))
		self["config"].list = self.list
		self["footnote"] = Label()
		self["footnote"].hide()
		self["description"] = Label()
		self.oldskin = config.plugins.enimaWelt.skinOption.value

	def save(self):
		reload = config.plugins.enimaWelt.skinOption.value != self.oldskin
		self.saveAll()
		self.close(reload)

	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(False)

	def ok(self):
		if self["config"].getCurrent()[1] == config.plugins.enimaWelt.savetopath:
			DLdir = config.plugins.enimaWelt.savetopath.value
			self.session.openWithCallback(self.DL_Path, DirBrowser, DLdir)

	def DL_Path(self, res):
		self["config"].setCurrentIndex(0)
		if res:
			config.plugins.enimaWelt.savetopath.value = res


class DirBrowser(Screen):
	def __init__(self, session, DLdir):
		Screen.__init__(self, session)
		self.skinName = ["FileBrowser"]
		self["key_red"] = StaticText("Abbrechen")
		self["key_green"] = StaticText("Speichern")
		if not path.exists(DLdir):
			DLdir = "/"
		self.filelist = FileList(DLdir, showFiles=False)
		self["filelist"] = self.filelist
		self["FilelistActions"] = ActionMap(["SetupActions", "ColorActions"], {"cancel": self.cancel, "red": self.cancel, "ok": self.ok, "green": self.save}, -2)

	def ok(self):
		if self.filelist.canDescent():
			self.filelist.descent()

	def save(self):
		fullpath = self["filelist"].getSelection()[0]
		if fullpath is not None and fullpath.endswith("/"):
			self.close(fullpath)

	def cancel(self):
		self.close(False)


def main(session, **kwargs):
	def mainCallback(answer=None):
		if answer:
			main(session=session)

	session.openWithCallback(mainCallback, enimaWeltScreen)


def Plugins(**kwargs):
	return PluginDescriptor(name="Enigmawelt", description="Der größte DreamOS/Enigma2 Video Blog", where=[PluginDescriptor.WHERE_PLUGINMENU], icon="plugin.png", fnc=main)
