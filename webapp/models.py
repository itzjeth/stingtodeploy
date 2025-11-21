from django.db import models  
from django.contrib.auth.models import User, AbstractBaseUser, BaseUserManager
from cloudinary.models import CloudinaryField
import json
            
class Review(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    USER_STATUS_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('visitor', 'Visitor'),
    ]

    Id = models.AutoField(primary_key=True)
    user = models.CharField(max_length=45)  # Name of the user submitting the review
    email = models.CharField(max_length=45)  # User's email
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
    )
    message = models.CharField(max_length=60)  # Review message
   
    user_status = models.CharField(
        max_length=10,
        choices=USER_STATUS_CHOICES,
        default='visitor',  # Default value can be 'visitor'
    )
    password = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "Review"

class Users(models.Model):
    CustId = models.AutoField(primary_key=True)
    userName = models.CharField(max_length=255)
    userEmail = models.EmailField(unique=True)
    userPass = models.CharField(max_length=255)
    userImage = CloudinaryField('Profile Images', default='default_h6ywr4.png')

    class Meta:
        db_table = "TB_Users"

class Admin(models.Model):
	AdminId   = models.CharField(primary_key=True,max_length=20)
	AdminPass = models.CharField(max_length=60)
	class Meta:
		db_table = "TB_Admin"



