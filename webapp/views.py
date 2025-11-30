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
  "cvsu president",
  "who is the president of cvsu",
  "current cvsu president",
  "cvsu university president",
  "who leads cvsu",
  "cvsu top official",
  "cvsu administration head",
  "dr ma agnes nuestro",
  "agnes nuestro cvsu president",
  "president of cavite state university",
  "cvsu leadership",
  "cvsu president information"
],

  "response": """
<img src="https://cvsu.edu.ph/wp-content/uploads/2025/01/2-1920x1920.png" alt"cvsu president photo" " style="display: block;margin-left: auto;margin-right: auto; width: 45%;"><br>
<b>Dr. Ma. Agnes P. Nuestro </b> has been named as the fourth president of Cavite State University (CvSU). The members of the CvSU Board of Regents elected Dr. Nuestro to become the next president of the University, succeeding Dr. Hernando D. Robles who retired in October 2024. Having served as the University’s Vice President for Academic Affairs, Dr. Nuestro envisions CvSU as a premier global university by 2028. In her presentation during the Public Forum for the Search for the 4th CvSU President, Dr. Nuestro emphasized her administration’s goals centered on IDEAL: Inclusive and Accessible Education, Dynamic and Competitive Research and Innovation, Empowered Communities and Stronger Partnership, Accountable and Client-Centered Governance, and Long-lasting/Sustainable Resource Generation.
  """
},

{
 "patterns": [
  "former cvsu president",
  "old president of cvsu",
  "who is the previous cvsu president",
  "cvsu past president",
  "who was cvsu president before",
  "cvsu former leadership",
  "cvsu administration history",
  "dr hernando robles",
  "hernando robles cvsu",
  "ex cvsu president",
  "past university president cvsu",
  "previous cvsu head"
],

  "response": """
<img src="https://www.manilatimes.net/uploads/imported_images/uploads/2021/03/CP-ONLINE_CVSU-PRESIDENT-Robles.jpg" alt"cvsu president photo" " style="display: block;margin-left: auto;margin-right: auto; width: 45%;"><br>Dr. Ma. Agnes P. Nuestro has been named as the fourth president of Cavite State University (CvSU).

<u>Dr. Hernando D. Robles </u> is the former President of Cavite State University (CvSU), serving from 2016 until his retirement in 2024. During his presidency, he also acted as the Vice-Chairperson of the CvSU Board of Regents. Under his leadership, CvSU achieved major milestones, including receiving the Philippine Quality Award for Quality Management Mastery, becoming one of the top-performing state universities in terms of accredited academic programs, and expanding its research and extension initiatives in agriculture, environmental studies, and community development. He supported collaborations with government agencies and private partners, strengthened infrastructure, improved management systems, and elevated the overall academic reputation of the university across all its campuses. His term ended when Dr. Ma. Agnes P. Nuestro succeeded him as the new university president in 2024.
  """
},

{
"patterns": [
  "cvsu bacoor department chairperson",
  "who is the department chair",
  "department chair of cvsu bacoor",
  "current department chairperson cvsu",
  "head of academic department cvsu bacoor",
  "program chair cvsu bacoor",
  "cvsu bacoor program head",
  "chairperson of my program cvsu",
  "who leads the department cvsu bacoor",
  "department head cvsu",
  "cvsu bacoor department leadership",
  "academic chairperson cvsu bacoor",
  "ms jovelyn d ocampo",
  "jovelyn d ocampo mit",
  "department chairperson jovelyn ocampo"
],


  "response": """

The current Department Chairperson is <u>Ms. Jovelyn D. Ocampo, MIT </u>. She leads the department in overseeing academic programs, guiding faculty members, and ensuring that the curriculum remains relevant and aligned with university standards. Through her leadership, the department continues to enhance its instructional quality, support student development, and maintain a strong academic environment

  """
},

{
"patterns": [
  "cvsu bacoor research coordinator",
  "who is the research coordinator",
  "current research coordinator cvsu bacoor",
  "research head cvsu bacoor",
  "research coordinator of cvsu",
  "cvsu bacoor research office head",
  "who handles research cvsu bacoor",
  "research program coordinator cvsu",
  "head of research cvsu bacoor",
  "research department coordinator cvsu",
  "who leads research cvsu bacoor",
  "cvsu bacoor research leader",
  "ronan m cajigal",
  "mr ronan cajigal",
  "research coordinator ronan cajigal"
],

  "response": """
  
The current Research Coordinator of CvSU Bacoor is <u>Mr. Ronan M. Cajigal, MAEd </u>. He is responsible for guiding the campus’ research initiatives, supporting faculty and student researchers, and ensuring that all research activities align with the university’s academic standards and goals. Through his leadership, the research culture of the campus continues to grow and strengthen.


  """
},

{
 "patterns": [
    "current campus administrator",
    "campus admin ",
    "bagong campus administrator",
    "bagong campus admin",
    "new campus administrator",
    "new campus admin",
    "admin",
    "administrator",
    "campus administrator",
    "cvsu bacoor campus director",
    "who is campus director",
    "current campus director cvsu bacoor",
    "cvsu bacoor director",
  "who leads cvsu bacoor",
  "head of cvsu bacoor",
  "campus head cvsu bacoor",
  "director of cvsu bacoor campus",
  "cvsu bacoor administrative head",
  "who manages cvsu bacoor",
  "cvsu bacoor leadership",
  "campus director information",
  "who is the campus administrator",
  "who is the campus admin",
  "who is the campus director",
  "current campus administrator",
  "campus admin cvsu bacoor",
  "cvsu bacoor campus director",
  "head of campus cvsu bacoor",
  "campus leader cvsu bacoor",
  "campus administrator of cvsu",
  "who leads the campus cvsu bacoor",
  "campus director role cvsu",
  "campus admin officer cvsu bacoor",
  "ms menvyluz s. macalalad",
  "mba campus director cvsu bacoor",
  "campus director ms macalalad"
],

  "response": """
  
The current Campus Administrator of CvSU Bacoor is <u>Ms. Menvyluz S. Macalalad, MBA </u>. She oversees the overall operations, academic services, and administrative functions of the campus, ensuring that students receive quality education and a supportive learning environment. Under her leadership, the campus continues to improve its programs, facilities, and student services.

  """
},

