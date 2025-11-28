from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.utils.safestring import mark_safe
from difflib import SequenceMatcher
import json, random, string, datetime

from webapp.forms import UserForm, ReviewForm
from webapp.models import Users, Review, Admin
"""{% load static %}"""






     
def home_page(request,):
    return render(request, 'pages/home.html')

def loader_page(request,):
    return render(request, 'pages/loader.html')

def chatbot_page(request):
    return render(request, 'pages/chatbot.html')

def dashboard_page(request):
    return render(request, 'pages/dashboard.html')

def chatbot_front(request):
    return render(request, 'pages/chatbot_front.html')

def userHomePage(request):
    return render(request, 'pages/userHome.html')


def generate_random_password(length=8):
    """Generate a random password with letters, digits, and symbols."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(chars) for _ in range(length))


def userReview(request):
    alert = None
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                alert = 'success'
            except Exception as e:
                print("Error saving form:", e)  # ✅ Add this
                alert = 'error'
        else:
            print("Form is invalid:", form.errors)  # ✅ Debug invalid form
            alert = 'error'
    else:
        form = ReviewForm()

    return render(request, "pages/home.html", {'form': form, 'alert': alert})


@transaction.atomic
def send_review_email(request, pk):
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect('review_list')

    review = get_object_or_404(Review, pk=pk)

    try:
        new_password = generate_random_password()
        review.password = new_password
        review.save()

        # Create or update user
        user_obj, created = Users.objects.update_or_create(
            userEmail=review.email,
            defaults={'userName': review.user, 'userPass': new_password}
        )

        # Email content
        subject = "Your Sting Chatbot Access Account"
        message = (
            f"Hello {review.user},\n\n"
            f"Your account has been {'created' if created else 'updated'}.\n\n"
            f"Username: {review.email}\n"
            f"Password: {new_password}\n\n"
            "Keep these credentials safe.\n\n– STING CHATBOT –"
        )

        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [review.email], fail_silently=False)
            messages.success(request, f"Email sent and account processed for {review.email}.")
            review.delete()
        except Exception as e:
            messages.error(request, f"Email could not be sent: {e}")

    except Exception as e:
        print("[send_review_email] ERROR:", e)
        messages.error(request, "An error occurred during account creation or email sending.")
        raise

    return redirect('review_list')


def review_list(request):
    query = request.GET.get('q')
    reviews = Review.objects.all()
    if query:
        reviews = reviews.filter(
            Q(user__icontains=query) |
            Q(email__icontains=query) |
            Q(message__icontains=query)
           
        )
    return render(request, 'pages/review_list.html', {'reviews': reviews})



@transaction.atomic
def review_create(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)

        if form.is_valid():
            review = form.save(commit=False)
            random_password = generate_random_password()

            review.password = random_password
            review.save()

            # Create user (Cloudinary default image used automatically)
            Users.objects.create(
                userName=review.user,
                userEmail=review.email,
                userPass=random_password
            )

            # Send email
            subject = "Your Sting Chatbot Access Account"
            message = (
                f"Hello {review.user},\n\n"
                f"Your account has been created successfully.\n\n"
                f"Username: {review.email}\n"
                f"Password: {random_password}\n\n"
                "Please keep these credentials safe.\n\n– STING CHATBOT –"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [review.email])

            messages.success(request, f"Access request created for {review.email}.")
            return redirect('review_list')

        messages.error(request, "Invalid form data.")
    else:
        form = ReviewForm()

    return render(request, 'pages/review_form.html', {'form': form})



def review_update(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            return redirect('review_list')
    else:
        form = ReviewForm(instance=review)
    return render(request, 'pages/review_form.html', {'form': form})

def review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if request.method == 'POST':
        review.delete()
        return redirect('review_list')
    return render(request, 'pages/review_confirm_delete.html', {'review': review})

def doLogin(request):
    if request.method == "POST":
        uid = request.POST.get('userId', '')
        upass = request.POST.get('userpass', '')
        utype = request.POST.get('type', '')

        # -------------------------
        # ADMIN LOGIN
        # -------------------------
        if utype == "Admin":
            for a in Admin.objects.raw(
                'SELECT * FROM TB_Admin WHERE AdminId=%s AND AdminPass=%s', [uid, upass]
            ):
                request.session['AdminId'] = uid
                return render(request, "pages/base.html")

            messages.error(request, "Incorrect username or password")
            return redirect("home")

        # -------------------------
        # USER LOGIN
        # -------------------------
        if utype == "User":
            for a in Users.objects.raw(
                'SELECT * FROM TB_Users WHERE userEmail=%s AND userPass=%s', [uid, upass]
            ):
                request.session['CustId'] = uid
                request.session['user_name'] = a.userName
                request.session['user_image'] = a.userImage.url if a.userImage else None
                return render(request, "pages/chatbot.html")

            messages.error(request, "Incorrect username or password")
            return redirect("home")

# views.py
@transaction.atomic
def edit_profile(request):
    user_email = request.session.get('CustId')
    user = get_object_or_404(Users, userEmail=user_email)

    if request.method == 'POST':
        user.userName = request.POST.get('userName')

        # Upload new image if provided
        if 'userImage' in request.FILES:
            user.userImage = request.FILES['userImage']

        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password or confirm_password:
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, 'pages/edit_profile.html', {'user': user})
            user.userPass = new_password

        user.save()

        # Update session with Cloudinary URL
        request.session['user_name'] = user.userName
        request.session['user_image'] = user.userImage.url if user.userImage else None

        messages.success(request, "Profile updated successfully.")
        return render(request, 'pages/edit_profile.html', {'user': user})

    return render(request, 'pages/edit_profile.html', {'user': user})




def base(request):

    return render(request, 'pages/base.html')

def user_list(request):
    query = request.GET.get('q')
    if query:
        users = Users.objects.filter(userName__icontains=query)
    else:
        users = Users.objects.all()
    return render(request, 'pages/user_list.html', {'users': users, 'query': query})


def user_add(request):  
    if request.method == "POST":  
        formtwo = UserForm(request.POST, request.FILES)  
        if formtwo.is_valid():  
            try:  
                user = formtwo.save()
                request.session['user_name'] = user.userName
                messages.success(request, '🎉 Account created successfully.')
                return redirect("user_list")  
            except:  
                messages.error(request, "❌ An unexpected error occurred.")
        else:
            messages.error(request, "⚠️ Form data is invalid. Please try again.")
    else:
        formtwo = UserForm()
    return render(request, 'pages/user_form.html', {'form': formtwo})

def user_edit(request, id):
    user = get_object_or_404(Users, pk=id)
    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ User updated successfully.")
            return redirect('user_list')
        else:
            messages.error(request, "❌ Failed to update user.")
    else:
        form = UserForm(instance=user)
    return render(request, 'pages/user_form.html', {'form': form})

def user_delete(request, id):
    user = get_object_or_404(Users, pk=id)
    if request.method == "POST":
        user.delete()
        messages.success(request, "🗑️ User deleted successfully.")
        return redirect('user_list')
    return render(request, 'pages/user_confirm_delete.html', {'user': user})














def userAdd(request):  
    if request.method == "POST":  
        formtwo = UserForm(request.POST)  
        if formtwo.is_valid():  
            try:  
                user = formtwo.save()
                
                # ✅ Store username in session
                request.session['user_name'] = user.userName

                messages.success(request, 'Your account is created. Now you can login')
                return redirect("/webapp/dashboard")  
            except:  
                return render(request, "../error.html")
        else:
            formtwo = UserForm()
        messages.success(request, 'Try another username')
        return render(request, 'dashboard.html', {'form': formtwo})
     
def forgot_password(request):
    message = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            user = Users.objects.get(userEmail=email)
            # Generate new random password
            new_password = generate_random_password()
            user.userPass = new_password
            user.save()

            # Send email
            send_mail(
                subject="Your New STING Chatbot Password",
                message=(
                    f"Hello {user.userName},\n\n"
                    f"A new password has been generated for your STING Chatbot account.\n\n"
                    f"Your new login details:\n"
                    f"Email: {user.userEmail}\n"
                    f"Password: {new_password}\n\n"
                    f"You can now log in using this new password.\n\n"
                    f"– STING Chatbot Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.userEmail],
                fail_silently=False,
            )

            message = "✅ A new password has been sent to your email."
        except Users.DoesNotExist:
            message = "⚠️ Email not found in our system."
        except Exception as e:
            print("Error sending reset email:", e)
            message = "❌ Something went wrong. Please try again later."

    return render(request, 'pages/forgot_password.html', {'message': message})

def doLogout(request):
	key_session = list(request.session.keys())
	for key in key_session:
		del request.session[key]
	return render(request,'pages/home.html',{'success':'Logged out successfully'})

def showUserInfo(request):
	userX = Users.objects.all()
	return render(request,'pages/chatbot.html',{'chatkot':userX})

def getUser(request,userId):
	userX = Users.objects.get(userId=userId)
	return render(request,'pages/chatbot.html',{'f':userX})


#def updateUser(request,userId):
	#userX = Users.objects.get(userId=userId)
	#formtwo = UserForm(request.POST,request.FILES,instance=userX)
	#if formtwo.is_valid():
		#formtwo.save()
		#return redirect("/allcaffe")
	#return render(request,'updatefood.html',{'f':userX})			
  

    














#def updatePic(request):
    #user = userInfo.objects.get(userId=userId)
    #form = userForm(request.POST, request.FILES,instance=user)
    #if form.is_valid():
    #    form.save()
    #    return redirect("/webapp/sting")
   # return render(request, 'chatbot.html',{'u':user})


from difflib import SequenceMatcher
from django.http import JsonResponse, HttpResponse
from django.utils.safestring import mark_safe
from django.shortcuts import render


QA_DATA = [
############ PERSONAL BOUT CVSU ####################
{
  "patterns": [
    "current president cvsu",
    "who is president cvsu",
    "cvsu president",
    "president"
  ],
  "response": """
