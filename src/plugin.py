# -*- coding: UTF-8 -*-
# This file is part of the OE-A distribution (https://github.com/xxxx or http://xxx.github.io).
# Copyright (c) 2024 EnigmaWelt
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
# Special thanks go to @jbleyel, @CommanderData2338 and @stein17 who was and is significantly involved in the realization.

import base64
from os import mkdir
from os.path import exists, join, splitext
from json import loads
import re
import requests
from twisted.internet.reactor import callInThread
from enigma import eServiceReference, ePicLoad, gPixmapPtr
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Plugins.Plugin import PluginDescriptor
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Downloader import downloadWithProgress
PLUGINPATH = "/usr/lib/enigma2/python/Plugins/Extensions/EnigmaWelt/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"
TMPIC = "/tmp/ewcover"


def geturl(url):
	try:
		r = requests.get(url, timeout=10, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-us,en;q=0.9,de-DE,de;q=0.8", "Accept-Encoding": "gzip, deflate"})
		r.raise_for_status()
		return r.content
	except requests.RequestException:
		return ""


def replace_html(txt):
	replacements = {"&#8211;": "-", "&#8218;": ",", "&#8216;": "'", "&#8217;": "'", "&#8220;": "„", "&#8222;": '"'}

	for key, value in replacements.items():
		txt = txt.replace(key, value)
	return txt


class enimaWeltScreen(Screen):

	skin = """
	<screen name="Main" position="center,center" size="1800,900" resolution="1920,1080" flags="wfNoBorder" >
		<widget source="Title" render="Label" position="10,15" size="1720,68" font="Bold;42" transparent="1" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Enigmawelt/img/bg.png" position="0,0" size="1920,1080" zPosition="-5"  scale="1" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Enigmawelt/img/head_logo.png" position="1720,11" size="68,68" alphatest="blend" scale="1" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Enigmawelt/img/red.png" position="1643,e-5" size="128,5" alphatest="blend" scale="1" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Enigmawelt/img/green.png" position="1493,e-5" size="128,5" alphatest="blend" scale="1" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Enigmawelt/img/yellow.png" position="1343,e-5" size="128,5" alphatest="blend" scale="1" />
			<widget source="movielist" render="Listbox" position="10,100" size="1070,728" scrollbarMode="showOnDemand" scrollbarForegroundColor="#029d9d" scrollbarBackgroundColor="#125454" foregroundColor="#d1d5d5" foregroundColorSelected="white" backgroundColor="background" backgroundColorSelected="#029d9d"  transparent="1">
			<convert type="TemplatedMultiContent">
				{
				"templates":
					{
					"default": (40,
						[
						MultiContentEntryText(pos=(5, 0), size=(1020, 35), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=0),
						])
					},
				"itemHeight" : 32,
				"fonts": [parseFont("Regular;28")]
				}
			</convert>
		</widget>
		<widget name="cover" position="1095,100" size="690,325" alphatest="blend" conditional="cover" scaleFlags="scaleCenter" transparent="1" />
		<widget source="description" render="Label" position="1095,445" size="680,420" conditional="description" font="Regular;27" horizontalAlignment="block" transparent="1"/>
		<widget source="key_red" render="Label" position="1643,e-60" size="128,60" font="Body;35" foregroundColor="white" halign="center" noWrap="1" valign="center" transparent="1">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="1493,e-60" size="128,60" font="Body;35" foregroundColor="white" halign="center" noWrap="1" valign="center" transparent="1">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="1343,e-60" size="128,60" font="Body;35" foregroundColor="white" halign="center" noWrap="1" valign="center" transparent="1">
			<convert type="ConditionalShowHide" />
		</widget>



		<widget source="key_blue" render="Label" position="1143,e-60" size="160,60" font="Body;35" foregroundColor="white" halign="center" noWrap="1" valign="center" transparent="1">
			<convert type="ConditionalShowHide" />
		</widget>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Enigmawelt/img/blue.png" position="1143,e-5" size="160,5" alphatest="blend" scale="1" />

		<widget name="progress" position="1102,52" size="540,15" foregroundColor="white" borderColor="white" borderWidth="1" transparent="1" />
		<widget name="DownloadLabel" position="1101,4" size="540,39" font="Bold;21" foregroundColor="white" halign="center" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "ChannelSelectBaseActions", "MenuActions"], {"green": self.ok, "red": self.exit, "yellow": self.search, "blue": self.download, "up": self.up, "down": self.down, "left": self.left, "right": self.right, "nextBouquet": self.p_up, "prevBouquet": self.p_down, "ok": self.ok, "cancel": self.exit}, -1)
		self["movielist"] = List()
		self["cover"] = Pixmap()
		self["description"] = StaticText()
		self["key_red"] = StaticText("EXIT")
		self["key_green"] = StaticText("OK")
		self["key_yellow"] = StaticText("SUCHE")
		self["key_blue"] = StaticText("Download")
		self["DownloadLabel"] = ScrollLabel()
		self["progress"] = ProgressBar()
		self["progress"].hide()
		self.filteredItems = []
		self.allItems = []
		self.DL_File = None
		if not exists("/tmp/ewcover/"):
			mkdir("/tmp/ewcover/")
		self.filter = ""
		self.onLayoutFinish.append(self.mainMenu)
		self.setTitle("Enigmawelt | Der größte DreamOS/Enigma2 Video Blog")

	def getUrl(self, data):
		parse = re.search(r"/embed/(.*)\?cover", data, re.S)
		if parse:
			return parse.group(1)
		return None

	def parseData(self, data):
		self.allItems = []
		try:
			items = loads(data)
			if "items" in items:
				for item in items["items"]:
					title = item.get("title")
					url = item.get("content_html")
					tags = item.get("tags")
					if tags and "Blog" in tags:
						continue
					if url:
						image_url = item.get("image", "")
						content_text = item.get("content_text", "")
						pos = content_text.find("\n\n")
						if pos > 0:
							content_text = content_text[:pos]
						url = self.getUrl(url)
						self.allItems.append((title, url, image_url, content_text))
		except Exception as e:
			print(e)

	def search(self):
		def searchCallback(text):
			self.filter = text.upper() if text else ""
			self.refresh()
		if self.filter:
			self.filter = ""
			self.refresh()
		else:
			self.session.openWithCallback(searchCallback, VirtualKeyBoard, title=_("Suche..."), windowTitle=_("Suche"))

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
			self.session.open(MessageBox, "kein eintrag", MessageBox.TYPE_INFO, timeout=5)
			self.filter = ""
			return
		self["movielist"].list = self.filteredItems
		self.infos()

	def ok(self):
		url = self["movielist"].getCurrent()[1]
		url = "https://public-api.wordpress.com/rest/v1.1/videos/%s" % url
		data = geturl(url)
		try:
			js = loads(data)
			videourl = js["original"]
			self.Play(videourl, self["movielist"].getCurrent()[0])
		except Exception as e:
			print(e)

	def exit(self):
		self.close()

	def Play(self, url, title):
		if url:
			sref = eServiceReference(4097, 0, url)
			sref.setName(title)
			self.session.open(MoviePlayer2, sref)

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
		pass

	def p_down(self):
		pass

	def infos(self):
		if self["movielist"].getCurrent() is not None:
			description = self["movielist"].getCurrent()[3]
			self["description"].setText(replace_html(description))
			self.show_cover()

	def show_cover(self):
		if self["movielist"].getCurrent() is not None:
			url = self["movielist"].getCurrent()[2]
			if url.startswith("http"):
				callInThread(self.getimage, url)
			elif url.startswith("/usr/"):
				self.get_cover(url)
			else:
				img = PLUGINPATH + "/img/nocover.png"
				self.get_cover(img)

	def getimage(self, url):
		try:
			imgpath = join(TMPIC, base64.b64encode(url.split("/")[-1].encode("ascii")).decode("ascii") + ".jpg")
			if not exists(imgpath):
				width = str(self["cover"].instance.size().width())
				url = url.replace("?fit=1500", "?fit=" + width)
				print("getimage", url)
				data = geturl(url)
				with open(imgpath, "wb") as f:
					f.write(data)
			self.get_cover(imgpath)
		except OSError as e:
			print("OSError", e)

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
			try:
				js = loads(data)
				videourl = js["original"]
				self.DL_Start(videourl, self["movielist"].getCurrent()[0])
			except Exception as e:
				print(e)

	def DL_Start(self, url, title):
		title = "".join(i for i in title if i not in r'\/":*?<>|')
		self.DL_File = "/media/hdd/movie/" + str(title) + ".mp4"
		if exists(self.DL_File):
			n = self.DL_File
			root, ext = splitext(self.DL_File)
			i = 0
			while exists(n):
				i += 1
				n = "%s_(%i)%s" % (root, i, ext)
			self.DL_File = n

		self["progress"].show()
		self["DownloadLabel"].show()
		self.downloader = downloadWithProgress(str(url), str(self.DL_File))
		if hasattr(downloadWithProgress, "setAgent"):
			self.downloader.setAgent(UA)
		self.downloader.addProgress(self.DL_progress)
		self.downloader.addEnd(self.DL_finished)
		self.downloader.addError(self.DL_failed)
		self.downloader.start()

	def DL_Stop(self, answer):
		if answer:
			self.downloader.stop()
			self.DL_File = None
			self["progress"].hide()
			self["DownloadLabel"].hide()

	def DL_finished(self, s=""):
		self["progress"].hide()
		self["DownloadLabel"].hide()
		self.DL_File = None
		self.session.open(MessageBox, "Download erfolgreich %s" % s, MessageBox.TYPE_INFO, timeout=5)

	def DL_failed(self, error):
		self["progress"].hide()
		self["DownloadLabel"].hide()
		self.downloader.stop()
		self.DL_File = None
		self.session.open(MessageBox, "Download-Fehler %s" % error, MessageBox.TYPE_INFO)

	def DL_progress(self, recvbytes, totalbytes):
		try:
			self["DownloadLabel"].setText(str(recvbytes // 1024 // 1024) + "MB/" + str(totalbytes // 1024 // 1024) + "MB")
			self["progress"].setValue(int(100 * recvbytes // totalbytes))
		except KeyError:
			pass


class MoviePlayer2(MoviePlayer):

	def __init__(self, session, service):
		MoviePlayer.__init__(self, session, service)
		self.skinName = "MoviePlayer"

	def up(self):
		pass

	def down(self):
		pass

	def leavePlayer(self):
		self.close()

	def leavePlayerOnExit(self):
		self.leavePlayer()

	def doEofInternal(self, playing):
		if not playing or not self.execing:
			return
		self.close()


def main(session, **kwargs):
	session.open(enimaWeltScreen)


def Plugins(**kwargs):
	return PluginDescriptor(name="Enigmawelt", description="Der größte DreamOS/Enigma2 Video Blog", where=[PluginDescriptor.WHERE_PLUGINMENU], icon="plugin.png", fnc=main)
