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
<a href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
    
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
    "application category",
    "",
    "reenroll subjects"
  ],
  "response": """
  KEEP THIS EMPTY - NO DATA HERE
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