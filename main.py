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
	boardID = ndb.IntegerProperty()
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
	boardUser = ndb.StringProperty()
	boardID = ndb.IntegerProperty()
	boardName =  ndb.StringProperty()
	followers = ndb.StringProperty(repeated=True)
	#TESTING
	boardJSON = ndb.TextProperty()

#Account Datastore - Parent of Board
class Account(ndb.Model):
	#email is key, refer using id
	usernick = ndb.StringProperty()
	email = ndb.StringProperty()
	accid = ndb.StringProperty()
	numBoards = ndb.IntegerProperty(default=0)
	counter = ndb.IntegerProperty(default=0)
	defaultBoardID = ndb.IntegerProperty(default=0)
	defaultBoardUser = ndb.StringProperty(default="")
	following = ndb.IntegerProperty(default=0)

class PairFollowerOwner(ndb.Model):
	follower = ndb.StringProperty()
	owner = ndb.StringProperty()
	boardID = ndb.IntegerProperty(repeated=True)

#Handler - Displays '/'
class MainHandler(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			userKey = ndb.Key('Account', user.email())
			userGet = userKey.get()
			if userGet:
				loadBoard(self, user, -1, userGet.defaultBoardUser)
			else:
				loadBoard(self, user, -1, user.email())
		else:
			template = jinja_environment.get_template('mainpage.html') 
			self.response.out.write(template.render())

#ShowBoard - Displays '/board'
class ShowBoard(webapp2.RequestHandler):
	def get(self):
		user=users.get_current_user()
		if user:
			userKey = ndb.Key('Account', user.email())
			userGet = userKey.get()
			#how do we pass values back and forth from the pinboard?
			if (self.request.get('boardID') > 0):
				loadBoard(self, user, self.request.get('boardID'), self.request.get('boardUser'))
			else:	
				loadBoard(self, user, -1, userGet.defaultBoardUser)
		else:
			self.redirect(users.create_login_url(self.request.uri))

#loadBoard - Function to display board
def loadBoard(self, user, boardID, boardUser):
	userKey = ndb.Key('Account', user.email())
	userGet = userKey.get()

	if userGet == None:
		#Create Acc
		logging.debug("Creating Account for: " + user.email() + ", " + user.nickname())
		currUser = Account(id=user.email(), accid=user.user_id(), usernick=user.nickname(), email=user.email())
		userGet = currUser.put()
		userKey = ndb.Key('Account', user.email())
		usernickname = user.nickname()
		boardID = 0
		boardUser = ""
	else:
		if (boardID == -1):
			boardID = userGet.defaultBoardID
		usernickname = userGet.usernick

	#Get default board if available
	try:
		if (boardID > 0):
			boardKey = ndb.Key('Account', boardUser, 'Board', int(boardID))
			currBoard = boardKey.get()
			boardData = boardKey.get().boardJSON
		else:
			currBoard = None
			boardData = ""
			
	except:
		#ERROR BOARD DOES NOT EXIST
		boardName = ""
		boardData = ""
		self.redirect("/")
		currBoard = None
		
	#Logging into Board - LoadBoard
	parameters = {
	'user': userGet,
	'user_nick': usernickname,
	'logout': users.create_logout_url(self.request.host_url),
	'currBoard': currBoard,
	'boardData': boardData,
	}

	#Dropdown button
	query = ndb.gql("SELECT * "
	"FROM Board "
	"WHERE ANCESTOR IS :1 "
	"ORDER BY boardID ASC",
	userKey)
	
	parameters.update({'boards': query,
	'boards2': [],
	})

	#PairFollowerOwner - owner = ?, follower = ?, boardID = ?
	follows = (ndb.gql("SELECT * "
	"FROM PairFollowerOwner "
	"WHERE ANCESTOR IS :1 ",
	userKey))

	#This includes the board that the user has followed
	for follow in follows:
		queryBoard = ndb.gql("SELECT * "
		"FROM Board "
		"WHERE ANCESTOR IS :1 "
		"ORDER BY boardID ASC",
		ndb.Key('Account', follow.owner))

		for board in queryBoard:
			if board.boardID in follow.boardID:
				parameters['boards2'].append(board)

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
			'user': userGet,
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
		'user': userGet,
		'logout': users.create_logout_url(self.request.host_url),
		'user_createdTotal': userGet.numBoards,
		'user_followedTotal': userGet.following,
		'update_status': status,
		}
		webpage = jinja_environment.get_template('setting.html')
		self.response.out.write(webpage.render(parameters))

