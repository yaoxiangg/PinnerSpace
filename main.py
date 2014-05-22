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
#Account Datastore - Parent of Board
class Account(ndb.Model):
	#email is key, refer using id
	accid = ndb.StringProperty()

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
			loadBoard(user, self)
		else:
			self.redirect(users.create_login_url(self.request.uri))

#loadBoard - Function to display board
def loadBoard(user, self):
	userKey = ndb.Key('Account', user.email()).get()

	if userKey == None:
		#Create Acc
		logging.debug("Creating Account for: " + user.email())
		currUser = Account(id=user.email(), accid=user.user_id())
		currkey = currUser.put()

	#Logging into Board - LoadBoard
	logging.debug("Logging in to: " + user.email())
	parameters = {
	'user_mail': user.email(),
	'user_nick': user.nickname(),
	'logout': users.create_logout_url(self.request.host_url),
	}
	webpage = jinja_environment.get_template('index.html')
	self.response.out.write(webpage.render(parameters))


#App
app = webapp2.WSGIApplication([('/', MainHandler),
	('/board', ShowBoard)], debug=True)
