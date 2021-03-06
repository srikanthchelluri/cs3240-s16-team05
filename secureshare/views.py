from django.shortcuts import render, render_to_response
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, update_session_auth_hash
from django.db.models import Q
from secureshare.models import User, UserProfile, Message, Group, Report, Folder
from secureshare.forms import UserForm, UserProfileForm, ReportForm, PasswordChangeForm
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.core.urlresolvers import reverse
from Crypto.Cipher import AES
import datetime
import binascii
import mimetypes
import hashlib
from django.views.decorators.csrf import csrf_exempt
import requests


def userlogin(request):
	if len(UserProfile.objects.filter(siteManager = True)) == 0:
		siteManager1 = User(username='admin',email='sc5ba@virginia.edu')
		siteManager1.set_password('admin')
		siteManager1.save()
		SMprofile = UserProfile(user=siteManager1,siteManager=True,picture='profile_images/Generic_Avatar.png')
		SMprofile.save()

	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')
		user = authenticate(username=username, password=password)
		if user:
			if user.is_active:
				login(request, user)
				return HttpResponseRedirect('/secureshare/home/')
			else:
				return HttpResponse("Your account is disabled.")
		else:
			return render(request, 'secureshare/failed.html')
	else:
		if (request.user.is_authenticated()):
			return HttpResponseRedirect('/secureshare/home/')
		return render(request, 'secureshare/login.html')


def register(request):
	registered = False
	if request.method == 'POST':
		user_form = UserForm(data=request.POST)
		profile_form = UserProfileForm(data=request.POST)
		if user_form.is_valid() and profile_form.is_valid():
			# Save the user's form data to the database.
			user = user_form.save()
			profile = profile_form.save(commit=False)
			profile.user = user
			if user.password != profile.password2:
				print('passwordsDontMatch')
				user.delete()
				return render(request, 'secureshare/failed.html')
			user.set_password(user.password)
			user.save()
			profile.password2 = 'Secret'  # dont save any copy of the users actual password!!
			profile.picture = 'profile_images/Generic_Avatar.png'
			if 'picture' in request.FILES:
				profile.picture = request.FILES['picture']
			profile.save()
			registered = True
		else:
			return render(request, 'secureshare/failed.html')
	else:
		user_form = UserForm()
		profile_form = UserProfileForm()
	return render(request, 'secureshare/register.html',
								{'user_form': user_form, 'profile_form': profile_form, 'registered': registered})


@login_required
def userlogout(request):
	logout(request)
	return HttpResponseRedirect('/secureshare/')


