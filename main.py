#PinnerSpace - Justin and Yao Xiang
#Virtual PinBoard WebApp

import urllib
import webapp2
import jinja2
import os
import datetime
import logging

from google.appengine.ext import ndb
from google.appengine.api import users

jinja_environment = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + "/www"), autoescape=True)

#DataStructure for PinnerSpace

#Item Datastore - Child of Board
class Item(ndb.Model):
	itemType = ndb.IntegerProperty()
	text = ndb.TextProperty()
	font = ndb.StringProperty()
	fontSize = ndb.IntegerProperty()
	height = ndb.IntegerProperty()
	width = ndb.IntegerProperty()

#Board Datastore - Child of Account, Parent of Item
class Board(ndb.Model):
	boardID = ndb.IntegerProperty()
	items = ndb.StructuredProperty(Item)

#Account Datastore - Parent of Board
class Account(ndb.Model):
	#email is key, refer using id
	usernick = ndb.StringProperty()
	accid = ndb.StringProperty()
	defaultBoard = ndb.StructuredProperty(Board)

#Handler - Displays '/'
class MainHandler(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			loadBoard(user, self)
		else:
			template = jinja_environment.get_template('mainpage.html') 
			self.response.out.write(template.render())

#ShowBoard - Displays '/board'
class ShowBoard(webapp2.RequestHandler):
	def get(self):
		user=users.get_current_user()
		if user:
			#how do we pass values back and forth from the pinboard?
			loadBoard(user, self)
		else:
			self.redirect(users.create_login_url(self.request.uri))

#loadBoard - Function to display board
def loadBoard(user, self):
	userKey = ndb.Key('Account', user.email()).get()

	if userKey == None:
		#Create Acc
		logging.debug("Creating Account for: " + user.email() + ", " + user.nickname())
		currUser = Account(id=user.email(), accid=user.user_id(), usernick=user.nickname())
		userKey = currUser.put()
		usernickname = user.nickname()
	else:
		usernickname = userKey.usernick

	#Logging into Board - LoadBoard
	logging.debug("Logging in to: " + user.email())
	parameters = {
	'user_mail': user.email(),
	'user_nick': usernickname,
	'logout': users.create_logout_url(self.request.host_url),
	}
	webpage = jinja_environment.get_template('index.html')
	self.response.out.write(webpage.render(parameters))

#Settings page - Change nickname
class updateProfile(webapp2.RequestHandler):
	def get(self):
		userKey = ndb.Key('Account', users.get_current_user().email()).get()
		if userKey:
			parameters = {
			'user_mail': users.get_current_user().email(),
			'user_nick': userKey.usernick,
			'logout': users.create_logout_url(self.request.host_url),
			}
			webpage = jinja_environment.get_template('setting.html')
			self.response.out.write(webpage.render(parameters))
		else:
			self.redirect(users.create_login_url(self.request.uri))

	def post(self):
		userKey = ndb.Key('Account', users.get_current_user().email()).get()
		userKey.usernick = self.request.get('newnickname')
		userKey.put()
		self.redirect(self.request.uri)

#App
app = webapp2.WSGIApplication([('/', MainHandler),
	('/board', ShowBoard),
	('/settings', updateProfile),
	('/update', updateProfile)], debug=True)
