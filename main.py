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

#CONSTANTS
MAX_BOARD = 5

jinja_environment = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + "/www"), autoescape=True)

#DataStructure for PinnerSpace

#Item Datastore - Child of Board
class Item(ndb.Model):
	itemType = ndb.IntegerProperty()
	coorx = ndb.IntegerProperty()
	coory = ndb.IntegerProperty()
	height = ndb.IntegerProperty()
	width = ndb.IntegerProperty()
	image = ndb.StringProperty()
	text = ndb.TextProperty()
	font = ndb.StringProperty()
	fontSize = ndb.IntegerProperty()

#Board Datastore - Child of Account, Parent of Item
class Board(ndb.Model):
	boardID = ndb.IntegerProperty()
	boardName =  ndb.StringProperty()
	items = ndb.StructuredProperty(Item)
	followers = ndb.IntegerProperty(default=0)
	#TESTING
	boardJSON = ndb.TextProperty()

#Account Datastore - Parent of Board
class Account(ndb.Model):
	#email is key, refer using id
	usernick = ndb.StringProperty()
	accid = ndb.StringProperty()
	numBoards = ndb.IntegerProperty(default=0)
	counter = ndb.IntegerProperty(default=0)
	defaultBoard = ndb.IntegerProperty(default=0)
	following = ndb.PickleProperty(indexed=True)

