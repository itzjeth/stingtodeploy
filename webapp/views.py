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
[
  {
"patterns": [
"What is the history of CvSU",
"When was CvSU established",
"Tell me about CvSU history",
"How did Cavite State University start",
"Background of CvSU"
],
"response": 
"Cavite State University traces its origins to the Indang Intermediate School established in 1906. Through the years, the institution underwent several transformations and was eventually converted into Cavite State University, continuing its commitment to quality education, research, extension, and production."
},
{

"patterns": [
"What is the vision of CvSU",
"CvSU vision statement",
"What does CvSU aim to achieve",
"University vision",
"Vision of Cavite State University"
],
"response": 
"The premier University in historic Cavite recognized for excellence in the development of globally competitive and morally upright individuals."
},
{

"patterns": [
"What is the mission of CvSU",
"CvSU mission statement",
"What is the University's mission",
"Mission of Cavite State University",
"What does CvSU do"
],
"response": 
"Cavite State University shall provide excellent, equitable, and relevant educational opportunities in the arts, sciences, and technology through quality instruction and responsive research and development activities. It shall produce professional, skilled, and morally upright individuals who are globally competitive."
},
{

"patterns": [
"What is the mission and vision of CvSU?",
"Tell me the mission and vision of Cavite State University.",
"What are CvSU's mission and vision statements?",
"Can you tell me the vision and mission of CvSU?",
"What does Cavite State University stand for?",
"vision and mission",
"mission and vision"
],
"response": 
"CvSU Vision:<br>The premier University in historic Cavite recognized for excellence in the development of globally competitive and morally upright individuals.<br><br>CvSU Mission:<br>Cavite State University shall provide excellent, equitable, and relevant educational opportunities in the arts, sciences, and technology through quality instruction and responsive research and development activities. It shall produce professional, skilled, and morally upright individuals who are globally competitive."
},

{

"patterns": [
"What is the core values of CvSU",
"CvSU core values statement",
"What is the University's core values",
"core values of Cavite State University",
"core values"
],
"response": 
"We Commit to the highest standards of education, value our stakeholders, Strive for continual improvement of our products and services, and Uphold the University's tenets of Truth, Excellence, and Service to produce globally competitive and morally upright individuals"
},

{

"patterns": [
"What is the motto of CvSU",
"CvSU motto",
"University motto",
"What is Cavite State University's motto",
"School motto"
],
"response": 
"The motto of Cavite State University is 'Truth, Excellence, and Service.'"
},
{

"patterns": [
"What are the official colors of CvSU",
"CvSU official colors",
"What colors represent the University",
"School colors",
"University color symbolism"
],
"response": 
"The official colors of Cavite State University are green and gold."
},
{

  "patterns": [
    "Does CvSU have a hymn",
    "What is the CvSU hymn",
    "University hymn",
    "School hymn information",
    "CvSU song"
  ],
  "response": 
    "Yes. Cavite State University has an official hymn that reflects the University's values, aspirations, and commitment to excellence."
  },
{

  "patterns": [
    "When is CvSU Foundation Day",
    "What is the foundation day of CvSU",
    "Foundation anniversary",
    "When does the University celebrate Foundation Day",
    "CvSU founding celebration",
    "When is the CvSU anniversary",
    "What month is Foundation Day",
    "When is the university founding day held",
    "When do they celebrate CvSU Foundation Day"
  ],
  "response": 
    "CvSU celebrates its Foundation Day annually through various academic, cultural, sports, and community activities organized by the University. The celebration typically takes place within the months of October to December, depending on the official university schedule for the year."
  },
{

"patterns": [
"What is the student publication",
"Does CvSU have a student publication",
"Campus journalism organization",
"Student newspaper",
"University publication"
],
"response": 
"The University supports student publication organizations that provide students opportunities to develop skills in journalism, writing, editing, photography, and media production while promoting responsible campus communication."
},

  {

    "patterns": [
      "When is the onsite validation for passers?",
      "What is the schedule for requirement validation?",
      "Onsite validation dates for incoming students",
      "When should I go to campus to validate my requirements?"
    ],
    "response": 
      "The onsite validation of requirements for qualified applicants (passers) for the First Semester, S.Y. 2026–2027 is scheduled according to the applicant's program:<br><br>June 22 – June 25<br><br>Bachelor of Science in Hospitality Management (BSHM)<br>Bachelor of Science in Business Administration (BSBA) – Marketing Management and Human Resource Management<br>Bachelor of Science in Information Technology (BSIT)<br>Bachelor of Science in Computer Science (BSCS)<br><br>June 29 – July 2<br><br>Bachelor of Science in Criminology (BSCrim)<br>Bachelor of Science in Psychology (BS Psychology)<br>Bachelor of Secondary Education (BSEd) – English and Mathematics<br><br>Please visit the campus on the date assigned to your program and bring all the required <br>documents for validation."
},
{

"patterns": [
"What is the admission process?",
"How do I apply for admission?",
"What are the steps for freshman enrollment?",
"How do I complete my admission at CvSU Bacoor?",
"What is the enrollment process?",
"How do I enroll in CvSU Bacoor?",
"What are the steps for enrollment?",
"How can new students enroll?",
"What are the steps of enrollment for new students?",
"How do new students enroll?",
"Enrollment process for freshmen",
"New student enrollment procedure",
"What is the admission and enrollment process?",
"How can I apply and enroll?",
"What should I do after being admitted?",
"How do freshmen register?",
"How does the enrollment procedure work?",
"What are the requirements for enrollment?"
],
"response": 
"The admission and enrollment process for new students generally follows these steps:<br><br>1. Checking of Requirements<br>2. Releasing of Notice of Admission and Medical Referral Slip<br>3. Medical Clearance and Physical Examination<br>4. Registration and Enrollment at the Registrar's Office<br><br>Students are advised to prepare and submit all required documents to ensure a smooth enrollment process. For updated admission guidelines and schedules, please coordinate with the Admissions Office or Registrar's Office."
},

{

"patterns": [
"Can I retake the entrance exam",
"Is retaking CvSU-CAT allowed",
"May I take the admission test again",
"Retake entrance examination",
"Can I apply for another exam schedule"
],
"response": 
"Retaking the entrance examination is subject to University admission policies. Applicants should consult the Admissions Office regarding eligibility and available examination schedules."
},
{

"patterns": [
"Can foreign students apply to CvSU",
"Are international students accepted",
"Foreign student admission requirements",
"How can international students enroll",
"Can non-Filipino students apply"
],
"response": 
"Yes. Foreign applicants may apply for admission subject to University requirements and applicable government regulations. Additional documents may be required for evaluation and processing."
},
{

"patterns": [
"Is there an age limit for admission",
"What is the age requirement for applicants",
"Can older applicants apply",
"Minimum age for enrollment",
"Admission age requirement"
],
"response": 
"Admission eligibility is generally based on academic qualifications and compliance with admission requirements. Applicants should verify specific age-related policies with the Admissions Office if applicable."
},
{

"patterns": [
"Is there an orientation for new students",
"What is the freshman orientation",
"Do new students attend orientation",
"Orientation program information",
"Student orientation schedule"
],
"response": 
"Yes. The University typically conducts orientation programs for new students to introduce important academic policies, campus services, student responsibilities, and University procedures."
},
{

"patterns": [
"Does CvSU have an online admission portal",
"Where can I apply online",
"Online admission application",
"How do I access the admission portal",
"Can I submit my application online"
],
"response": 
"Yes. Applicants may submit admission applications through the University's official online admission portal when applications are open."
},
{

"patterns": [
"Who is qualified to apply for admission",
"Admission qualifications",
"Who can apply to CvSU",
"Eligibility for admission",
"Admission requirements for applicants"
],
"response": 
"Applicants must satisfy the University's admission requirements, submit complete documents, and comply with established admission procedures to be considered for enrollment."
},

  {

  "patterns": [
    "What degrees are available?",
    "List of degrees in CvSU Bacoor",
    "What bachelor's degrees do you offer?",
    "Available degree programs",
    "What degree programs are offered?",
    "What can I take in CvSU Bacoor?",
    "What undergraduate programs are available?"
  ],
  "response": 
    "CvSU Bacoor offers the following bachelor's degree programs:<br><br>• Bachelor of Secondary Education (BSEd)<br>• Bachelor of Science in Business Management (BSBM)<br>• Bachelor of Science in Computer Science (BSCS)<br>• Bachelor of Science in Criminology (BSCrim)<br>• Bachelor of Science in Hospitality Management (BSHM)<br>• Bachelor of Science in Information Technology (BSIT)<br>• Bachelor of Science in Psychology (BSPsych)<br><br>These programs are designed to prepare students for professional careers and further studies in their chosen fields."
  },
{
 
  "patterns": [
    "What courses are offered?",
    "Can you give me the list of courses?",
    "What can I study here?",
    "Courses available in the campus",
    "What programs can I enroll in?",
    "What academic programs are available?",
    "What fields of study are offered?"
  ],
  "response": 
    "Students may choose from a variety of academic programs at CvSU Bacoor, including Education, Business, Information Technology, Computer Science, Psychology, Criminology, and Hospitality Management.<br><br>Available courses:<br>• Bachelor of Secondary Education (BSEd)<br>• BS Business Management (BSBM)<br>• BS Computer Science (BSCS)<br>• BS Criminology (BSCrim)<br>• BS Hospitality Management (BSHM)<br>• BS Information Technology (BSIT)<br>• BS Psychology (BSPsych)"
  },
  {
   
    "patterns": [
      "What are the extracurricular activities?",
       "What extracurricular activities are available",
      "Are there clubs I can join?",
      "What student organizations are there?",
      "Does the school have sports or arts activities?",
       "What clubs and activities can I join",
        "Campus extracurricular activities",
    "Student activities and organizations",
    "Available extracurricular programs"
    ],
    "response": 
      "We're excited to share with you the various extracurricular and co-curricular opportunities available at CvSU Bacoor Campus.<br>At Cavite State University – Bacoor City Campus, student development goes beyond the classroom, encouraging participation in activities that build skills, leadership, and camaraderie.<br>Students may join or participate in activities such as:<br><br>**Sports and Athletics**<br>• Basketball<br>• Volleyball<br>• Athletics / Track and Field<br>• Other sports activities organized through campus events and intramurals<br><br> **Mind Sports**<br>• Chess (often included in intramurals and intercollegiate competitions)<br><br>**Cultural and Arts Activities**<br>• Theater and Performing Arts (during campus events and festivals)<br>• Music and Choral Performances<br>• Visual Arts (posters, painting, and creative competitions)<br><br>**Student Organizations**<br>• Department-based student organizations<br>• Recognized campus clubs and organizations under the Office of Student Affairs (OSA)<br>• Community service and volunteer groups<br><br>**Academic and Development Activities**<br>• Seminars and workshops<br>• Leadership training programs<br>• Research presentations and academic competitions<br><br>These activities are designed to help <br>students develop teamwork, leadership skills, creativity, and social responsibility while enhancing their overall college experience.<br>For updated lists of active organizations and upcoming activities, students may coordinate with the **Office of Student Affairs and Service (OSAS)**.<br>CvSU Bacoor Campus Contact Number: (046) 476-5029<br><br>Participation in extracurricular activities is encouraged to support holistic student development and campus engagement."
},

  {
  
  "patterns": [
    "What sports are available in CvSU Bacoor",
    "Sports activities on campus",
    "Can I join sports teams",
    "Available sports programs",
    "Athletic activities"
  ],
  "response": 
    "Students may participate in various sports and athletic activities offered by the University.<br><br>Available sports may include basketball, volleyball, tennis, athletics, chess, and other competitive or recreational activities depending on University programs and student interest."
  },
  {
   
    "patterns": [
      "What is OSAS?",
      "What does OSAS stand for?",
      "Meaning of OSAS",
      "What services does the Office of Student Affairs provide?",
      "How can OSAS help students?",
      "Where is the Office of Student Affairs?",
      "What student services are available?"
    ],
    "response": 
      "The Office of Student Affairs and Services (OSAS) supports students through leadership development, student organizations, scholarships, counseling referrals, student welfare programs, and other student-related services"
},
  {
  
    "patterns": [
      "What are the rooms in CvSU Bacoor?",
      "List of facilities in the campus",
      "Where are the classrooms and offices located?",
      "Campus facilities overview",
      "What facilities are available in CvSU?",
      "What buildings are inside the campus?",
      "What services can students use?",
      "Does the campus have laboratories?",
      "What campus facilities are available?",
      "Can students access campus facilities?",
      "Campus facilities"
    ],
    "response": 
      "I'm happy to help you with your query.<br>At Cavite State University – Bacoor City Campus, the campus facilities are composed of several academic and administrative buildings that support the learning needs of students across different programs.<br>Instead of fixed room counts per building, CvSU Bacoor Campus is organized by **functional areas and departments**, which may include:<br><br>**Administrative Offices**<br>• Office of the Campus Administrator<br>• Registrar’s Office<br>• Cashier’s Office<br>• Office of Student Affairs and Services (OSAS)<br><br>**Academic Buildings**<br>• Classrooms for General Education and program-based subjects<br>• Laboratories for IT, computer science, and other technical courses 💻<br>• Faculty rooms for instructors and advisers<br><br>**Student Support Facilities**<br>• Library 📖<br>• Guidance Office<br>• Clinic / Health Services 🏥<br>• Student organizations and activity areas<br><br>**Other Campus Facilities**<br>• Computer laboratories 💻<br>• Lecture rooms and conference areas<br>• Designated event and defense venues (varies by schedule)<br><br>The exact number of rooms and <br>their assignments may change depending on campus development, renovations, and academic scheduling.<br>For the most accurate and updated campus facility information, you may contact CvSU Bacoor Campus at:<br>Email: cvsubacoor@cvsu.edu.ph<br>(046) 476-5029<br><br>CvSU Bacoor continues to improve its facilities to better serve students and support quality education."
},
  {
  
    "patterns": [
      "What degree programs are currently available?",
      "Which degrees can I take up?",
      "Undergraduate programs offered",
      "What are the available courses to enroll in?"
    ],
    "response": 
      "🎓 We're glad you're interested in learning more about the academic programs offered at CvSU Bacoor Campus.<br>📚<br><br>At Cavite State University – Bacoor City Campus, we offer a selection of undergraduate degree programs under different colleges and departments, designed to support various career paths and fields of study.<br>📖 **Available Programs include:**<br><br>• Bachelor of Science in Information Technology (BSIT) 💻<br>• Bachelor of Science in Computer Science (BSCS) 💻<br>• Bachelor of Science in Psychology (BS Psychology) 🧠<br>• Bachelor of Science in Business Management (BSBM) 📊<br>• Bachelor of Science in Hospitality Management (BSHM) 🏨<br>• Bachelor of Secondary Education (BSEd) 👩‍🏫<br><br>📌 These programs are aligned with the university’s academic standards and may include General Education courses, major subjects, laboratory work, and practical training depending on your chosen field.<br>📞 For more information about program requirements, enrollment, or curriculum details, you may contact the campus office or visit CvSU Bacoor Campus directly.<br>📧 Email: Email: cvsubacoor@cvsu.edu.ph<br>📞 Phone: (046) 476-5029<br><br>🎓 We’re happy to help guide you in choosing the program that best fits your interests and career goals."
},
  {
  
    "patterns": [
      "Who handles OJT concerns?",
      "Who do I talk to about my internship?",
      "Where can I ask about OJT requirements?",
      "Contact person for OJT"
    ],
    "response": 
      "At Cavite State University - Bacoor City Campus, OJT-related matters are usually coordinated through your assigned department and OJT adviser 📚.<br>If you have questions or concerns about completing your OJT hours, requirements, or company placement, **you can also ask your OJT adviser** for guidance.<br>They can assist you with clarifications regarding documents, requirements, and proper procedures.<br>📞<br><br>To complete your OJT requirements, you will typically need to prepare the following documents:<br><br>1. Updated Resume 📄<br>2. Endorsement Letter 📨<br>3. Other requirements as specified by your department or OJT adviser 📝<br><br>📈 It is important to follow all OJT guidelines and complete the required hours properly to avoid delays or issues with your final grade.<br>📌 For any specific concerns, you may coordinate with your OJT adviser or department office, as they will provide the most accurate and updated instructions based on your program.<br>If you need further help, feel free to ask. I'm here to assist you anytime.<br>😊🎉"
},
  {
 
    "patterns": [
      "I lost my items on campus",
      "Where is the lost and found?",
      "What to do if I lose something?",
      "How to report a lost belonging?",
      "What should I do if I lost something on campus",
    "Lost and found services",
    "I lost my belongings",
    "Where can I report lost items",
    "How do I recover lost property"
    ],
    "response": 
      "I'm happy to help you with your concern. 🤔 Losing belongings can be frustrating, but don’t worry—CvSU Bacoor Campus has a process in place to help you retrieve lost items.<br>📚<br><br>To recover lost belongings, you may start by **asking the security guard on duty** at the campus entrance or building posts 🛡️.<br>They often receive or are informed about items that have been found within the campus.<br>You can also visit the **Student Affairs Office** 🏢. They will ask you to provide a detailed description of the lost item, including the date and location where you last saw it 📝.<br>📱 You may also check campus announcements or social media groups where found items are sometimes posted.<br>Additionally, you can ask your classmates or friends if they have seen your lost item 🤝.<br>📋 If the item is not immediately found, you may file a lost item report at the University Security Office.<br>This helps the security personnel track and monitor reported belongings in case they are turned in later.<br>🕒 Please report lost items as soon as possible, as unclaimed items may only be kept for a limited period before being disposed of or turned over following campus policy.<br>If you have any further questions or need assistance, feel free to approach the Student Affairs Office or the University Security personnel.<br>📞 Good luck, and I hope you recover your belongings soon!<br>🤞"
},
  {
   
    "patterns": [
      "What is the contact number of the campus?",
      "How can I call CvSU Bacoor?",
      "What is the email address of the school?",
      "Campus contact details",
       "How can I contact CvSU Bacoor",
    "What is the contact information of CvSU Bacoor",
    "How do I reach the University",
    "Where can I contact the school",
    "University contact details"
    ],
    "response": 
      "Students, applicants, parents, and stakeholders may contact CvSU Bacoor through its official communication channels for inquiries, concerns, and requests.<br><br> **CvSU Bacoor Campus Contact Information**<br><br>Email: Email: cvsubacoor@cvsu.edu.ph<br>Telephone: (046) 476-5029<br><br>Cavite State University – Bacoor City Campus<br>Lily Street, Phase II Soldiers Hills IV, Bacoor City, Cavite, Philippines<br><br>For inquiries and concerns, you may contact the campus through the email or telephone number provided.<br>These are the official contact details used for administrative, academic, and student-related concerns.<br>If you need further assistance or specific office contacts (such as registrar, admissions, or OJT concerns), feel free to ask."
},
  {
   
    "patterns": [
      "How many OJT hours per department?",
      "How many hours for internship?",
      "Required OJT hours for my course",
      "BSIT OJT hours"
    ],
    "response": 
      "The required number of On-the-Job Training (OJT) hours at CvSU Bacoor Campus depends on your degree program and the curriculum prescribed by your department.<br>🎓<br><br>⏰ General OJT hour requirements per program:<br><br>• Bachelor of Science in Information Technology (BSIT): **360–486 hours**<br>• Bachelor of Science in Computer Science (BSCS): **240–360 hours**<br>• Bachelor of Science in Business Management (BSBM): **300–400 hours**<br>• Bachelor of Science in Hospitality Management (BSHM): **300–600 hours**<br>• Bachelor of Science in Psychology (BS Psych): **200–300 hours**<br>• Bachelor of Secondary Education (BSEd): **300–500 hours**<br><br>📝 Please note that these are **general program-based requirements** and may still vary depending on your specific curriculum, year level, and department policies at CvSU Bacoor Campus.<br>📄 To confirm your exact required OJT hours, always coordinate with your OJT coordinator, program adviser, or department office.<br>📅 Make sure to complete all required documents and hours within your assigned schedule to avoid delays in graduation processing.<br>If you need clarification for your specific program, feel free to ask your department office for the official breakdown.<br>😊 Good luck with your OJT journey! 🎓💼"
},
  {
 
    "patterns": [
      "How much is the statistician fee?",
      "What are the research fees?",
      "Fee for the statistician",
      "How much do I pay for capstone evaluation?"
    ],
    "response": 
      "At CvSU Bacoor Campus, the fees associated with Capstone or Research evaluation may include the following:<br><br>• **Technical Adviser (TA) Fee:** ₱1,500.00<br>• **Technical Critic (TC) Fee:** ₱800.00<br>• **Statistician Fee:** ₱500.00<br><br>📝 Please note that these fees **may vary depending on your department, degree program, or course requirements**.<br>Different departments may implement different fee structures based on their academic policies and evaluation procedures.<br>💸 To avoid any discrepancies, it is recommended that you confirm the exact fees with your department office, research coordinator, capstone coordinator, or the Cashier's Office before making any payment.<br>📅 Be sure to settle any required fees within the prescribed deadlines to prevent delays in the evaluation and completion of your academic requirements.<br>🏫 For additional information regarding payment procedures, requirements, and schedules, you may visit your department office or coordinate directly with the concerned faculty members.<br>If you have any further questions or concerns, feel free to ask. I'm always happy to assist you.<br>😊🎓"
},
  {

"patterns": [
"How much is the capstone defense fee?",
"What is the defense fee for capstone?",
"How much do we pay for capstone defense?",
"What is the estimated capstone defense fee?",
"How much should we prepare for the defense fee?",
"Is there a fee for capstone defense?",
"How much is the panel fee for capstone defense?",
"What are the defense expenses for capstone?",
"How much is the payment for capstone panelists?",
"What is the cost of defending our capstone project?"
],
"response": 
"The capstone defense fee is not fixed and may vary depending on the number of panelists assigned and their availability. The fee usually ranges from ₱200 to ₱500 per panelist.<br><br>For example, if the total defense fee amounts to around ₱1,000 and your group has three members, each member may contribute approximately ₱333.33.<br><br>Students are advised to coordinate with their capstone adviser, subject instructor, or department for the official defense fee and payment arrangements."
},
{

"patterns": [
"How much is the thesis defense fee?",
"What is the defense fee for thesis?",
"How much do we pay for thesis defense?",
"How much is the panel fee for thesis?",
"What is the estimated thesis defense fee?"
],
"response": 
"The thesis defense fee is determined based on the number of panelists and their availability. Fees are not fixed and may vary each semester. In most cases, the fee ranges from ₱200 to ₱500 per panelist. Students should consult their adviser or department for the official amount and payment procedure."
},

  {
    "patterns": [
      "How much is the TA and TC fee?",
      "Technical adviser fee",
      "Technical critic fee",
      "How much do we pay the technical critic?",
      "Panel fees for capstone"
    ],
    "response": 
      "At CvSU Bacoor Campus, the fees for Capstone or Research evaluation are as follows:<br><br>• **Technical Adviser (TA) Fee:** ₱1,000.00<br>• **Technical Critic (TC) Fee:** ₱800.00<br><br>📝 Please note that these fees may vary depending on your department, program, or current university policies.<br>It is always best to verify the exact amount with your department office, capstone coordinator, or the Cashier's Office before making any payment.<br>💸 Students are encouraged to settle the required fees on or before the designated deadline to avoid delays in the evaluation and defense process.<br>📅 For more information regarding payment procedures and schedules, you may coordinate with your Technical Adviser, Technical Critic, or department office.<br>If you have any further questions or concerns, feel free to ask. I'm happy to assist you.<br>😊"
},
  {
   
    "patterns": [
      "Where does defense usually take place?",
      "What room is used for capstone defense?",
      "Where is the thesis defense held?",
      "Defense venue in campus"
    ],
    "response": 
      "At CvSU Bacoor Campus, thesis, capstone, and research defenses are typically conducted in designated classrooms, laboratories, conference rooms, or other venues assigned by the department or program.<br>📚🎓<br><br>The exact venue for a defense may vary depending on:<br>• Your degree program or department<br>• The type of defense (proposal, pre-oral, final oral, or capstone defense)<br>• The number of groups scheduled for the day<br>• Room availability and administrative arrangements<br><br>📅 To know the exact room and schedule for your defense, please check the official announcement from your course instructor, research adviser, capstone coordinator, or department office.<br>These details are usually provided before the scheduled defense date.<br>📝 If you are unsure about your assigned venue, you may contact your department chairperson, Technical Adviser (TA), or class representative for confirmation.<br>🎉 Good luck with your defense! Be prepared, arrive early, and make sure to bring all required documents and presentation materials.<br>If you have any other questions about capstone, thesis, or campus services, feel free to ask.<br>😊"
},
  {
 
  "patterns": [
    "Is there a computer laboratory?",
    "Can students use computer labs?",
    "Computer laboratory facilities",
    "Where is the computer laboratory?",
    "Computer lab access",
    "Where is the comp lab located?",
    "What floor is the computer lab on?",
    "How do I get to the computer lab?",
    "Location of IT laboratory",
    "Where can I find the computer laboratory?",
    "Is there an IT lab in CvSU?",
    "Do students have access to computer labs?",
    "How to access the computer laboratory?"
  ],
  "response": 
    "Yes, CvSU provides computer laboratory facilities that support instruction, laboratory activities, research, and other academic requirements of students.<br><br>The computer laboratory is located on the 3rd floor of the campus building. To get there, proceed to the main building and take the stairs to the third floor. You will find the designated computer laboratory rooms used for classes, laboratory activities, and academic requirements.<br><br>Students are required to follow all laboratory rules and regulations. Please handle all equipment properly, maintain cleanliness, and use the facilities responsibly to ensure a productive learning environment.<br><br>If you need assistance, laboratory personnel and instructors are available to guide you. Always check your class schedule and assigned laboratory room before attending your lab sessions."
  },
  {
   
    "patterns": [
      "What are the rules inside the laboratory?",
      "Computer lab rules and regulations",
      "Can we eat inside the comp lab?",
      "Laboratory guidelines"
    ],
    "response": 
      "📚💻 As a student of CvSU Bacoor Campus, it's important to follow the rules and regulations inside the computer laboratory to maintain a productive, safe, and respectful learning environment.<br>Here are some guidelines to keep in mind:<br><br>1. Computer Usage: 🖥️ Computers are intended for academic purposes only.<br>Students may use them for research, assignments, programming activities, projects, and other coursework-related tasks.<br>Avoid using laboratory computers for activities unrelated to academics.<br><br>2. Food and Drinks: 🍔🥤 Eating and drinking are strictly prohibited inside the computer laboratory to prevent damage to equipment and maintain cleanliness.<br>3. Noise Level: 🗣️ Maintain a quiet environment while inside the laboratory.<br>Avoid loud conversations and unnecessary noise that may distract other students.<br>4. Proper Handling of Equipment: ⚙️ Handle all computers, peripherals, and laboratory equipment with care.<br>Do not attempt to disconnect, transfer, modify, or damage any hardware components.<br>5. Software and Resources: 📁 Use only the software and resources provided or approved by the laboratory instructor.<br>Do not install unauthorized programs or make changes to system settings.<br>6. Laboratory Hours and Schedule: 🕒 Follow the designated laboratory schedule and use the facilities only during authorized hours.<br>Students should vacate the laboratory promptly when their scheduled class or session ends.<br>7. Cleanliness and Orderliness: 🧹 Keep your workstation clean and organized.<br>Arrange chairs properly and dispose of any trash before leaving the laboratory.<br>8. Supervision and Assistance: 🤔 Laboratory personnel and instructors are available to provide guidance and assistance.<br>Follow their instructions at all times and seek help whenever necessary.<br>By following these rules and regulations, you help create a safe, efficient, and conducive learning environment for everyone.<br>📚💻 If you have any questions regarding laboratory policies, feel free to ask your instructor or laboratory personnel.<br>👍"
},
  {
   
    "patterns": [
      "What subjects are offered for first year students?",
      "First year college subjects",
      "What will I study in my first year?",
      "Freshman curriculum subjects"
    ],
    "response": 
      "As a first-year student, you'll be excited to begin your academic journey with a variety of subjects designed to build a strong foundation in your chosen program.<br>📖✨<br><br>The subjects you will take during your first year depend on your degree program.<br>CvSU Bacoor Campus offers programs such as:<br><br>🎓 Bachelor of Science in Information Technology (BSIT)<br>🎓 Bachelor of Science in Computer Science (BSCS)<br>🎓 Bachelor of Science in Psychology (BS Psych)<br>🎓 Bachelor of Science in Business Management (BSBM)<br>🎓 Bachelor of Science in Hospitality Management (BSHM)<br>🎓 Bachelor of Secondary Education (BSEd)<br><br>For first-year students, common subjects may include:<br><br>📚 General Education (GE) Courses<br>• Understanding the Self<br>• Purposive Communication<br>• Mathematics in the Modern World<br>• Science, Technology, and Society<br>• Readings in Philippine History<br>• The Contemporary World<br>• Art Appreciation<br>• Ethics<br><br>💻 Program-Specific Courses<br><br>For BSIT and BSCS students:<br>• Introduction to Computing<br>• Computer Programming<br>• Fundamentals of Information Technology<br><br>🧠 For BS Psychology students:<br>• <br>Introduction to Psychology<br>• Psychological Statistics<br>• Understanding Human Behavior<br><br>📊 For BS Business Management students:<br>• Fundamentals of Business Management<br>• Principles of Marketing<br>• Financial Management Basics<br><br>🏨 For BS Hospitality Management students:<br>• Introduction to Hospitality Management<br>• Tourism and Hospitality Operations<br>• Food and Beverage Service Fundamentals<br><br>👨‍🏫 For BSEd students:<br>• The Teaching Profession<br>• Foundations of Education<br>• Child and Adolescent Development<br><br>Please note that the exact subjects and schedules may vary depending on your curriculum and year of admission.<br>📅<br><br>For the most accurate and updated information, you may consult your department chairperson, program adviser, or the Registrar's Office.<br>We wish you a successful and enjoyable first year at CvSU Bacoor Campus!<br>💚💛 If you have any questions about enrollment, schedules, or campus services, feel free to ask.<br>😊"
},
  {
   
    "patterns": [
      "Where is the library located?",
      "How do I find the library?",
      "What floor is the library on?",
      "Library location in campus"
    ],
    "response": 
      "The library is an important resource for your studies, providing access to books, references, research materials, and a quiet place for learning.<br>📖✨<br><br>📍 The CvSU Bacoor Campus Library is located on the second floor of the old campus building.<br>Simply proceed to the old campus building and head up to the second floor, where you will find the library and its available services for students.<br>🕒 The library is open during regular campus operating hours.<br>However, schedules may vary depending on academic activities, holidays, or special events.<br>It is always a good idea to check with the library staff for the latest updates regarding operating hours and available services.<br>📚 The library offers various resources and facilities to support your academic needs, including reference materials, study spaces, and research assistance.<br>If you have any more questions or need further assistance, feel free to ask.<br>🤔"
},
  {
   
    "patterns": [
      "How much is the OJT fee?",
      "Do I need to pay for OJT?",
      "Payment for internship",
      "Where do I pay the OJT fee?"
    ],
    "response": 
      "The On-the-Job Training (OJT) fee is **₱100.00**. 💸 However, please note that the amount **may vary depending on your department, program, or course requirements**.<br>🏫📚 It is recommended to confirm the exact fee with your department or OJT coordinator before making any payment.<br>To pay your OJT fee, you may visit the University's Cashier's Office during office hours.<br>🕒 You can also check with your department for any updated payment procedures and deadlines.<br>Additionally, don't forget to prepare the required documents for your OJT, which may include:<br><br>📄 Updated Resume<br>📨 Endorsement Letter<br>📝 Other supporting documents (as required by your department)<br><br>Make sure to submit all required documents to your OJT coordinator or department office to complete your OJT requirements.<br>📚<br><br>If you have any further questions or concerns, feel free to ask, and I'll be happy to assist you.<br>😊 Wishing you a successful and productive OJT experience. 💪🎉"
},
  {
   
    "patterns": [
      "What is TA and TC?",
      "Meaning of TA and TC in capstone",
      "What is a Technical Adviser?",
      "What is a Technical Critic?"
    ],
    "response": 
      "In the context of Capstone Defense, **TA** and **TC** are important members of the evaluation panel.<br>📝<br><br>**TA** stands for **Technical Adviser**. 👨‍🏫👩‍🏫 The Technical Adviser is the faculty member who guides and mentors the group throughout the development of the Capstone project.<br>They provide technical expertise, monitor the project's progress, ensure that academic and technical standards are met, and help the students address challenges encountered during the research and development process.<br>💻📖<br><br>On the other hand, **TC** stands for **Technical Critic**. 🔍 The Technical Critic serves as an evaluator who reviews the project from a critical and technical perspective.<br>They assess the quality, feasibility, functionality, methodology, and overall technical soundness of the project.<br>During the defense, the Technical Critic may ask questions, provide recommendations, and identify areas for improvement to ensure that the project meets the required standards.<br>📊⚙️<br><br>During the Capstone Defense, both the **Technical Adviser (TA)** and the **Technical Critic (TC)** play significant roles in evaluating and improving the quality of your project.<br>📢 They will provide feedback, ask questions, and assess your team's ability to explain and defend the work you have completed.<br>💪<br><br>I hope this helps you understand the roles of the **TA (Technical Adviser)** and **TC (Technical Critic)** in the Capstone Defense at CvSU Bacoor Campus.<br>If you have any further questions or concerns, feel free to ask!<br>😊"
},
{
  
    "patterns": [
      "Who is the current campus administrator?",
      "Name of the campus head",
      "Bacoor campus administrator",
      "Who runs the campus operations?",
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
    "response": 
      "The current Campus Administrator of CvSU Bacoor is Ms.<br>Menvyluz S. Macalalad. MBA She oversees the overall operations, academic services, and administrative functions of the campus, ensuring that students receive quality education and a supportive learning environment.<br>Under her leadership, the campus continues to improve its programs, facilities, and student services."
},


  {
   
    "patterns": [
      "Who is the research coordinator?",
      "Name of the campus research head",
      "Who handles research initiatives?",
      "Contact for research activities"
    ],
    "response": 
      "The current Research Coordinator of CvSU Bacoor is Mr.<br>Ronan M. Cajigal, MAEd. He is responsible for guiding the campus’ research initiatives, supporting faculty and student researchers, and ensuring that all research activities align with the university’s academic standards and goals.<br>Through his leadership, the research culture of the campus continues to grow and strengthen."
},
  {
 
  "patterns": [
    "Who is the campus secretary head?",
    "Who is the campus secretary?",
    "Name of the campus secretary",
    "Who handles campus records and documentation?",
    "Who is in charge of the campus secretary office?",
    "Campus secretary of CvSU Bacoor",
    "Who manages official campus documents?",
    "Who is the secretary head of CvSU Bacoor?",
    "Who oversees campus administrative records?",
    "Can you tell me the campus secretary?"
  ],
  "response": 
    "The current Campus Secretary Head of CvSU Bacoor is Mr. Ronan M. Cajigal, MAEd.<br>He oversees the management of official campus records, documentation, correspondence, and other administrative functions of the Campus Secretary's Office.<br>Through his service, the campus ensures efficient record-keeping, proper documentation, and effective administrative support for students, faculty, and staff."
  },
  {
 
    "patterns": [
      "Who is the department chairperson?",
      "Name of the department head",
      "Who leads the academic department?",
      "Current department chair",
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
    "response": 
      "The current Department Chairperson is Ms.<br>Jovelyn D. Ocampo, MIT. She leads the department in overseeing academic programs, guiding faculty members, and ensuring that the curriculum remains relevant and aligned with university standards.<br>Through her leadership, the department continues to enhance its instructional quality, support student development, and maintain a strong academic environment"
},
{
  
    "patterns": [
      "Who is the former president of CvSU?",
      "Past university president",
      "Who was the president before 2024?",
      "Dr. Hernando Robles",
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
    "response": 
      "The former president of Cavite State University was Dr. Hernando D. Robles.<br>He served as the university president from 2016 until 2024 and played an important role in strengthening the university’s academic programs, research initiatives, and campus development projects.<br>During his administration, CvSU continued to expand its educational services and improve facilities across different campuses.<br>He also supported innovation, student development, and partnerships that helped the university maintain its reputation as one of the leading state universities in the Philippines."
},
  {
  
    "patterns": [
      "Who is the current president of CvSU?",
      "University president name",
      "Who leads Cavite State University now?",
      "Current head of the university system",
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
    "response": 
      "The current president of Cavite State University is Dr.<br>Ma. Agnes P. Nuestro. She officially became the fourth university president in 2025. As the current leader of the university, she continues to guide CvSU in providing quality education, promoting research and innovation, and supporting the growth and welfare of students, faculty, and staff.<br>Her administration focuses on maintaining academic excellence, strengthening community engagement, and preparing students to become globally competitive professionals and responsible citizens."
},
  {
 
  "patterns": [
    "Who is the chairperson of the Department of Computer Studies?",
    "Who heads the Department of Computer Studies?",
    "Who is the DCS chairperson?",
    "Who manages the Computer Studies department?",
    "Can you tell me the Computer Studies chairperson?"
  ],
  "response": 
    "The Chairperson of the Department of Computer Studies is Jovelyn D. Ocampo."
  },
{
 
  "patterns": [
    "Who is the chairperson of Criminology?",
    "Who heads the Department of Criminology?",
    "Who is the Criminology chairperson?",
    "Who manages the Criminology department?",
    "Can you tell me the Criminology chairperson?"
  ],
  "response": 
    "The Chairperson of the Department of Criminology is Jimmy M. Caltino."
  },
{
  
  "patterns": [
    "Who is the chairperson of the Department of Arts and Sciences?",
    "Who heads Arts and Sciences?",
    "Who is the Arts and Sciences chairperson?",
    "Who manages the Department of Arts and Sciences?",
    "Can you tell me the Arts and Sciences chairperson?"
  ],
  "response": 
    "The Chairperson of the Department of Arts and Sciences is Kathy C. Jamero."
  },
{
  
  "patterns": [
    "Who is the chairperson of Management Studies?",
    "Who heads the Department of Management Studies?",
    "Who manages the Management Studies department?",
    "Who is the Management Studies chairperson?",
    "Can you tell me the chairperson of Management Studies?"
  ],
  "response": 
    "The Chairperson of the Department of Management Studies is Janice A. Nealega."
  },
{
 
  "patterns": [
    "Who is the chairperson of Teacher Education?",
    "Who heads the Department of Teacher Education?",
    "Who manages Teacher Education?",
    "Who is the Teacher Education chairperson?",
    "Can you tell me the Teacher Education chairperson?"
  ],
  "response": 
    "The Chairperson of the Department of Teacher Education is Jolina Razell M. Mindoro."
  },
{
 
  "patterns": [
    "Who is the IT coordinator?",
    "Who is the Information Technology Program coordinator?",
    "Who coordinates the IT program?",
    "Who handles the Information Technology program?",
    "Can you tell me the IT coordinator?"
  ],
  "response": 
    "The Coordinator of the Information Technology Program is Donnalyn B. Montallana."
  },
{
 
  "patterns": [
    "Who is the Computer Science coordinator?",
    "Who coordinates the Computer Science program?",
    "Who handles the Computer Science program?",
    "Can you tell me the Computer Science coordinator?",
    "Who is in charge of the Computer Science program?"
  ],
  "response": 
    "The Coordinator of the Computer Science Program is Ely Rose L. Panganiban-Briones."
  },
{
 
  "patterns": [
    "Who is the Business Administration coordinator?",
    "Who coordinates the Business Administration program?",
    "Who handles the Business Administration program?",
    "Can you tell me the Business Administration coordinator?",
    "Who is in charge of the BA program?"
  ],
  "response": 
    "The Coordinator of the Business Administration Program is Maria Lourdez D. Lamanilao."
  },
{
 
  "patterns": [
    "Who is the Hospitality Management coordinator?",
    "Who coordinates the Hospitality Management program?",
    "Who handles the Hospitality Management program?",
    "Can you tell me the Hospitality Management coordinator?",
    "Who is in charge of Hospitality Management?"
  ],
  "response": 
    "The Coordinator of the Hospitality Management Program is Ryan S. Acojedo."
  },
{
 
  "patterns": [
    "Who is the Psychology coordinator?",
    "Who coordinates the Psychology program?",
    "Who handles the Psychology program?",
    "Can you tell me the Psychology coordinator?",
    "Who is in charge of Psychology?"
  ],
  "response": 
    "The Coordinator of the Psychology Program is Janette E. Alagar."
  },
{

  "patterns": [
    "Who is the Physical Education coordinator?",
    "Who coordinates the Physical Education program?",
    "Who handles the Physical Education program?",
    "Can you tell me the Physical Education coordinator?",
    "Who is in charge of Physical Education?"
  ],
  "response": 
    "The Coordinator of the Physical Education Program is Regine U. Caltino"
  },
{
 
  "patterns": [
    "Who is the campus nurse?",
    "Who works at the Health Services Office?",
    "Who is the nurse of CvSU Bacoor?",
    "Can you tell me the campus nurse?",
    "Who handles health services?"
  ],
  "response": 
    "The Campus Nurse of CvSU Bacoor is Aivan Rhei P. Cacho."
  },
{
 
  "patterns": [
    "Who heads the Office of Student Affairs and Services?",
    "Who is in charge of student affairs?",
    "Who manages the OSAS office?",
    "Can you tell me the head of student affairs?",
    "Who handles student services?",
    "Who is the head of OSAS?",
    "Name of the Student Affairs head",
    "Who manages OSAS?",
    "Contact person for OSAS",
    "Who manages the Quality Assurance Office?",
"Who heads Quality Assurance Office?",
"Who is in charge of Quality Assurance Office?",
"Can you tell me the head of the Quality Assurance Office?"

  ],
  "response": 
    "The Head of the Office of Student Affairs and Services is Steffanie M. Bato."
  },
{

"patterns": [
"Who is the head of the Administration and Support Services Office?",
"Who manages the Administration and Support Services Office?",
"Who heads administration and support services?",
"Who is in charge of administration and support services?",
"Can you tell me the head of the Administration and Support Services Office?"
],
"response": 
"The Head of the Administration and Support Services Office is Zannie I. Gamuyao."
},
{

"patterns": [
"Who is the coordinator for Secondary Education major in Mathematics?",
"Who coordinates the Mathematics Education program?",
"Who handles the BSEd Mathematics program?",
"Who is the Mathematics program coordinator?",
"Can you tell me the Mathematics coordinator?"
],
"response": 
"The Coordinator of the Secondary Education Program major in Mathematics is Nezil Obiado."
},
{

"patterns": [
"Who is the coordinator for Secondary Education major in English?",
"Who coordinates the English Education program?",
"Who handles the BSEd English program?",
"Who is the English program coordinator?",
"Can you tell me the English coordinator?"
],
"response": 
"The Coordinator of the Secondary Education Program major in English is Jay Anne F. Salles-Villareal."
},
{

  "patterns": [
    "Who is the campus registrar?",
    "Who handles the registrar office?",
    "Who is the registrar of CvSU Bacoor?",
    "Can you tell me the campus registrar?",
    "Who manages student records?",
    "Who heads the Office of the Campus Registrar?",
    "Who is in charge of the registrar office?"
  ],
  "response": 
    "The Campus Registrar of CvSU Bacoor is Jimwell G. Dacanay."
  },
{

  "patterns": [
    "Who is the campus librarian?",
    "Who heads the Library Services Office?",
    "Who manages the campus library?",
    "Who manages the library?",
    "Who is in charge of the library?",
    "Can you tell me the campus librarian?"
  ],
  "response": 
    "The Campus Librarian and head of the Library Services Office of CvSU Bacoor is Lorema N. Acapulco."
  },
{

"patterns": [
"Who is the quality assurance coordinator?",
"Who heads the Quality Assurance Office?",
"Who manages quality assurance activities?",
"Who is responsible for quality assurance?",
"Can you tell me the quality assurance coordinator?"
],
"response": 
"The Coordinator of the Quality Assurance Office is Steffanie M. Bato."
},
{

"patterns": [
"Who is the ARTA focal person?",
"Who handles Anti-Red Tape Authority concerns?",
"Who is responsible for ARTA implementation?",
"Who is the Campus ARTA focal person?",
"Can you tell me the ARTA focal person?"
],
"response": 
"The Campus Anti-Red Tape Authority (ARTA) Focal Person is Haydih Anne T. Velasco."
},
{

"patterns": [
"Who is the Human Resource Development coordinator?",
"Who heads the Human Resource and Development Office?",
"Who manages human resource services?",
"Who is in charge of HR development?",
"Can you tell me the HR coordinator?"
],
"response": 
"The Coordinator of the Human Resource and Development Office is Rimat Maris I. Taclibon."
},
{

"patterns": [
"Who is the Public Information Officer?",
"Who handles public information concerns?",
"Who manages public announcements?",
"Who is responsible for campus information dissemination?",
"Can you tell me the Public Information Officer?"
],
"response": 
"The Public Information Officer of CvSU Bacoor is Rimat Maris I. Taclibon."
},
{

"patterns": [
"Who is the security officer?",
"Who heads the Civil Security Services Office?",
"Who manages campus security?",
"Who is responsible for security services?",
"Can you tell me the security officer?"
],
"response": 
"The Security Officer of CvSU Bacoor is James E. Dalis."
},
{

"patterns": [
"Who is the Knowledge Management coordinator?",
"Who heads the Knowledge Management Office?",
"Who manages knowledge management activities?",
"Who is responsible for knowledge management?",
"Can you tell me the Knowledge Management coordinator?"
],
"response": 
"The Coordinator of the Knowledge Management Office is James E. Dalis."
},
{

"patterns": [
"Who is the Pollution Control coordinator?",
"Who heads the Pollution Control Office?",
"Who manages environmental compliance activities?",
"Who is responsible for pollution control?",
"Can you tell me the Pollution Control coordinator?"
],
"response": 
"The Coordinator of the Pollution Control Office is Arman C. Maribojo."
},
{

"patterns": [
"Who is the Alumni Affairs coordinator?",
"Who heads Alumni Affairs?",
"Who manages alumni relations?",
"Who is responsible for alumni affairs?",
"Can you tell me the Alumni Affairs coordinator?"
],
"response": 
"The Coordinator of Alumni Affairs is Alvina E. Ramallosa."
},
{

"patterns": [
"Who is the budget officer?",
"Who handles the campus budget?",
"Who manages budget-related concerns?",
"Who is responsible for budgeting?",
"Can you tell me the budget officer?"
],
"response": 
"The Budget Officer of CvSU Bacoor is Ryan Angelo G. Mojica."
},
{

"patterns": [
"Who is in charge of the Procurement Office?",
"Who manages procurement activities?",
"Who handles procurement concerns?",
"Who oversees the Procurement Office?",
"Can you tell me who is in charge of procurement?"
],
"response": 
"Ryan Angelo G. Mojica is the officer in charge of the Procurement Office."
},
{

"patterns": [
"Who is the safety officer?",
"Who heads the Campus DRRM Office?",
"Who manages campus safety?",
"Who is responsible for disaster risk reduction and management?",
"Can you tell me the safety officer?"
],
"response": 
"The Safety Officer of CvSU Bacoor is Gilbert E. Magano."
},
{

"patterns": [
"Who is the Physical Plant Services coordinator?",
"Who heads the Physical Plant Services Office?",
"Who manages facility maintenance services?",
"Who is responsible for physical plant operations?",
"Can you tell me the Physical Plant Services coordinator?"
],
"response": 
"The Coordinator of the Physical Plant Services Office is Gilbert E. Magano."
},
{

"patterns": [
"Who is the head of the Business and Resource Generation Office?",
"Who manages the Business and Resource Generation Office?",
"Who heads resource generation activities?",
"Who is responsible for business and resource generation?",
"Can you tell me the head of the Business and Resource Generation Office?"
],
"response": 
"The Head of the Business and Resource Generation Office is Diana Mae M. Belarmino."
},
{

"patterns": [
"Who is the property custodian?",
"Who manages university properties?",
"Who heads the Property Management Unit?",
"Who is in charge of campus properties?",
"Can you tell me the property custodian?"
],
"response": 
"The Property Custodian of CvSU Bacoor is Zannie I. Gamuyao."
},
{

"patterns": [
"Who is the research coordinator for Teacher Education?",
"Who handles research in the Department of Teacher Education?",
"Who is the Teacher Education research coordinator?",
"Who manages Teacher Education research activities?",
"Can you tell me the Teacher Education research coordinator?"
],
"response": 
"The Research Coordinator for the Department of Teacher Education is Ronan M. Cajigal."
},
{

"patterns": [
"Who is the research coordinator for Business Administration?",
"Who handles Business Administration research?",
"Who is the BA research coordinator?",
"Who manages research in the Business Administration Program?",
"Can you tell me the Business Administration research coordinator?"
],
"response": 
"The Research Coordinator for the Business Administration Program is Maria Lourdez D. Lamanilao."
},
{

"patterns": [
"Who is the research coordinator for Hospitality Management?",
"Who handles Hospitality Management research?",
"Who manages research in Hospitality Management?",
"Who is the Hospitality Management research coordinator?",
"Can you tell me the Hospitality Management research coordinator?"
],
"response": 
"The Research Coordinator for the Hospitality Management Program is Ryan Acojedo."
},
{

"patterns": [
"Who is assigned to the Events Management Unit?",
"Who handles event management?",
"Who manages campus events?",
"Who is in charge of the Events Management Unit?",
"Can you tell me the Events Management Unit coordinator?"
],
"response": 
"Ryan Acojedo is assigned to the Events Management Unit."
},
{

"patterns": [
"Who is the 5S focal person?",
"Who handles the 5S program?",
"Who is responsible for 5S implementation?",
"Who manages 5S activities?",
"Can you tell me the 5S focal person?"
],
"response": 
"Ryan Acojedo serves as the 5S Focal Person."
},
{

"patterns": [
"Who is the research coordinator for Criminology?",
"Who handles Criminology research?",
"Who manages research in the Department of Criminology?",
"Who is the Criminology research coordinator?",
"Can you tell me the Criminology research coordinator?"
],
"response": 
"The Research Coordinator for the Department of Criminology is James E. Dalis"
},
{

"patterns": [
"Who is the research coordinator for Arts and Sciences?",
"Who handles Arts and Sciences research?",
"Who manages research in the Department of Arts and Sciences?",
"Who is the Arts and Sciences research coordinator?",
"Can you tell me the Arts and Sciences research coordinator?"
],
"response": 
"The Research Coordinator for the Department of Arts and Sciences is Arth G. Mangcoy."
},
{

"patterns": [
"Who is the research coordinator for Computer Studies?",
"Who handles IT and Computer Science research?",
"Who manages research in the Department of Computer Studies?",
"Who is the Computer Studies research coordinator?",
"Can you tell me the Computer Studies research coordinator?"
],
"response": 
"The Research Coordinator for the Department of Computer Studies is Clarissa V. Rostrollo."
},
{

"patterns": [
"Who is the extension coordinator for Computer Studies?",
"Who handles extension activities in Computer Studies?",
"Who manages extension programs in IT and Computer Science?",
"Who is the Computer Studies extension coordinator?",
"Can you tell me the Computer Studies extension coordinator?"
],
"response": 
"The Extension Coordinator for the Department of Computer Studies is Alvina E. Ramallosa."
},
{

"patterns": [
"Who is the extension coordinator for Teacher Education?",
"Who handles Teacher Education extension programs?",
"Who manages extension activities in Teacher Education?",
"Who is the Teacher Education extension coordinator?",
"Can you tell me the Teacher Education extension coordinator?"
],
"response": 
"The Extension Coordinator for the Department of Teacher Education is Jay Anne F. Salles"
},
{

"patterns": [
"Who is the coordinator of the Instructional Materials Development Unit?",
"Who handles instructional materials development?",
"Who manages the IMD Unit?",
"Who is responsible for instructional materials?",
"Can you tell me the coordinator of the Instructional Materials Development Unit?"
],
"response": 
"Jay Anne F. Salles serves as the Program Coordinator of the Instructional Materials Development Unit."
},
{

"patterns": [
"Who is the extension coordinator for Criminology?",
"Who handles Criminology extension programs?",
"Who manages extension activities in Criminology?",
"Who is the Criminology extension coordinator?",
"Can you tell me the Criminology extension coordinator?"
],
"response": 
"Arman C. Maribojo serves as the Extension Coordinator for the Department of Criminology."
},
{

"patterns": [
"Who is the coordinator for student misdemeanor cases?",
"Who handles student misconduct concerns?",
"Who is in charge of student misdemeanors?",
"Who manages student disciplinary concerns?",
"Can you tell me the Student Misdemeanor Coordinator?"
],
"response": 
"Arman C. Maribojo serves as the Coordinator for Student Misdemeanor."
},
{

"patterns": [
"Who is the extension coordinator for Hospitality Management?",
"Who handles Hospitality Management extension programs?",
"Who manages extension activities in Hospitality Management?",
"Who is the Hospitality Management extension coordinator?",
"Can you tell me the Hospitality Management extension coordinator?"
],
"response": 
"Francis A. Paredes serves as the Extension Coordinator for the Hospitality Management Program."
},
{

"patterns": [
"Who is the extension coordinator for Business Administration?",
"Who handles Business Administration extension programs?",
"Who manages extension activities in Business Administration?",
"Who is the BA extension coordinator?",
"Can you tell me the Business Administration extension coordinator?"
],
"response": 
"The Extension Coordinator for the Business Administration Program is Rosette P. Sarmiento."
},
{

"patterns": [
"Who is the extension coordinator for Arts and Sciences?",
"Who handles Arts and Sciences extension programs?",
"Who manages extension activities in Arts and Sciences?",
"Who is the Arts and Sciences extension coordinator?",
"Can you tell me the Arts and Sciences extension coordinator?"
],
"response": 
"The Extension Coordinator for the Department of Arts and Sciences is Ana Rose M. Rupido."
},
{

"patterns": [
"Who is the OJT coordinator?",
"Who handles job placement services?",
"Who manages the Campus OJT and Job Placement Unit?",
"Who is responsible for internship placement?",
"Can you tell me the OJT coordinator?"
],
"response": 
"The Coordinator of the Campus OJT and Job Placement Unit is Ana Rose M. Rupido."
},
{

"patterns": [
"Who is the NSTP coordinator?",
"Who manages the National Service Training Program?",
"Who handles NSTP concerns?",
"Who is responsible for NSTP?",
"Can you tell me the NSTP coordinator?"
],
"response": 
"The Coordinator of the National Service Training Program (NSTP) is Steffanie M. Bato."
},
{

"patterns": [
"Who is the mental health counselor?",
"Who provides mental health counseling?",
"Who should I contact for mental health concerns?",
"Who handles mental health services?",
"Can you tell me the mental health counselor?"
],
"response": 
"The Mental Health Counselor of CvSU Bacoor is Janette E. Alagar."
},
{

"patterns": [
"Who is the coordinator of Student Development Services?",
"Who handles Student Development Services?",
"Who manages student development programs?",
"Who is responsible for Student Development Services?",
"Can you tell me the Student Development Services coordinator?"
],
"response": 
"The Coordinator of the Student Development Services Unit is Maria Lyn E. Dela Cruz."
},
{

"patterns": [
"Who is the NSTP-ROTC coordinator?",
"Who manages the ROTC unit?",
"Who handles ROTC concerns?",
"Who is responsible for NSTP-ROTC?",
"Can you tell me the ROTC coordinator?"
],
"response": 
"The Coordinator of the NSTP-ROTC Unit is Maria Lyn E. Dela Cruz."
},
{

"patterns": [
"Who is the Student Welfare Services coordinator?",
"Who handles student welfare services?",
"Who manages student welfare concerns?",
"Who is responsible for Student Welfare Services?",
"Can you tell me the Student Welfare Services coordinator?"
],
"response": 
"The Coordinator of the Student Welfare Services Unit is Julios M. Mojas."
},
{

"patterns": [
"Who handles institutional student programs and services?",
"Who manages student programs and services?",
"Who is responsible for Institutional Student Programs and Services?",
"Who coordinates student programs?",
"Can you tell me the coordinator of Institutional Student Programs and Services?"
],
"response": 
"The Coordinator of the Institutional Student Programs and Services Unit is Julios M. Mojas."
},
{

"patterns": [
"Who is the sports coordinator?",
"Who handles sports development?",
"Who manages sports activities?",
"Who is responsible for sports programs?",
"Can you tell me the sports coordinator?"
],
"response": 
"The Coordinator for Sports and Development is Michael John C. Sullano."
},
{

"patterns": [
"Who is the Admission and Testing Services coordinator?",
"Who handles admissions and testing?",
"Who manages admission concerns?",
"Who is responsible for testing services?",
"Can you tell me the Admission and Testing Services coordinator?"
],
"response": 
"The Coordinator of the Admission and Testing Services Unit is Rimat Maris I. Taclibon."
},
{

"patterns": [
"Who is the Culture and Arts coordinator?",
"Who handles culture and arts activities?",
"Who manages cultural programs?",
"Who is responsible for arts activities?",
"Can you tell me the Culture and Arts coordinator?"
],
"response": 
"The Coordinator of the Culture and Arts Unit is Stephen G. Bacolor."
},
{

"patterns": [
"Who is the scholarship coordinator?",
"Who handles scholarship concerns?",
"Who manages the Scholarship Unit?",
"Who is responsible for scholarships?",
"Can you tell me the scholarship coordinator?"
],
"response": 
"The Coordinator of the Scholarship Unit is Haydih Anne T. Velasco."
},
{

"patterns": [
"Who is the TES focal person?",
"Who handles TDP concerns?",
"Who is responsible for TES and TDP programs?",
"Who manages TES and TDP scholarships?",
"Can you tell me the TES or TDP focal person?"
],
"response": 
"The Focal Person for TES and TDP programs is Haydih Anne T. Velasco."
},
{

"patterns": [
"Who is the campus records custodian?",
"Who manages campus records?",
"Who is responsible for records custody?",
"Who handles official records?",
"Can you tell me the campus records custodian?"
],
"response": 
"The Campus Records Custodian is Haydih Anne T. Velasco."
},
{

"patterns": [
"Who is the privacy compliance officer?",
"Who handles data privacy concerns?",
"Who is the Compliance Officer for Privacy?",
"Who manages privacy compliance?",
"Can you tell me the privacy officer?"
],
"response": 
"The Compliance Officer for Privacy (COP) is Haydih Anne T. Velasco."
},
{

"patterns": [
"Who is the alternate GAD coordinator?",
"Who is the alternate coordinator for Gender and Development?",
"Who assists the Gender and Development Office?",
"Who is the alternate GAD focal person?",
"Can you tell me the alternate GAD coordinator?"
],
"response": 
"The Alternate Coordinator of the Gender and Development Office is Lorema N. Acapulco."
},
{

"patterns": [
"Who is the Planning Unit coordinator?",
"Who handles planning activities?",
"Who manages the Planning Unit?",
"Who is responsible for planning services?",
"Can you tell me the Planning Unit coordinator?"
],
"response": 
"The Coordinator of the Planning Unit is Edmund C. Martinez."
},
{

"patterns": [
"Who is the LMS coordinator?",
"Who manages the Learning Management System?",
"Who handles LMS concerns?",
"Who is responsible for the LMS?",
"Can you tell me the LMS coordinator?"
],
"response": 
"The Coordinator of the Learning Management System (LMS) is Jovelyn D. Ocampo."
},
{

"patterns": [
"Who is the current 5S focal person?",
"Who handles the 5S program?",
"Who manages 5S implementation?",
"Who is responsible for 5S activities?",
"Can you tell me the 5S focal person?"
],
"response": 
"The 5S Focal Person is Ryan Angelo G. Mojica."
}

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