##########################################################################
{
  "patterns": [
  "available programs cvsu bacoor",
  "courses offered cvsu bacoor",
  "cvsu bacoor programs",
  "list of courses cvsu bacoor",
  "what courses are available",
  "degree programs offered",
  "program offerings cvsu bacoor",
  "cvsu bacoor academic programs",
  "courses allowed for enrollment",
  "what program can i take",
  "cvsu bacoor course list",
  "available degrees cvsu bacoor",

  "course group chat cvsu bacoor",
  "cvsu bacoor gc for courses",
  "official group chat for course",
  "program group chat list",
  "society group chat cvsu bacoor",
  "course organization gc",
  "society gc of each course",

  "bsed group chat",
  "bachelor of secondary education group chat",
  "bsed society group",
  "bsed society gc",

  "bscs group chat",
  "bachelor of science in computer science group chat",
  "bscs society group",
  "bscs society gc",

  "bs criminology group chat",
  "bs criminology society group",
  "bs crim gc",
  "criminology society gc",

  "bshm group chat",
  "hospitality management group chat",
  "bshm society group",
  "bshm society gc",

  "bsit group chat",
  "information technology group chat",
  "bsit society group",
  "bsit society gc",

  "bs psychology group chat",
  "bs psych gc",
  "psychology society group",
  "bs psych society gc",

  "bsbm group chat",
  "business management group chat",
  "bsbm society group",
  "bsbm society gc"
  ],
  "response": """
  CvSU offers a variety of course and program this includes the following: <br><br>
 <table style="width: 100%; border: 1px solid var(--text-color); padding: 30px;">
        <tr>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Program / Course</th>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Abbreviation</th>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Notes</th>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Society Link</th>
        </tr>
      <tbody>
        <tr>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Bachelor of Secondary Education</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">BSED</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Teacher education — various specializations may be offered.</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><a style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CvSUEDUCSociety" target="_blank" rel="noopener">BSSD Society</a></td>
        </tr>
        <tr>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Bachelor of Science in Computer Science</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">BSCS</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Software, algorithms, and systems.</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><a style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CvSUBacoorDCS" target="_blank" rel="noopener">BSCS Society</a></td>
        </tr>
        <tr>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Bachelor of Science in Criminology</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">BS Crim</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Law enforcement and criminal justice.</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><a style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CriminologyBacoorOfficial" target="_blank" rel="noopener">BS Crim Society</a></td>
        </tr>
        <tr>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Bachelor of Science in Hospitality Management</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">BSHM</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Hospitality, hotel & restaurant management (formerly HRM).</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><a style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/bshmsocietycvsubacoor" target="_blank" rel="noopener">BSHM Society</a></td>
        </tr>
        <tr>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Bachelor of Science in Information Technology</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">BSIT</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Practical IT skills and systems administration.</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><a style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor" target="_blank" rel="noopener">BSIT Society</a></td>
        </tr>
        <tr>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Bachelor of Science in Psychology</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">BS Psych</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Foundations in psychology and counseling.</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><a style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor" target="_blank" rel="noopener">CvSU Bacoor Society</a></td>
        </tr>
        <tr>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Bachelor of Science in Business Management</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">BSBM</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Business and management fundamentals.</td>
          <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"><a style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor" target="_blank" rel="noopener">CvSU Bacoor Society</a></td>
        </tr>
      </tbody>
    </table>
    <br>
    To stay updated for changes about Courses in CvSU, make sure to follow these reliable sources
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CvSU.B.Admission">Official CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a>

 
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

<br><br><b>Typical jobs:</b> Programmer, software developer, game developer, web developer, AI engineer.
<br><b>Difficulty:</b> Hard – requires strong logic, patience, and a lot of coding practice.
<br><b>Passing Rate:</b>: No national licensure exam.
<br><b>Summary:</b> CS focuses on creating technology through coding and building software.


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
<br><br><b>Typical jobs:</b> IT technician, network administrator, cybersecurity specialist, IT support, system analyst.
<br><b>Difficulty:</b> Moderate to Hard – easier than CS but challenging in networking, troubleshooting, and cybersecurity.
<br><b>Passing Rate:</b>: No national licensure exam.
<br><b>Summary:</b> IT focuses on maintaining and supporting technology in real-world workplaces.

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
<br><br><b>Typical jobs:</b> Manager, HR officer, marketing assistant, entrepreneur, business analyst.
<br><b>Difficulty:</b> Easy to Moderate – less math-heavy than CS/IT but requires strong communication, analysis, and management skills.
<br><b>Passing Rate:</b>: No national licensure exam.
<br><b>Summary:</b> Business Administration focuses on running and leading a business effectively.

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
<br><br><b>Typical jobs:</b> Teacher, tutor, school administrator, guidance associate, curriculum developer.
<br><b>Difficulty:</b> Moderate – requires patience, communication, and mastery of teaching techniques.
<br><b>Passing Rate:</b> (CvSU Bacoor): 90% passing rate in the 2025 Licensure Exam for Teachers (LET).
<br><b>Summary:</b> Education focuses on training teachers to help students learn well.

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
<br><br><b>Typical jobs:</b> Guidance counselor, HR specialist, mental health aide, researcher, psychometrician.
<br>Difficulty: Moderate to Hard – involves heavy reading, research, and understanding human behavior.
<br>Passing Rate: Psychology board exam is only for Psychometricians/Psychologists; no specific CvSU data available.
<br><b>Summary:</b> Psychology focuses on understanding the human mind and behavior.
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
<br><br><b>Typical jobs:</b> Police officer, investigator, forensic assistant, crime analyst, corrections officer.
<br><b>Difficulty:</b> Moderate – includes law, investigation techniques, physical training, and forensic concepts.
<br><b>Passing Rate:</b> (CvSU Bacoor): 94% passing rate in the February 2025 Criminology Licensure Exam.
<br><b>Summary:</b> Criminology focuses on crime, law enforcement, and keeping communities safe.
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
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
    
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
  "admission at cvsu",
  "admission in cvsu",
  "cvsu admission",
  "admission schedule",
  "admission period",
  "admission requirements",

  "enrollment",
  "enrollment in",
  "enrollment in cvsu",
  "enroll",
  "enroll in",
  "enroll in cvsu",
  "how to enroll",
  "how to enroll in cvsu",

  "application",
  "application in",
  "application in cvsu",
  "application process",
  "application procedure",
  "procedure for application",
  "application requirements",
  "application category",

  "requirement",
  "requirements",
  "requirements in",
  "requirements in cvsu",
  "document requirements",
  "the requirement",
  "admission requirements",

  "procedure",
  "procedure in",
  "procedure in cvsu",

  "examination",
  "examination in",
  "examination in cvsu",
  "admission examination",
  "the examination",
  "reminders for examination",

  "reminders",
  "reminder for",
  "reminder in",
  "reminder in cvsu",
  "reminder for applicant",

  "applicant",
  "first year applicant",
  "senior high",
  "grade 12 student",
  "new student",
  "graduate",
  "transferee",
  "second course",
  "tcp applicant",
  "als applicant",
  "diploma degree holder",

  "of admission examination",
  "qr code",
  "scan qr",
  "admission qr",

  "cvsu admission",
  "cavite state university admission",
  "cvsu application",
  "apply cvsu",
  "cvsu online admission",
  "admission schedule cvsu",
  "cvsu enrollment",
  "cvsu first semester",
  "admission link cvsu",
  "when is cvsu admission",
  "cvsu requirements",
  "cvsu application date",
  "how to apply cvsu",
  "cvsu college admission",
  "cvsu 2026 admission",
  "online admission 2026",
  "cvsu qr code admission",
  "where to apply cvsu",
  "cvsu admission portal",
  "cvsu application 2025 2026",

  "cvsu bacoor entrance exam",
  "is there entrance exam cvsu bacoor",
  "entrance exam reminders cvsu bacoor",
  "important reminders before cvsu exam",
  "what to know before entrance exam",
  "requirements for cvsu bacoor exam",
  "exam guidelines cvsu bacoor",
  "entrance test info cvsu bacoor"
   
   
  ],
  "response": """
 <table style="width: 100%; border: 1px solid var(--text-color); padding: 30px;">
 <tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;"><b>IMPORTANT:</b></td>
</tr>
<tr>
<td style="padding: 15px; border-bottom: 1px solid var(--text-color);">Beginning <b style="border-bottom: 2px solid var(--text-color) ">October 15, 2025 - April 16, 2026</b>, the Online Admission System will be open for aspiring applicants to process their application for College Admission for the First Semester, S.Y. 2026-2027 <br><br>

<b>LINK: </b><a target="_blank" style="cursor: pointer; background: var(--sidebar-color); color: var(--text-color);" href="https://admission.cvsu.edu.ph/">https://admission.cvsu.edu.ph/</a><br>
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
a Gmail account. Download and Fill out the online application form, <a target="_blank" style="cursor: pointer; background: var(--sidebar-color); color: var(--text-color);" href="https://drive.google.com/file/d/1zoG0QutodBOX_iegsrPdtaXlgBs8Gn0a/view?fbclid=IwAR0cxxbPFag9mCOKcdWDrqd4Og8ytmJL_WFJYA5M4l_guRogSN7Ds-GBgoo" alt="admission.pdf" style="cursor: pointer;">Application Form</a> keep in mind the following:    
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
* The result of the admission examination will be announced via our Facebook page once out, so stay posted. <br><a target="_blank" style="cursor: pointer; background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CvSU.B.Admission">Cavite State University - Bacoor Guidance and Admission Services</a><br><br>
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
            "grade requirements", "grade required", "grade requirements for cvsu",
            "grade required for cvsu", "grade require", "grade require for cvsu"
        ],
        "response": """

        Here’s what’s known per course type, though note: actual acceptance may vary by campus and slot availability.
      <table  style="width: 100%; border: 1px solid var(--text-color); padding: 30px;>

    <tr>
      <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;></td>
      <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;">Course</td>
      <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;">Key Information / Admission Notes</td>
    </tr>
  <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Computer Science (BSCS)</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Technical course. <b>SHS grades of 85+ in Math, Science, and English</b> recommended. SHS strand must match (STEM or TVL-ICT).</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Information Technology (BSIT)</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Similar to CS. SHS strand must match (STEM or TVL-ICT). High demand may limit slots.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Business Administration / Management</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">No strict grade requirement. SHS report card is evaluated. Admission is more flexible than technical courses.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Education (BSEd / BEEd)</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);"><b>Final grade of 85+</b> in relevant subjects recommended. SHS strand must match campus requirements (GAS, HUMSS, STEM).</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Psychology (BS Psychology)</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">No strict grade requirement. Submit SHS report card; may include entrance exam or interview.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Criminology (BS Criminology)</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Submit SHS report card (Form 138). Admission may include exam, interview, or screening.</td>
    </tr>
</table>

      """
        },  
    {
    "patterns": [
    "unit load",
    "unit load in cvsu",
    "what is unit load",
    "what is unit load in cvsu",
    "meaning unit load",
    "meaning unit load in cvsu",
    "maximum load",
    "maximum load in cvsu",
    "minimum load",
    "minimum load in cvsu",
    "maximum and minimum load",
    "maximum and minimum load in cvsu",
    "units",
    "units in cvsu"
  ],
   "response": """ 

   Unit load refers to the total number of academic units (credits) a student enrolls in for a semester. Each subject or course has a specific number of units assigned to it, which reflects the amount of academic work or class hours per week.
   <br>
   <br>
<table style="width:100%; border-collapse: collapse; border: 1px solid var(--text-color);">
 
    <tr style="background: var(--text-color);">
      <th style="padding: 10px; border: 1px solid var(--sidebar-color); color: var(--sidebar-color); ">Topic</th>
      <th style="padding: 10px; border: 1px solid var(--sidebar-color); color: var(--sidebar-color); ">Details</th>
    </tr>
 
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Understanding Unit Load</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        <ul>
          <li><b>1 unit</b> = 1 hour of lecture per week or 3 hours of lab/practical per week (may vary by course).</li>
          <li>Each course carries a certain number of units (usually 3–4 units for lecture courses, more for lab-heavy courses like IT, CS, or Engineering).</li>
          <li>Your <b>unit load</b> is the sum of all the units of the courses you are taking in that semester.</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Maximum and Minimum Load</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        <ul>
          <li><b>Normal load:</b> 15–21 units per semester (common for most programs).</li>
          <li><b>Overload:</b> Some students may take more than 21 units if approved, usually based on GPA and other requirements.</li>
          <li><b>Underload:</b> Students may take fewer units if there are valid reasons, like health issues or academic probation.</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Why Unit Load Matters</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        <ul>
          <li>Determines your study schedule and workload.</li>
          <li>Impacts tuition and fees, because fees are often based on units.</li>
          <li>Affects graduation timeline—taking more units per semester can shorten your stay, while fewer units may extend it.</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>


    """
    },
  
    {
        "patterns": [
            "dress code",
            "dress code in cvsu",
            "wash day",
            "wash day in cvsu",
            "uniform day",
            "uniform day in cvsu",
            "what is the dress code of cvsu",
            "which day usually is wash day",
            "which day usually is uniform day",
            "dress code for events",
            "dress code for research",
            "what to wear",
            "clothes to wear"


            
        ],
        "response": """
        
<table style="width:100%; border-collapse: collapse; border: 1px solid var(--text-color);">
  <thead>
    <tr>
      <th style="padding: 10px; border: 1px solid var(--text-color);">Day / Event</th>
      <th style="padding: 10px; border: 1px solid var(--text-color);">Dress Requirement / Notes</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Monday</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Uniform Day – Students are expected to wear their official CvSU uniform.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Tuesday</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Uniform Day</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Wednesday</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Wash Day – Students may wear casual/alternate attire as permitted.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Thursday</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Uniform Day</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Friday</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Uniform Day</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Saturday</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Wash Day</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Special Events / Ceremonies</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Students are required to wear the official uniform or formal attire as directed by the event organizers.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Research Defense / Academic Presentations</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Students must wear formal clothing, such as a blouse/shirt with slacks or skirt, or business attire, as required by the faculty and department guidelines.</td>
    </tr>
  </tbody>
</table>
<br>
 To stay updated on dress code announcements, make sure to follow these reliable sources
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
        
        """
    },
    {
        "patterns": [
  "what is cor",
  "get certification of registration",
  "cor used for",
  "cor form valid",
  "cor proof of enrollment",
  "is cor required",
  "proof of enrollment",
  "used as proof of enrollment",
  "can cor can be used as proof of enrollment",
  "what is cog",
  "request certificate of grades",
  "get certificate of enrollment",
  "how to request certificate of enrollment",
  "certificate of enrollment process",
  "where to get certificate of enrollment",
  "requesting enrollment certificate",
  "certificate of enrollment requirements",
  "how to obtain enrollment certificate",
  "enrollment verification document",
  "ask for certificate of enrollment",
  "coen request",
  "coen processing",
  "cvsu bacoor certificate of enrollment",
  "when request certificate of grades"

        ],
        "response": """
<table style="width:100%; border-collapse: collapse; border: 1px solid var(--text-color); text-align: left;">
  <thead>
    <tr>
      <th style="padding: 10px; border: 1px solid var(--text-color);">Question</th>
      <th style="padding: 10px; border: 1px solid var(--text-color);">Answer / Details</th>
    </tr>
  </thead>
  <tbody>
   
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What is COR?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        COR stands for <b>Certificate of Registration</b>. It is an official document issued by CvSU that shows a student’s enrolled courses, units, and schedule for a specific semester.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">How do I get a COR?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Students can obtain a COR after completing enrollment through the registrar’s office or online student portal. Some campuses require clearance or payment confirmation first.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What is a COR used for?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        COR is used to verify enrollment, check registered subjects, and for official purposes such as scholarships, clearance, loans, and administrative transactions.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">How long is a COR valid?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        COR is valid only for the semester it was issued. Students must obtain a new COR for each subsequent semester.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Can COR be used as an ID or replace the school ID?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        No, COR is not an official ID. It cannot replace the school ID, but it can serve as proof of enrollment for specific administrative purposes.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Is COR required to bring to school?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Students may be asked to present COR during enrollment, class registration, or certain verification procedures. It is recommended to have a copy on hand for official transactions.
      </td>
    </tr>

    <!-- COG Questions -->
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What is COG?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        COG stands for <b>Certificate of Grades</b>. It shows a student’s academic performance or grades for a specific semester or school year.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">How can I request a COG?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Students can request a COG at the registrar’s office or via the official student portal. Some campuses may require a request form or payment of fees.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">When can I request a COG?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        A COG can be requested after grades have been officially released for the semester or academic term. Check the registrar’s schedule for availability.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What is a COG used for?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        COG is used to verify academic performance, for scholarship applications, transfer credentials, or other administrative purposes requiring proof of grades.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Can a COG be used as proof of enrollment?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
          No, COG only shows grades and academic performance. Proof of enrollment requires a COR or school ID.
      </td>
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">How long is a COG valid?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        A COG is valid indefinitely as proof of grades for the specific semester it represents.
      </td>
    </tr>
  </tbody>
</table>

<br>
For more information about Certification of Grades and Certification of Registration , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
        """

     },
       {
       "patterns": [
  "student id in cvsu bacoor",
  "why no student ids yet",
  "when student ids available",
  "lost cor before student id",
  "student id proof of enrollment",
  "lost student id",
  "bring student id everyday",
  "temporary documents replace student id"
  "get student id",
  "how to get student id",
  "student id requirements",
  "student id application",
  "how can i obtain student id",
  "request student id",
  "student identification card",
  "how to apply student id",
  "getting student id",
  "student id process",
  "where to get student id",
  "student id issuance"
],
     "response": """ 
<table style="width:100%; border-collapse: collapse; border: 1px solid var(--text-color); text-align: left;">
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Is there a Student ID in CvSU Bacoor?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Yes, CvSU Bacoor issues official Student IDs to enrolled students. The ID is used for identification, library access, campus transactions, and verification purposes.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Why don’t we have our Student IDs yet?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Student IDs are usually processed after enrollment and payment verification. Delays can happen due to printing schedules, administrative processing, or verification requirements.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">When will the Student IDs be available?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        IDs are typically released a few weeks after enrollment. The exact date depends on the registrar’s office and campus printing schedule. Students are advised to follow announcements for distribution dates.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What should I do if I lose my COR before getting my Student ID?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        You should request a duplicate COR from the registrar. This duplicate can temporarily serve for verification purposes until your Student ID is issued.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Can I use my Student ID as proof of enrollment?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Yes, the Student ID can serve as proof of enrollment along with your COR for most campus transactions and verification purposes.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What should I do if I lose my Student ID?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Report the loss immediately to the registrar’s office. You will need to request a replacement ID, which may require payment of a replacement fee.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Do I need to bring my Student ID every day?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Yes, it is recommended to carry your Student ID for identification, library access, and any official campus transactions.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Can temporary documents replace a Student ID?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Yes, in some cases, a COR or temporary enrollment slip can be used until your official Student ID is issued.
      </td>
    </tr>
  </tbody>
</table>
<br>
Here is the step-by-step process on how to get Student ID:
<br>
<table style="width:100%; border-collapse: collapse; border: 1px solid var(--text-color); margin-top: 20px;">
  <thead>
    <thead>
    <tr>
      <th style="padding: 10px; border: 1px solid var(--text-color);">Step</th>
      <th style="padding: 10px; border: 1px solid var(--text-color);">Description</th>
    </tr>
  </thead>
  </thead>

  <tbody>

    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">1. Complete Your Enrollment</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        You must be officially enrolled in CvSU Bacoor. Your Student ID will only be processed once your name appears in the school system.
      </td>
    </tr>

    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">2. Watch for Facebook Announcements</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        All Student ID schedules (picture-taking, processing, releasing) are posted on the official CvSU Bacoor Facebook page. Check regularly for updates about your batch.
      </td>
    </tr>

    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">3. Prepare Required Documents</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Bring the required documents, usually:
        <ul style="margin: 5px 0 0 18px;">
          <li>Enrollment slip or proof of enrollment</li>
          <li>A valid ID (if needed)</li>
          <li>Any additional documents stated in the announcement</li>
        </ul>
      </td>
    </tr>

    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">4. Go to Campus on Your Assigned Date</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Follow the exact schedule posted for your batch. Arrive on time and proceed to the room/building indicated in the Facebook announcement.
      </td>
    </tr>

    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">5. Attend Photo-Taking Session (if applicable)</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Some semesters require on-site photo capture. If your batch already submitted photos earlier, you may skip this and move directly to ID claiming.
      </td>
    </tr>

    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">6. Claim Your Student ID</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Go to the designated office, typically the Registrar’s Office or OSAS/Student Affairs Office. Present your documents and claim your official Student ID.
      </td>
    </tr>

    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">7. For Late or Missed Schedules</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        If you missed your assigned date, wait for additional announcements. CvSU Bacoor often posts separate instructions for late claimants or alternative schedules.
      </td>
    </tr>

  </tbody>
</table>


<br>
For more information about Student ID announcements and queries , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
    """
     },
     {
      "patterns": [
  "cvsu free tuition"
],

     "response": """ 
CvSU offers <b>free tuition</b> because it is a state university covered by RA 10931, which provides free tuition and waived school fees for qualified Filipino students taking their <b>first bachelor’s degree</b>. You only need to meet CvSU’s admission and academic requirements to stay eligible.

"""
     },
     {
     "patterns": [
  "meaning of cvsu logo",
  "cvsu mission",
  "cvsu vision",
  "why logo symbols agriculture science technology",
  "cvsu core values",
  "purpose of vision mission",
  "logo reflect mission vision",
  "cvsu vision and mission",
  "vision and mission of cvsu",
  "what is cvsu vision",
  "what is cvsu mission",
  "mission and vision statement cvsu",
  "cvsu institutional mission",
  "cvsu institutional vision",
  "university vision mission cvsu",
  "purpose of cvsu vision",
  "purpose of cvsu mission",
  "explain cvsu vision and mission",
  "meaning of cvsu vision mission"
],
    "response": """ 
<table style="width:100%; border-collapse: collapse; border: 1px solid var(--text-color); text-align: left;">
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What is the meaning of the CvSU logo / seal?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        The seal presents a number of symbolic elements: a book and torch (representing knowledge and wisdom, symbolizing education and humanities), a coffee twig with berries (representing the agriculture thrust of Cavite and the university’s agricultural programs), an atomic structure (for science and research), and a gear (symbolizing engineering and technology programs). <br>
        The overall triangular shape refers to the three-fold functions of the university: instruction, research, and extension/services.  <br>
        The date “1906” on the seal marks the year when the institution first started (as a school), signifying its long history and heritage. 
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What is the vision of CvSU?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        CvSU’s vision is: <b>“The premier university in historic Cavite globally recognized for excellence in character development, academics, research, innovation and sustainable community engagement.”</b>
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What is the mission of CvSU?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        CvSU’s mission is <b>"To provide excellent, equitable, and relevant educational opportunities in the arts, sciences and technology through quality instruction and responsive research and development activities. It aims to produce professional, skilled, and morally upright individuals for global competitiveness."</b>
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Why does the logo include symbols like agriculture, science, and gear/technology?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Because CvSU offers a diverse set of programs — from agriculture and agronomy, to science, engineering/technology, and humanities. The logo symbolizes this diversity and reflects the university’s commitment to serve multiple sectors, aligned with its mandate for instruction, research, and extension.
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What are the core values of CvSU?</td>
      <td style="padding:  10px; border: 1px solid var(--text-color);">
        The core values of CvSU are <b>Truth, Excellence, and Service.</b> 
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">What is the purpose of the vision and mission statements?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        The vision gives the long-term aspiration of CvSU (what it aims to be globally recognized for). The mission outlines the concrete commitments and actions — offering quality, relevant education, research, and development — to produce competent and morally upright graduates able to compete globally. 
      </td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">How does the logo reflect the mission and vision?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        The elements of the seal (book/torch, agriculture, science, technology) reflect the university’s commitment to a wide range of disciplines — embodying its mission of providing “arts, sciences and technology.” The use of the university’s founding date and the symbolic representation of instruction-research-extension reflects its long history and its aspiration in the vision to be recognized for excellence and holistic development. 
      </td>
    </tr>
  </tbody>
</table>



"""
     },
{
"patterns": [
  "park anywhere near cvsu bacoor",
  "park in official cvsu bacoor parking",
  "cvsu parking fee",
  "parking",
  "parking area",
  "park area",
  "park in cvsu",
  "students allowed to park inside campus",
  "motorcycle parking area",
  "parking during events",
  "overnight parking allowed",
  "mag park",
  "cvsu bacoor parking safe",
  "where to park in cvsu bacoor",
  "cvsu bacoor parking",
  "parking area cvsu bacoor",
  "vehicle parking cvsu bacoor",
  "cvsu bacoor parking slots",
  "parking spaces cvsu bacoor",
  "can i park my car in cvsu bacoor",
  "where is parking lot cvsu bacoor",
  "campus parking cvsu bacoor",
  "allowed parking cvsu bacoor",
  "student parking cvsu bacoor",
  "visitor parking cvsu bacoor"
],
     "response": """ 

<table style="width:100%; border-collapse: collapse; border: 1px solid var(--text-color); margin-top: 20px;">
  <tbody>

    <!-- Parking near CvSU -->
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Can I park anywhere near CvSU Bacoor?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        No. You can only park in designated areas near the campus. Some nearby streets may prohibit parking or require permission from residents. Always check signages to avoid towing or penalties.
      </td>
    </tr>

    <!-- CvSU Parking Area -->
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Can I park in the official CvSU Bacoor parking area?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Yes, CvSU Bacoor has limited parking slots available for students, staff, and visitors. Availability may depend on campus rules, events, or peak hours. Always follow the guard’s instructions upon entering.
      </td>
    </tr>

    <!-- Parking Fee -->
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Is there a parking fee?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Typically, parking inside CvSU Bacoor is free, but this may change depending on campus policies or special events. Some nearby private parking areas may charge hourly or daily rates.
      </td>
    </tr>

    <!-- Student Parking Rules -->
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Are students allowed to park inside the campus?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Yes, students may park inside as long as they follow the campus parking rules, present valid identification (ID or COR), and there are available slots. Some terms may vary during busy days.
      </td>
    </tr>

    <!-- Motorcycle Parking -->
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Is there a separate parking area for motorcycles?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Yes. CvSU Bacoor usually provides a designated motorcycle parking zone. Motorcycles must be parked properly within the marked lanes.
      </td>
    </tr>

    <!-- Parking During Events -->
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Is parking allowed during big events or special activities?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        Parking may be restricted or rerouted during university events such as orientations, performances, or exams. Guards will often guide traffic and advise alternative parking options.
      </td>
    </tr>

    <!-- Overnight Parking -->
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Is overnight parking allowed?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        No. Overnight parking is not allowed unless approved by campus administration for official purposes. Unattended vehicles may be reported or ordered to vacate.
      </td>
    </tr>

    <!-- Safety & Security -->
    <tr>
      <td style="padding: 10px; border: 1px solid var(--text-color);">Is the CvSU Bacoor parking area safe?</td>
      <td style="padding: 10px; border: 1px solid var(--text-color);">
        The parking area is monitored by campus security, but the university is not responsible for lost items or damages. Always lock your vehicle and avoid leaving valuables inside.
      </td>
    </tr>

  </tbody>
</table>

<br>
For more information about Parking Area inside CvSU and parking inqueries , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
"""

},
{
     "patterns": [
  "shift courses",
  "how to shift course",
  "changing course",
  "course transfer",
  "apply to shift course",
  "requirements for shifting course",
  "shifting course process",
  "course shifting procedure",
  "how can i transfer course",
  "switch course",
  "CvSU Bacoor course shift",
  "change course",
  "shift program",
  "how to shift course",
  "process for changing course",
  "course shifting requirements",
  "transfer to another program",
  "how to switch course",
  "steps to shift program",
  "apply for course shifting",
  "requirements for shifting program",
  "course change procedure",
  "cvsu bacoor shifting process",
  "request to shift course"
],
     "response": """ 
<table style="width:100%; border-collapse: collapse; border: 1px solid var(--text-color); margin-top:20px;">
  <thead>
    <tr>
      <th style="padding:10px; border:1px solid var(--text-color); width:25%;">Step</th>
      <th style="padding:10px; border:1px solid var(--text-color);">Description</th>
    </tr>
  </thead>

  <tbody>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color);">1. Decide & Check Feasibility</td>
      <td style="padding:10px; border:1px solid var(--text-color);">
        Choose the course you want to shift into and make sure it is offered by CvSU (including your campus).  
        Check if shifting is allowed from your current program, especially if you are moving from non-degree to degree programs.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color);">2. Get the Shifting Form</td>
      <td style="padding:10px; border:1px solid var(--text-color);">
        Obtain the official <b>Application for Shifting / Change of Program</b> form from your campus.  
        Fill it out with your current program, desired program, and the reason for shifting (if required).
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color);">3. Get Required Approvals</td>
      <td style="padding:10px; border:1px solid var(--text-color);">
        Your form must be signed by:
        <ul style="margin:5px 0 0 18px;">
          <li>Your current Dean / Program Head (for release)</li>
          <li>Dean / Program Head of the course you want to shift into (for acceptance)</li>
        </ul>
        Some campuses may also require guidance counseling or evaluation.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color);">4. Submit to Registrar</td>
      <td style="padding:10px; border:1px solid var(--text-color);">
        Submit your fully signed shifting form to the Campus Registrar or the office in charge of shiftees.  
        Submission must be done <b>before the start of enrollment</b> since shifting is processed before registration.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color);">5. Submit Additional Requirements (If Needed)</td>
      <td style="padding:10px; border:1px solid var(--text-color);">
        Some programs may require:
        <ul style="margin:5px 0 0 18px;">
          <li>Minimum GPA</li>
          <li>Entrance exam</li>
          <li>Transcript of Grades / academic records</li>
          <li>Certificate of Good Moral Character</li>
        </ul>
        This depends on the course you want to enter.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color);">6. Wait for Confirmation</td>
      <td style="padding:10px; border:1px solid var(--text-color);">
        The Registrar will update your records once your shifting is approved.  
        After approval, you can enroll under your new program during the next enrollment period.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); ">⚠️ Important Reminders</td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        <ul style="margin:5px 0 0 18px;">
          <li>Shifting approval depends on slot availability and your academic standing.</li>
          <li>Some programs have year-level limits for shiftees.</li>
          <li>Board-related programs may require additional prerequisites.</li>
          <li>Shifting late in your college years may delay graduation.</li>
        </ul>
      </td>
    </tr>

  </tbody>
</table>

<br>
For more information about Shifting and Changing course , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
"""

},
{ "patterns": [
  "fail subject",
  "failing grade appeal",
  "recover from failing grade",
  "absences allowed",
  "passing after failing quizzes",
  "struggling in subject",
  "dropped vs failed",
  "retake subject",
  "improve grades",
  "failing grade prerequisites",
  "failing grade scholarship",
  "grade impact",
  "subject failure consequences"
],

 "response": """ 
<table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width:100%;">
  <tbody>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>What happens if I fail a subject?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">If you fail a subject, you are required to retake it in the following semester or during the next available offering. Failing a major subject may affect your progression in your program and could delay your graduation, especially if it is a prerequisite to other subjects.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>How can I appeal a failing grade?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">You may file a grade appeal through your instructor and program coordinator. Provide valid reasons such as grade computation errors, missing requirements that you can prove were submitted, or other academic concerns. The department will review your case and decide if your grade can be revised.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>How many absences are allowed?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Most subjects allow a maximum of <b>20% of total class hours</b> as allowable absences. If you exceed this limit, you may receive a failing grade (FA) or be dropped from the class, depending on the instructor’s policy.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Can I still pass if I fail quizzes or activities?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Yes, you can still pass if your overall weighted grade meets the passing requirement (typically 75% or 3.00). Performance in finals, major outputs, and class participation can still raise your overall score.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>What should I do if I am struggling in a subject?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Talk to your instructor early, attend consultations, ask for clarifications, and participate in review sessions. Managing your time and organizing your study schedule can also help improve your performance.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>What is the difference between “Dropped” and “Failed”?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">“Dropped” means you are removed from the subject before the midterm or final cutoff, often due to absences. “Failed” means you completed the course but did not meet the passing requirements.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Can I retake a subject multiple times?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Yes, but repeated failing attempts may require special approval from the dean or department. Retaking subjects increases workload and may delay your graduation.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>How can I improve my grades after performing poorly?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Consistent studying, attending all classes, submitting complete requirements, improving exam preparation, and seeking feedback from instructors can significantly raise your chances of passing.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>What happens if my failing grade affects my prerequisites?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">If the failed subject is a prerequisite, you cannot enroll in the next-level subject until you pass it. This may affect your semester load and graduation timeline.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Does failing a subject affect my scholarship?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Yes, many scholarships require maintaining a certain GPA or no failing grades. A failing grade can lead to probation or loss of scholarship benefits.</td>
    </tr>

  </tbody>
</table>

<br>
For more information about failing grade inqueries , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
"""


},
{
     "patterns": [ 
  "is ID required",
  "is student ID needed",
  "ID policy inside campus",
  "are IDs mandatory",
  "uniform requirement",
  "is uniform compulsory",
  "campus ID enforcement",
  "campus uniform enforcement",
  "ID and uniform rules",
  "what happens without ID",
  "what happens without uniform",
  "ID or uniform exceptions",
  "uniform policy cvsu bacoor"
],

    "response": """ 
At CvSU, both student IDs and the prescribed school uniform are required inside the campus; according to the Code of Conduct and Dress Code, every enrolled student must wear the official uniform on school days and must also display their official ID card whenever on campus.
<br><br>
<table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width:100%;">
  <thead>
    <tr>
      <th style="padding:10px; border:1px solid var(--text-color); ">Requirement</th>
      <th style="padding:10px; border:1px solid var(--text-color); ">Details</th>
      <th style="padding:10px; border:1px solid var(--text-color); ">Consequences if Not Followed</th>
      <th style="padding:10px; border:1px solid var(--text-color); ">Notes / Exceptions</th>
    </tr>
  </thead>

  <tbody>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Student ID</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Must wear the official ID visibly at all times while inside campus.</td>
      <td style="padding:10px; border:1px solid var(--text-color); ">May be denied entry to campus or classrooms; repeated offenses can lead to disciplinary action.</td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Special cases may exist for events or temporary permissions; generally required for all students.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>School Uniform</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Must wear the prescribed official uniform on school days.</td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Denied entry to campus or classrooms; repeated non-compliance may result in sanctions.</td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Some campuses may allow exceptions on designated “wash days” or special events.</td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Both ID & Uniform</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Required together to fully comply with CvSU’s student conduct policies.</td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Non-compliance with either can result in restricted access or disciplinary measures.</td>
      <td style="padding:10px; border:1px solid var(--text-color); ">Essential whenever a student is considered “on campus duty” (classes, labs, facilities).</td>
    </tr>

  </tbody>

</table>

<br>
For more information make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>

  """
},
{
"patterns": [
  "how to join student organizations",
  "join student org cvsu",
  "are student organizations open to all students",
  "student org eligibility cvsu",
  "do i need to pay membership fees",
  "student organization fees cvsu",
  "list of recognized student organizations cvsu",
  "where to find student org list cvsu",
  "when is student org recruitment",
  "student organization recruitment period",
  "requirements to join student organization",
  "can i join multiple organizations cvsu",
  "benefits of joining student organizations",
  "are student organizations required",
  "student organization mandatory or not",
  "what happens if i become inactive in student org",
  "inactive member student org rules",
  "student clubs cvsu",
  "cvsu bacoor student organizations info",
  "how to become a member of student organization"
],

    "response": """ 

<table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width:100%;">
  <tbody>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>How do I join student organizations in CvSU Bacoor?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        You can join any recognized student organization during their recruitment period, usually held at the start of every semester. 
        Visit their booths during the Student Organization Fair, or follow their official social media pages for announcements. 
        Most organizations require you to fill out a registration form and attend an orientation.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Are all student organizations open to all students?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Many organizations are open to everyone, but some are <em>program-based</em> (e.g., IT, Business, Education orgs) and accept only students enrolled in those courses. 
        Interest-based orgs (arts, sports, culture, volunteering) are usually open to all CvSU Bacoor students.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Do I need to pay membership fees?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Some organizations require a small membership fee to support activities, uniforms, or events. 
        However, many organizations do not require fees, especially academic and volunteer-based groups.
        Fees (if any) are always announced before joining.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Where can I see the list of recognized student organizations?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        The official list is posted at the Office of Student Affairs and Services (OSAS) or on their official Facebook page. 
        Each academic program also posts updates about their course-based organizations.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>When is the recruitment period?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Recruitment typically happens at the beginning of every semester during the **Student Org Recruitment Week** or **Organization Fair**. 
        Some orgs also accept mid-semester applicants depending on their activities and membership needs.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>What are the requirements to join an organization?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Requirements vary per org, but usually include:
        <ul>
          <li>Being an officially enrolled CvSU Bacoor student</li>
          <li>Filling out a membership form</li>
          <li>Attending orientation or interview (for some orgs)</li>
          <li>Commitment to attend meetings and activities</li>
        </ul>
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Can I join multiple organizations?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes. Students are allowed to join more than one organization, as long as they can manage their time and fulfill the responsibilities of each organization. 
        Some students join both an academic org and an interest-based org.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>What benefits do student organizations provide?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Student orgs offer opportunities such as:
        <ul>
          <li>Leadership development</li>
          <li>Community involvement</li>
          <li>Skill-building workshops and trainings</li>
          <li>Access to academic support and networks</li>
          <li>Participation in events, competitions, and seminars</li>
        </ul>
        Being active in orgs also enhances your resume.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>Are student organizations required?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        No. Joining student organizations is voluntary. 
        However, being part of one is highly encouraged because it improves your campus life, builds connections, and helps develop useful skills.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><b>What happens if I become inactive after joining?</b></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Inactive members may lose benefits such as event participation, priority slots, or officer opportunities. 
        Some orgs may also remove inactive members from their official records. 
        However, you can usually apply again during the next recruitment period.
      </td>
    </tr>

  </tbody>
</table>


<br>
For more information about Student Organization , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
"""
    
},
{
  "patterns": [
  "is there free wifi on campus",
  "cvsu bacoor free wifi",
  "is cvsu bacoor wifi available for students",
  "campus wifi for students cvsu",
  "what is the wifi password cvsu",
  "where to get latest wifi password cvsu",
  "cannot connect to campus wifi",
  "why can't i connect to cvsu wifi",
  "is the campus wifi fast",
  "wifi speed cvsu bacoor",
  "can visitors or parents use the wifi",
  "guest wifi cvsu",
  "are mobile hotspots allowed on campus",
  "personal hotspot policy cvsu",
  "is there wifi inside classrooms",
  "classroom wifi availability cvsu",
  "what to do if i need wifi for academic requirements",
  "wifi help for students cvsu",
  "campus internet issues cvsu",
  "how to access cvsu bacoor wifi"
],
"response": """ 
<table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width:100%;">

  <tbody>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Is there free Wi-Fi on campus?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes. CvSU Bacoor provides free Wi-Fi access for enrolled students inside campus. 
        The signal is strongest near academic buildings, the library, laboratories, and selected hallways.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Is CvSU Bacoor campus Wi-Fi available for students?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes. Students can connect to the official campus Wi-Fi network. 
        You must be an officially enrolled student to receive access or a login credential (if required).
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>What’s the Wi-Fi password?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Wi-Fi passwords are <strong>not publicly posted</strong> for security reasons.  
        Students may get the password from:
        <ul>
          <li>The campus IT Office</li>
          <li>The Library (front desk)</li>
          <li>Your class adviser or program office</li>
        </ul>
        The password also changes regularly to maintain network security.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Where can I get the latest Wi-Fi password?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Visit the IT Office or Library and present your valid COR/ID. 
        Some programs also announce updated passwords in official group chats or Facebook pages.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Why can’t I connect to the campus Wi-Fi?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Common reasons include:
        <ul>
          <li>Incorrect password</li>
          <li>Too many connected users (peak hours)</li>
          <li>Weak signal in your location</li>
          <li>Your device needs to “forget network” and reconnect</li>
        </ul>
        If the issue persists, you may report it to the IT Office.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Is the Wi-Fi fast?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Speed varies depending on the time of day, number of users, and location. 
        Wi-Fi is generally good for research, LMS access, email, and basic browsing. 
        Heavy downloads and video streaming may be limited during high-traffic hours.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Can visitors or parents use the Wi-Fi?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Campus Wi-Fi is reserved for students and staff only.  
        Guests may request temporary access during official events, but approval depends on campus policy.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Are mobile hotspots allowed on campus?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes, but students are encouraged to use them responsibly. 
        In some computer labs or testing rooms, personal hotspots may be restricted to avoid interference with school networks.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Is there Wi-Fi inside classrooms?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes, but the signal strength depends on the building. 
        Some rooms have stronger access points than others. 
        Students usually get better connection near hallways or common areas.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>What should I do if I need Wi-Fi for academic requirements?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        You may use Wi-Fi–enabled areas like the library, student lounges, or designated study spaces.  
        These places usually have more reliable signal for online activities and LMS submissions.
      </td>
    </tr>

  </tbody>
</table>

<br>
For more information about Wi-Fi in CvSU Bacoor , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
"""

  
},
{
     "patterns": [
  "when is the cvsu bacoor recognition ceremony",
  "when is the graduation ceremony cvsu bacoor",
  "cvsu bacoor graduation schedule",
  "where is the recognition or graduation held",
  "venue for cvsu bacoor graduation",
  "who can attend the ceremony cvsu",
  "attendance rules for recognition graduation",
  "dress code for cvsu recognition",
  "graduation attire requirements cvsu",
  "do we need to pay graduation fees",
  "recognition fees cvsu bacoor",
  "am i eligible for graduation cvsu",
  "how to know graduation eligibility",
  "am i part of the honor list cvsu recognition",
  "honor list announcement cvsu",
  "do i need to attend rehearsals cvsu graduation",
  "is recognition practice required",
  "what happens if i miss the ceremony",
  "missed graduation cvsu",
  "can i join graduation with pending grades",
  "pending grades graduation policy cvsu",
  "can i request digital copy of ceremony",
  "is there livestream for cvsu recognition",
  "graduation live stream cvsu bacoor"
],

"response": """ 
<table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width:100%;">

  <tbody>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>When is the CvSU Bacoor Recognition or Graduation ceremony?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        The schedule varies every academic year.  
        Recognition (for non-graduating honor students) is usually held <strong>near the end of the 2nd semester</strong> 
        or <strong>after finals</strong>, while Graduation is usually held <strong>around June–July</strong>.  
        The official dates are announced on:
        <ul>
          <li>CvSU Bacoor Official Facebook Page</li>
          <li>Registrar’s Office announcements</li>
          <li>Program or college pages</li>
        </ul>
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Where is the Recognition/Graduation held?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        It is typically held at a designated venue announced by the campus —  
        common locations include large auditoriums, gyms, or partner event halls.  
        The venue depends on batch size and availability.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Who is allowed to attend the ceremony?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Graduating students or awardees may bring a limited number of guests.  
        The guest limit is announced per academic year (usually 1–3 guests).  
        All attendees must follow campus security and dress-code policies.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>What is the dress code for Recognition or Graduation?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Students are required to wear <strong>formal attire</strong>.  
        Common requirements:
        <ul>
          <li>White polo or blouse</li>
          <li>Black pants or skirt</li>
          <li>Formal shoes</li>
          <li>Academic sash, hood, or toga (if required for graduation)</li>
        </ul>
        Guests are also encouraged to dress formally.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Do we need to pay graduation or recognition fees?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes. Graduation fees typically include the cost of:
        <ul>
          <li>Toga rental</li>
          <li>Diploma jacket</li>
          <li>Program booklet</li>
          <li>Venue and event expenses</li>
        </ul>
        Recognition may have minimal or no fees depending on the campus.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>How do I know if I’m eligible for graduation?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        You must complete all academic requirements, pass all subjects, finish OJT (if applicable), 
        and have no pending balances.  
        The Registrar’s Office and your program will verify your status during the graduation evaluation.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>How do I know if I’m part of the honor list for Recognition?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        The Dean’s Office releases the official list of academic awardees.  
        Students must meet the required GWA, have no failing grades, and comply with university policies.  
        The final list is posted before the Recognition ceremony.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Do I need to attend rehearsals?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes. Graduation and Recognition rehearsals are <strong>mandatory</strong> for participating students.  
        Important instructions such as:
        <ul>
          <li>Walk sequence</li>
          <li>Awarding guidelines</li>
          <li>Dress code check</li>
          <li>Seating arrangements</li>
        </ul>
        are given during rehearsals.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>What happens if I miss the ceremony?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        You can still receive your diploma or certificate from the Registrar’s Office on the scheduled release date.  
        However, you may not participate in the on-stage awarding or photo sessions.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Can I still join if I have pending grades?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Students with unresolved INC or pending grades are <strong>not allowed</strong> to join graduation until cleared.  
        Complete any deficiencies with your instructors before the deadline posted by the Registrar.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Can I request a digital copy or livestream of the ceremony?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Many ceremonies are livestreamed on the official CvSU Bacoor Facebook Page.  
        Photos and recordings may also be uploaded after the event for students and families to download.
      </td>
    </tr>

  </tbody>
</table>
<br>
For more information about Graduation in CvSU Bacoor , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>


""",

},

