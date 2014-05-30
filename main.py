#PinnerSpace - Justin and Yao Xiang
#Virtual PinBoard WebApp

import urllib
import webapp2
import jinja2
import os
import cgi
import datetime
import logging
import json

from google.appengine.ext import ndb
from google.appengine.api import users
from datetime import datetime, date, time, timedelta

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
	boardEditor = ndb.StringProperty(repeated=True)
	boardPoster = ndb.StringProperty(repeated=True)
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
	access_token = ndb.StringProperty()
	login_type = ndb.StringProperty()

class PairFollowerOwner(ndb.Model):
	follower = ndb.StringProperty()
	owner = ndb.StringProperty()
	boardID = ndb.IntegerProperty(repeated=True)


def current_user(self):
	if not hasattr(self, "_current_user"):
		if users.get_current_user():
			userKey = ndb.Key('Account', users.get_current_user().email())
			if userKey.get():
				self._current_user = userKey.get()
				self._current_user.login_type = "google"
				self._current_user.put()
			else:
				user=users.get_current_user()
				currUser = Account(id=user.email(), accid=user.user_id(), usernick=user.nickname(), email=user.email(), login_type="google")
				self._current_user = currUser.put().get()
		elif self.request.cookies.get("fb_user"):
			user_id = self.request.cookies.get("fb_user")
			self._current_user = ndb.Key('Account', user_id).get()
		else:
			self._current_user = None
	return self._current_user

#ALL USERS BELOW WILL BE FROM CURRENT_USER. ALL WILL BE RETRIEVED FROM NDB
#Handler - Displays '/'
class MainHandler(webapp2.RequestHandler):
	def get(self):
		user = current_user(self)
		if user:
				loadBoard(self, user, -1, user.defaultBoardUser)
		else:
			template = jinja_environment.get_template('mainpage.html') 
			self.response.out.write(template.render())

#ShowBoard - Displays '/board'
class ShowBoard(webapp2.RequestHandler):
	def get(self):
		user=current_user(self)
		if user:
			if (self.request.get('boardID') > 0):
				loadBoard(self, user, self.request.get('boardID'), self.request.get('boardUser'))
			else:	
				loadBoard(self, user, -1, user.defaultBoardUser)
		else:
			self.redirect('/')

#loadBoard - Function to display board
def loadBoard(self, user, boardID, boardUser):
	if user == None:
		#Create Acc
		logging.debug("Creating Account for: " + user.email + ", " + user.usernick)
		currUser = Account(id=user.email, usernick=user.usernick, email=user.email)
		userGet = currUser.put()
		userKey = ndb.Key('Account', user.email)
		usernickname = user.nickname()
		boardID = 0
		boardUser = ""
	else:
		if (boardID == -1):
			boardID = user.defaultBoardID

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
	'user': user,
	'user_nick': user.usernick,
	'currBoard': currBoard,
	'boardData': boardData,
	}

	userKey = ndb.Key('Account', user.email)
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
		user=current_user(self)
		if user:
			userGet = ndb.Key('Account', user.email).get()
			if userGet:
				parameters = {
				'user': userGet,
				'user_createdTotal': userGet.numBoards,
				'user_followedTotal': userGet.following,
				'update_status': "",
				}
				webpage = jinja_environment.get_template('setting.html')
				self.response.out.write(webpage.render(parameters))
			else:
				self.redirect('/')
		else:
			self.redirect('/')

	def post(self):
		user=current_user(self)
		try:
			userGet = ndb.Key('Account', user.email).get()
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
		'user_createdTotal': userGet.numBoards,
		'user_followedTotal': userGet.following,
		'update_status': status,
		}
		webpage = jinja_environment.get_template('setting.html')
		self.response.out.write(webpage.render(parameters))