<img src="https://cvsu.edu.ph/wp-content/uploads/2025/01/2-1920x1920.png" alt"cvsu president photo" " style="display: block;margin-left: auto;margin-right: auto; width: 75%;"><br>Dr. Ma. Agnes P. Nuestro has been named as the fourth president of Cavite State University (CvSU). The members of the CvSU Board of Regents elected Dr. Nuestro to become the next president of the University, succeeding Dr. Hernando D. Robles who retired in October 2024. Having served as the University’s Vice President for Academic Affairs, Dr. Nuestro envisions CvSU as a premier global university by 2028. In her presentation during the Public Forum for the Search for the 4th CvSU President, Dr. Nuestro emphasized her administration’s goals centered on IDEAL: Inclusive and Accessible Education, Dynamic and Competitive Research and Innovation, Empowered Communities and Stronger Partnership, Accountable and Client-Centered Governance, and Long-lasting/Sustainable Resource Generation.
  """
},

{
 "patterns": [
    "old president cvsu",
    "old president",
    "old cvsu president"
  ],
  "response": """
<img src="https://www.manilatimes.net/uploads/imported_images/uploads/2021/03/CP-ONLINE_CVSU-PRESIDENT-Robles.jpg" alt"cvsu president photo" " style="display: block;margin-left: auto;margin-right: auto; width: 75%;"><br>Dr. Ma. Agnes P. Nuestro has been named as the fourth president of Cavite State University (CvSU).