{
"patterns": [
  "how to apply for deans lister",
  "application process for deans list cvsu",
  "minimum grade requirement for deans lister",
  "grade requirement deans list",
  "do i need full load for deans lister",
  "unit load requirement deans list",
  "does pe or nstp affect deans lister qualification",
  "pe nstp effect on deans list",
  "what disqualifies a student from deans list",
  "deans lister disqualification cvsu",
  "do transferees qualify for deans lister",
  "can irregular students be deans lister",
  "will i receive certificate as deans lister",
  "deans lister certificate cvsu",
  "is there cash incentive for deans listers",
  "scholarship for deans listers cvsu",
  "how to know if i made it to deans list",
  "deans list announcement cvsu",
  "requirements to become deans lister",
  "eligibility for deans lister cvsu",
  "am i qualified for deans list",
  "deans lister rules cvsu",
  "process for checking deans list results",
  "where to see deans lister list cvsu"
],
"response": """ 

<table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width:100%;">

  <tbody>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>How do I apply for Dean’s Lister?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        To apply for Dean’s Lister status at CvSU Bacoor:
        <ul>
          <li>Wait for the official announcement from your department or the campus Facebook page.</li>
          <li>Download or get the Dean’s List application form (if required).</li>
          <li>Submit your grades or Certificate of Grades (COG) to your program’s office for evaluation.</li>
          <li>Follow additional instructions from your program chair or dean.</li>
        </ul>
        Some semesters automatically evaluate students without needing an application.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>What is the minimum grade requirement to qualify as a Dean’s Lister?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Requirements may vary slightly by campus or program, but the common rule is:
        <ul>
          <li><strong>No grade below 2.0</strong> in any subject.</li>
          <li><strong>No INC, DROPPED, or FAILED</strong> subjects.</li>
          <li><strong>GWA of 1.75 or higher</strong> (some colleges require 1.50–1.75).</li>
          <li>Complete load — must be enrolled in the normal full academic load.</li>
        </ul>
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Do I need a full load to qualify?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes. Most colleges of CvSU require students to be enrolled in a <strong>regular full load</strong> 
        to be eligible for Dean’s List.  
        Underloaded students are usually not considered, unless under special cases approved by the Dean.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>If I have PE or NSTP, will it affect Dean’s Lister qualification?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        PE and NSTP subjects are counted.  
        You must pass them with qualifying grades (no 3.0, no INC, no Fail) to remain eligible.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>What disqualifies a student from the Dean’s List?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        You will not qualify if you have:
        <ul>
          <li>A failing grade (5.0)</li>
          <li>Grade of 3.0 in some strict programs</li>
          <li>INC or DROPPED in any subject</li>
          <li>Conduct violations or disciplinary cases</li>
          <li>An incomplete academic load</li>
        </ul>
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Do transferees or irregular students qualify?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes, as long as:
        <ul>
          <li>They are enrolled in a full load for that semester.</li>
          <li>They meet the GWA and grade requirements.</li>
          <li>They have no failing or incomplete grades.</li>
        </ul>
        Previous school grades are not counted; only current CvSU grades matter.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Do I receive a certificate if I become a Dean’s Lister?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Yes. Dean’s Listers receive a <strong>Certificate of Academic Excellence</strong>  
        during Recognition Day or from their department.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>Is there a cash incentive or scholarship for Dean’s Listers?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        Some semesters offer incentives or priority perks (depending on campus policies), such as:
        <ul>
          <li>Scholarship priority</li>
          <li>Discounts or stipends (if funded for that year)</li>
          <li>Recognition during awards ceremonies</li>
        </ul>
        Incentives vary per academic year.
      </td>
    </tr>

    <tr>
      <td style="padding:10px; border:1px solid var(--text-color); "><strong>How will I know if I made it to the Dean’s List?</strong></td>
      <td style="padding:10px; border:1px solid var(--text-color); ">
        The official list is posted on:
        <ul>
          <li>The department bulletin boards</li>
          <li>CvSU Bacoor Facebook page</li>
          <li>College or program announcements</li>
        </ul>
      </td>
    </tr>

  </tbody>
</table>
<br>
For more information about Graduation in CvSU Bacoor , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>


""",
},
{
"patterns": [
  "what is ojt in cvsu bacoor",
  "ojt meaning cvsu",
  "how many ojt hours required",
  "ojt hours per course cvsu",
  "when does ojt start",
  "what year takes ojt cvsu",
  "requirements for ojt cvsu",
  "ojt prerequisites cvsu bacoor",
  "can i choose my own ojt company",
  "self arranged ojt cvsu",
  "does cvsu allow online ojt",
  "online ojt option cvsu",
  "what happens if i fail ojt",
  "incomplete ojt hours consequence",
  "where to get ojt updates cvsu",
  "ojt announcements cvsu bacoor",
  "ojt coordinator cvsu bacoor",
  "ojt guidelines cvsu bacoor",
  "companies accepted for ojt cvsu",
  "ojt placement process cvsu"
],

"response": """ 
<table border="1" cellpadding="8" cellspacing="0">
 

    <tr>
        <td style="padding:10px; border:1px solid var(--text-color); ">What is OJT in CvSU Bacoor?</td>
        <td style="padding:10px; border:1px solid var(--text-color); ">OJT (On-the-Job Training) is a required internship program for graduating students where they gain real work experience in partner companies or agencies. CvSU Bacoor requires all OJT to be done on-site; <b>online OJT is no longer allowed</b>.</td>
    </tr>

    <tr>
        <td style="padding:10px; border:1px solid var(--text-color); ">How many OJT hours are required per course?</td>
        <td style="padding:10px; border:1px solid var(--text-color); ">
            <ul>
                <li><b>BS Information Technology (BSIT)</b> – 486 hours</li>
                <li><b>Bachelor of Science in Computer Science (BSCS)</b> – 486 hours</li>
                <li><b>BS Business Management (HRDM / Marketing)</b> – ~300 hours</li>
                <li><b>BS Hospitality Management (BSHM)</b> – 600 hours</li>
                <li><b>BS Office Administration (BSOA)</b> – 300 hours</li>
                <li><b>BS Psychology (if offered)</b> – 200–300 hours</li>
            </ul>
            Note: Hours may slightly vary based on updated campus guidelines, but these are the most common requirements.
        </td>
    </tr>

    <tr>
        <td style="padding:10px; border:1px solid var(--text-color); ">What year does OJT usually start?</td>
        <td style="padding:10px; border:1px solid var(--text-color); ">
            OJT schedules may vary depending on curriculum changes, but the most common pattern in CvSU Bacoor is:
            <ul>
                <li><b>BSIT / BSCS / BSHM</b> – usually during <b>4th year, 2nd semester</b></li>
                <li><b>BSOA</b> – often during <b>3rd year or 4th year</b> depending on section and curriculum</li>
                <li><b>Business Management programs</b> – commonly <b>4th year, 1st or 2nd semester</b></li>
            </ul>
            Final schedules depend on the released curriculum for your year level, so it’s best to wait for official department announcements.
        </td>
    </tr>

    <tr>
        <td style="padding:10px; border:1px solid var(--text-color); ">What are the requirements for OJT?</td>
        <td style="padding:10px; border:1px solid var(--text-color); ">
            <ul>
                <li>Updated Resume</li>
                <li>Endorsement Letter from Department</li>
                <li>Parent's Consent</li>
                <li>MOA (Memorandum of Agreement) with company</li>
                <li>Medical Certificate (for companies requiring it)</li>
                <li>School ID & Registration Form</li>
                <li>Good Moral Certificate (if needed)</li>
            </ul>
            All documents must be processed in the department office. <b>Note: Online OJT is no longer accepted.</b>
        </td>
    </tr>

    <tr>
        <td style="padding:10px; border:1px solid var(--text-color); ">Can I choose my own company for OJT?</td>
        <td style="padding:10px; border:1px solid var(--text-color); ">Yes. Students can choose their preferred company, but it must be related to their program and must be approved by the department. The company must agree to sign a MOA with CvSU Bacoor.</td>
    </tr>

    <tr>
        <td style="padding:10px; border:1px solid var(--text-color); ">Does CvSU Bacoor still allow online OJT?</td>
        <td style="padding:10px; border:1px solid var(--text-color); "><b>No. CvSU Bacoor no longer accepts or provides online OJT.</b> All OJT must be completed on-site.</td>
    </tr>

    <tr>
        <td style="padding:10px; border:1px solid var(--text-color); ">What happens if I fail or cannot complete my OJT hours?</td>
        <td style="padding:10px; border:1px solid var(--text-color); ">Failure to complete the required hours or violating company guidelines may result in an incomplete or failing grade. Students must repeat their OJT the next semester to graduate.</td>
    </tr>

    <tr>
        <td style="padding:10px; border:1px solid var(--text-color); ">Where can I get updates about OJT?</td>
        <td style="padding:10px; border:1px solid var(--text-color); ">OJT announcements are posted through your respective departments (IT, CS, HM, BM, BSOA, etc.) and on the official CvSU Bacoor Facebook page. Advisers may also post updates in group chats.</td>
    </tr>

</table>
<br>
For more information about OJT in CvSU Bacoor , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>


""",
},
#XXXXXXXXXXXXXXXXXXXXX
{
  "patterns": [
  "cvsu clearance",
  "is there clearance in cvsu",
  "what is clearance cvsu bacoor",
  "clearance requirements cvsu",
  "requirements for clearance",
  "when to process clearance cvsu",
  "clearance schedule cvsu bacoor",
  "where to get clearance form",
  "cvsu clearance form location",
  "who signs the clearance cvsu",
  "clearance signatories cvsu bacoor",
  "can i enroll without clearance cvsu",
  "enrollment blocked no clearance",
  "graduating student clearance cvsu",
  "special clearance for graduates",
  "how long clearance processing takes",
  "clearance processing duration cvsu",
  "can i process clearance with failing grades",
  "lost clearance form what to do",
  "replace lost clearance cvsu",
  "is online clearance available",
  "cvsu online clearance system",
  "clearance steps cvsu bacoor",
  "student clearance cvsu"
],
"response": """ 

<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
 
  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Is there a clearance in CvSU?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Yes. CvSU requires students to complete a <b>Student Clearance</b> at the end of every semester. This ensures the student has no pending obligations such as unpaid fees, unreturned books, missing requirements, or incomplete academic tasks.</td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">What is Clearance in CvSU Bacoor?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">The CvSU Bacoor clearance is a document that needs to be signed by various offices to verify that the student has settled all responsibilities. It is often required for:<br>
      <ul>
        <li>Graduation</li>
        <li>Enrollment for next semester</li>
        <li>Requesting COG / COR / Grades</li>
        <li>OJT Applications</li>
        <li>Claiming school documents (ID, TOR, Certificate, etc.)</li>
      </ul>
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">What are the requirements for clearance?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">The usual requirements include:
      <ul>
        <li>No unpaid school fees</li>
        <li>No unreturned library books</li>
        <li>No pending violations with OSAS</li>
        <li>Completed academic requirements</li>
        <li>Signed forms from your department / adviser</li>
        <li>Receipt (if printing fees apply)</li>
      </ul>
      Requirements may change depending on campus announcements.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">When do students process clearance?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Clearance is usually processed <b>at the end of every semester</b> or <b>before graduation.</b> Some courses require mid-year clearance for OJT and practicum.</td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Where can I get the clearance form?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">You can get the clearance form from your department office or the Registrar. Some semesters allow downloading a digital form from the campus Facebook page.</td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Who needs to sign the clearance?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Clearance typically requires signatures from:
      <ul>
        <li>Your instructor(s)</li>
        <li>Department Chairperson</li>
        <li>Library</li>
        <li>Cashier</li>
        <li>Registrar</li>
        <li>OSAS / Student Affairs</li>
        <li>Laboratory Custodian (for programs with labs)</li>
      </ul>
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Can I enroll next semester without clearance?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">No. Students with incomplete clearance from the previous semester usually cannot proceed with enrollment or cannot claim certain documents.</td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Do graduating students need a special clearance?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Yes. Graduating students must process a <b>Graduation Clearance</b>, which includes additional checks like:<br>
      <ul>
        <li>Complete academic records</li>
        <li>OJT completion (if applicable)</li>
        <li>Good Moral clearance</li>
        <li>Final evaluation from Registrar</li>
      </ul>
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">How long does clearance processing take?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">It depends on the semester, but usually:
      <ul>
        <li>Regular clearance: 1–3 days</li>
        <li>Graduation clearance: 3–7 days</li>
      </ul>
      Delays may occur if offices have long lines or if students have incomplete requirements.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Can I process clearance even if I have failing grades?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Yes. Clearance focuses on responsibilities (fees, library, documents) not on grades. However, instructors must still sign your academic clearance to verify you completed all academic requirements.</td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">What happens if I lose my clearance form?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">You must request another copy and redo the signatures. Always take a photo of your clearance as backup.</td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Is online clearance available?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Some semesters temporarily offered partial online clearance, but <b>CvSU Bacoor mostly requires on-site signing</b>. Always check the official Facebook page for announcements.</td>
  </tr>
</table>
<br>
For more information about Clearance in CvSU Bacoor , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>


"""
},
{
     "patterns": [
  "cvsu hymn",
  "what is the cvsu hymn",
  "cvsu hymn lyrics",
  "lyrics of cvsu hymn",
  "cvsu hymn youtube",
  "cvsu hymn video",
  "cvsu hymn instrumental",
  "download cvsu hymn",
  "cvsu hymn mp3",
  "who composed the cvsu hymn",
  "composer of cvsu hymn",
  "when do students sing the cvsu hymn",
  "is cvsu hymn required",
  "memorize cvsu hymn",
  "cvsu hymn vs cvsu march",
  "difference between cvsu hymn and cvsu march",
  "where to find cvsu hymn",
  "cvsu hymn audio",
  "cvsu hymn practice",
  "how to learn cvsu hymn",
  "cvsu hymn information",
  "cvsu hymn guide",
  "official cvsu hymn"
],
 "response": """ 
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">



  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">What is the CvSU Hymn?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      The CvSU Hymn is the official school song of Cavite State University. It is sung during official events,
      flag ceremonies, orientations, recognition rites, and graduation ceremonies. The hymn symbolizes unity,
      discipline, and loyalty to the university.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">CvSU Hymn Lyrics</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      <pre style="white-space: pre-wrap; font-family: inherit;">
Hail Alma Mater Dear, Cavite State University
Thy honor we’ll uphold and love
Wherever we may be.

Thy glory we’ll pursue
Thy name we shall revere
We’ll live to make you proud of us
Through the years.

We’ll keep our paths aglow
With noble dreams in view
We’ll strive to reach our goals
For the glory of God and our country too.

Hail Alma Mater Dear
Cavite State University
The love we pledge will never die
Loyalty we’ll keep to thee.
      </pre>
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Who composed the CvSU Hymn?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      The CvSU Hymn was composed specifically for Cavite State University to represent its spirit, 
      values, and mission. It is traditionally played during major campus events. (Note: Composer 
      details are not always disclosed in public student documents.)
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">When do students sing the CvSU Hymn?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Students sing the hymn during:
      <ul>
        <li>Flag ceremonies</li>
        <li>University assemblies</li>
        <li>Recognition and graduation</li>
        <li>Campus programs and orientations</li>
        <li>Major university celebrations</li>
      </ul>
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Is the CvSU Hymn required to memorize?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Yes. Students are highly encouraged to memorize the CvSU Hymn because it is regularly 
      performed during important ceremonies and university events.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Is the CvSU Hymn different from the CvSU March?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Yes. The CvSU Hymn is the solemn school song, while the CvSU March is an upbeat ceremonial 
      march often played before events or formal programs.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Where can I download an MP3 or instrumental version?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Students may download or access versions through:
      <ul>
        <li>Official CvSU YouTube uploads</li>
        <li>Campus media pages</li>
        <li>Audio provided during orientations or classes</li>
      </ul>
      The school does not officially release MP3 downloads, but videos are publicly accessible.
    </td>
  </tr>

</table>


<br>
<table >
<tr>
<td style="padding:10px; border:1px solid var(--text-color); ">
This is the CvSU Hymn YouTube Video :
<br><iframe width="560" height="315" 
src="https://www.youtube.com/embed/A2fOWAo9jME?si=O1ptwtJvYc-me84N&amp;start=12" 
title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; 
gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
</td>
</tr>

</table>
<br><br>
For more information about CvSU Hymn in CvSU Bacoor , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>

  """

},
#XXXXXXXXXXXXXXXXXXX
{
    "patterns": [
  "old student",
  "how to enroll as old student",
  "old student enrollment cvsu",
  "cvsu bacoor enrollment old students",
  "process for old student enrollment",
  "enrollment steps for returning students",
  "how to enroll as regular student",
  "regular student enrollment cvsu",
  "cvsu bacoor regular student process",
  "requirements for old student enrollment",
  "where to enroll old students",
  "old student enrollment guide",
  "regular student enrollment guide",

  "how much is society fee",
  "society fee amount",
  "cvsu society fee",
  "student organization fee cvsu",
  "society fee payment",
  "what is society fee",
  "meaning of society fee",
  "purpose of society fee",
  "why do students pay society fee",
  "society fee explanation",
  "society fee details cvsu"
],

 "response": """ 
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
  <tr>
    <th style="padding:10px; border:1px solid var(--text-color); ">Step</th>
    <th style="padding:10px; border:1px solid var(--text-color); ">Action</th>
    <th style="padding:10px; border:1px solid var(--text-color);">Details / Notes</th>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Step 1</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Pay your society fee as announced by your department.</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      <b>The society fee usually cost 100 pesos per student.</b> The <u>Society fee</u> is a mandatory payment for student organizations and student activities. 
      Check your department announcements or your batch adviser for the exact amount and deadline. 
      Keep the official receipt for later verification.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Step 2</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Secure your Curriculum Checklist from your department.</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Obtain a printed or digital copy of your curriculum checklist. 
      This document shows your completed subjects, pending courses, and sequence of enrollment. 
      It will guide your subject selection during advising.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Step 3</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Proceed with grade evaluation and subject advising.</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Meet with your department adviser for evaluation of your grades and eligibility to enroll in 
      certain courses. The adviser will suggest subjects based on prerequisites, failed courses, and 
      your academic standing.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Step 4</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Obtain your queuing number per program.</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Queuing numbers are issued to manage enrollment in an orderly manner. 
      The number is usually distributed by the Registrar or department office and determines the order 
      for encoding your subjects.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Step 5</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Wait for encoding and validation of subjects.</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      The Registrar’s Office or your department staff will encode your selected subjects in the system. 
      Validation ensures that prerequisites are met, no schedule conflicts exist, and your enrollment is accurate.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Step 6</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">Settle your payment at the Cashier's Office and keep your receipt.</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      After validation, pay your tuition and other fees at the Cashier’s Office. Always keep your official 
      receipt as proof of payment, which may be required for document processing, ID issuance, or OJT registration.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Additional Notes</td>
    <td style="padding:10px; border:1px solid var(--text-color);" colspan="2">
      <ul>
        <li>Bring your valid Student ID and any required documents (e.g., COR, previous grades, OJT forms) during enrollment.</li>
        <li>Follow official schedules announced via CvSU Bacoor Facebook page or department notifications.</li>
        <li>Incomplete or late steps may delay your enrollment, document issuance, or access to certain services.</li>
      </ul>
    </td>
  </tr>

</table>

<br>
For more information about Regular Student Enrollment , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>

"""


},
{
     "patterns": [
  "regular student enrollment schedule cvsu",
  "when do regular students enroll",
  "irregular student enrollment cvsu",
  "when do irregular students enroll",
  "why irregular students enroll later",
  "regular vs irregular enrollment schedule",
  "different enrollment schedule cvsu",
  "how to know enrollment date cvsu",
  "can irregular students enroll early",
  "prepare for enrollment irregular student",
  "advising process regular vs irregular",
  "cvsu bacoor enrollment timeline"
],
"response": """ 

<table border="1" cellspacing="0" cellpadding="8">

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">When do regular students enroll in CvSU Bacoor?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Regular students are always scheduled to enroll first. Typically, enrollment for regular students starts during the main enrollment month announced by the campus (e.g., July for first semester). They are prioritized because their subjects follow a fixed curriculum flow.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">When do irregular students enroll?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Irregular students usually enroll **one month after** the regular students.  
      For example:  
      <b>If regular students enroll in July, irregular students are scheduled around August.</b>  
      This delay allows departments to finalize available subjects and remaining slots.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Why do irregular students enroll later than regular students?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Because irregular schedules vary and depend on:  
      • Available subject slots after regular enrollment  
      • Prerequisite checks  
      • Department evaluation  
      This ensures proper advising and avoids conflicts in schedule.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Is the schedule for regular and irregular students always different?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Yes. CvSU Bacoor normally sets separate dates. Regular students follow a standard timeline, while irregular students are given a later date to ensure accurate evaluation and subject availability.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">How do I know my exact enrollment date?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Enrollment dates are posted through:  
      • Official campus Facebook page  
      • Department announcements  
      • Program advisers  
      Always check updates because schedules may change depending on the semester.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Can irregular students enroll early?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      No. Irregular students cannot enroll early because they must undergo evaluation first. Departments need to determine which subjects are available and which prerequisites are met.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">What should irregular students prepare before their enrollment month?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      • Updated curriculum checklist  
      • Evaluation form from department  
      • List of completed and pending subjects  
      • Accountabilities checked (library, registrar, cashier)  
      • Always monitor announcements for advising schedules
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Do regular and irregular students have the same advising process?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      The process is similar, but regular students have faster advising because their flowchart is fixed. Irregular students undergo detailed evaluation to determine subject availability and prerequisites.
    </td>
  </tr>
</table>
<br>
For more information about Schedule of Regular and Irregular Student , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>
"""


     
},
{
"patterns": [
  "graduation requirements cvsu",
  "what are the requirements for graduation",
  "cvsu bacoor graduation requirements",
  "requirements to graduate",
  "eligibility for graduation cvsu",
  "documents needed for graduation",
  "graduation checklist cvsu",
  "graduating student requirements",
  "what students need to graduate cvsu",
  "how to qualify for graduation",
  "academic requirements for graduation",
  "graduation clearance requirements",
  
  "when is graduation evaluation",
  "graduation evaluation schedule cvsu",
  "uniform requirement during evaluation",
  "wear uniform for graduation evaluation",
  "join graduation with incomplete requirements",
  "incomplete requirements graduation policy",
  "who announces graduation candidates",
  "graduation candidates list announcer",
  "can student graduate with inc",
  "inc grade effect on graduation"
],

"response": """ 

<table border="1" cellpadding="8" cellspacing="0">
  <tr>
    <th  style="padding:10px; border:1px solid var(--text-color); >Requirement</th>
    <th style="padding:10px; border:1px solid var(--text-color); >Details</th>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">1. Complete all academic and non-academic requirements</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Students must finish all subjects in their curriculum, including minor and major courses, OJT (if required), research/capstone, and other academic outputs. 
      Non-academic requirements include attending orientations, seminars, and mandatory institutional activities, depending on the program. 
      Grades must be officially encoded and passed before the final evaluation.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">2. Have no pending balances</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Students must settle all financial obligations at the Cashier’s Office, such as: <br>
      • Tuition & miscellaneous fees <br>
      • Library fines <br>
      • Laboratory payments <br>
      • Lost ID or replacement fees <br> 
      • Departmental fees (if applicable) <br><br>
      A final assessment is usually required to verify that the student has zero outstanding balance before graduation.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">3. Submit clearance forms from all departments</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      The clearance process ensures that the student has no liabilities with any office. 
      Departments included in the clearance are usually: <br>
      • Library <br>
      • Laboratory / IT Department <br>
      • Registrar’s Office <br>
      • Cashier <br>
      • Department Chairperson <br>
      • Property / Equipment Custodian (if program-related) <br><br>
      Students must secure signatures from all required offices before the deadline.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">4. Attend the graduation rehearsal</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Attendance to graduation rehearsal is mandatory to ensure proper organization during the ceremony.  
      During rehearsal, students receive instructions about: <br>
      • Processional and recessional order <br>
      • Stage entering and exiting <br>
      • Seating arrangement <br>
      • Name calling procedure <br>
      • Dress code for graduation <br><br>
      Failure to attend may result in exclusion from the ceremony depending on campus rules.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">5. Submit an application for graduation to the Registrar</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Students must file their Application for Graduation within the schedule announced by the Registrar’s Office.  
      The application usually requires: <br>
      • Accomplished graduation form <br>
      • Updated curriculum checklist <br>
      • 2x2 or passport-size photo (depending on the requirement) <br>
      • Evaluation slip from the department <br>
      • Latest registration forms & grades <br><br>
      Late submission may delay processing and affect inclusion in the graduation roster.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Additional Common Questions</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      <b>• When is the graduation evaluation?</b><br>
      Usually conducted 1–2 months before the ceremony.<br><br>

      <b>• Do students need to wear complete uniform during evaluation?</b><br>
      No, but proper attire is required when submitting documents.<br><br>

      <b>• Can a student join the graduation ceremony with incomplete requirements?</b><br>
      No. All requirements must be completed before receiving confirmation of graduation.<br><br>

      <b>• Who announces the list of graduation candidates?</b><br>
      The Registrar releases the official list after department evaluation.<br><br>

      <b>• Can a student graduate with INC grades?</b><br>
      No, incomplete grades must be cleared before the deadline.
    </td>
  </tr>
</table>

<br>
For more information about Requirements for Graduating Students , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>

"""
   

},