#This function is used by DisplayAllBoards, refreshBoard
def showBoardsOf(instance, _target, email, template_values):
	if email != "" and email != "#":
		userKey = ndb.Key('Account', email)
		#Get All Board, for each board, display the link.
		query = ndb.gql("SELECT * "
		"FROM Board "
		"WHERE ANCESTOR IS :1 "
		"ORDER BY boardID ASC",
		userKey)
		template_values.update({
		'targetMail': email,
		'boards': query,
		})
		if query.count() == 0 and email != users.get_current_user().email():
			template_values.update({'error': "Cannot find any board for %s" % email,})
	else:
		template_values.update({'error': "User does not exist",})

	template = jinja_environment.get_template(_target)
	instance.response.out.write(template.render(template_values))

#This function is used in ChangeDefaultBoard, FollowBoard, UnfollowBaord
def refreshBoard(instance, boardUser, userKey):
	if boardUser == "":
		template_values = {
		'user': userKey.get(),
		'logout': users.create_logout_url(instance.request.host_url),
		'error': "User does not exist",
		}
		showBoardsOf(instance, "boards.html", "", template_values)
	else:
		try:
			target = ndb.Key('Account', boardUser).get()
			template_values = {
			'user': userKey.get(),
			'logout': users.create_logout_url(instance.request.host_url),
			}
			if target != None:
				template_values.update({'target_mail': boardUser,})
				showBoardsOf(instance, "boards.html", boardUser, template_values)
			else:
				showBoardsOf(instance, "boards.html", "#", template_values)
		except:
			template_values = {'error': "User does not exist",}
			showBoardsOf(instance, "boards.html", "", template_values)

#Show all Board
class DisplayAllBoards(webapp2.RequestHandler):
	def get(self):
		userKey = ndb.Key('Account', users.get_current_user().email())
		template_values = {
		'user': userKey.get(),
		'logout': users.create_logout_url(self.request.host_url),
		'error': self.request.get('error'),
		}
		showBoardsOf(self, "boards.html", users.get_current_user().email(), template_values)

	def post(self):
		userKey = ndb.Key('Account', users.get_current_user().email())
		target_mail = self.request.get('targetMail')
		if target_mail == "":
			template_values = {
				'user': userKey.get(),
				'user_mail': users.get_current_user().email(),
				'logout': users.create_logout_url(self.request.host_url),
				'error': "User does not exist",
			}
			showBoardsOf(self, "boards.html", "", template_values)
		else:
			try:
				target = ndb.Key('Account', target_mail).get()
				template_values = {
				'user': userKey.get(),
				'user_mail': users.get_current_user().email(),
				'logout': users.create_logout_url(self.request.host_url),
				}
				if target != None:
					template_values.update({'target_mail': target_mail,})
					showBoardsOf(self, "boards.html", target_mail, template_values)
				else:
					showBoardsOf(self, "boards.html", "#", template_values)
			except:
				template_values = {'error': "User does not exist",}
				showBoardsOf(self, "boards.html", "", template_values)

#Change Default Board
class ChangeDefaultBoard(webapp2.RequestHandler):
	def post(self):
		#Change Default Board - Only available to user when user has followed
		boardid = self.request.get('boardID')
		boardUser = self.request.get('boardUser')
		userKey = ndb.Key('Account', users.get_current_user().email())
		userGet = userKey.get()
		userGet.defaultBoardID = int(boardid)
		userGet.defaultBoardUser = boardUser
		userGet.put()
		refreshBoard(self, boardUser, userKey)

#Follow Board
class FollowBoard(webapp2.RequestHandler):
	def post(self):
		boardID = self.request.get('boardID')
		boardUser = self.request.get('boardUser')
		userKey = ndb.Key('Account', users.get_current_user().email())
		boardKey = ndb.Key('Account', boardUser, 'Board', int(boardID))
		currBoard = boardKey.get()
		currBoard.followers.append(users.get_current_user().email())
		currBoard.put()
		query = ndb.gql("SELECT * "
		"FROM PairFollowerOwner "
		"WHERE ANCESTOR IS :1 "
		"AND owner = :2",
		userKey, boardUser)
		pairFollower = query.fetch(1)
		if pairFollower:
			pairGet = pairFollower[0]
			pairGet.boardID.append(int(boardID))
			pairGet.put()
		else:
			pairFollower = PairFollowerOwner(parent=userKey, follower=users.get_current_user().email(), owner=boardUser, boardID=[int(boardID)])
			pairGet = pairFollower.put()
		userKey.get().following += 1
		userKey.get().put()
		refreshBoard(self, boardUser, userKey)
		