Dr. Hernando D. Robles is the former President of Cavite State University (CvSU), serving from 2016 until his retirement in 2024. During his presidency, he also acted as the Vice-Chairperson of the CvSU Board of Regents. Under his leadership, CvSU achieved major milestones, including receiving the Philippine Quality Award for Quality Management Mastery, becoming one of the top-performing state universities in terms of accredited academic programs, and expanding its research and extension initiatives in agriculture, environmental studies, and community development. He supported collaborations with government agencies and private partners, strengthened infrastructure, improved management systems, and elevated the overall academic reputation of the university across all its campuses. His term ended when Dr. Ma. Agnes P. Nuestro succeeded him as the new university president in 2024.
  """
},

{
 "patterns": [
    "current department chairperson",
    "department chairperson",
    "chairperson"
  ],
  "response": """

<b> JOVELYN D. OCAMPO, MIT </b>

  """
},

{
 "patterns": [
    "current research coordinator",
    "campus research coordinator ",
    "research coordinator"
  ],
  "response": """
  
<b> RONAN M. CAJIGAL, MAEd </b>


  """
},

{
 "patterns": [
    "current campus administrator",
    "campus admin ",
    "admin",
    "administrator",
    "campus administrator"
  ],
  "response": """
  
<b> MENVYLUZ S. MACALALAD, MBA </b>

  """
},

##########################################################################

{
  "patterns": [
    "cvsu bacoor majors",
    "courses offered bacoor",
    "courses offered",
    "what major cvsu bacoor offers",
    "cvsu bacoor offers",
    "courses in cvsu"
  ],
  "response": """
  CvSU Bacoor offers various majors including Computer Science, Information Technology, Business Administration, Education, Pychology, and Criminology
  """
},

{
 "patterns": [
    "in computer science",
    "is computer science ",
    "computer science",
    "BSCS"
  ],
  "response": """
  
BSCS or BS Computer Science is the study of how computers work and how to create programs, apps, websites, and other technologies by learning coding, problem-solving, and how machines “think.”
<br>Typical jobs: Programmer, software developer, game developer, web developer, AI engineer.
<b>Difficulty: Hard – requires strong logic, patience, and a lot of coding practice.
<b>Passing Rate: No national licensure exam.
<br>Summary: CS focuses on creating technology through coding and building software.


  """
},

{
 "patterns": [
    "in information technology",
    "is information technology",
    "information technology",
    "BSIT"
  ],
  "response": """
  
