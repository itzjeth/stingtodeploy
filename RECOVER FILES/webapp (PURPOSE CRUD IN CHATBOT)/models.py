from django.db import models  
            
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

    class Meta:
        db_table = "Review"

class Users(models.Model):
    CustId = models.AutoField(primary_key=True)
    userName = models.CharField(max_length=55)
    userEmail = models.CharField(max_length=55)
    userPass  = models.CharField(max_length=61)
    userImage = models.ImageField(upload_to='profile_images/', default='profile_images/default.png')  # NEW
    class Meta:
        db_table = "TB_Users"

class Admin(models.Model):
	AdminId   = models.CharField(primary_key=True,max_length=20)
	AdminPass = models.CharField(max_length=60)
	class Meta:
		db_table = "TB_Admin"


class ChatPair(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()

    def __str__(self):
        return self.question