#Unfollow Board
class UnfollowBoard(webapp2.RequestHandler):
	def post(self):
		boardID = self.request.get('boardID')
		boardUser = self.request.get('boardUser')
		userKey = ndb.Key('Account', users.get_current_user().email())
		boardKey = ndb.Key('Account', boardUser, 'Board', int(boardID))
		currBoard = boardKey.get()
		currBoard.followers.remove(users.get_current_user().email())
		currBoard.put()
		query = ndb.gql("SELECT * "
		"FROM PairFollowerOwner "
		"WHERE ANCESTOR IS :1 "
		"AND owner = :2",
		userKey, boardUser)
		pairFollower = query.fetch(1)
		pairFollower = pairFollower[0]
		pairFollower.boardID.remove(int(boardID))
		pairFollower.put()
		if (len(pairFollower.boardID) == 0):
			pairFollower.key.delete()
		userKey.get().following -= 1
		userKey.get().put()
		refreshBoard(self, boardUser, userKey)

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
					currBoard.boardUser = users.get_current_user().email()
					currBoard.boardID = userGet.counter
					currBoard.boardJSON = '{"objects":[{"type":"rect","originX":"left","originY":"top","left":100,"top":100,"width":20,"height":20,"fill":"black","stroke":null,"strokeWidth":1,"strokeDashArray":null,"strokeLineCap":"butt","strokeLineJoin":"miter","strokeMiterLimit":10,"scaleX":1,"scaleY":1,"angle":0,"flipX":false,"flipY":false,"opacity":1,"shadow":null,"visible":true,"clipTo":null,"backgroundColor":"","rx":0,"ry":0,"x":0,"y":0}],"background":"white"}'
					currBoard.put()
					if userGet.numBoards == 1:
						#Set default board
						userGet.defaultBoardID = currBoard.boardID
						userGet.defaultBoardUser = users.get_current_user().email()
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

		#Delete from all followers
		#following - 1 for all followers.
		for follower in boardKey.get().followers:
			followerGet = ndb.Key('Account', follower).get()
			followerGet.following -= 1
			if followerGet.defaultBoardID == int(boardid) and followerGet.defaultBoardUser == userGet.email:
				followerGet.defaultBoardUser = ""
				followerGet.defaultBoardID = 0
			followerGet.put()
		
		boardKey.delete()
		if (userGet.numBoards > 0):
			userGet.numBoards -= 1
		if (userGet.defaultBoardID == int(boardid)):
			query = ndb.gql("SELECT * "
			"FROM Board "
			"WHERE ANCESTOR IS :1 "
			"ORDER BY boardID ASC",
			userKey)
			nextBoard = query.fetch(1)
			if (len(nextBoard) > 0):
				userGet.defaultBoardID = nextBoard[0].boardID
				userGet.defaultBoardUser = users.get_current_user().email()
			else:
				userGet.defaultBoardID = 0
				userGet.defaultBoardUser = ""
		userGet.put()
		
		self.redirect("/boards")

#Save Board
class SaveBoard(webapp2.RequestHandler):
	def post(self):
		boardID = self.request.get('boardID')
		boardUser = self.request.get('boardUser')
		bData = self.request.get('data')
		currBoard = ndb.Key('Account', boardUser, 'Board', int(boardID)).get()
		currBoard.boardJSON = bData
		currBoard.put()

#App
app = webapp2.WSGIApplication([('/', MainHandler),
	('/board', ShowBoard),
	('/newBoard', AddBoard),
	('/deleteBoard', DeleteBoard),
	('/saveBoard', SaveBoard),
	('/boards', DisplayAllBoards),
	('/followBoard', FollowBoard),
	('/unfollowBoard', UnfollowBoard),
	('/changeDefaultBoard', ChangeDefaultBoard),
	('/settings', UpdateProfile),
	('/update', UpdateProfile)], debug=True)
