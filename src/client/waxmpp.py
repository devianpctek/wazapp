# -*- coding: utf-8 -*-
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import time, threading, select, os, urllib;
from utilities import Utilities, S40MD5Digest
from protocoltreenode import BinTreeNodeWriter,BinTreeNodeReader,ProtocolTreeNode
from connengine import MySocketConnection
from walogin import WALogin;
#from funstore import FunStore
from waeventbase import WAEventBase
#from contacts import WAContacts;
from messagestore import Key;
from notifier import Notifier
from connmon import ConnMonitor
import sys
from constants import WAConstants
from waexceptions import *
from PySide import QtCore
from PySide.QtCore import QThread, QTimer, Qt
from PySide.QtGui import QApplication, QImage, QPixmap, QPainter, QTransform
from waupdater import WAUpdater
from wamediahandler import WAMediaHandler, WAVCardHandler
from wadebug import WADebug
import thread
from watime import WATime
from time import sleep
#import Image
#import ExifTags


class WAEventHandler(WAEventBase):
	
	connecting = QtCore.Signal()
	connected = QtCore.Signal();
	sleeping = QtCore.Signal();
	disconnected = QtCore.Signal();
	loginFailed = QtCore.Signal()
	######################################
	new_message = QtCore.Signal(dict);
	typing = QtCore.Signal(str);
	paused = QtCore.Signal(str);
	available = QtCore.Signal(str);
	unavailable = QtCore.Signal(str);
	showUI = QtCore.Signal(str);
	messageSent = QtCore.Signal(int,str);
	messageDelivered = QtCore.Signal(int,str);
	lastSeenUpdated = QtCore.Signal(str,int);
	updateAvailable = QtCore.Signal(dict);
	
	##############Media#####################
	mediaTransferSuccess = QtCore.Signal(str,int,dict)
	mediaTransferError = QtCore.Signal(str,int,dict)
	mediaTransferProgressUpdated = QtCore.Signal(int,str,int)
	#########################################
	
	sendTyping = QtCore.Signal(str);
	sendPaused = QtCore.Signal(str);
	getLastOnline = QtCore.Signal(str);
	getGroupInfo = QtCore.Signal(str);
	createGroupChat = QtCore.Signal(str);
	groupCreated = QtCore.Signal(str);
	groupInfoUpdated = QtCore.Signal(str)
	addParticipants = QtCore.Signal(str, str);
	addedParticipants = QtCore.Signal();
	removeParticipants = QtCore.Signal(str, str);
	removedParticipants = QtCore.Signal();
	getGroupParticipants = QtCore.Signal(str);
	groupParticipants = QtCore.Signal(str);
	endGroupChat = QtCore.Signal(str);
	groupEnded = QtCore.Signal();
	setGroupSubject = QtCore.Signal(str, str);
	groupSubjectChanged = QtCore.Signal();
	getPictureIds = QtCore.Signal(str);
	getPicture = QtCore.Signal(str, str);
	profilePictureUpdated = QtCore.Signal(str);
	getPicture = QtCore.Signal(str, str);
	setPicture = QtCore.Signal(str, str);
	doQuit = QtCore.Signal();
	
	

	def __init__(self,conn):
		
		WADebug.attach(self);
		self.conn = conn;
		super(WAEventHandler,self).__init__();
		
		self.notifier = Notifier();
		self.connMonitor = ConnMonitor();
		
		self.connMonitor.connected.connect(self.networkAvailable);
		self.connMonitor.disconnected.connect(self.networkDisconnected);
		
		self.account = "";

		
		#self.connMonitor.sleeping.connect(self.networkUnavailable);
		#self.connMonitor.checked.connect(self.checkConnection);
		
		self.listJids = [];

		self.mediaHandlers = []
		self.sendTyping.connect(self.conn.sendTyping);
		self.sendPaused.connect(self.conn.sendPaused);
		self.getLastOnline.connect(self.conn.getLastOnline);
		self.getGroupInfo.connect(self.conn.sendGetGroupInfo);
		self.createGroupChat.connect(self.conn.sendCreateGroupChat);
		self.addParticipants.connect(self.conn.sendAddParticipants);
		self.removeParticipants.connect(self.conn.sendRemoveParticipants);
		self.getGroupParticipants.connect(self.conn.sendGetParticipants);
		self.endGroupChat.connect(self.conn.sendEndGroupChat);
		self.setGroupSubject.connect(self.conn.sendSetGroupSubject);
		self.getPictureIds.connect(self.conn.sendGetPictureIds);
		self.getPicture.connect(self.conn.sendGetPicture);
		self.setPicture.connect(self.conn.sendSetPicture);

		self.connected.connect(self.conn.resendUnsent);
		
		self.pingTimer = QTimer();
		self.pingTimer.timeout.connect(self.sendPing)
		self.pingTimer.start(180000);
		
		#self.connMonitor.start();
		
	
	def quit(self):
		
		#self.connMonitor.exit()
		#self.conn.disconnect()
		
		'''del self.connMonitor
		del self.conn.inn
		del self.conn.out
		del self.conn.login
		del self.conn.stanzaReader'''
		#del self.conn
		self.doQuit.emit();
		
	
	def initialConnCheck(self):
		if self.connMonitor.isOnline():
			self.connMonitor.connected.emit()
		else:
			self.connMonitor.createSession();
	
	def setMyAccount(self, account):
		self.account = account
	
	def onFocus(self):
		'''self.notifier.disable()'''
		
	def onUnfocus(self):
		'''self.notifier.enable();'''
	
	def checkConnection(self):
		try:
			if self.conn.state == 0:
				raise Exception("Not connected");
			elif self.conn.state == 2:
				self.conn.sendPing();
		except:
			self._d("Connection crashed, reason: %s"%sys.exc_info()[1])
			self.networkDisconnected()
			self.networkAvailable();
			
		
	
	def onLoginFailed(self):
		self.loginFailed.emit()
	
	def onLastSeen(self,jid,seconds,status):
		self._d("GOT LAST SEEN ON FROM %s"%(jid))
		
		if seconds is not None:
			self.lastSeenUpdated.emit(jid,int(seconds));
	
	
	def fetchVCard(self,messageId):
		mediaMessage = WAXMPP.message_store.store.Message.create()
		message = mediaMessage.findFirst({"media_id":mediaId})
		jid = message.getConversation().getJid()
		media = message.getMedia()
		
		mediaHandler = WAVCardHandler(jid,message.id,contactData)
		
		mediaHandler.success.connect(self._mediaTransferSuccess)
		mediaHandler.error.connect(self._mediaTransferError)
		mediaHandler.progressUpdated.connect(self.mediaTransferProgressUpdated)
		
		mediaHandler.pull();
		
		self.mediaHandlers.append(mediaHandler);
	
	def fetchMedia(self,mediaId):
		
		mediaMessage = WAXMPP.message_store.store.Message.create()
		message = mediaMessage.findFirst({"media_id":mediaId})
		jid = message.getConversation().getJid()
		media = message.getMedia()
		
		mediaHandler = WAMediaHandler(jid,message.id,media.remote_url,media.mediatype_id)
		
		mediaHandler.success.connect(self._mediaTransferSuccess)
		mediaHandler.error.connect(self._mediaTransferError)
		mediaHandler.progressUpdated.connect(self.mediaTransferProgressUpdated)
		
		mediaHandler.pull();
		
		self.mediaHandlers.append(mediaHandler);
		
	def fetchGroupMedia(self,mediaId):
		
		mediaMessage = WAXMPP.message_store.store.Groupmessage.create()
		message = mediaMessage.findFirst({"media_id":mediaId})
		jid = message.getConversation().getJid()
		media = message.getMedia()
		
		mediaHandler = WAMediaHandler(jid,message.id,media.remote_url,media.mediatype_id)
		
		mediaHandler.success.connect(self._mediaTransferSuccess)
		mediaHandler.error.connect(self._mediaTransferError)
		mediaHandler.progressUpdated.connect(self.mediaTransferProgressUpdated)
		
		mediaHandler.pull();
		
		self.mediaHandlers.append(mediaHandler);
	
	
	def _mediaTransferSuccess(self, jid, messageId,savePath):
		try:
			jid.index('-')
			message = WAXMPP.message_store.store.Groupmessage.create()
		
		except ValueError:
			message = WAXMPP.message_store.store.Message.create()
		
		message = message.findFirst({'id':messageId});
		
		if(message.id):
			media = message.getMedia()
			media.preview = savePath if media.mediatype_id == WAConstants.MEDIA_TYPE_IMAGE else None
			media.local_path = savePath
			media.transfer_status = 2
			media.save()
			self._d(media.getModelData())
			self.mediaTransferSuccess.emit(jid,messageId, media.getModelData())
		
		
	def _mediaTransferError(self, jid, messageId):
		try:
			jid.index('-')
			message = WAXMPP.message_store.store.Groupmessage.create()
		
		except ValueError:
			message = WAXMPP.message_store.store.Message.create()
		
		message = message.findFirst({'id':messageId});
		
		if(message.id):
			media = message.getMedia()
			media.transfer_status = 1
			media.save()
			self.mediaTransferError.emit(jid,messageId, media.getModelData())
	
	
	def onDirty(self,categories):
		self._d(categories)
		#ignored by whatsapp?
	
	def onAccountChanged(self,account_kind,expire):
		#nothing to do here
		return;
		
	def onRelayRequest(self,pin,timeoutSeconds,idx):
		#self.wtf("RELAY REQUEST");
		return
	
	def sendPing(self):
		self._d("Pinging")
		if self.connMonitor.isOnline() and self.conn.state == 2:
			self.conn.sendPing();
		else:
			self.connMonitor.createSession();
	
	def onPing(self,idx):
		self._d("Sending PONG")
		self.conn.sendPong(idx)
		
	
	def wtf(self,what):
		self._d("%s, WTF SHOULD I DO NOW???"%(what))
	
		
	
	def networkAvailable(self):
		self._d("NET AVAILABLE")
		self.updater = WAUpdater()
		self.updater.updateAvailable.connect(self.updateAvailable)
		
		
		self.connecting.emit();
		
		#thread.start_new_thread(self.conn.changeState, (2,))
		
		self.conn.changeState(2);
		#DISABLED CHECK FOR UPDATES FOR NOW
		#self.updater.run()
		
		#self.conn.disconnect()
		
		
		
		
	def networkDisconnected(self):
		self.sleeping.emit();
		self.conn.changeState(0);
		#thread.start_new_thread(self.conn.changeState, (0,))
		#self.conn.disconnect();
		self._d("NET SLEEPING")
		
	def networkUnavailable(self):
		self.disconnected.emit();
		self._d("NET UNAVAILABLE");
		
		
	def onUnavailable(self):
		self._d("SEND UNAVAILABLE")
		self.conn.sendUnavailable();
	
	
	def conversationOpened(self,jid):
		self.notifier.hideNotification(jid);
	
	def onAvailable(self):
		self.conn.sendAvailable();
		
	
	def sendMessage(self,jid,msg_text):
		self._d("sending message now")
		fmsg = WAXMPP.message_store.createMessage(jid);
		
		
		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		msg_text = msg_text.replace("&quot;","\"")
		msg_text = msg_text.replace("&amp;", "&");
		msg_text = msg_text.replace("&lt;", "<");
		msg_text = msg_text.replace("&gt;", ">");
		msg_text = msg_text.replace("<br />", "\n");

		fmsg.setData({"status":0,"content":msg_text.encode('utf-8'),"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)
		
		self.conn.sendMessageWithBody(fmsg);

	def sendLocation(self,jid,latitude,longitude,rotate):
		self._d("Capturing preview...")
		QPixmap.grabWindow(QApplication.desktop().winId()).save("/home/user/.cache/wazapp/tempimg.png", "PNG")
		img = QImage("/home/user/.cache/wazapp/tempimg.png")

		if rotate == "true":
			rot = QTransform()
			rot = rot.rotate(90)
			img = img.transformed(rot)

		if img.height() > img.width():
			result = img.scaledToWidth(320,Qt.SmoothTransformation);
			result = result.copy(result.width()/2-28,result.height()/2-25,51,51);
		elif img.height() < img.width():
			result = img.scaledToHeight(320,Qt.SmoothTransformation);
			result = result.copy(result.width()/2-25,result.height()/2-28,51,51);
		#result = img.scaled(96, 96, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation);

		result.save( "/home/user/.cache/wazapp/tempimg2.jpg", "JPG" );

		f = open("/home/user/.cache/wazapp/tempimg2.jpg", 'r')
		stream = f.read()
		iconBase = QtCore.QByteArray(stream).toBase64()
		stream = iconBase
		f.close()


		os.remove("/home/user/.cache/wazapp/tempimg.png")
		os.remove("/home/user/.cache/wazapp/tempimg2.jpg")

		self._d("sending location to "+jid)
		fmsg = WAXMPP.message_store.createMessage(jid);
		
		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_LOCATION
		mediaItem.remote_url = None
		mediaItem.preview = bytes(iconBase)
		mediaItem.local_path ="%s,%s"%(latitude,longitude)
		mediaItem.transfer_status = 2

		fmsg.content = QtCore.QCoreApplication.translate("WAEventHandler", "Location")
		fmsg.Media = mediaItem

		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		fmsg.setData({"status":0,"content":"","type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)
		
		self.conn.sendMessageWithLocation(fmsg,latitude,longitude,iconBase);


	def sendVCard(self,jid,contactName):
		contactName = contactName.encode('utf-8')
		self._d("Sending vcard: " + "/home/user/.cache/wazapp/vcards/" + contactName + ".vcf")

		stream = ""
		while not "END:VCARD" in stream:
			f = open("/home/user/.cache/wazapp/vcards/"+contactName+".vcf", 'r')
			stream = f.read()
			f.close()
			sleep(0.1)
			
		#print "DATA: " + stream

		fmsg = WAXMPP.message_store.createMessage(jid);
		
		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.mediatype_id = 6
		mediaItem.remote_url = None
		mediaItem.local_path = "/home/user/.cache/wazapp/vcards/"+contactName+".vcf"
		mediaItem.transfer_status = 2

		if "PHOTO;BASE64" in stream:
			n = stream.find("PHOTO;BASE64") +13
			vcardImage = stream[n:]
			vcardImage = vcardImage.replace("END:VCARD","")
			mediaItem.preview = vcardImage

		if "PHOTO;TYPE=JPEG" in stream:
			n = stream.find("PHOTO;TYPE=JPEG") +27
			vcardImage = stream[n:]
			vcardImage = vcardImage.replace("END:VCARD","")
			mediaItem.preview = vcardImage

		if "PHOTO;TYPE=PNG" in stream:
			n = stream.find("PHOTO;TYPE=PNG") +26
			vcardImage = stream[n:]
			vcardImage = vcardImage.replace("END:VCARD","")
			mediaItem.preview = vcardImage

		fmsg.content = contactName
		fmsg.Media = mediaItem

		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		fmsg.setData({"status":0,"content":fmsg.content,"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)
		
		self.conn.sendMessageWithVCard(fmsg,stream);



	def sendMediaMessage(self,jid,url):
		url = url.replace("file://","")
		self._d("sending media message to " +jid + " - file: " + url)
		fmsg = WAXMPP.message_store.createMessage(jid);
		
		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		fmsg.setData({"status":0,"content":msg_text.encode('utf-8'),"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)
		
		self.conn.sendNewMMSMessage(fmsg);

	
	def notificationClicked(self,jid):
		self._d("SHOW UI for "+jid)
		self.showUI.emit(jid);

	def message_received(self,fmsg,duplicate = False):
		msg_type = "duplicate" if duplicate else "new";

		if fmsg.content is not None:
			#self.new_message.emit({"data":fmsg.content,"user_id":fmsg.getContact().jid})
			msg_contact = fmsg.getContact();
			try:
				msg_contact = WAXMPP.message_store.store.getCachedContacts()[msg_contact.number];
			except:
				msg_contact.name= fmsg.getContact().number
				msg_contact.picture = WAConstants.DEFAULT_GROUP_PICTURE
			
						
			msgContent = fmsg.content
			contactName = msg_contact.name
			if fmsg.type == 20:
				msgContent = QtCore.QCoreApplication.translate("WAEventHandler", "%1 has join the group")
				msgContent = msgContent.replace("%1", fmsg.content)
			elif fmsg.type == 21:
				msgContent = QtCore.QCoreApplication.translate("WAEventHandler", "%1 has left the group")
				msgContent = msgContent.replace("%1", fmsg.content)
			elif fmsg.type == 22:
				msgContent = QtCore.QCoreApplication.translate("WAEventHandler", "%1 has changed the subject to %2")
				if contactName == self.account:
					contactName == QtCore.QCoreApplication.translate("WAEventHandler", "You")
				msgContent = msgContent.replace("%1", contactName)
				msgContent = msgContent.replace("%2", fmsg.content)
							
			if fmsg.Conversation.type == "single":
				msgPicture = "/home/user/.cache/wazapp/contacts/" + msg_contact.jid.replace("@s.whatsapp.net","") + ".png"
				self.notifier.newMessage(msg_contact.jid, contactName, msgContent, msgPicture.encode('utf-8'),callback = self.notificationClicked);
			else:
				conversation = fmsg.getConversation();
				msgPicture = "/home/user/.cache/wazapp/contacts/" + conversation.jid.replace("@g.us","") + ".png"
				self.notifier.newMessage(conversation.jid, "%s - %s"%(contactName,conversation.subject), msgContent, msgPicture.encode('utf-8'),callback = self.notificationClicked);
			
			self._d("A {msg_type} message was received: {data}".format(msg_type=msg_type, data=fmsg.content));
		else:
			self._d("A {msg_type} message was received".format(msg_type=msg_type));

		if(fmsg.wantsReceipt):
			self.conn.sendMessageReceived(fmsg);

	
		
	
	def subjectReceiptRequested(self,to,idx):
		self.conn.sendSubjectReceived(to,idx);
		
		
			
	def presence_available_received(self,fromm):
		if(fromm == self.conn.jid):
			return
		self.available.emit(fromm)
		self._d("{Friend} is now available".format(Friend = fromm));
	
	def presence_unavailable_received(self,fromm):
		if(fromm == self.conn.jid):
			return
		self.unavailable.emit(fromm)
		self._d("{Friend} is now unavailable".format(Friend = fromm));
	
	def typing_received(self,fromm):
		self._d("{Friend} is typing ".format(Friend = fromm))
		self.typing.emit(fromm);

	def paused_received(self,fromm):
		self._d("{Friend} has stopped typing ".format(Friend = fromm))
		self.paused.emit(fromm);


	def message_error(self,fmsg,errorCode):
		self._d("Message Error {0}\n Error Code: {1}".format(fmsg,str(errorCode)));

	def message_status_update(self,fmsg):
		self._d("Message status updated {0} for {1}".format(fmsg.status,fmsg.getConversation().getJid()));
		
		if fmsg.status == WAXMPP.message_store.store.Message.STATUS_SENT:
			self.messageSent.emit(fmsg.id,fmsg.getConversation().getJid());
		elif fmsg.status == WAXMPP.message_store.store.Message.STATUS_DELIVERED:
			self.messageDelivered.emit(fmsg.id,fmsg.getConversation().getJid()); 
	

	def onGroupCreated(self,jid,group_id):
		self._d("Got group created " + group_id)
		jname = jid.replace("@g.us","")
		img = QImage("/opt/waxmppplugin/bin/wazapp/UI/common/images/group.png")
		img.save("/home/user/.cache/wazapp/contacts/" + jname + ".png")
		self.groupCreated.emit(group_id);

	def onAddedParticipants(self):
		self._d("participants added!")
		self.addedParticipants.emit();

	def onRemovedParticipants(self):
		self._d("participants removed!")
		self.removedParticipants.emit();

	def onGroupEnded(self):
		self._d("group deleted!")
		self.groupEnded.emit();

	def onGroupSubjectChanged(self):
		self._d("group subject changed!")
		self.groupSubjectChanged.emit();
	
	def onGroupInfo(self,jid,ownerJid,subject,subjectOwnerJid,subjectT,creation):
		self._d("Got group info")
		if jid == "ERROR":
			self.groupInfoUpdated.emit("ERROR")
		else:
			self.groupInfoUpdated.emit(jid+"<<->>"+str(ownerJid)+"<<->>"+subject+"<<->>"+subjectOwnerJid+"<<->>"+str(subjectT)+"<<->>"+str(creation))
			WAXMPP.message_store.updateGroupInfo(jid,ownerJid,subject,subjectOwnerJid,subjectT,creation)
		#self.conn.sendGetPicture("g.us",jid,"group")
		
	def onGroupParticipants(self,jid,jids):
		self._d("GOT group participants")
		self.groupParticipants.emit(",".join(jids));
		conversation = WAXMPP.message_store.getOrCreateConversationByJid(jid);
		
		# DO WE REALLY NEED TO ADD EVERY CONTACT ?
		for j in jids:
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(j)
			conversation.addContact(contact.id);
		
		WAXMPP.message_store.sendConversationReady(jid);
		
	def groupSubjectUpdated(self, jid,author,newSubject,timestamp):
		self._d("Got group subject update")
		g = WAXMPP.message_store.getOrCreateConversationByJid(jid);
		contact = g.getOwner();
		cjid = contact.jid if contact is not 0 else "";
     
		self.onGroupInfo(jid,cjid,newSubject,author,timestamp,g.created);
		
	def onGetPictureIds(self,jids):
		self._d("Got picture ids")
		self.listJids = jids
		if len(self.listJids)>0:
			self.conn.sendGetPicture(self.listJids[0],"image")

	def onGetPictureDone(self, jid):
		self.profilePictureUpdated.emit(jid);
		if len(self.listJids)>0:
			self.listJids.pop(0);
			if len(self.listJids)>0:
				self.conn.sendGetPicture(self.listJids[0],"image")

	def onSetPicture(self,jid,res):
		self._d("Set Picture "+res)
		if res == "done":
			self.conn.sendGetPicture(jid,"image")

class StanzaReader(QThread):
	def __init__(self,connection):
		WADebug.attach(self);
		
		self.connection = connection
		self.inn = connection.inn;
		self.eventHandler = None;
		self.groupEventHandler = None;
		super(StanzaReader,self).__init__();
		self.requests = {};
		self.lastContactAddded = "";
		self.lastContactRemoved = "";
		self.currentPictureJid = "";

	def setEventHandler(self,handler):
		self.eventHandler = handler;

	def run(self):
		flag = True;
		self._d("Read thread started");
		while flag == True:
			
			self._d("waiting");
			ready = select.select([self.inn.rawIn], [], [])
			if ready[0]:
				try:
					node = self.inn.nextTree();
				except ConnectionClosedException:
					self._d("Socket closed, got 0 bytes")
					
					if self.eventHandler.connMonitor.isOnline():
						self.eventHandler.connMonitor.connected.emit()
					return
				except:
					self._d("Unhandled error: %s .restarting connection " % sys.exc_info()[1])
					if self.eventHandler.connMonitor.isOnline():
						self.eventHandler.connMonitor.connected.emit()
					else:
						self._d("Not online, aborting restart")
					return
					
					

				self.lastTreeRead = int(time.time())*1000;
			    
			    
			    
			    
			    
			    
			    
			    
				if node is not None:
					if ProtocolTreeNode.tagEquals(node,"iq"):
						iqType = node.getAttributeValue("type")
						idx = node.getAttributeValue("id")
						jid = node.getAttributeValue("from");
						
						if iqType is None:
							raise Exception("iq doesn't have type")
						
						if iqType == "result":
							if self.requests.has_key(idx):
								self.requests[idx](node,jid)
								del self.requests[idx]
							elif idx.startswith(self.connection.user):
								accountNode = node.getChild(0)
								ProtocolTreeNode.require(accountNode,"account")
								kind = accountNode.getAttributeValue("kind")
								
								if kind == "paid":
									self.connection.account_kind = 1
								elif kind == "free":
									self.connection.account_kind = 0
								else:
									self.connection.account_kind = -1
								
								expiration = accountNode.getAttributeValue("expiration")
								
								if expiration is None:
									raise Exception("no expiration")
								
								try:
									self.connection.expire_date = long(expiration)
								except ValueError:
									raise IOError("invalid expire date %s"%(expiration))
								
								self.eventHandler.onAccountChanged(self.connection.account_kind,self.connection.expire_date)
						elif iqType == "error":
							if self.requests.has_key(idx):
								self.requests[idx](node)
								del self.requests[idx]
						elif iqType == "get":
							childNode = node.getChild(0)
							if ProtocolTreeNode.tagEquals(childNode,"ping"):
								self.eventHandler.onPing(idx)
							elif ProtocolTreeNode.tagEquals(childNode,"query") and jid is not None and "http://jabber.org/protocol/disco#info" == childNode.getAttributeValue("xmlns"):
								pin = childNode.getAttributeValue("pin");
								timeoutString = childNode.getAttributeValue("timeout");
								try:
									timeoutSeconds = int(timeoutString) if timoutString is not None else None
								except ValueError:
									raise Exception("relay-iq exception parsing timeout %s "%(timeoutString))
								
								if pin is not None:
									self.eventHandler.onRelayRequest(pin,timeoutSeconds,idx)
						elif iqType == "set":
							childNode = node.getChild(0)
							if ProtocolTreeNode.tagEquals(childNode,"query"):
								xmlns = childNode.getAttributeValue("xmlns")
								
								if xmlns == "jabber:iq:roster":
									itemNodes = childNode.getAllChildren("item");
									ask = ""
									for itemNode in itemNodes:
										jid = itemNode.getAttributeValue("jid")
										subscription = itemNode.getAttributeValue("subscription")
										ask = itemNode.getAttributeValue("ask")
						else:
							raise Exception("Unkown iq type %s"%(iqType))
					
					elif ProtocolTreeNode.tagEquals(node,"presence"):
						xmlns = node.getAttributeValue("xmlns")
						jid = node.getAttributeValue("from")
						
						if (xmlns is None or xmlns == "urn:xmpp") and jid is not None:
							presenceType = node.getAttributeValue("type")
							if presenceType == "unavailable":
								self.eventHandler.presence_unavailable_received(jid);
							elif presenceType is None or presenceType == "available":
								self.eventHandler.presence_available_received(jid);
						
						elif xmlns == "w" and jid is not None:
							add = node.getAttributeValue("add");
							remove = node.getAttributeValue("remove")
							status = node.getAttributeValue("status")
							
							if add is not None:
								self._d("GROUP EVENT ADD")
								self.parseMessage(node)	
							elif remove is not None:
								self._d("GROUP EVENT REMOVE")
								self.parseMessage(node)	
							elif status == "dirty":
								categories = self.parseCategories(node);
								self.eventHandler.onDirty(categories);
								
					elif ProtocolTreeNode.tagEquals(node,"subject"):
						xmlns = node.getAttributeValue("xmlns")
						jid = node.getAttributeValue("from")

						subject = node.getAttributeValue("type");
						
						if subject == "subject" and fromAttribute.index('-') != -1:
							self._d("SUBJECT UPDATED")
							self.parseMessage(node)	
								
					elif ProtocolTreeNode.tagEquals(node,"message"):
						self.parseMessage(node)	

				
				'''
				if self.eventHandler is not None:
					if ProtocolTreeNode.tagEquals(node,"presence"):

						fromm = node.getAttributeValue("from");
						
						if node.getAttributeValue("type") == "unavailable":
							self.eventHandler.presence_unavailable_received(fromm);
						else:
							self.eventHandler.presence_available_received(fromm);
					
					elif ProtocolTreeNode.tagEquals(node,"message"):
						self.parseMessage(node);
					else:
						Utilities.debug("Not implemented");
				'''
	
	
	def handlePingResponse(self,node,fromm=None):
		self._d("Ping response received")
		    		
			    		
	def handleLastOnline(self,node,jid=None):
		firstChild = node.getChild(0);
		ProtocolTreeNode.require(firstChild,"query");
		seconds = firstChild.getAttributeValue("seconds");
		status = None
		status = firstChild.data
		
		try:
			if seconds is not None and jid is not None:
				self.eventHandler.onLastSeen(jid,int(seconds),status);
		except:
			self._d("Ignored exception in handleLastOnline "+ sys.exc_info()[1])
			
	def handleGroupInfo(self,node,jid=None):
		groupNode = node.getChild(0)
		if "error code" in groupNode.toString():
			self.eventHandler.onGroupInfo("ERROR","","","",0,0)
		else:
			ProtocolTreeNode.require(groupNode,"group")
			gid = groupNode.getAttributeValue("id")
			owner = groupNode.getAttributeValue("owner")
			subject = groupNode.getAttributeValue("subject")
			subjectT = groupNode.getAttributeValue("s_t")
			subjectOwner = groupNode.getAttributeValue("s_o")
			creation = groupNode.getAttributeValue("creation")
			self.eventHandler.onGroupInfo(jid,owner,subject,subjectOwner,int(subjectT),int(creation))

	def handleAddedParticipants(self,fromm,successVector=None,failTable=None):
		self.eventHandler.onAddedParticipants()

	def handleRemovedParticipants(self,fromm,successVector=None,failTable=None):
		print "handleRemovedParticipants DONE!";
		self.eventHandler.onRemovedParticipants()

	def handleGroupCreated(self,node,jid):
		groupNode = node.getChild(0)
		ProtocolTreeNode.require(groupNode,"group")
		group_id = groupNode.getAttributeValue("id")
		self.eventHandler.onGroupCreated(jid,group_id)

	def handleGroupEnded(self,node,jid):
		self.eventHandler.onGroupEnded()

	def handleGroupSubject(self,node,error=None):
		self.eventHandler.onGroupSubjectChanged()
		
	def handleParticipants(self,node,jid):
		children = node.getAllChildren("participant");
		jids = []
		for c in children:
			jids.append(c.getAttributeValue("jid"))
		
		self.eventHandler.onGroupParticipants(jid,jids)	

	def handleGetPicture(self,node,jid=None):
		if "error code" in node.toString():
			return;
		data = node.getChild("picture").toString()
		if data is not None:
			n = data.find(">") +2
			data = data[n:]
			data = data.replace("</picture>","")
			cjid = self.currentPictureJid.replace("@s.whatsapp.net","").replace("@g.us","")
			text_file = open("/home/user/.cache/wazapp/contacts/" + cjid + ".jpg", "w")
			text_file.write(data)
			text_file.close()
			if os.path.isfile("/home/user/.cache/wazapp/contacts/" + cjid + ".png"):
				os.remove("/home/user/.cache/wazapp/contacts/" + cjid + ".png")
			self.eventHandler.onGetPictureDone(self.currentPictureJid)

		
	def handleGetPictureIds(self,node,jid=None):
		groupNode = node.getChild("list")
		print "RESPUESTA PICTURE IDS"
		print groupNode.toString()
		#1340436828
		children = groupNode.getAllChildren("user");
		jids = []
		for c in children:
			if c.getAttributeValue("id") is not None:
				jids.append(c.getAttributeValue("jid"))
		
		self.eventHandler.onGetPictureIds(jids)
				

	def handleSetPicture(self,node,jid=None):
		picNode = node.getChild("picture")
		if picNode is not None:
			res = "done"
		else:
			res = "error"
		self.eventHandler.onSetPicture(self.currentPictureJid,res)


	def parseCategories(self,dirtyNode):
		categories = {}
		if dirtyNode.children is not None:
			for childNode in dirtyNode.getAllChildren():
				if ProtocolTreeNode.tagEquals(childNode,"category"):
					cname = childNode.getAttributeValue("name");
					timestamp = childNode.getAttributeValue("timestamp")
					categories[cname] = timestamp
		
		return categories

	def parseOfflineMessageStamp(self,stamp):
		
		watime = WATime();
		parsed = watime.parseIso(stamp)
		local = watime.utcToLocal(parsed)
		stamp = watime.datetimeToTimestamp(local)
		
		return stamp
	
	def parseMessage(self,messageNode):
	
		if "Offline Storage" in messageNode.toString():
			return;

		bodyNode = messageNode.getChild("body");
		newSubject = "" if bodyNode is None else bodyNode.data;
		if newSubject.find("New version of WhatsApp Messenger is now available")>-1:
			print "Rejecting whatsapp server message"
			return #REJECT THIS FUCKING MESSAGE!


		#if messageNode.getChild("media") is not None:
		#	return
		
		fromAttribute = messageNode.getAttributeValue("from");
		author = messageNode.getAttributeValue("author");
		
		fmsg = WAXMPP.message_store.createMessage(fromAttribute)
		fmsg.wantsReceipt = False
		
		
		conversation = WAXMPP.message_store.getOrCreateConversationByJid(fromAttribute);
		fmsg.conversation_id = conversation
		fmsg.Conversation = conversation
		
		
		
		
		msg_id = messageNode.getAttributeValue("id");
		attribute_t = messageNode.getAttributeValue("t");
		
		

		typeAttribute = messageNode.getAttributeValue("type");

		if typeAttribute == "error":
			errorCode = 0;
			errorNodes = messageNode.getAllChildren("error");
			for errorNode in errorNodes:
				codeString = errorNode.getAttributeValue("code")
				try:
					errorCode = int(codeString);
				except ValueError:
					'''catch value error'''
			message = None;
			if fromAttribute is not None and msg_id is not None:
				key = Key(fromAttribute,True,msg_id);
				message = message_store.get(key);

			if message is not None:
				message.status = 7
				self.eventHandler.message_error(message,errorCode);
		
		elif typeAttribute == "available":
			print "GROUP NOTIFICATION!"
			receiptRequested = False;

			addSubject = messageNode.getAttributeValue("add");
			removeSubject = messageNode.getAttributeValue("remove");
			cont = False
			if addSubject is not None and self.lastContactAddded != addSubject:
				if addSubject == self.eventHandler.account:
					print "THIS IS ME! GETTING OWNER..."
					addSubject = fromAttribute.split('-')[0]+"@s.whatsapp.net"
				self.lastContactAddded = addSubject
				if addSubject == self.eventHandler.account:
					return;
				print "CONTACTO AGREGADO : " + addSubject
				fmsg.Media = None
				key = Key(fromAttribute,False,"");
				print "MESSAGE KEY ::::::::::::::::::::::::::::::: " + key.toString();
				fmsg.setData({"status":0,"key":key.toString(),"content":addSubject,"type":20});
				author = addSubject
				cont = True
			elif removeSubject is not None and self.lastContactRemoved != removeSubject:
				if removeSubject == self.eventHandler.account:
					print "THIS IS ME! GETTING OWNER..."
					removeSubject = fromAttribute.split('-')[0]+"@s.whatsapp.net"
				self.lastContactRemoved = removeSubject
				if addSubject == self.eventHandler.account:
					return;
				print "CONTACTO ELIMINADO : " + removeSubject
				fmsg.Media = None
				key = Key(fromAttribute,False,"");
				print "MESSAGE KEY ::::::::::::::::::::::::::::::: " + key.toString();
				fmsg.setData({"status":0,"key":key.toString(),"content":removeSubject,"type":21});
				author = removeSubject
				cont = True

			if fmsg.timestamp is None:
				fmsg.timestamp = time.time()*1000;
				fmsg.offline = False;

			if self.eventHandler is not None and cont is True:
				signal = True
				contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(author)
				fmsg.contact_id = contact.id
				fmsg.contact = contact
				
				if conversation.type == "group":
					if conversation.subject is None:
						signal = False
						self._d("GETTING GROUP INFO")
						self.connection.sendGetGroupInfo(fromAttribute)
				
					if not len(conversation.getContacts()):
						self._d("GETTING GROUP CONTACTS")
						self.connection.sendGetParticipants(fromAttribute)
					
				ret = WAXMPP.message_store.get(key);
			
				conversation.incrementNew();		
				WAXMPP.message_store.pushMessage(fromAttribute,fmsg)
				fmsg.key = key
				duplicate = False;
			
				if signal:
					self.eventHandler.message_received(fmsg,False);
			
		elif typeAttribute == "subject":
			receiptRequested = False;
			requestNodes = messageNode.getAllChildren("request");
			for requestNode in requestNodes:
				if requestNode.getAttributeValue("xmlns") == "urn:xmpp:receipts":
					receiptRequested = True;
			
			bodyNode = messageNode.getChild("body");
			newSubject = None if bodyNode is None else bodyNode.data;

			if newSubject is not None and self.eventHandler is not None:
				self.eventHandler.groupSubjectUpdated(fromAttribute,author,newSubject,int(attribute_t));
			
			if receiptRequested and self.eventHandler is not None:
				self.eventHandler.subjectReceiptRequested(fromAttribute,msg_id);

			if newSubject is not None and self.eventHandler is not None:
				fmsg.Media = None
				key = Key(fromAttribute,False,newSubject);
				print "MESSAGE KEY ::::::::::::::::::::::::::::::: " + key.toString();
				fmsg.setData({"status":0,"key":key.toString(),"content":newSubject,"type":22});

				if fmsg.timestamp is None:
					fmsg.timestamp = time.time()*1000;
					fmsg.offline = False;

				if self.eventHandler is not None:
					signal = True
					contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(author)
					fmsg.contact_id = contact.id
					fmsg.contact = contact
					ret = WAXMPP.message_store.get(key);
					#conversation.incrementNew();		
					#WAXMPP.message_store.pushMessage(fromAttribute,fmsg)
					#fmsg.key = key
					duplicate = False;
					if ret is None:
						conversation.incrementNew();		
						WAXMPP.message_store.pushMessage(fromAttribute,fmsg)
						fmsg.key = key
					else:
						fmsg.key = eval(ret.key)
						duplicate = True;
				
					if signal:
						self.eventHandler.message_received(fmsg,duplicate);
						

		elif typeAttribute == "chat":
			duplicate = False;
			wantsReceipt = False;
			messageChildren = [] if messageNode.children is None else messageNode.children

			for childNode in messageChildren:
				if ProtocolTreeNode.tagEquals(childNode,"composing"):
						if self.eventHandler is not None:
							self.eventHandler.typing_received(fromAttribute);
				elif ProtocolTreeNode.tagEquals(childNode,"paused"):
						if self.eventHandler is not None:
							self.eventHandler.paused_received(fromAttribute);
				
				elif ProtocolTreeNode.tagEquals(childNode,"media") and msg_id is not None:
					self._d("MULTIMEDIA MESSAGE!");
					mediaItem = WAXMPP.message_store.store.Media.create()
					mediaItem.remote_url = messageNode.getChild("media").getAttributeValue("url");
					mediaType = messageNode.getChild("media").getAttributeValue("type")
					msgdata = mediaType
					preview = None
					
					try:
						index = fromAttribute.index('-')
						#group conv
						contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(author)
						fmsg.contact_id = contact.id
						fmsg.contact = contact
					except ValueError: #single conv
						pass
					
					if mediaType == "image":
						mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_IMAGE
						mediaItem.preview = messageNode.getChild("media").data
						msgdata = QtCore.QCoreApplication.translate("StanzaReader", "Image")
					elif mediaType == "audio":
						mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_AUDIO
						msgdata = QtCore.QCoreApplication.translate("StanzaReader", "Audio")
					elif mediaType == "video":
						mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_VIDEO
						msgdata = QtCore.QCoreApplication.translate("StanzaReader", "Video")
					elif mediaType == "location":
						mlatitude = messageNode.getChild("media").getAttributeValue("latitude")
						mlongitude = messageNode.getChild("media").getAttributeValue("longitude")
						mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_LOCATION
						mediaItem.remote_url = None
						mediaItem.preview = messageNode.getChild("media").data
						mediaItem.local_path ="%s,%s"%(mlatitude,mlongitude)
						mediaItem.transfer_status = 2
						msgdata = messageNode.getChild("media").getAttributeValue("name")
						if msgdata is None:
							msgdata =  QtCore.QCoreApplication.translate("StanzaReader", "Location")
						
					elif mediaType =="vcard":
						#return
						#mediaItem.preview = messageNode.getChild("media").data
						msgdata = messageNode.getChild("media").getChild("vcard").toString()
						msgname = messageNode.getChild("media").getChild("vcard").getAttributeValue("name")
						if msgdata is not None:
							if not os.path.exists("/home/user/.wazapp/media/contacts"):
								os.makedirs("/home/user/.wazapp/media/contacts")
							text_file = open("/home/user/.wazapp/media/contacts/" + msgname + ".vcf", "w")
							n = msgdata.find(">") +1
							msgdata = msgdata[n:]
							text_file.write(msgdata.replace("</vcard>",""))
							text_file.close()
							mediaItem = WAXMPP.message_store.store.Media.create()
							mediaItem.mediatype_id = 6
							mediaItem.transfer_status = 2
							msgdata = msgname
							mediaItem.setData({"local_path": "/home/user/.wazapp/media/contacts/" + msgname + ".vcf"})
							photo = messageNode.getChild("media").getChild("vcard").toString()

							if "PHOTO;BASE64" in photo:
								print "GETTING BASE64 PICTURE"
								n = photo.find("PHOTO;BASE64") +13
								vcardImage = photo[n:]
								vcardImage = vcardImage.replace("END:VCARD","")
								vcardImage = vcardImage.replace("</vcard>","")
								mediaItem.preview = vcardImage
								#image = QImage()
								#bytearr = QtCore.QByteArray()
								#bytearr = bytearr.fromBase64(vcardImage)
								#imagen = image.loadFromData(bytearr, 'PNG')
								#image.save("/home/user/.wazapp/media/images/" + msgname + ".png", "PNG");
								#mediaItem.setData({"preview": "/home/user/.wazapp/media/images/" + msgname + ".png"})

							if "PHOTO;TYPE=JPEG" in photo:
								n = photo.find("PHOTO;TYPE=JPEG") +27
								vcardImage = photo[n:]
								vcardImage = vcardImage.replace("END:VCARD","")
								vcardImage = vcardImage.replace("</vcard>","")
								mediaItem.preview = vcardImage
								#image = QImage()
								#bytearr = QtCore.QByteArray(vcardImage)
								#imagen = image.loadFromData(bytearr, 'JPG')
								#image.save("/home/user/.wazapp/media/images/" + msgname + ".png", "PNG");
								#mediaItem.setData({"preview": "/home/user/.wazapp/media/images/" + msgname + ".png"})

							if "PHOTO;TYPE=PNG" in photo:
								n = photo.find("PHOTO;TYPE=PNG") +26
								vcardImage = photo[n:]
								vcardImage = vcardImage.replace("END:VCARD","")
								vcardImage = vcardImage.replace("</vcard>","")
								mediaItem.preview = vcardImage
								#image = QImage()
								#bytearr = QtCore.QByteArray(vcardImage)
								#imagen = image.loadFromData(bytearr, 'JPG')
								#image.save("/home/user/.wazapp/media/images/" + msgname + ".png", "PNG");
								#mediaItem.setData({"preview": "/home/user/.wazapp/media/images/" + msgname + ".png"})
								

					else:
						self._d("Unknown media type")
						return
							
					fmsg.Media = mediaItem

					#if ProtocolTreeNode.tagEquals(childNode,"body"):   This suposses handle MEDIA + TEXT
					#	msgdata = msgdata + " " + childNode.data;		But it's not supported in whatsapp?

					key = Key(fromAttribute,False,msg_id);
					
					fmsg.setData({"status":0,"key":key.toString(),"content":msgdata,"type":WAXMPP.message_store.store.Message.TYPE_RECEIVED});
				
				elif ProtocolTreeNode.tagEquals(childNode,"body") and msg_id is not None:
					msgdata = childNode.data;
					
					#mediaItem = WAXMPP.message_store.store.Media.create()
					#mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_TEXT
					#fmsg.Media = mediaItem
					fmsg.Media = None
					
					key = Key(fromAttribute,False,msg_id);
					print "MESSAGE KEY ::::::::::::::::::::::::::::::: " + key.toString();
					fmsg.setData({"status":0,"key":key.toString(),"content":msgdata,"type":WAXMPP.message_store.store.Message.TYPE_RECEIVED});
					
				
				elif not (ProtocolTreeNode.tagEquals(childNode,"active")):
					if ProtocolTreeNode.tagEquals(childNode,"request"):
						fmsg.wantsReceipt = True;
					
					elif ProtocolTreeNode.tagEquals(childNode,"notify"):
						fmsg.notify_name = childNode.getAttributeValue("name");
						
						
					elif ProtocolTreeNode.tagEquals(childNode,"delay"):
						xmlns = childNode.getAttributeValue("xmlns");
						if "urn:xmpp:delay" == xmlns:
							stamp_str = childNode.getAttributeValue("stamp");
							if stamp_str is not None:
								stamp = stamp_str	
								fmsg.timestamp = self.parseOfflineMessageStamp(stamp)*1000;
								fmsg.offline = True;
					
					elif ProtocolTreeNode.tagEquals(childNode,"x"):
						xmlns = childNode.getAttributeValue("xmlns");
						if "jabber:x:event" == xmlns and msg_id is not None:
							
							key = Key(fromAttribute,True,msg_id);
							message = WAXMPP.message_store.get(key)
							if message is not None:
								WAXMPP.message_store.updateStatus(message,WAXMPP.message_store.store.Message.STATUS_SENT)
								
								if self.eventHandler is not None:
									self.eventHandler.message_status_update(message);
						elif "jabber:x:delay" == xmlns:
							continue; #TODO FORCED CONTINUE, WHAT SHOULD I DO HERE? #wtf?
							stamp_str = childNode.getAttributeValue("stamp");
							if stamp_str is not None:
								stamp = stamp_str	
								fmsg.timestamp = stamp;
								fmsg.offline = True;
					else:
						if ProtocolTreeNode.tagEquals(childNode,"delay") or not ProtocolTreeNode.tagEquals(childNode,"received") or msg_id is None:
							continue;
						key = Key(fromAttribute,True,msg_id);
						message = WAXMPP.message_store.get(key);
						if message is not None:
							WAXMPP.message_store.updateStatus(message,WAXMPP.message_store.store.Message.STATUS_DELIVERED)
							if self.eventHandler is not None:
								self.eventHandler.message_status_update(message);
							self._d(self.connection.supports_receipt_acks)
							if self.connection.supports_receipt_acks:
								
								receipt_type = childNode.getAttributeValue("type");
								if receipt_type is None or receipt_type == "delivered":
									self.connection.sendDeliveredReceiptAck(fromAttribute,msg_id); 
								elif receipt_type == "visible":
									self.connection.sendVisibleReceiptAck(fromAttribute,msg_id);  
					
			
			
			if fmsg.timestamp is None:
				fmsg.timestamp = time.time()*1000;
				fmsg.offline = False;
			
			print fmsg.getModelData();
			
			if self.eventHandler is not None:
				signal = True
				if fmsg.content:
					
					try:
						index = fromAttribute.index('-')
						#group conv
						contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(author)
						fmsg.contact_id = contact.id
						fmsg.contact = contact
					except ValueError: #single conv
						pass
						
					if conversation.type == "group":
						if conversation.subject is None:
							signal = False
							self._d("GETTING GROUP INFO")
							self.connection.sendGetGroupInfo(fromAttribute)
						
						if not len(conversation.getContacts()):
							self._d("GETTING GROUP CONTACTS")
							self.connection.sendGetParticipants(fromAttribute)
							
					ret = WAXMPP.message_store.get(key);
					
					if ret is None:
						conversation.incrementNew();		
						WAXMPP.message_store.pushMessage(fromAttribute,fmsg)
						fmsg.key = key
					else:
						fmsg.key = eval(ret.key)
						duplicate = True;
				
				if signal:
					self.eventHandler.message_received(fmsg,duplicate);
			



class WAXMPP():
	message_store = None
	def __init__(self,domain,resource,user,push_name,password):
		
		WADebug.attach(self);
		
		self.domain = domain;
		self.resource = resource;
		self.user=user;
		self.push_name=push_name;
		self.password = password;
		self.jid = user+'@'+domain
		self.fromm = user+'@'+domain+'/'+resource;
		self.supports_receipt_acks = False;
		self.msg_id = 0;
		self.state = 0 #0 disconnected 1 connecting 2 connected
		self.retry = True
		self.eventHandler = WAEventHandler(self);
		self.conn =MySocketConnection();		
		self.stanzaReader = None
		self.login = None;
		
		self.disconnectRequested = False
		
		self.connTries = 0;
		
		self.verbose = True
		self.iqId = 0;
		self.lock = threading.Lock()
		
		self.waiting = 0;
		
		#super(WAXMPP,self).__init__();
		
		self.eventHandler.initialConnCheck();
		
		#self.do_login();
		
	
	
	
	def setContactsManager(self,contactsManager):
		self.contactsManager = contactsManager
		
	def setReceiptAckCapable(self,can):
		#print "Switching to True"
		self.supports_receipt_acks = True;
		#print self.supports_receipt_acks

		
	
	
	
	def onLoginSuccess(self):
		self.changeState(4)
		
		self.connectionTries = 0
		c = StanzaReader(self);
		
		c.setEventHandler(self.eventHandler);
		
		#initial presence
		self.stanzaReader = c
		
		self.stanzaReader.start();
		
		
		self.sendClientConfig('','',False,'');
		self.sendAvailableForChat();
		self.eventHandler.connected.emit();
		
		

	def onConnectionError(self):
		self.login.wait()
		self.conn.close()	

		self.changeState(3)
		
		'''
		if self.connTries < 4:
			print "trying connect "+str(self.connTries)
			self.retryLogin()
		else:
			print "Too many tries, trying in 30000"
			t = QTimer.singleShot(30000,self.retryLogin)
		'''
	
	
	
	def disconnect(self):
		self.conn.close()
	
	def retryLogin(self):
		self.changeState(3);
	
	def changeState(self,newState):
		self._d("Entering critical area")
		self.waiting+=1
		self.lock.acquire()
		self.waiting-=1
		self._d("inside critical area")
		
		if self.state == 0:
			if newState == 2:
				self.state = 1
				self.do_login();
				
		elif self.state == 1:
			#raise Exception("mutex violated! I SHOULDN'T BE HERE !!!")
			if newState == 0:
				self.retry = False
			elif newState == 2:
				self.retry = True
			elif newState == 3: #failed
				if self.retry:
					
					
					if self.connTries >= 3:
						self._d("%i or more failed connections. Will try again in 30 seconds" % self.connTries)
						QTimer.singleShot(30000,self.retryLogin)
						self.connTries-=1
						
					else:	
						self.do_login()
						self.connTries+=1
				else:
					self.connTries = 0
					self.state = 0
					self.retry = True
					
			elif newState == 4:#connected
				self.connTries = 0
				self.retry = True
				self.state = 2
		elif self.state == 2:
			if newState == 2:
				self.disconnect()
				self.state = 1
				self.do_login()
			elif newState == 0:
				self.disconnect()
				self.state = 0
		
		
		self._d("Releasing lock")
		self.lock.release()
		
		
			

	def do_login(self):
		
		self.conn = conn = MySocketConnection();
		#conn.connect((HOST, PORT));

		self.inn = BinTreeNodeReader(conn,WALogin.dictionary+WALogin.dictionaryIn);
		self.out = BinTreeNodeWriter(conn,WALogin.dictionary);
		
		
		self.login = WALogin(conn,self.inn,self.out,S40MD5Digest());
		
		
		self.login.setConnection(self);
		
		self.login.loginSuccess.connect(self.onLoginSuccess)
		self.login.loginFailed.connect(self.eventHandler.onLoginFailed);
		
		self.login.connectionError.connect(self.onConnectionError)
		self.login.start();
		
		'''try:
			self.login.login();
		except:
			print "LOGIN FAILED"
			#sys.exit()
			return
		'''
		



		#fmsg = FMessage();
		#fmsg.setData('201006960035@s.whatsapp.net',True,"Hello World");
		
		#self.sendIq();
		#self.inn.nextTree();
		#print self.inn.inn.buf;
		#exit();
		#self.inn.nextTree();
		
		
		
		#self.sendMessageWithBody("ok");
		#node = self.inn.nextTree();
		#print node.toString();

		#self.sendSubscribe("201006960035@s.whatsapp.net");
		
		#self.sendMessageWithBody("OK");
		#self.sendMessageWithBody("OK");
		#node = self.inn.nextTree();
		#print node.toString();
		#raw_input();
		#self.sendMessageWithBody(fmsg);
	
	
	def resendUnsent(self):
		'''
			Resends all unsent messages, should invoke on connect
		'''
		
		
		messages = WAXMPP.message_store.getUnsent();
		self._d("Resending %i old messages"%(len(messages)))
		for m in messages:
			self.sendMessageWithBody(m);
		
		
	
	def sendTyping(self,jid):
		self._d("SEND TYPING TO JID")
		composing = ProtocolTreeNode("composing",{"xmlns":"http://jabber.org/protocol/chatstates"})
		message = ProtocolTreeNode("message",{"to":jid,"type":"chat"},[composing]);
		self.out.write(message);
		
	
		
	def sendPaused(self,jid):
		self._d("SEND PAUSED TO JID")
		composing = ProtocolTreeNode("paused",{"xmlns":"http://jabber.org/protocol/chatstates"})
		message = ProtocolTreeNode("message",{"to":jid,"type":"chat"},[composing]);
		self.out.write(message);

	
	
	def getSubjectMessage(self,to,msg_id,child):
		messageNode = ProtocolTreeNode("message",{"to":to,"type":"subject","id":msg_id},[child]);
		
		return messageNode
	
	def sendSubjectReceived(self,to,msg_id):
		self._d("Sending subject recv receipt")
		receivedNode = ProtocolTreeNode("received",{"xmlns": "urn:xmpp:receipts"});
		messageNode = self.getSubjectMessage(to,msg_id,receivedNode);
		self.out.write(messageNode);

	def sendMessageReceived(self,fmsg):
		receivedNode = ProtocolTreeNode("received",{"xmlns": "urn:xmpp:receipts"})
		messageNode = ProtocolTreeNode("message",{"to":fmsg.key.remote_jid,"type":"chat","id":fmsg.key.id},[receivedNode]);
		self.out.write(messageNode);


	def sendDeliveredReceiptAck(self,to,msg_id):
		self.out.write(self.getReceiptAck(to,msg_id,"delivered"));
	
	def sendVisibleReceiptAck(self,to,msg_id):
		self.out.write(self.getReceiptAck(to,msg_id,"visible"));
	
	def getReceiptAck(self,to,msg_id,receiptType):
		ackNode = ProtocolTreeNode("ack",{"xmlns":"urn:xmpp:receipts","type":receiptType})
		messageNode = ProtocolTreeNode("message",{"to":to,"type":"chat","id":msg_id},[ackNode]);
		return messageNode;

	def makeId(self,prefix):
		self.iqId += 1
		idx = ""
		if self.verbose:
			idx += prefix + str(self.iqId);
		else:
			idx = "%x" % self.iqId
		
		return idx
		 	
	
	def sendPing(self):
		
		idx = self.makeId("ping_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handlePingResponse;
		
		pingNode = ProtocolTreeNode("ping",{"xmlns":"w:p"});
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get","to":self.domain},[pingNode]);
		self.out.write(iqNode);
		
	
	def sendPong(self,idx):
		iqNode = ProtocolTreeNode("iq",{"type":"result","to":self.domain,"id":idx})
		self.out.write(iqNode);
	
	def getLastOnline(self,jid):
		
		if len(jid.split('-')) == 2 or jid == "Server@s.whatsapp.net": #SUPER CANCEL SUBSCRIBE TO GROUP AND SERVER
			return
		
		self.sendSubscribe(jid);
		
		self._d("presence request Initiated for %s"%(jid))
		idx = self.makeId("last_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleLastOnline;
		
		query = ProtocolTreeNode("query",{"xmlns":"jabber:iq:last"});
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get","to":jid},[query]);
		self.out.write(iqNode)
	
	
	def sendIq(self):
		node = ProtocolTreeNode("iq",{"to":"g.us","type":"get","id":str(int(time.time()))+"-0"},None,'expired');
		self.out.write(node);

		node = ProtocolTreeNode("iq",{"to":"s.whatsapp.net","type":"set","id":str(int(time.time()))+"-1"},None,'expired');
		self.out.write(node);

	def sendAvailableForChat(self):
		presenceNode = ProtocolTreeNode("presence",{"name":self.push_name})
		self.out.write(presenceNode);
		
	def sendAvailable(self):
		if self.state != 2:
			return
		presenceNode = ProtocolTreeNode("presence",{"type":"available"})
		self.out.write(presenceNode);
	
	
	def sendUnavailable(self):
		if self.state != 2:
			return
		presenceNode = ProtocolTreeNode("presence",{"type":"unavailable"})
		self.out.write(presenceNode);
		

	def sendSubscribe(self,to):
		presenceNode = ProtocolTreeNode("presence",{"type":"subscribe","to":to});
		
		self.out.write(presenceNode);

	def sendMessageWithBody(self,fmsg):
		#bodyNode = ProtocolTreeNode("body",None,message.data);
		#self.out.write(self.getMessageNode(message,bodyNode));

		bodyNode = ProtocolTreeNode("body",None,None,fmsg.content);
		self.out.write(self.getMessageNode(fmsg,bodyNode));
		self.msg_id+=1;


	def sendNewMMSMessage(self,fmsg):
		bodyNode = ProtocolTreeNode("body",None,None,fmsg.content);
		self.out.write(self.getMessageNode(fmsg,bodyNode));
		self.msg_id+=1;


	def sendMessageWithLocation(self,fmsg,latitude,longitude,preview):
		bodyNode = ProtocolTreeNode("media", {"xmlns":"urn:xmpp:whatsapp:mms","type":"location","latitude":latitude,"longitude":longitude},None,preview)
		self.out.write(self.getMessageNode(fmsg,bodyNode));
		self.msg_id+=1;

	def sendMessageWithVCard(self,fmsg,data):
		cardNode = ProtocolTreeNode("vcard",{"name":fmsg.content},None,data);
		bodyNode = ProtocolTreeNode("media", {"xmlns":"urn:xmpp:whatsapp:mms","type":"vcard"},[cardNode])
		self.out.write(self.getMessageNode(fmsg,bodyNode));
		self.msg_id+=1;


	def sendClientConfig(self,sound,pushID,preview,platform):
		idx = self.makeId("config_");
		configNode = ProtocolTreeNode("config",{"xmlns":"urn:xmpp:whatsapp:push","sound":sound,"id":pushID,"preview":"1" if preview else "0","platform":platform})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":self.domain},[configNode]);
		
		self.out.write(iqNode);
		
	
	
	def sendGetGroupInfo(self,jid):
		self._d("getting group info for %s"%(jid))
		idx = self.makeId("get_g_info_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleGroupInfo;
		
		queryNode = ProtocolTreeNode("query",{"xmlns":"w:g"})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get","to":jid},[queryNode])
		
		self.out.write(iqNode)
		
	def sendCreateGroupChat(self,subject):
		self._d("creating group: %s"%(subject))
		idx = self.makeId("create_group_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleGroupCreated;
		
		queryNode = ProtocolTreeNode("group",{"xmlns":"w:g","action":"create","subject":subject})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":"g.us"},[queryNode])
		
		self.out.write(iqNode)


	def sendAddParticipants(self,gjid,participants):
		self._d("opening group: %s"%(gjid))
		self._d("adding participants: %s"%(participants))
		idx = self.makeId("add_group_participants_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleAddedParticipants;
		parts = participants.split(',')
		innerNodeChildren = []
		i = 0;
		for part in parts:
			if part != "undefined":
				innerNodeChildren.append( ProtocolTreeNode("participant",{"jid":part}) )
			i = i + 1;

		queryNode = ProtocolTreeNode("add",{"xmlns":"w:g"},innerNodeChildren)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":gjid},[queryNode])
		
		self.out.write(iqNode)
		

	def sendRemoveParticipants(self,gjid,participants):
		self._d("opening group: %s"%(gjid))
		self._d("removing participants: %s"%(participants))
		idx = self.makeId("remove_group_participants_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleRemovedParticipants;
		parts = participants.split(',')
		innerNodeChildren = []
		i = 0;
		for part in parts:
			if part != "undefined":
				innerNodeChildren.append( ProtocolTreeNode("participant",{"jid":part}) )
			i = i + 1;

		queryNode = ProtocolTreeNode("remove",{"xmlns":"w:g"},innerNodeChildren)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":gjid},[queryNode])
		
		self.out.write(iqNode)


	def sendEndGroupChat(self,gjid):
		self._d("removing group: %s"%(gjid))
		idx = self.makeId("leave_group_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleGroupEnded;
		
		innerNodeChildren = []
		innerNodeChildren.append( ProtocolTreeNode("group",{"id":gjid}) )

		queryNode = ProtocolTreeNode("leave",{"xmlns":"w:g"},innerNodeChildren)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":"g.us"},[queryNode])
		
		self.out.write(iqNode)

	def sendSetGroupSubject(self,gjid,subject):
		self._d("setting group subject of " + gjid + " to " + subject)
		idx = self.makeId("set_group_subject_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleGroupSubject
		
		queryNode = ProtocolTreeNode("subject",{"xmlns":"w:g","value":subject})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":gjid},[queryNode]);
		
		self.out.write(iqNode)

		
	def sendGetParticipants(self,jid):
		idx = self.makeId("get_participants_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleParticipants
		
		listNode = ProtocolTreeNode("list",{"xmlns":"w:g"})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get","to":jid},[listNode]);
		
		self.out.write(iqNode)


	def sendGetPicture(self,jid,ptype):
		idx = self.makeId("get_picture_")

		self.stanzaReader.currentPictureJid = jid
		self.stanzaReader.requests[idx] = self.stanzaReader.handleGetPicture
		
		listNode = ProtocolTreeNode("picture",{"xmlns":"w:profile:picture","type":ptype})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"to":jid,"type":"get"},[listNode]);
		
		self.out.write(iqNode)
		


	def sendGetPictureIds(self,jids):
		idx = self.makeId("get_picture_ids_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleGetPictureIds

		parts = jids.split(',')
		innerNodeChildren = []
		i = 0;
		for part in parts:
			if part != "undefined":
				innerNodeChildren.append( ProtocolTreeNode("user",{"jid":part}) )
			i = i + 1;

		queryNode = ProtocolTreeNode("list",{"xmlns":"w:profile:picture"},innerNodeChildren)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get"},[queryNode])
		
		self.out.write(iqNode)


	def sendSetPicture(self, jid, filepath):
		filepath = filepath.replace("file://","")
		print "Setting image: " + filepath
		rotation = 0
		#im = Image.open(filepath)
		#exif=dict((ExifTags.TAGS[k], v) for k, v in im._getexif().items())
		#if exif['Orientation'] == 6:
		#    rotation = 90


		img = QImage(filepath);
		if img.height() > img.width():
			result = img.scaledToWidth(96,Qt.SmoothTransformation);
			result = result.copy(0,result.height()/2-32,96,96);
		elif img.height() < img.width():
			result = img.scaledToHeight(96,Qt.SmoothTransformation);
			result = result.copy(result.width()/2-32,0,96,96);
		elif img.height() > 96:
			result = img.scaled(96, 96, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation);
			result = result.copy(0,0,96,96);
		else:
			result = img;

		result.save( "/home/user/.cache/wazapp/tempimg.jpg", "JPG" );

		#if rotation == 90:
		#	im = Image.open("/home/user/.cache/wazapp/tempimg.jpg")
		#	im = im.rotate(90)
		#	im.save("/home/user/.cache/wazapp/tempimg.jpg", "JPEG", quality=85)


		currentPictureJid = jid;
		f = open("/home/user/.cache/wazapp/tempimg.jpg", 'r')
		stream = f.read()
		stream = bytearray(stream)
		f.close()
		#print stream
		idx = self.makeId("set_picture_")
		self.stanzaReader.requests[idx] = self.stanzaReader.handleSetPicture
		
		listNode = ProtocolTreeNode("picture",{"xmlns":"w:profile:picture","type":"image"}, None, stream)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"to":jid,"type":"set"},[listNode])
		
		self.out.write(iqNode)


	
	def getMessageNode(self,fmsg,child):
			requestNode = None;
			serverNode = ProtocolTreeNode("server",None);
			xNode = ProtocolTreeNode("x",{"xmlns":"jabber:x:event"},[serverNode]);
			childCount = (0 if requestNode is None else 1) +2;
			messageChildren = [None]*childCount;
			i = 0;
			if requestNode is not None:
				messageChildren[i] = requestNode;
				i+=1;
			#System.currentTimeMillis() / 1000L + "-"+1
			messageChildren[i] = xNode;
			i+=1;
			messageChildren[i]= child;
			i+=1;
			
			key = eval(fmsg.key)
			messageNode = ProtocolTreeNode("message",{"to":key.remote_jid,"type":"chat","id":key.id},messageChildren)
			
			
			return messageNode;