#This function is used by DisplayAllBoards, refreshBoard
def showBoardsOf(instance, _target, email, template_values):
	user=current_user(instance)
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
		'numBoards': query.count(),
		})
		if query.count() == 0 and email != user.email:
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
		'error': "User does not exist",
		}
		showBoardsOf(instance, "boards.html", "", template_values)
	else:
		try:
			target = ndb.Key('Account', boardUser).get()
			template_values = {
			'user': userKey.get(),
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
		user=current_user(self)
		if user:
			userKey = ndb.Key('Account', user.email)
			template_values = {
			'user': userKey.get(),
			'error': self.request.get('error'),
			}
			showBoardsOf(self, "boards.html", user.email, template_values)
		else:
			self.redirect('/')

	def post(self):
		user=current_user(self)
		userKey = ndb.Key('Account', user.email)
		target_mail = self.request.get('targetMail')
		if target_mail == "":
			template_values = {
				'user': userKey.get(),
				'user_mail': user.email,
				'error': "User does not exist",
			}
			showBoardsOf(self, "boards.html", "", template_values)
		else:
			try:
				target = ndb.Key('Account', target_mail).get()
				template_values = {
				'user': userKey.get(),
				'user_mail': user.email,
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
		user=current_user(self)
		#Change Default Board - Only available to user when user has followed
		boardid = self.request.get('boardID')
		boardUser = self.request.get('boardUser')
		userKey = ndb.Key('Account', user.email)
		userGet = userKey.get()
		userGet.defaultBoardID = int(boardid)
		userGet.defaultBoardUser = boardUser
		userGet.put()
		refreshBoard(self, boardUser, userKey)

#Follow Board
class FollowBoard(webapp2.RequestHandler):
	def post(self):
		user=current_user(self)
		boardID = self.request.get('boardID')
		boardUser = self.request.get('boardUser')
		userKey = ndb.Key('Account', user.email)
		boardKey = ndb.Key('Account', boardUser, 'Board', int(boardID))
		currBoard = boardKey.get()
		currBoard.followers.append(user.email)
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
			pairFollower = PairFollowerOwner(parent=userKey, follower=user.email, owner=boardUser, boardID=[int(boardID)])
			pairGet = pairFollower.put()
		userKey.get().following += 1
		userKey.get().put()
		refreshBoard(self, boardUser, userKey)
		

#Unfollow Board
class UnfollowBoard(webapp2.RequestHandler):
	def post(self):
		user=current_user(self)
		boardID = self.request.get('boardID')
		boardUser = self.request.get('boardUser')
		userKey = ndb.Key('Account', user.email)
		boardKey = ndb.Key('Account', boardUser, 'Board', int(boardID))
		currBoard = boardKey.get()
		currBoard.followers.remove(user.email)
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
		user=current_user(self)
		error = ""
		bName = self.request.get('boardName')
		if bName != "":
			try:
				userKey = ndb.Key('Account', user.email)
				userGet = userKey.get()
				if userGet.numBoards < MAX_BOARD:
					userGet.numBoards += 1
					userGet.counter += 1
					currBoard = Board(parent=userKey, id=userGet.counter)
					currBoard.boardName = bName
					currBoard.boardUser = user.email
					currBoard.boardID = userGet.counter
					currBoard.boardJSON = '{"objects":[],"background":"#966C42"}'
					currBoard.put()
					if userGet.numBoards == 1:
						#Set default board
						userGet.defaultBoardID = currBoard.boardID
						userGet.defaultBoardUser = user.email
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
		user=current_user(self)
		boardid = self.request.get('boardID')
		userKey = ndb.Key('Account', user.email)
		userGet = userKey.get()
		#Delete Board Entity
		boardKey = ndb.Key('Account', user.email, 'Board', int(boardid))

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
				userGet.defaultBoardUser = user.email
			else:
				userGet.defaultBoardID = 0
				userGet.defaultBoardUser = ""
		userGet.put()
		
		self.redirect("/boards")

#Save Board
class SaveBoard(webapp2.RequestHandler):
	def post(self):
		user=current_user(self)
		boardID = self.request.get('boardID')
		boardUser = self.request.get('boardUser')
		bData = self.request.get('data')
		currBoard = ndb.Key('Account', boardUser, 'Board', int(boardID)).get()
		currBoard.boardJSON = bData
		currBoard.put()


def show(instance, boardID):
	user=current_user(instance)
	userGet = ndb.Key('Account', user.email).get()
	currBoard = ndb.Key('Account', user.email, 'Board', int(boardID)).get()
	if userGet:
		parameters = {
		'user': userGet,
		'board': currBoard,
		}
		webpage = jinja_environment.get_template('boardsettings.html')
		instance.response.out.write(webpage.render(parameters))
	else:
		instance.redirect(users.create_login_url(instance.request.uri))

class ShowBoardSettings(webapp2.RequestHandler):
	def post(self):
		show(self, self.request.get('boardID'))

#Update Board Settings
class UpdateBoard(webapp2.RequestHandler):
	def post(self):
		user=current_user(self)
		boardID = self.request.get('boardID')
		userGranted = self.request.get('userGranted')
		userPermission = self.request.get('userPermission')
		userState = self.request.get('state')
		currBoard = ndb.Key('Account', user.email, 'Board', int(boardID)).get()

		if userState == "editor":
			currBoard.boardEditor.remove(userGranted)
		if userState == "poster":
			currBoard.boardPoster.remove(userGranted)

		if userPermission == "edit":
			currBoard.boardEditor.append(userGranted)
		if userPermission == "post":
			currBoard.boardPoster.append(userGranted)

		currBoard.put()
		show(self, boardID)

class LoginFBHandler(webapp2.RequestHandler):
	def get(self):
		args = dict(client_id='1430441490551788', redirect_uri="http://pinnerspace.appspot.com/login/FB", scope="email")
		self.redirect("https://graph.facebook.com/oauth/authorize?" + urllib.urlencode(args))
		args["client_secret"] = '34ba2e64a0f9be54ec21f5a7e4646957'
		args["code"] = self.request.get("code")
		response = cgi.parse_qs(urllib.urlopen("https://graph.facebook.com/oauth/access_token?" + urllib.urlencode(args)).read())
		access_token = response["access_token"][-1]

		profile = json.load(urllib.urlopen("https://graph.facebook.com/me?" + urllib.urlencode(dict(access_token=access_token))))
		fbuser = ndb.Key('Account', str(profile["email"]))
		if fbuser.get() == None:
			user = Account(id=str(profile["email"]), accid=str(profile["id"]), usernick=profile["name"], email=str(profile["email"]), access_token=access_token, login_type="facebook")
			user.put()
		else:
			fbuser.get().access_token = access_token
			fbuser.get().login_type = "facebook"
			fbuser.get().put()
		self.response.set_cookie("fb_user", str(profile["email"]), expires=datetime.now() + timedelta(days=1))
		self.redirect("/")

class LoginFB(webapp2.RequestHandler):
	def get(self):
		args = dict(client_id='1430441490551788', redirect_uri="http://pinnerspace.appspot.com/login/FB")
		self.redirect("https://graph.facebook.com/oauth/authorize?" + urllib.urlencode(args))

class LoginGoogleHandler(webapp2.RequestHandler):
	def get(self):
		self.redirect(users.create_login_url(self.request.host_url))

class LogoutHandler(webapp2.RequestHandler):
	def get(self):
		user=current_user(self)
		if user.login_type == "google":
			url = users.create_logout_url(self.request.host_url)
			self.redirect(url)
		else:
			self.response.set_cookie("fb_user", "", expires=datetime.now() - timedelta(days=1) )
			self.redirect('/')

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
	('/boardSettings', ShowBoardSettings),
	('/updateBoard', UpdateBoard),
	('/settings', UpdateProfile),
	('/update', UpdateProfile),
	('/login', MainHandler),
	('/login/FB', LoginFBHandler),
	('/login/Google', LoginGoogleHandler),
	('/logout', LogoutHandler),
	('/login/FaceBook', LoginFB)], debug=True)
