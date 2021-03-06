from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User, Group

# USERS
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    password2 = models.CharField(max_length = 100)
    website = models.URLField(blank=True)
    picture = models.ImageField(upload_to='profile_images', blank=True)
    siteManager = models.BooleanField(default=False)
    def __unicode__(self):
      return self.user.username

class PasswordChange(models.Model):
	oldPassword = models.CharField(max_length = 100)
	newPassword = models.CharField(max_length = 100)

class UploadFile(models.Model):
  file = models.FileField(upload_to='files/%Y/%m/%d')

# MESSAGES
class Message(models.Model):
  sender = models.ForeignKey(User, related_name="sender")
  receiver = models.ForeignKey(User, related_name="receiver")
  content = models.TextField()
  created_at = models.TextField()
  encrypt = models.BooleanField(default=False)
  read = models.BooleanField(default=False)

# REPORTS
class Folder(models.Model):
  owner = models.ForeignKey(User, null=True)
  name = models.CharField(max_length=100, null=True)
  def __unicode__(self):
    return self.name
  # THIS CANNOT BE FOREIGNKEY, MUST BE MANYTOMANY
  # reports = models.ForeignKey(Report, null=True)
class Report(models.Model):
  name = models.CharField(max_length=100)
  owner = models.ForeignKey(User, related_name="owner")
  created_at = models.TextField()
  short_description = models.CharField(max_length=200)
  detailed_description = models.TextField()
  tags = models.CharField(max_length=300, null=True)
  upload_path = 'files/' + '%Y%m%d'
  file1 = models.FileField(upload_to=upload_path, null=True)
  file2 = models.FileField(upload_to=upload_path, null=True)
  file3 = models.FileField(upload_to=upload_path, null=True)
  file4 = models.FileField(upload_to=upload_path, null=True)
  file5 = models.FileField(upload_to=upload_path, null=True)
  private = models.BooleanField(default=False)
  encrypt = models.BooleanField(default=False)
  int_hash = models.CharField(max_length=100, default="")
  # collection of user permissions
  auth_users = models.ManyToManyField(User)
  # collection of group permissions
  auth_groups = models.ManyToManyField(Group)
  # collection of folders
  folders = models.ManyToManyField(Folder)