{
"patterns": [
  "how to request tor",
  "tor request process cvsu",
  "transcript of records request",
  "tor requirements cvsu",
  "documents needed for tor",
  "tor processing time",
  "how long tor processing",
  "can i request tor while studying",
  "tor request as current student",
  "claiming tor by representative",
  "can someone else claim my tor",
  "tor unpaid balance issue",
  "unpaid balance tor restriction",
  "digital tor request",
  "electronic tor cvsu",
  "tor fee cost",
  "how much is tor",
  "tor correction process",
  "what to do if tor has errors",
  "fix errors in tor",
  "tor release procedure",
  "what is tor",
  "what is transcript of record",
  "meaning of tor",
  "can i request an electronic/digital TOR",
  "tor definition cvsu"
],

"response": """ 
<table border="1" cellpadding="8" cellspacing="0">
  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">What is TOR?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      TOR stands for <b>Transcript of Records</b>.  
      It is an official document issued by the Registrar that contains your complete academic history in CvSU, including all subjects taken, grades received, number of units, remarks, and GPA (if applicable).  
      It is required for graduation, employment, transferring schools, and applying for scholarships or further studies.
    </td>
  </tr>
  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">How to request a Transcript of Records (TOR)?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      To request your TOR at CvSU Bacoor, follow these steps: <br><br>
      <b>1. Secure your clearance.</b> You must be fully cleared from all departments before TOR processing begins. <br>
      <b>2. Proceed to the Registrar’s Office.</b> Request the TOR form and fill it out completely. <br>
      <b>3. Submit required documents.</b> These usually include: valid ID, student ID, and clearance form. <br>
      <b>4. Pay the TOR processing fee.</b> Payment is made at the Cashier’s Office; keep your receipt. <br>
      <b>5. Wait for processing.</b> TOR processing typically takes <b>5–15 working days</b> depending on workload and peak season. <br>
      <b>6. Claim your TOR.</b> Bring your receipt and valid ID when claiming your document.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">How long does TOR processing take?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      TOR processing usually takes <b>5 to 15 working days</b>.  
      During peak seasons such as graduation, enrollment, or mass requests, processing may take longer—up to **3–4 weeks**.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">What documents do I need to request a TOR?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Requirements typically include: <br>
      • Completed clearance <br>
      • Valid ID or Student ID <br>
      • TOR request form from the Registrar <br>
      • Official receipt of payment <br><br>
      Additional documents may be required depending on your status (e.g., transferee, graduating).
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Can I request TOR while still studying?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Yes. Students may request a TOR for certain purposes such as scholarship application, transfer, or personal reasons.  
      However, only completed/encoded subjects will appear in the document.  
      Some offices may issue a **Certified True Copy of Grades** if a full TOR is not necessary.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Can someone else claim my TOR?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Yes, a representative may claim your TOR as long as they bring: <br>
      • Authorization letter signed by you <br>
      • Their valid ID <br>
      • A photocopy of your valid ID <br>
      • Official receipt (if required)
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">What if I have unpaid balances?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      You cannot request or process your TOR if you have outstanding balances with the school.  
      All payments must be settled first at the Cashier’s Office before the Registrar can proceed.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">Can I request an electronic/digital TOR?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      CvSU campuses usually release <b>printed TOR only</b>.  
      For digital copies, you may ask the Registrar if they can provide a scanned copy, but this depends on campus policy and may not always be available.
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">How much is the TOR fee?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      TOR fees vary by semester and campus.  
      The typical cost ranges from <b>₱50 to ₱150 per page</b>, plus certification fees and additional charges for rush processing (if offered).
    </td>
  </tr>

  <tr>
    <td style="padding:10px; border:1px solid var(--text-color); ">What should I do if my TOR has errors?</td>
    <td style="padding:10px; border:1px solid var(--text-color); ">
      Report any mistakes immediately to the Registrar’s Office.  
      Bring supporting documents (e.g., class cards, grade slips, evaluation forms) to verify the correct information.  
      Corrections usually take a few days depending on the error.
    </td>
  </tr>

</table>

<br>
For more information about Transcript of Record , make sure to follow these reliable sources :
<br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/CSGBacoor">Central Student Government - CvSU Bacoor</a><br>
<a target="_blank" style="background: var(--sidebar-color); color: var(--text-color);" href="https://www.facebook.com/its.cvsubacoor">CvSU Bacoor Society</a>

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