BSIT or BS Information Technology is about using, managing, and maintaining computer systems, networks, and data to help organizations run smoothly, including fixing technical problems and protecting systems from hackers.
<br>Typical jobs: IT technician, network administrator, cybersecurity specialist, IT support, system analyst.
<b>Difficulty: Moderate to Hard – easier than CS but challenging in networking, troubleshooting, and cybersecurity.
<b>Passing Rate: No national licensure exam.
<br>Summary: IT focuses on maintaining and supporting technology in real-world workplaces.

  """
},

{
 "patterns": [
    "in business admin",
    "in business administration",
    "is business administration",
    "business administration",
    "BSBA"
  ],
  "response": """
  
BSBA or BS Business Administration teaches how businesses work and how to manage people, money, operations, and marketing to make an organization successful and efficient.
<br>Typical jobs: Manager, HR officer, marketing assistant, entrepreneur, business analyst.
<b>Difficulty: Easy to Moderate – less math-heavy than CS/IT but requires strong communication, analysis, and management skills.
<b>Passing Rate: No national licensure exam.
<br>Summary: Business Administration focuses on running and leading a business effectively.

  """
},

{
 "patterns": [
    "in education",
    "is education",
    "is educ",
    "education",
    "second education",
    "BSEd"
  ],
  "response": """
  
BSEd or BS Education prepares future teachers by teaching them how to handle classrooms, create lessons, guide students, and understand how children learn and grow.
<br>Typical jobs: Teacher, tutor, school administrator, guidance associate, curriculum developer.
<b>Difficulty: Moderate – requires patience, communication, and mastery of teaching techniques.
<b>Passing Rate (CvSU Bacoor): 90% passing rate in the 2025 Licensure Exam for Teachers (LET).
<br>Summary: Education focuses on training teachers to help students learn well.

  """
},

{
 "patterns": [
    "in pyschology",
    "is psychology",
    "psychology",
    "psych",
    "BSP"
  ],
  "response": """
  
BSP or BS Psychology studies how people think, feel, and behave, helping explain emotions, actions, personality, relationships, and mental health.
<br>Typical jobs: Guidance counselor, HR specialist, mental health aide, researcher, psychometrician.
<br>Difficulty: Moderate to Hard – involves heavy reading, research, and understanding human behavior.
<br>Passing Rate: Psychology board exam is only for Psychometricians/Psychologists; no specific CvSU data available.
<br>Summary: Psychology focuses on understanding the human mind and behavior.
  """
},

{
 "patterns": [
    "in criminology",
    "is criminology",
    "criminology",
    "crim",
    "BSC"
  ],
  "response": """
  
Criminology studies crime, how and why it happens, how investigations work, and how police, courts, and forensic experts maintain peace and safety.
<br>Typical jobs: Police officer, investigator, forensic assistant, crime analyst, corrections officer.
<b>Difficulty: Moderate – includes law, investigation techniques, physical training, and forensic concepts.
<b>Passing Rate (CvSU Bacoor): 94% passing rate in the February 2025 Criminology Licensure Exam.
<br>Summary: Criminology focuses on crime, law enforcement, and keeping communities safe.
"""
},

{
 "patterns": [
    "between computer science and IT",
    "computer science and it",
    "computer science and information technology",
    "information technology and computer science",
    "cs and it",
    "BSIT and BSCS"
  ],
  "response": """
  
<b>Computer Science (CS)</b>
<br>
Focus: Creating technology.<br>
What it deals with:
<br>
*How computers work internally
<br>
*Programming and building software
<br>
*Algorithms and problem-solving
<br>
*Artificial intelligence, machine learning, data science
<br>
*Designing new systems, apps, and advanced tech
<br><br>
Typical work: Software developer, programmer, AI engineer, systems architect, researcher.
<br><br>
Summary: <br>
CS is more theoretical and focuses on coding, algorithms, and making new technologies.
<br><br>
<b>Information Technology (IT)</b>
<br>
Focus: Using technology.<br>
What it deals with:
<br>
*Managing computer systems and networks
<br>
*Troubleshooting hardware and software
<br>
*Cybersecurity and protecting data
<br>
*Maintaining servers, databases, and IT infrastructure
<br>
*Ensuring organizations run smoothly using technology
<br><br>
*Typical work: IT support specialist, network admin, cybersecurity technician, system analyst.
<br><br>
Summary:<br>
IT is more practical and focuses on operating, securing, and managing existing technology.
<br>"""
},



{
  "patterns": [
    "who suspends classes",
    "suspend classes",
    "suspend class",
    "to suspend classes",
    "class suspension",
    "walang pasok"
    
  ],
  "response": """
    At CvSU, the University President who has final authority to suspend classes throughout the University including all units or branches.
    The university president may suspend classes in specific units or campuses for specified periods of units.
    Suspension of classes does not mean that faculty and employee will not report for duty <br><br>
  
    but in emergencies such as typhoons or floods, class suspension may also follow alerts from PAGASA or official orders from the city mayor.
    <br><br>

    To stay updated on class suspension announcements, make sure to follow these reliable sources