def home(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	unreadMessageCount = len(Message.objects.filter(receiver=request.user, read=False))
	reportCount = len(Report.objects.filter(owner=request.user))
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return render(request, 'secureshare/home.html',
								{'unreadMessageCount': unreadMessageCount, 'reportCount': reportCount, 'siteManager': siteManager})


def createreport(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		report_form = ReportForm(request.POST or None, request.FILES or None)
		if report_form.is_valid():
			name = report_form.cleaned_data['name']
			owner = request.user
			t = datetime.datetime.now()
			timeStr = str(t)[:-7]
			short_description = report_form.cleaned_data['short_description']
			detailed_description = report_form.cleaned_data['detailed_description']
			file1 = file2 = file3 = file4 = file5 = ''
			if 'file1' in request.FILES:
				file1 = request.FILES['file1']
			if 'file2' in request.FILES:
				file2 = request.FILES['file2']
			if 'file3' in request.FILES:
				file3 = request.FILES['file3']
			if 'file4' in request.FILES:
				file4 = request.FILES['file4']
			if 'file5' in request.FILES:
				file5 = request.FILES['file5']
			private = report_form.cleaned_data['private']
			encrypt = report_form.cleaned_data['encrypt']
			tags = report_form.cleaned_data['tags']
			# Hash check
			m = hashlib.md5()
			toHash = str(owner) + str(timeStr) + str(short_description) + str(detailed_description) + str(file1) + str(
			 		file2) + str(file3) + str(file4) + str(file5) + str(private) + str(encrypt)
			uni = b'toHash'
			m.update(uni)
			int_hash = m.hexdigest()
			report = Report(
					name = name,
					owner=owner,
					created_at=timeStr,
					short_description=short_description,
					detailed_description=detailed_description,
					file1=file1,
					file2=file2,
					file3=file3,
					file4=file4,
					file5=file5,
					private=private,
					encrypt=encrypt,
					int_hash=int_hash,
					tags=tags,
			)
			report.save()
			siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
			return render(request, 'secureshare/create-report.html',
										{'report_form': report_form, 'message': "The report was successfully submitted.",
										 'siteManager': siteManager})
		else:
			siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
			return render(request, 'secureshare/create-report.html',
										{'report_form': report_form, 'message': "You need to fill out a name, short description, long description, and tags.",
										 'siteManager': siteManager})
	else:
		report_form = ReportForm()
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		return render(request, 'secureshare/create-report.html',
									{'report_form': report_form, 'siteManager': siteManager})


@csrf_exempt
def fda_reports(request):
	reportList = Report.objects.filter(owner=request.user)
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return render(request, 'secureshare/fda_reports.html', {'reportList': reportList, 'siteManager': siteManager})


def managereports(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	reportList = Report.objects.filter(owner=request.user)
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return render(request, 'secureshare/manage-reports.html', {'reportList': reportList, 'siteManager': siteManager})


def requestnewusertoreport(request, report_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		reportList = Report.objects.filter(owner=request.user)
		user = request.user
		report = Report.objects.filter(id=report_pk)[0]
		userToAddUsername = request.POST.get('user')
		userToAddList = User.objects.filter(username=userToAddUsername)
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		if len(userToAddList) == 0:
			return render(request, 'secureshare/manage-reports.html',
										{'reportList': reportList, 'message': 'Couldn\'t find that user.',
										 'siteManager': siteManager})
		userToAdd = userToAddList[0]
		if userToAdd in report.auth_users.all():
			return render(request, 'secureshare/manage-reports.html',
										{'reportList': reportList, 'message': "That user is already shared.",
										 'siteManager': siteManager})
		else:
			report.auth_users.add(userToAdd)
			return render(request, 'secureshare/manage-reports.html',
										{'reportList': reportList, 'message': "Shared successfully.", 'siteManager': siteManager})

def requestnewgrouptoreport(request, report_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		reportList = Report.objects.filter(owner=request.user)
		user = request.user
		report = Report.objects.filter(id=report_pk)[0]
		groupToAddName = request.POST.get('group')
		groupToAddList = Group.objects.filter(name=groupToAddName)
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		if len(groupToAddList) == 0:
			return render(request, 'secureshare/manage-reports.html',
										{'reportList': reportList, 'message': 'Couldn\'t find that group.',
										 'siteManager': siteManager})
		groupToAdd = groupToAddList[0]
		usersInGroup = groupToAdd.user_set.all()
		for user in usersInGroup:
			if user not in report.auth_users.all():
				report.auth_users.add(user)
		return render(request, 'secureshare/manage-reports.html',
										{'reportList': reportList, 'message': "Shared successfully.", 'siteManager': siteManager})


def requestdeletereport(request, report_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	report = Report.objects.filter(id=report_pk).delete()
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return HttpResponseRedirect('/secureshare/managereports/', {'siteManager': siteManager})


def requesteditreport(request, report_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		report = Report.objects.filter(id=report_pk)[0]
		name = request.POST.get('name')
		short_description = request.POST.get('shortdescription')
		detailed_description = request.POST.get('detaileddescription')
		user = request.user
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		if user.is_active:
			if name != '':
				report.name = name
			if short_description != '':
				report.short_description = short_description
			if detailed_description != '':
				report.detailed_description = detailed_description
			report.save()
		return render(request, 'secureshare/report-page.html', {'report': report, 'siteManager': siteManager})
	else:
		return render(request, 'secureshare/report-page.html', {'report': report, 'siteManager': siteManager})


def reportpage(request, report_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	reportList = Report.objects.filter(id=report_pk)
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	if len(reportList) == 0:
		return render(request, 'secureshare/report-page.html',
									{'message': "That report does not exist", 'siteManager': siteManager})
	else:
		report = reportList[0]
		profile = UserProfile.objects.get(user=request.user)
		if request.user in report.auth_users.all() or report.owner == request.user or profile.siteManager or report.private == False:
			return render(request, 'secureshare/report-page.html', {'report': report, 'siteManager': siteManager})
		else:
			return render(request, 'secureshare/report-page.html',
										{'message': "You are not authorized to see this report.", 'siteManager': siteManager})

@csrf_exempt
def requestfiledownload(request, report_pk, file_pk):
	# not request.user.is_authenticated():
	#return render(request, 'secureshare/failed.html')
	# Add check to see if report exists (for invalid URL)
	report_id = report_pk[0:report_pk.index("/")]
	file_directory = report_pk[report_pk.index("/"):] + "/"
	report = Report.objects.get(id=report_id)

	fp = open('static/' + file_directory[1:] + file_pk, 'rb')
	response = HttpResponse(fp.read())
	fp.close()
	type, encoding = mimetypes.guess_type(file_pk)
	if type is None:
		type = 'application/octet-stream'
	response['Content-Type'] = type
	if encoding is not None:
		response['Content-Encoding'] = encoding
	if u'WebKit' in request.META['HTTP_USER_AGENT']:
		filename_header = 'filename=%s' % file_pk.encode('utf-8')
	elif u'MSIE' in request.META['HTTP_USER_AGENT']:
		filename_header = ''
	else:
		filename_header = 'filename*=UTF-8\'\'%s' & urllib.quote(original_filename.encode('utf-8'))
	filename_header = filename_header[2:]  # fixes byte string output
	response['Content-Disposition'] = 'attachment; ' + filename_header
	
	return response

def viewreports(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	authReportList = Report.objects.filter(auth_users__username=request.user)
	profile = UserProfile.objects.get(user=request.user)
	if profile.siteManager == True:
		authReportList = Report.objects.all()
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return render(request, 'secureshare/view-reports.html',
								{'authReportList': authReportList, 'siteManager': siteManager})


def searchreports(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		query = request.POST.get('query')
		if "AND" in query:
			queryList = query.split(" AND ")
			results1 = Report.objects.all()
			for item in queryList:
				results1 = results1.filter(
					Q(owner__username__icontains=item) |
					Q(created_at__icontains=item) |
					Q(short_description__icontains=item) |
					Q(detailed_description__icontains=item) |
					Q(name__icontains=item)
				)
			results = list(results1)
			for report in results:
				if report.private == True:
					if request.user not in report.auth_users.all() or not siteManager:
						results.remove(report)
			return render(request, 'secureshare/search-reports.html',
										{'results': results, 'query': "You searched for: " + query + ".", 'siteManager': siteManager})
		elif "OR" in query:
			queryList = query.split(" OR ")
			results1 = []
			for item in queryList:
				results1.extend(list(Report.objects.filter(
					Q(owner__username__icontains=item) |
					Q(created_at__icontains=item) |
					Q(short_description__icontains=item) |
					Q(detailed_description__icontains=item) |
					Q(name__icontains=item)
				)))
			results = results1
			for report in results:
				if report.private == True:
					if request.user not in report.auth_users.all() or not siteManager:
						results.remove(report)
			return render(request, 'secureshare/search-reports.html',
										{'results': results, 'query': "You searched for: " + query + ".", 'siteManager': siteManager})
		else:
			results1 = Report.objects.filter(
					Q(owner__username__icontains=query) |
					Q(created_at__icontains=query) |
					Q(short_description__icontains=query) |
					Q(detailed_description__icontains=query) |
					Q(name__icontains=query) |
					Q(tags__icontains=query)
			)
			results = list(results1)
			for report in results:
				if report.private == True:
					if request.user not in report.auth_users.all() or not siteManager:
						results.remove(report)
			return render(request, 'secureshare/search-reports.html',
										{'results': results, 'query': "You searched for: " + query + ".", 'siteManager': siteManager})
	else:
		return HttpResponseRedirect('/secureshare/viewreports/')

def searchreportsadvanced(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		name = request.POST.get('name')
		owner = request.POST.get('owner')
		encrypted = request.POST.get('encrypted')
		tags = request.POST.get('tags')
		description = request.POST.get('description')
		if not name:
			name = ""
		if not owner:
			owner = ""
		if not description:
			description = ""
		if not tags:
			tags = ""
		if encrypted == "yes":
			results1 = Report.objects.filter(encrypt=True)
		elif encrypted == "no":
			results1 = Report.objects.filter(encrypt=False)
		else:
			results1 = Report.objects.all()
		results1 = results1.filter(
				Q(name__icontains=name) &
				Q(owner__username__icontains=owner) &
				(Q(short_description__icontains=description) |
				 Q(detailed_description__icontains=description)) 
		)
		if tags != "":
			results1 = results1.filter(
				Q(tags__icontains=tags)
			)
		results = list(results1)
		for report in results:
			if report.private == True:
				if request.user not in report.auth_users.all() or not siteManager:
					results.remove(report)
		return render(request, 'secureshare/search-reports.html',
									{'results': results, 'query': "You used an advanced search.", 'siteManager': siteManager})
	else:
		return HttpResponseRedirect('/secureshare/viewreports/')


def searchusers(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		query = request.POST.get('query')
		results = UserProfile.objects.filter(
				Q(user__username__icontains=query)
		)
		return render(request, 'secureshare/search-users.html',
									{'results': results, 'query': query, 'siteManager': siteManager})
	else:
		return HttpResponseRedirect('/secureshare/home/')


def managefolders(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	reportList = Report.objects.filter(owner=request.user)
	folderList = Folder.objects.filter(owner=request.user)
	noFolderList = Report.objects.filter(owner=request.user, folders=None)
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return render(request, 'secureshare/manage-folders.html',
								{'folderList': folderList, 'reportList': reportList, 'noFolderList': noFolderList,
								 'siteManager': siteManager})


def requestcreatefolder(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		reportList = Report.objects.filter(owner=request.user)
		folderList = Folder.objects.filter(owner=request.user)
		folderName = request.POST.get('folderName')
		user = request.user
		if user.is_active:
			currentFolderList = Folder.objects.filter(owner=request.user, name=folderName)
			if len(currentFolderList) == 0:
				folder = Folder(owner=request.user, name=folderName)
				folder.save()
				return HttpResponseRedirect('/secureshare/managefolders')
			else:
				return render(request, 'secureshare/manage-folders.html',
											{'folderList': folderList, 'reportList': reportList,
											 'message': "That folder already exists."})
		else:
			return render(request, 'secureshare/failed.html')
	else:
		return render(request, 'secureshare/failed.html')


def requestaddtofolder(request, report_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		folderName = request.POST.get('folderName')
		user = request.user
		if user.is_active:
			report = Report.objects.filter(id=report_pk)[0]
			report.folders.add(Folder.objects.filter(owner=request.user, name=folderName)[0])
			return HttpResponseRedirect('/secureshare/managefolders')
		else:
			return render(request, 'secureshare/failed.html')
	else:
		return render(request, 'secureshare/failed.html')


def requestdeletefolder(request, folder_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	folder_id = folder_pk[0:len(folder_pk) - 1]
	Folder.objects.filter(owner=request.user, id=folder_id).delete()
	return HttpResponseRedirect('/secureshare/managefolders')


def requestremovefromfolder(request, folder_pk, report_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	report = Report.objects.filter(id=report_pk)[0]
	folder = Folder.objects.filter(id=folder_pk)[0]
	report.folders.remove(folder)
	return HttpResponseRedirect('/secureshare/managefolders')


def requestrenamefolder(request, folder_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		folder = Folder.objects.get(id=folder_pk)
		folder.name = request.POST.get('folderName')
		folder.save()
		return HttpResponseRedirect('/secureshare/managefolders')

# For AES encryption/decryption
key = "7AqDiyLmzcjmPO7n"


# class AESCipher adapted from GitHub
class AESCipher:
	def __init__(self, key):
		self.key = bytes(key, encoding='utf-8')
		self.BLOCK_SIZE = 16

	def __pad(self, raw):
		if (len(raw) % self.BLOCK_SIZE == 0):
			return raw
		padding_required = self.BLOCK_SIZE - (len(raw) % self.BLOCK_SIZE)
		padChar = b'\x00'
		data = raw.encode('utf-8') + padding_required * padChar
		return data

	def __unpad(self, s):
		s = s.rstrip(b'\x00')
		return s

	def encrypt(self, raw):
		if (raw is None) or (len(raw) == 0):
			raise ValueError('input text cannot be null or empty set')
		raw = self.__pad(raw)
		cipher = AES.new(self.key[:32], AES.MODE_ECB)
		ciphertext = cipher.encrypt(raw)
		return binascii.hexlify(bytearray(ciphertext)).decode('utf-8')

	def decrypt(self, enc):
		if (enc is None) or (len(enc) == 0):
			raise ValueError('input text cannot be null or empty set')
		enc = binascii.unhexlify(enc)
		cipher = AES.new(self.key[:32], AES.MODE_ECB)
		enc = self.__unpad(cipher.decrypt(enc))
		return enc.decode('utf-8')


def viewmessages(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	messageIn = Message.objects.filter(receiver=request.user)
	Message.objects.filter(receiver=request.user).update(read=True)
	messageOut = Message.objects.filter(sender=request.user)
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return render(request, 'secureshare/view-messages.html',
								{'messageIn': messageIn, 'messageOut': messageOut, 'siteManager': siteManager})


def sendmessage(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		recepient = request.POST.get('recepient')
		message = request.POST.get('message')
		encrypt = request.POST.get('encrypt')
		user = request.user
		if user.is_active:
			# Check if recepient exists
			listUser = User.objects.filter(username=recepient)
			if len(listUser) == 0:
				messageList = Message.objects.all()
				messageIn = []
				messageOut = []
				for message in messageList:
					if message.receiver == request.user:
						messageIn.append(message)
					if message.sender == request.user:
						messageOut.append(message)
						siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
				return render(request, 'secureshare/view-messages.html',
											{'messageIn': messageIn, 'messageOut': messageOut, 'message': "That user doesn't exist.",
											 'siteManager': siteManager})
			# Save to database
			recepientUser = User.objects.filter(username=recepient)[0]
			t = datetime.datetime.now()
			timeStr = str(t)[:-7]
			if encrypt == "encrypted":
				aesObj = AESCipher(key)
				encryptedMsg = aesObj.encrypt(message)
				msg = Message(sender=user, receiver=recepientUser, content=encryptedMsg, created_at=timeStr,
											encrypt=True, read=False)
			else:
				databaseMessage = message
				msg = Message(sender=user, receiver=recepientUser, content=databaseMessage, created_at=timeStr,
											encrypt=False, read=False)
			msg.save()
			siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
			return HttpResponseRedirect('/secureshare/viewmessages/')
		else:
			return render(request, 'secureshare/failed.html')
	else:
		if (request.user.is_authenticated()):
			return HttpResponseRedirect('/secureshare/home/')
		return render(request, 'secureshare/login.html')


def decryptmessage(request, message_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	message = Message.objects.filter(id=message_pk)[0]
	if message.encrypt:
		aesObj = AESCipher(key)
		decrypted = aesObj.decrypt(message.content)
		return HttpResponse(decrypted + "<br><br><a href='/secureshare/viewmessages/'>Go back</a>")
	else:
		return HttpResponse(
			"That message was not encrypted. Go back to see the plaintext." + "<br><br><a href='/secureshare/viewmessages/'>Go back</a>")


def deletemessage(request, message_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	Message.objects.filter(id=message_pk).delete()
	return HttpResponseRedirect('/secureshare/viewmessages/')


def deletesentmessages(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	Message.objects.filter(sender=request.user).delete()
	return HttpResponseRedirect('/secureshare/viewmessages')


def deletereceivedmessages(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	Message.objects.filter(receiver=request.user).delete()
	return HttpResponseRedirect('/secureshare/viewmessages')


def managegroups(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	user = User.objects.filter(username=request.user)[0]
	profile = UserProfile.objects.get(user=request.user)
	groupList = user.groups.all()
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	if profile.siteManager:
		groupList2 = Group.objects.all()
		return render(request, 'secureshare/manage-groups.html',
									{'groupList': groupList, 'groupList2': groupList2, 'siteManager': siteManager})
	return render(request, 'secureshare/manage-groups.html', {'groupList': groupList, 'siteManager': siteManager})


def requestnewusertogroup(request, group_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		user = request.user
		groupList = user.groups.all()
		userToAddUsername = request.POST.get('user')
		userToAddList = User.objects.filter(username=userToAddUsername)
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		if len(userToAddList) == 0:
			return render(request, 'secureshare/manage-groups.html',
										{'groupList': groupList, 'message': 'Couldn\'t find that user.', 'siteManager': siteManager})
		userToAdd = userToAddList[0]
		if userToAdd.groups.filter(id=group_pk).exists():
			return render(request, 'secureshare/manage-groups.html',
										{'groupList': groupList, 'message': "That user is already a member.",
										 'siteManager': siteManager})
		else:
			group = Group.objects.filter(id=group_pk)[0]
			group.user_set.add(userToAdd)
			return HttpResponseRedirect('/secureshare/grouppage/' + group.name)
			#return render(request, 'secureshare/manage-groups.html',
			 #             {'groupList': groupList, 'message': "Added successfully.", 'siteManager': siteManager})


def requestdeletefromgroup(request, group_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	group = Group.objects.filter(id=group_pk)[0]
	group.user_set.remove(request.user)
	return HttpResponseRedirect('/secureshare/managegroups/')


def creategroup(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return render(request, 'secureshare/create-group.html', {'siteManager': siteManager})


def requestgroup(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		groupName = request.POST.get('groupName')
		user = request.user
		if user.is_active:
			groupList = Group.objects.filter(name=groupName)
			user = User.objects.filter(username=request.user)[0]
			if len(groupList) == 0:  # Group does not exist
				group = Group(name=groupName)
				group.save()
				user.groups.add(group)
				siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
				return render(request, 'secureshare/create-group.html',
											{'message': "You have been added.", 'siteManager': siteManager})
			else:
				siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
				return render(request, 'secureshare/create-group.html',
											{'message': "That group already exists.", 'siteManager': siteManager})
		else:
			return render(request, 'secureshare/failed.html')
	else:
		return render(request, 'secureshare/failed.html')


def grouppage(request, group_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	groupList = Group.objects.filter(name=group_pk)
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	if len(groupList) == 0:
		return render(request, 'secureshare/group-page.html',
									{'message': "That group does not exist.", 'siteManager': siteManager})
	else:
		group = groupList[0]
		name = group.name
		members = group.user_set.all()
		profile = UserProfile.objects.get(user=request.user)
		profiles = []
		for member in members:
			aProfile = UserProfile.objects.get(user__username=member.username)
			profiles.append(aProfile)
		if request.user in group.user_set.all() or profile.siteManager:
			return render(request, 'secureshare/group-page.html',
										{'group': group, 'name': name, 'members': members, 'siteManager': siteManager,
										 'profiles': profiles})
		else:
			return render(request, 'secureshare/group-page.html',
										{'message': "You are not authorized to see this group.", 'siteManager': siteManager})


def removeuserfromgroup(request, group_pk, user_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	group = Group.objects.get(name=group_pk)
	user = User.objects.get(id=user_pk)
	group.user_set.remove(user)
	return grouppage(request,group_pk)

def manageaccount(request):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		password_change_form = PasswordChangeForm(data=request.POST)
		newEmail = request.POST.get('newEmail')
		if password_change_form.is_valid():
			user = request.user
			oldpassword = request.POST.get('oldPassword')
			newpassword = request.POST.get('newPassword')
			if user.check_password(oldpassword):
				user.set_password(newpassword)
				user.save()
				update_session_auth_hash(request, user)
				siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
				return render(request, 'secureshare/home.html', {'siteManager': siteManager})
			else:
				return render(request, 'secureshare/failed.html')
		elif newEmail:
			user = request.user
			newEmail = request.POST.get('newEmail')
			user.email = newEmail
			user.save()
			siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
			return render(request, 'secureshare/home.html', {'siteManager':siteManager})
		else:
			siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
			return render(request, 'secureshare/manage-account.html',
								{'password_change_form': password_change_form, 'siteManager': siteManager, 'message': 'Invalid input received'})
	else:
		password_change_form = PasswordChangeForm(data=request.POST)
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return render(request, 'secureshare/manage-account.html',
								{'password_change_form': password_change_form, 'siteManager': siteManager})


def userprofile(request, user_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	modUserList = UserProfile.objects.filter(user_id=user_pk)
	if len(modUserList) == 0:
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		return render(request, 'secureshare/user-profile.html',
									{'message': "That user does not exist", 'siteManager': siteManager})
	else:
		modUser = modUserList[0]
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		publicReportList = Report.objects.filter(owner=modUser.user)
		if not siteManager:
			publicReportList = publicReportList.filter(private=False)
		reportCount = len(Report.objects.filter(owner=modUser.user))
		return render(request, 'secureshare/user-profile.html', {'profile': modUser, 'siteManager': siteManager, 'reportCount': reportCount, 'publicReportList':publicReportList})


def manageusersreports(request):
	if not UserProfile.objects.get(user_id=request.user.id).siteManager:
		return render(request, 'secureshare/failed.html')
	allUserList = UserProfile.objects.all()
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return render(request, 'secureshare/manage-users-and-reports.html',
								{'allUserList': allUserList, 'siteManager': siteManager})


def requestedituser(request, user_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.method == 'POST':
		modUser = UserProfile.objects.filter(user_id=user_pk)[0]
		siteM = request.POST.get('siteM')
		modEmail = request.POST.get('email')
		siteMBool = False
		message = ''
		if siteM == "True":
			siteMList = UserProfile.objects.filter(siteManager=True)
			if siteMList.__len__() < 3:
				siteMBool = True
			else:
				message = '3 Site Managers already exist. To create another, remove an existing site manager'
		modUser.siteManager = siteMBool
		modUser.user.email = modEmail
		modUser.user.save()
		modUser.save()
		reportCount = len(Report.objects.filter(owner=modUser.user))
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		publicReportList = Report.objects.filter(owner=modUser.user)
		if not siteManager:
			publicReportList = publicReportList.filter(private=False)
		return render(request, 'secureshare/user-profile.html',
									{'profile': modUser, 'siteManager': siteManager, 'message': message, 'reportCount':reportCount, 'publicReportList':publicReportList})
	else:
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		return render(request, 'secureshare/manage-users-and-reports.html.html', {'siteManager': siteManager})


def deactivateuser(request, user_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.user.username == UserProfile.objects.get(user_id=user_pk).user.username:
		return render(request, 'secureshare/failed.html')
	modUser = UserProfile.objects.get(user_id=user_pk).user
	modUser.is_active = False
	modUser.save()
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return HttpResponseRedirect('/secureshare/manageusersreports/', {'siteManager': siteManager})


def activateuser(request, user_pk):
	if not request.user.is_authenticated():
		return render(request, 'secureshare/failed.html')
	if request.user.username == UserProfile.objects.get(user_id=user_pk).user.username:
		return render(request, 'secureshare/failed.html')
	modUser = UserProfile.objects.get(user_id=user_pk).user
	modUser.is_active = True
	modUser.save()
	siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
	return HttpResponseRedirect('/secureshare/manageusersreports/', {'siteManager': siteManager})


# fda
@csrf_exempt
def fdalogin(request):
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')
		user = authenticate(username=username, password=password)
		if user:
			if user.is_active:
				login(request, user)
				return HttpResponse('Login successful.')
			else:
				return HttpResponse('Your account is disabled.')
		else:
			return HttpResponse('Login failed.')

@csrf_exempt
def fdaviewreports(request):
	if not request.user.is_authenticated():
		return HttpResponse('You are not authenticated')
	if request.user.is_active:
		# reportList = Report.objects.filter(owner=request.user)
		siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
		results1 = Report.objects.all()
		reportList = list(results1)
		for report in reportList:
			if report.private == True:
				if request.user not in report.auth_users.all() or not siteManager:
					reportList.remove(report)
		if len(reportList) == 0:
			return HttpResponse("You don't have any reports to view.")
		else:
			myResponse = ""
			myResponse += ("These are the reports that are available to you:")
			for report in reportList:
					myResponse += ("\nReport ID: " + str(report.id) + "\n   Name: " + report.name + "\n   Owner: " + str(report.owner) + "\n   Short description: " + report.short_description + "\n   Encrypted = " + str(
					report.encrypt) + "\n" + "\n")
			return HttpResponse(myResponse)


@csrf_exempt
def fdadisplayreport(request):
	if not request.user.is_authenticated():
		return HttpResponse("You are not authenticated")
	if request.user.is_active:
		if request.method == 'POST':
			h = ""
			reportid = request.POST.get('reportid')
			siteManager = UserProfile.objects.get(user_id=request.user.id).siteManager
			results1 = Report.objects.all()
			reportList = list(results1)
			for report in reportList:
				if report.private == True:
					if request.user not in report.auth_users.all() or not siteManager:
						reportList.remove(report)
			if len(reportList) == 0:
				return HttpResponse("You don't have any reports to view.")

			match = False
			report = None
			for item in reportList:
				if int(reportid) == int(item.id):
					match = True
					report = item
					break

			if match:
				h += "   Name: " + str(report.name) + "\n"
				h += "   Created at: " + str(report.created_at) + "\n"
				h += "   Owner: " + str(report.owner) + "\n"
				h += "   Short description: " + str(report.short_description) + "\n"
				h += "   Detailed description: " + str(report.detailed_description) + "\n"
				h += "   Tags: " + str(report.tags) + "\n"
				h += "   Private? " + str(report.private) + "\n"
				h += "   Encrypted? " + str(report.encrypt) + "\n"
				h += "   Files?\n"

				if not report.file1 and not report.file2 and not report.file3 and not report.file4 and not report.file5:
					h += "      "
				else:
					if report.file1:
						h +=  "      "+str(report.file1)
					h += "\n"
					if report.file2:
						h += "      "+str(report.file2)
					h += "\n"
					if report.file3:
						h += "      "+str(report.file3)
					h += "\n"
					if report.file4:
						h += "      "+str(report.file4)
					h += "\n"
					if report.file5:
						h += "      "+str(report.file5)
					h += "\n"
			else:
				h = "You don't have access to this report or it does not exist."
				return HttpResponse(h)
		return HttpResponse(h)