#Handler - Displays '/'
class MainHandler(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			loadBoard(self, user, -1)
		else:
			template = jinja_environment.get_template('mainpage.html') 
			self.response.out.write(template.render())

#ShowBoard - Displays '/board'
class ShowBoard(webapp2.RequestHandler):
	def get(self):
		user=users.get_current_user()
		if user:
			#how do we pass values back and forth from the pinboard?
			if (self.request.get('boardID') > 0):
				loadBoard(self, user, self.request.get('boardID'))
			else:	
				loadBoard(self, user, -1)
		else:
			self.redirect(users.create_login_url(self.request.uri))

#loadBoard - Function to display board
def loadBoard(self, user, boardID):
	userKey = ndb.Key('Account', user.email())
	userGet = userKey.get()

	if userGet == None:
		#Create Acc
		logging.debug("Creating Account for: " + user.email() + ", " + user.nickname())
		currUser = Account(id=user.email(), accid=user.user_id(), usernick=user.nickname())
		userKey = currUser
		userGet = currUser.put()
		usernickname = user.nickname()
		boardID = 0
	else:
		if (boardID == -1):
			boardID = userGet.defaultBoard
		usernickname = userGet.usernick

	#Get default board if available
	try:
		if (boardID > 0):
			boardKey = ndb.Key('Account', users.get_current_user().email(), 'Board', int(boardID))
			currBoard = boardKey.get()
			boardData = boardKey.get().boardJSON
		else:
			currBoard = None
			
	except:
		#ERROR BOARD DOES NOT EXISST
		boardName = ""
		boardData = ""
		self.redirect("/")
		
	#Logging into Board - LoadBoard
	logging.debug("Logging in to: " + user.email())
	parameters = {
	'user': userGet,
	'user_mail': user.email(),
	'user_nick': usernickname,
	'logout': users.create_logout_url(self.request.host_url),
	'currBoard': currBoard,
	'boardData': boardData,
	}

	query = ndb.gql("SELECT * "
	"FROM Board "
	"WHERE ANCESTOR IS :1 "
	"ORDER BY boardID ASC",
	userKey)
	parameters.update({'boards': query,})

	#if user has default board, display the board. else redirect to create board
	if boardID > 0:
		webpage = jinja_environment.get_template('index.html')
		self.response.out.write(webpage.render(parameters))
	else:
		self.redirect("/boards")

#Settings page - Change nickname
class UpdateProfile(webapp2.RequestHandler):
	def get(self):
		userGet = ndb.Key('Account', users.get_current_user().email()).get()
		if userGet:
			parameters = {
			'user_mail': users.get_current_user().email(),
			'user_nick': userGet.usernick,
			'logout': users.create_logout_url(self.request.host_url),
			'user_createdTotal': userGet.numBoards,
			'user_followedTotal': userGet.following,
			'update_status': "",
			}
			webpage = jinja_environment.get_template('setting.html')
			self.response.out.write(webpage.render(parameters))
		else:
			self.redirect(users.create_login_url(self.request.uri))

	def post(self):
		try:
			userGet = ndb.Key('Account', users.get_current_user().email()).get()
			if (self.request.get('newnickname') != ""):
				userGet.usernick = self.request.get('newnickname')
				userGet.put()
				status = "Updated Successfully!"
			else:
				status = "Nickname is empty."
		except:
			pass

		#Success
		parameters = {
		'user_mail': users.get_current_user().email(),
		'user_nick': userGet.usernick,
		'logout': users.create_logout_url(self.request.host_url),
		'user_createdTotal': userGet.numBoards,
		'user_followedTotal': userGet.following,
		'update_status': status,
		}
		webpage = jinja_environment.get_template('setting.html')
		self.response.out.write(webpage.render(parameters))

#Show all Board
class DisplayAllBoards(webapp2.RequestHandler):
	def showBoardsOf(self, _target, email, template_values):
		if email != "" and email != "#":
			userKey = ndb.Key('Account', email)
			#Get All Board, for each board, display the link.
			query = ndb.gql("SELECT * "
			"FROM Board "
			"WHERE ANCESTOR IS :1 "
			"ORDER BY boardID ASC",
			userKey)
			template_values.update({'boards': query,})
			if query.count() == 0 and email != users.get_current_user().email():
				template_values.update({'error': "Cannot find any board for %s" % email,})
		else:
			template_values.update({'error': "User does not exist",})

		template = jinja_environment.get_template(_target)
		self.response.out.write(template.render(template_values))

	def get(self):
		userKey = ndb.Key('Account', users.get_current_user().email())
		template_values = {
		'user_mail': users.get_current_user().email(),
		'user_nick': userKey.get().usernick,
		'logout': users.create_logout_url(self.request.host_url),
		'defaultBoardID': userKey.get().defaultBoard,
		'error': self.request.get('error'),
		}
		self.showBoardsOf("boards.html", users.get_current_user().email(), template_values)

	def post(self):
		userKey = ndb.Key('Account', users.get_current_user().email())
		target_mail = self.request.get('targetMail')
		try:
			target = ndb.Key('Account', target_mail).get()
			template_values = {
				'user_mail': users.get_current_user().email(),
				'user_nick': userKey.get().usernick,
				'logout': users.create_logout_url(self.request.host_url),
				'defaultBoardID': userKey.get().defaultBoard,
			}
			if target != None:
				template_values.update({'target_mail': target_mail,})
				self.showBoardsOf("boards.html", target_mail, template_values)
			else:
				self.showBoardsOf("boards.html", "#", template_values)
		except:
			template_values = {'error': "User does not exist",}
			self.showBoardsOf("boards.html", "", template_values)

#Add Board
class AddBoard(webapp2.RequestHandler):
	def post(self):
		#addBoard
		error = ""
		bName = self.request.get('boardName')
		if bName != "":
			try:
				userKey = ndb.Key('Account', users.get_current_user().email())
				userGet = userKey.get()
				if userGet.numBoards < MAX_BOARD:
					userGet.numBoards += 1
					userGet.counter += 1
					currBoard = Board(parent=userKey, id=userGet.counter)
					currBoard.boardName = bName
					currBoard.boardID = userGet.counter
					currBoard.boardJSON = '{"objects":[{"type":"rect","originX":"left","originY":"top","left":100,"top":100,"width":20,"height":20,"fill":"black","stroke":null,"strokeWidth":1,"strokeDashArray":null,"strokeLineCap":"butt","strokeLineJoin":"miter","strokeMiterLimit":10,"scaleX":1,"scaleY":1,"angle":0,"flipX":false,"flipY":false,"opacity":1,"shadow":null,"visible":true,"clipTo":null,"backgroundColor":"","rx":0,"ry":0,"x":0,"y":0}],"background":"green"}'
					currBoard.put()
					if userGet.numBoards == 1:
						#Set default board
						userGet.defaultBoard = currBoard.boardID
					#save
					userGet.put()
				else:
					error = "You cannot create anymore, reached a maximum of %d Boards." % MAX_BOARD
			except:
				pass
		else:
			error = "Create board failed. Board name cannot be empty."
		#Finally
		if error == "":
			self.redirect("/boards")
		else:
			self.redirect("/boards?error="+error)

#Delete Board
class DeleteBoard(webapp2.RequestHandler):
	def post(self):
		#Delete Board
		boardid = self.request.get('boardID')
		userKey = ndb.Key('Account', users.get_current_user().email())
		userGet = userKey.get()
		#Delete Board Entity
		boardKey = ndb.Key('Account', users.get_current_user().email(), 'Board', int(boardid))
		boardKey.delete()
		if (userGet.numBoards > 0):
			userGet.numBoards -= 1
		if (userGet.defaultBoard == int(boardid)):
			query = ndb.gql("SELECT * "
			"FROM Board "
			"WHERE ANCESTOR IS :1 "
			"ORDER BY boardID ASC",
			userKey)
			nextBoard = query.fetch(1)
			if (len(nextBoard) > 0):
				userGet.defaultBoard = nextBoard[0].boardID
			else:
				userGet.defaultBoard = 0
		userGet.put()
		self.redirect("/boards")

#Save Board
#class SaveBoard(webapp2.RequestHandler):
#	def post(self):
#		bData = self.request.get('save')
#		if bData == "saveCanvas()":
#			self.redirect("/error")
#			return
#		userGet = ndb.Key('Account', users.get_current_user().email()).get()
#		defBoard = ndb.Key('Account', users.get_current_user().email(), 'Board', int(userGet.defaultBoard)).get()
#		defBoard.boardJSON = bData
#		defBoard.put()
#		self.redirect("/board") #consider just running loadBoard

#Change Default Board
class ChangeDefaultBoard(webapp2.RequestHandler):
	def post(self):
		#Change Default Board
		boardid = self.request.get('boardID')
		userKey = ndb.Key('Account', users.get_current_user().email())
		userGet = userKey.get()
		userGet.defaultBoard = int(boardid)
		userGet.put()
		self.redirect("/boards")

#App
app = webapp2.WSGIApplication([('/', MainHandler),
	('/board', ShowBoard),
	('/newBoard', AddBoard),
	('/deleteBoard', DeleteBoard),
#	('/saveBoard', SaveBoard),
	('/boards', DisplayAllBoards),
	('/changeDefaultBoard', ChangeDefaultBoard),
	('/settings', UpdateProfile),
	('/update', UpdateProfile)], debug=True)