<br>
<a style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
    
  """
},

{
  "patterns": [
    "program accreditation",
    "what is accreditation",
    "meaning of program accreditation"
  ],
  "response": """
 The university shall as much as possible, submit all programs for accreditation particularly by Accrediting Agency of Chartered Colleges and Universities in the Philippines (AACCUP) or any accrediting agency prescribed by CHED and the Philippine Association of State Universities and Colleges
  """
},
{
  "patterns": [
    "academic load",
    "what is academic load",
    "meaning academic load"
  ],
  "response": """
  No student shall be alowed to take more than the maximum credit units per semester. A graduating student may be allowed to enroll more than the maximum allowable may be allowed to enroll more than the maximum allowable credit units not to exceed 26 units during the last two semesters of his course provided that he has a GPA of 2.50 or better in the previous two semesters as certified by the University Registrar. A graduating student petitioning for registrating up to maximum allowable academic load must secure a certification from the University Registrar that he is a graduating student.
  """
},
{
  "patterns": [
    "do i need attendance to pass",
    "maintain attendance to pass",
    "attendance to pass",
    "attendance requirement",
    "attendance important",
    "attendance"
    
  ],
  "response": """
    Pupils/Students are required to attend their classes and campus events promptly and regularly. Attendance alone does not guarantee passing; students must also complete and pass the projects, activities, and requirements given by the instructor. If a university student accumulates absences equivalent to 20% or more of the total class hours without an excusable reason, they may be dropped from the roll. Additionally, if a student’s academic performance is poor, they may receive a failing grade of 5.0.
  """
},
{
  "patterns": [
    "passing grade cvsu bacoor",
    "passing grade",
    "the passing grade",
    "grading system of cvsu bacoor",
    "the grading system",
    "grading system",
    "table of conversion",
    "the table of conversion",
    "cvsu passing grade",
    "cvsu failing grade",
    "failing grade",
    "fail grade",
    "what is passing grade"
  ],
  "response": """
 All credits earned from other colleges or universities will be evaluated according to the following table of conversion, which reflects the grading system used at CvSU Bacoor. The passing grade is 3.00, while 5.00 is considered failing. Below is the grading system of CvSU Bacoor.<br><br>
    
    
  <table style="width: 100%; border: 1px solid var(--text-color);; padding: 30px;">
  <tr>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;">Grade</td>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;">Grade</td>
  </tr>
    <tr >
       <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 1.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> 95%' </td>
    </tr>
<tr >
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 1.25 </td>
    <td style="border-bottom: 1px solid var(--text-color);"> 93%' </td>

   </tr>
<tr >
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 1.50 </td>
    <td style="border-bottom: 1px solid var(--text-color);"> 90%' </td>
   
 </tr>
 <tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 1.75 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 89%' </td>
 
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 2.00 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 85%' </td>
 
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 2.25 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 83%' </td>
 
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 2.50 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 80%' </td>
 
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 2.75 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 78%' </td>
 
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 3.00 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 75%' </td>
 
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 4.00 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> INC/INCOMPLETE' </td>

</tr>
<tr>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 5.00 </td>
    <td style="border-bottom: 1px solid var(--text-color);"> DRP/DROP - The student failed the course. The numberical grade of "5.00" must be written in red ink by the teacher </td>
</tr>
    
    
    </table><br><br>
    
    Each College shall endeavor to formulate and adopt a uniform method or system of assigning grades to scores and the assignment of weights to different types of test, requirements, laboratory exercises, and the like. This should be forwarded to the Vice President for Academic Affairs for his review and corrections before final adoption of the College concerned.
  """
},

{
  "patterns": [
    "admission",
    "admission in",
    "admission of",
    "enrollment",
    "enrollment in",
    "enroll",
    "enroll in",
    "reenroll",
    "application",
    "application in",
    "requirements",
    "requirements in"
    "requirement",
    "procedure",
    "procedure in",
    "applicant",
    "examination",
    "examination in",
    "reminders",
    "reminders for",
    "reminders in",
    "graduate",
    "the examination",
    "the requirement",
    "document requirements",
    "cvsu admission",
    "admission period",
    "first year applicant",
    "grade 12 student",
    "senior high",
    "new student",
    "transferee",
    "second course",
    "tcp applicant",
    "als applicant",
    "diploma degree holder",
    "procedure for application",
    "application procedure",
    "application category",
    "reminder for applicant",
    "of admission examination",
    "QR code"
   
    "",
   
  ],
  "response": """
 <table style="width: 100%; border: 1px solid var(--text-color); padding: 30px;">
 <tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;"><b>IMPORTANT:</b></td>
</tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Beginning <b style="border-bottom: 2px solid var(--text-color) ">October 15, 2025 - April 16, 2026</b>, the Online Admission System will be open for aspiring applicants to process their application for College Admission for the First Semester, S.Y. 2026-2027 <br><br>

<b>LINK: </b><a style="cursor: pointer; background: var(--sidebar-color); color: var(--text-color);" href="https://admission.cvsu.edu.ph/">https://admission.cvsu.edu.ph/</a><br>
OR ACCESS THE LINK THROUGH THIS QR CODE:</b>
<img src="data:image/jpeg;base64,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8U88oQwA8oksI8gMoc88U88sgAA8wUsks88I088U888888888888888888U488888888888888888U8sMMMMMMMMMMMMMMMM8888sUU8U8844cgQg8888884gUYQ0Qgog0AQ888888UIwscUUEs8QU4888c88888888888888888o88888888888888888gc/8QALxAAAQQBAgYCAgEEAwEBAAAABAACAwUBBhYQFBUgNDUSExEzUCEwMTIiJEU2I//aAAgBAQABBwK9vMg55aYich3y/gf8KvvDQX4QxERcEc5MziCJpq6unsp/qxpIX8LaQa2kGtpBraQa2kGtpBraQa2kGtpBraQa2kGtpBraQa2kGtpBraQa2kGtpBraQa2kGtpBraQa2kGtpBraQa2kGtpBraQa2kGtpBraQa2kGj9LugidKq65mAgzEtI4xy5ef4IrGGlE44aR8Ur+DM8wrjpHxSv4MzzCuOkfFK7LKxirIWy7tCW7Qlu0JbtCW7Qlu0JM1UG97W8HarDbnOIpMSxRyIrUogpEsARTDRoiDtQjAEvHrzo7Ef77K8HrJ2w1tnFZxyPs7iCrzFjdoS3aEt2hLdoS3aEt2hITUgpZEUHYZ5hXHSPildmrPAgQIM1hN9O1bJbVsltWyW1bJS6ZsIYpJB/3w8N11qzpixkzl7NRgisYPBK0iGKaw04eUaTMNbjU0LALYuI46WfS/q1eUpdiXHLRVs9bBMzV/wCwFV9WRZ5lxtWyW1bJbVsltWyRenzgh5CKT2oXaZ5hXHSPildmrPAgWl/ZosuEGHM256pbnqlDqGtnljiO8IxD/vh4bZtVHj4sZgjTlnIRO+C8ABgiFHnYTDHNf+3MQlGebA2ejDnBB+k24Cr5WxA2A9gx79X/ALAVpH/c5HWI1c1jtz1S3PVIS7ANmxDqH05ipPahdpnmFcdI+KV2as8CBaX9mtS+pl41XsgEd4RiH/fDw3FTrcVOmPbIxjzqK1mNLkDtgK8WES3IiKsSZqW5rg66KHcVOtQGjHGRyaS8Qpav/YCtI/7nLV3jicdNe2hWofTmKk9qF2meYVx0j4pXZqzwIFpf2a1L6mXjVeyAR3hGIf8AfDw6FbLOPxnOAvDEUl1WRPfGdWnHFkE9Ctl0K2RA04kn1jVpxjMyabDJDHIbq/8AYCtI/wC5y1d44nHTXtoV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" 
style="display: block;margin-left: auto;margin-right: auto; width: 25%;">
</td>
</tr>
</table>


    
    
  <table style="width: 100%; border: 1px solid var(--text-color); padding: 30px;">
<tr>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;"></td>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;"><b>APPLICANT MUST REFER TO THE TABLE BELOW TO DETERMINE THEIR APPLICATION CATEGORY: </b></td>
  </tr>
  <tr>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;">       Category</td>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;">Definition</td>
  </tr>
    <tr >
       <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> First-year applicant/<br>
	New Student </td>
       <td style="border-bottom: 1px solid var(--text-color);"> <br>
A. Current Grade 12 student is expecting to finish SHS at the end of the school year (2025-2026). <br>
B. SHS Graduate who have never been enrolled in any college/university <br>
C. ALS Completer <br>
D. Associate, Certificate, Vocational, or Diploma Degree Holder - one who has finished a certificate, vocational, diploma course or associate degree in any college/university <br></td>
    </tr>
 <tr >
       <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> Transferee </td>
       <td style="border-bottom: 1px solid var(--text-color);">
