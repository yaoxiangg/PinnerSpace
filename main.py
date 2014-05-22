#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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

class Account(ndb.Model):
	#email is key, refer using id
	accid = ndb.StringProperty()

class Item(ndb.Model):
		itemType = ndb.IntegerProperty()
		text = ndb.TextProperty()
		font = ndb.StringProperty()
		fontSize = ndb.IntegerProperty()
		height = ndb.IntegerProperty()
		width = ndb.IntegerProperty()

class Board(ndb.Model):
		boardID = ndb.IntegerProperty()
		items = ndb.StructuredProperty(Item)

#Handler
class MainHandler(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			loadBoard(self)
		else:
			template = jinja_environment.get_template('mainpage.html') 
			self.response.out.write(template.render())

#ShowBoard
class ShowBoard(webapp2.RequestHandler):
	def get(self):
		user=users.get_current_user()
		if user:
			loadBoard(self)
		else:
			self.redirect(users.create_login_url(self.request.uri))

#loadBoard
def loadBoard(self):
	user = users.get_current_user()
	userKey = ndb.Key('Account', user.email()).get()

	if userKey == None:
		#Create Acc
		logging.debug("Creating Account for: " + users.get_current_user().email())
		currUser = Account(id=user.email(), accid=user.user_id())
		currkey = currUser.put()


	logging.debug("Logging in to: " + users.get_current_user().email())
	
	#LoadBoard
	parameters = {
	'user_mail': user.email(),
	'user_nick': user.nickname(),
	'logout': users.create_logout_url(self.request.host_url),
	}
	webpage = jinja_environment.get_template('index.html')
	self.response.out.write(webpage.render(parameters))


app = webapp2.WSGIApplication([('/', MainHandler),
			('/board', ShowBoard)], debug=True)