Applicants who started their college level at another university/school or another CvSU campus <br></td>
    </tr>
 <tr >
       <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> Second Courser </td>
       <td style="border-bottom: 1px solid var(--text-color);"> 
One who has already completed and graduated with any Bachelor's degree program <br></td>
    </tr>
 <tr >
       <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> TCP Applicant </td>
       <td style="border-bottom: 1px solid var(--text-color);">
Applicant who graduated from any Bachelor's degree program, interested in pursuing 18 units of Education <br></td>
    </tr>
    
    </table><br><br>

 <table style="width: 100%; border: 1px solid var(--text-color); padding: 30px;">
 <tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;"><b> PROCEDURE FOR APPLICATION FOR COLLEGE ADMISSION</b></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;"></td>
</tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>1.</b> Access the admission link on a website browser then sign up with
a Gmail account. Download and Fill out the online application form, <a style="cursor: pointer; background: var(--sidebar-color); color: var(--text-color);" href="https://drive.google.com/file/d/1zoG0QutodBOX_iegsrPdtaXlgBs8Gn0a/view?fbclid=IwAR0cxxbPFag9mCOKcdWDrqd4Og8ytmJL_WFJYA5M4l_guRogSN7Ds-GBgoo" alt="admission.pdf" style="cursor: pointer;">Application Form</a> keep in mind the following:    
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* The declared track/strand in the online application form and the track/strand indicated in the documentary requirement should match. <br><br>
* Choose the correct entry type/category of applicant.  <br><br>
* Thoroughly check all information input in the online application form before saving and submitting  to avoid typographical errors, wrong spelling, incorrect entries, or wrong entry of information.  <br><br>
* Do not forget to update/save the application every time there is a change made to each field and page. 
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>2.</b> Prepare, scan (or take a screenshot) then upload all the
documentary requirements in the online admission system. Please take note of the following:
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* The 2 x 2 ID photo (in white background) file size must be at most <br><br>
* All the original documentary requirements must be signed by the authorized school personnel before scanning  <br><br>
* Screenshot of the documentary requirement using a cellphone is allowed  <br><br>
* Each documentary requirement is limited to 1mb (1024kb) in size only The file type of each documentary requirement must be either jpeg/png/bmp type
Upload the scanned pages individually (per page)
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>DOCUMENTARY REQUIREMENTS FOR
FIRST YEAR APPLICANTS (CURRENT GRADE 12 STUDENTS)</b> 
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* Completed grade 11 card (1st and 2nd semester) <br><br>
* Certificate from the principal or adviser indicating that the applicant is currently enrolled as a grade 12 student with the track/strand and school year indicated  <br><br>
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>DOCUMENTARY REQUIREMENTS FOR
FIRST YEAR APPLICANTS (SENIOR HIGH SCHOOL GRADUATE) </b> 
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* Completed grade 12 report card (1st and 2nd semester) <br><br>
* Certificate of non-issuance of form 137/sf-10 for college admission (this certification shall prove that the applicant has never been enrolled in another university/college)<br><br>
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>DOCUMENTARY REQUIREMENT FOR
FIRST YEAR APPLICANTS (ALS COMPLETER/PASSER) </b> 
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* Certificate of Rating (COR) with eligibility to enroll in college
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>DOCUMENTARY REQUIREMENT FOR
ASSOCIATE, CERTIFICATE, VOCATIONAL, OR DIPLOMA DEGREE HOLDER </b> 
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* Transcript of Records (TOR) with graduation date
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>DOCUMENTARY REQUIREMENT FOR
TRANSFEREE APPLICANTS </b> 
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* Certificate of Grades (COG) or Transcript of Records (TOR) -  
all enrolled subjects must have final grades
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>DOCUMENTARY REQUIREMENT FOR
SECOND-COURSE APPLICANTS </b> 
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* Transcript of Records (TOR) with graduation date  
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>DOCUMENTARY REQUIREMENT FOR
TCP APPLICANTS </b> 
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* Transcript of Records (TOR) with graduation date  
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>3.</b> Applicant will select the next available date and time for the
validation of the application and save the schedule from the online admission system. It is important to save the schedule.
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
<b>NOTE:</b> Applicant <b>MUST</b> select the date and time of validation. Once the validation appointment has been saved, the information details cannot be edited again.
<br><br>On-site validation is from <b>October 20, 2025 to February 19, 2026</b>.
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>4.</b> On the appointment date, the applicant will present the
original copies of documentary requirements at the Office of Student Affairs and Services (OSAS).
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
<b>NOTE:</b> Only applicants who are scheduled on the particular date and time will be accommodated. Strictly no-walk ins.
 <br><br>
</td>
  </tr>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>5.</b> Once the application has been validated by the OSAS personnel,
the applicant will be scheduled to take the admission examination (on-site). 
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
The applicant <b>MUST</b> download and print
the exam permit from the online admission system (after validation) and bring the exam permit on the
examination day.
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>6.</b> Transferee applicants, second course takers, and associate/certificate/ vocational/diploma degree holders will only undergo department evaluation and will not take the admission exam.
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
 The result of the evaluation from the department shall determine if the applicant is qualified to proceed with the application or not.
 <br><br>
</td>
  </tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><b>7.</b> TCP applicants will only undergo college evaluation from
the Teacher Education Department (TED) and will not take the admission exam.
<br><br></td>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
 <br><br>
</td>
  </tr>
</table>
<br><br>

 <table style="width: 100%; border: 1px solid var(--text-color); padding: 30px;">
 <tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;"><b>REMINDERS FOR APPLICANTS DURING EXAMINATION</b></td>
</tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">
* Applicants must print their Exam Permit on a letter-sized (short) bond paper and bring it on the examination day. <br><br>
* Applicants with NO physical copy of the exam permit SHALL NOT be allowed to take the exam. <br><br>
* Applicants will attach a 1x1 ID picture to their examination permit. They must also bring a valid ID (School ID or government-issued ID) for verification. <br><br>
* Applicants must bring two pieces of Pencil No. 2.  <br><br>
* Only applicants who are scheduled for the admission exam shall be allowed to enter the University premises and will be directed to the designated examination area. They will not be allowed to roam around in the campus.  <br><br>
* Food is not allowed inside the venue or during the examination.   <br><br>
* The use of cellphones, calculators, and other electronic devices during the exam is strictly prohibited and shall cause disqualification.  <br><br>
* Applicants must dress appropriately. Attire must not be too revealing or scandalous.   <br><br>
* Tampering, falsification, and editing of this exam permit will mean disqualification from taking the exam.  <br><br>
* Applicants are expected to come to their assigned examination schedule on time.  <br><br>
* Physical distancing must be observed for the entire duration of the applicants' stay in the University.  
<br><br>
<b>NOTES:</b>
* The result of the admission examination will be announced via our Facebook page once out, so stay posted. <br><a style="cursor: pointer; background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CvSU.B.Admission">Cavite State University - Bacoor Guidance and Admission Services</a><br><br>
* The Office of Student Affairs and Services (OSAS) of CVSU Campus informs all applicants that filling out the online application form and having a control number do not mean a sure slot for admission.  <br><br>
* All applicants are advised to remember the control number assigned to them.
<br><br>
</td>
  </tr>
</table>

  """
},

{
  "patterns": [
    "re enrollment subjects",
    "what happens re enrollment",
    "reenroll subjects"
  ],
  "response": """
  KEEP THIS EMPTY - NO DATA HERE
  """
},
{
  "patterns": [
    "prerequisite subjects",
    "what is prerequisite",
    "subject prerequisite meaning"
  ],
  "response": """ 
  KEEP THIS EMPTY - NO DATA HERE
  """
},
{
  "patterns": [
    "leave of absence",
    "what is loa",
    "meaning leave of absence"
  ],
  "response": """ 
  KEEP THIS EMPTY - NO DATA HERE 
  """
}


  ##CUSTOM
  
  









]    

def fuzzy_match(user_message, threshold=0.55):
    """Compare user's message to QA_DATA patterns and return best matching response."""
    best_match = None
    best_score = 0
    for item in QA_DATA:
        for pattern in item["patterns"]:
            score = SequenceMatcher(None, user_message.lower(), pattern.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = item["response"]
    if best_score >= threshold:
        return best_match
    return None

def getResponse(request):
    user_message = request.GET.get('userMessage', '')
    if not user_message:
        return HttpResponse(mark_safe("Please provide a message."))
    chat_response = fuzzy_match(user_message)
    if not chat_response:
        chat_response = "I'm sorry, I couldn’t find an answer. Try rephrasing or ask about CvSU Bacoor services."
    return HttpResponse(mark_safe(chat_response))

def chatbot_response(request):
    if request.method == "POST":
        user_message = request.POST.get("message", "")
        answer = fuzzy_match(user_message)
        if not answer:
            answer = "I'm sorry, I couldn’t find an answer. Try rephrasing or ask about CvSU Bacoor services."
        return JsonResponse({"response": answer})
    return JsonResponse({"response": "Invalid request method."})

def chat_page(request):
    return render(request, "pages/chat_page.html")




#corpus
#ChatterBotCorpusTrainer = ChatterBotCorpusTrainer(bot)
#corpusend

#list_trainer = ListTrainer(bot)
#list_trainer.train(list_to_train)

#corpus
#ChatterBotCorpusTrainer.train('chatterbot.corpus.english')
#corpusend