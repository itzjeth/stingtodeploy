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
  {
"patterns": [
"What is the history of CvSU",
"When was CvSU established",
"Tell me about CvSU history",
"history of cvsu",
"Background of CvSU"
],
"response": 
"Cavite State University traces its origins to the Indang Intermediate School established in 1906. Through the years, the institution underwent several transformations and was eventually converted into Cavite State University, continuing its commitment to quality education, research, extension, and production."
},
{

"patterns": [
"What is the vision of CvSU",
"cvsu vision",
"what is cvsu vission",
"Vision of Cavite State University"
],
"response": 
"The premier University in historic Cavite recognized for excellence in the development of globally competitive and morally upright individuals."
},
{

"patterns": [
"What is the mision of CvSU",
"cvsu mission",
"what is cvsu mission",
"Mision of Cavite State University"
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
"what is the university mission and vision",
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
"core values",
"core valus of cvsu"
],
"response": 
"We Commit to the highest standards of education, value our stakeholders, Strive for continual improvement of our products and services, and Uphold the University's tenets of Truth, Excellence, and Service to produce globally competitive and morally upright individuals"
},

{

"patterns": [
"What is the motto of CvSU",
"CvSU motto",
"What is Cavite State University motto",
"motto of cvsu"
],
"response": 
"The motto of Cavite State University is 'Truth, Excellence, and Service.'"
},
 {
 
  "patterns": [
    "What are the lyrics to the CvSU hymn?",
    "Can you provide the CvSU hymn lyrics?",
    "Lyrics of the school hymn",
    "How does the CvSU hymn go?",
    "What is cvsu hymn lyrics",
    "lyrics of cvsu hymn",
    "What is the CvSU hymn?",
    "Meaning of the school hymn",
    "Why do we sing the CvSU hymn?",
    "what is cvsu hymn",
    "cvsu hymn"
  ],
  "response": 
    "The CvSU Hymn is the official school song of Cavite State University. It is sung during official university events, ceremonies, and gatherings as a symbol of unity, pride, and identity among students, faculty, and alumni.\n\nThe hymn expresses the university’s values, mission, and commitment to excellence in education, service, integrity, and character formation. It also highlights pride in being part of CvSU and encourages everyone to uphold dedication and responsibility in their academic journey.\n\nYou may listen to and follow the official CvSU Hymn through this video:\n\nhttps://www.youtube.com/watch?v=A2fOWAo9jME\n\nThe hymn is commonly performed during flag ceremonies, graduation rites, and other important university occasions."
  
},

  {

    "patterns": [
    "When is the onsite validation for passers?",
      "What is the onsite validation for passers?",
      "onsite validation for passers?",
      "What is the schedule for requirement validation?",
      "Onsite validation dates for incoming students",
      "Onsite validation date",
      "What date is onsite validation"
    ],
    "response": 
      "The onsite validation of requirements for qualified applicants (passers) for the First Semester, S.Y. 2026–2027 is scheduled according to the applicant's program:<br><br>June 22 – June 25<br><br>Bachelor of Science in Hospitality Management (BSHM)<br>Bachelor of Science in Business Administration (BSBA) – Marketing Management and Human Resource Management<br>Bachelor of Science in Information Technology (BSIT)<br>Bachelor of Science in Computer Science (BSCS)<br><br>June 29 – July 2<br><br>Bachelor of Science in Criminology (BSCrim)<br>Bachelor of Science in Psychology (BS Psychology)<br>Bachelor of Secondary Education (BSEd) – English and Mathematics<br><br>Please visit the campus on the date assigned to your program and bring all the required <br>documents for validation."
},
{
  "patterns": [
   "How do I register?",
    "How to enroll",
    "What is the registration process?",
    "How can I enroll?",
    "Enrollment process",
    "Registration procedure",
    "Steps for registration",
    "Steps for enrollment",
    "What are the steps in enrollment?",
    "Can you explain the registration process?",
    "How does enrollment work?",
    "What should I do to register?",
    "How can I complete my enrollment?",
    "Registration steps",
    "Enrollment steps",
    "Student registration process",
    "How to register in CvSU Bacoor?",
    "How to enroll in CvSU Bacoor?",
    "CvSU Bacoor registration",
    "CvSU Bacoor enrollment process",
    "Procedure for enrollment",
    "Procedure for registration",
    "What are the enrollment procedures?",
    "What comes after admission?",
    "How do I proceed with registration?",
    "Registration guide",
    "Enrollment guide",
    "What is the admission process?",
    "step by step enroll process",
    "step by step registration process",
    "How do I apply for admission?",
    "How can new students enroll?",
    "How do new students enroll?",
    "Enrollment process for freshmen",
    "New student enrollment procedure",
    "What is the admission and enrollment process?",
    "How can I apply and enroll?",
    "How do freshmen register?",
    "What are the requirements for enrollment?"
  ],
  "response": 
    "The admission, registration, and enrollment process for new students at CvSU Bacoor generally consists of several important steps to ensure that applicants are officially admitted and enrolled in their chosen academic program.\n\n1. Checking and Verification of Requirements\n   - Applicants must submit all required admission documents for evaluation.\n   - The Admissions Office will review and verify the authenticity and completeness of the submitted requirements.\n   - Incomplete or incorrect documents may delay the admission process.\n\n2. Issuance of Notice of Admission and Medical Referral Slip\n   - Qualified applicants will receive a Notice of Admission confirming their eligibility for enrollment.\n   - A Medical Referral Slip will also be provided, which is required for the medical examination and health clearance process.\n\n3. Medical Examination and Clearance\n   - Applicants must undergo the required medical and physical examination at the designated clinic or health facility.\n   - The examination may include basic health assessments and laboratory procedures as required by the university.\n   - Students must secure a Medical Clearance before proceeding to the next stage of enrollment.\n\n4. Registration and Enrollment at the Registrar's Office\n   - Once all requirements and clearances have been completed, students must proceed to the Registrar's Office for registration.\n   - Personal information, academic records, and enrollment details will be verified and encoded into the university system.\n   - Students will be officially enrolled in their selected degree program upon successful processing.\n\n5. Final Enrollment Confirmation and Class Registration\n   - Students must follow the instructions provided by the Registrar regarding subject enrollment, section assignment, and class schedules.\n   - Any additional forms or enrollment procedures must be completed within the designated enrollment period.\n   - After confirmation, students may access their class schedule and other academic information.\n\nImportant Reminders:\n- Prepare all required documents before visiting the campus to avoid delays.\n- Follow the official enrollment schedule announced by the university.\n- Keep copies of all submitted documents and receipts for future reference.\n- For the latest admission guidelines, enrollment schedules, documentary requirements, and announcements, students are encouraged to coordinate directly with the Admissions Office or the Registrar's Office of CvSU Bacoor."
  
},

{

  "patterns": [
    "application category",
    "applicant category",
    "new student category",
    "first year applicant",
    "grade 12 student",
    "senior high graduate",
    "transfer student",
    "college transferee",
    "tcp applicant",
    "teacher certificate program",
    "tcp requirements",
    "document submission",
    "requirements for grade 12 student",
    "shs student requirements",
    "requirements for transferee",
    "requirements for shs graduate",
    "requirements for grade 12 graduate",
    "requirements for ALS passer",
    "requirements for admission",
    "requirements in cvsu",
    "requirements for enrollment",
    "senior high graduate requirements",
    "transferee requirements"
  ],
  "response": 
    "ADMISSION REQUIREMENTS (Passers) FIRST SEMESTER S.Y. 2026-2027\n\nFOR SHS GRADUATES\nCan be found in the Admission Portal:\n• Notice of Admission (NOA)\n• Medical Referral Slip\n• Medical Endorsement Form\n• Student Health Record (USHE-QF-15)\n• Interview Permit (for BSHM passers only)\n\nOther Requirements:\n• Grade 12 Report Card (original)\n• Good Moral Certificate (original)\n\nFOR ALS PASSERS\nCan be found in the Admission Portal:\n• Notice of Admission (NOA)\n• Medical Referral Slip\n• Medical Endorsement Form\n• Student Health Record (USHE-QF-15)\n• Interview Permit (for BSHM passers only)\n\nOther Requirements:\n• Certificate of Rating (COR) with eligibility to enroll in college (original)\n\nFOR TRANSFEREES\nCan be found in the Admission Portal:\n• Notice of Admission (NOA)\n• Medical Referral Slip\n• Medical Endorsement Form\n• Student Health Record (USHE-QF-15)\n• Interview Permit (for BSHM passers only)\n\nOther Requirements:\n• Transcript of Records or Certificate of Grades (original)\n• Certificate of Good Moral Character (original)\n• Honorable Dismissal (original)\n• NBI or Police Clearance (original)"
},
{

"patterns": [
"Is there an orientation for new students",
"What is the freshman orientation",
"Do new students attend orientation",
"orientation for first year",
"orientation for freshmen",
"is orientation required to attend"
],
"response": 
"The University typically conducts orientation programs for new students to introduce important academic policies, campus services, student responsibilities, and University procedures."

},

{

"patterns": [
"Does CvSU have an online admission portal",
"Where can I apply online",
"How do i apply online admission",
"How do i enroll online",
"Online admission application",
"How do I access the admission portal",
"Can I submit my application online",
"admission link cvsu",
"where to apply cvsu",
"cvsu admission portal",
"online admission"

],
"response": [
    "Applicants may submit admission applications through the CvSU Online Admission System when applications are open.\n\nYou may access the admission portal through:\nhttps://admission.cvsu.edu.ph/\n\nApplicants should sign up using a valid Gmail account and follow the instructions provided in the portal for the application process."
  ]
},

 {

  "patterns": [
    "What are the extracurricular activities?",
    "What extracurricular activities are available",
    "Are there clubs I can join?",
    "Does the school have sports or arts activities?",
    "What clubs and activities can I join",
    "Campus extracurricular activities",
    "Available extracurricular programs",
    "What sports are available in CvSU Bacoor",
    "Sports activities on campus",
    "Can I join sports teams",
    "Available sports programs",
    "Athletic activities"
  ],
  "response": 
    "CvSU Bacoor Campus offers various extracurricular and co-curricular activities that support student development, leadership, teamwork, creativity, and campus engagement.\n\nStudents may participate in activities such as:\n\n**Sports and Athletics**\n• Basketball\n• Volleyball\n• Tennis\n• Athletics / Track and Field\n• Chess and other mind sports\n• Other recreational and competitive activities depending on University programs and student interest\n\n**Cultural and Arts Activities**\n• Theater and Performing Arts\n• Music and Choral Performances\n• Visual Arts activities and creative competitions\n\n**Student Organizations and Clubs**\n• Department-based student organizations\n• Recognized campus organizations under the Office of Student Affairs and Services (OSAS)\n• Community service and volunteer groups\n\n**Academic and Development Activities**\n• Seminars and workshops\n• Leadership training programs\n• Research presentations\n• Academic competitions\n\nThese activities help students develop teamwork, leadership skills, creativity, and social responsibility while enhancing their overall college experience.\n\nFor updated lists of active organizations, sports programs, and upcoming activities, students may coordinate with the Office of Student Affairs and Services (OSAS).\n\nCvSU Bacoor Campus Contact Number: (046) 476-5029"
  
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
       "OSAS, or the Office of Student Affairs and Services, is dedicated to supporting students throughout their university life. It provides assistance with student organizations, leadership and skills development programs, scholarships, counseling referrals, student welfare concerns, disciplinary matters, and various campus activities. If you need help with student-related concerns, opportunities, or support services, OSAS is one of the primary offices you can approach."
},

{
  "patterns": [
    "Who is in charge of student affairs?",
    "Who manages the OSAS office?",
    "head of student affairs?",
    "Who handles student services?",
    "Who is the head of OSAS?",
    "Name of the Student Affairs head",
    "Who manages OSAS?",
    "Contact person for OSAS",
    "who leads OSAS",
    "Who manages the Quality Assurance Office?",
    "Who heads Quality Assurance Office?",
    "Who is in charge of Quality Assurance Office?",
    "Can you tell me the head of the Quality Assurance Office?",
    "Who is the quality assurance coordinator?",
    "Who manages quality assurance activities?",
    "Who is responsible for quality assurance?",
    "Can you tell me the quality assurance coordinator?",
    "Who is the NSTP coordinator?",
    "Who manages the National Service Training Program?",
    "Who handles NSTP concerns?",
    "Who is responsible for NSTP?",
    "Can you tell me the NSTP coordinator?"
  ],
  "response": [
    "Steffanie M. Bato serves as the Head of the Office of Student Affairs and Services (OSAS) of CvSU Bacoor.<br><br>She also serves as the Coordinator of the Quality Assurance Office and the Coordinator of the National Service Training Program (NSTP)."
  ]
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
      "rooms in cvsu",
      "facilities in cvsu",
      "faclity in cvsu",
      "what kind of facilities in cvsu",
      "Campus facilities",
      "Where can I find the registrar?",
  "Where is the cashier's office located?",
  "Where is the admissions office?",
  "Where is the OSAS office?",
  "Where is the Office of Student Affairs and Services?",
  "Where is the guidance office?",
  "Where is the Guidance and Counseling Office?",
  "Where is the campus clinic?",
  "Where can I find the clinic?",
  "Where is the campus administrator's office?",
  "Where are the faculty rooms located?",
  "Where are the consultation areas?",
  "Where is the gymnasium?",
  "Where is the school court?",
  "Where is the canteen?",
  "Where can students eat on campus?",
  "Where are the multipurpose rooms?",
  "Where are the meeting rooms located?",
  "Where are the classrooms located?",
  "What floor are the classrooms on?",
  "Where can I hold my thesis defense?",
  "Where are project defense rooms located?",
  "Where is the student organization office?",
  "Where are the student activity spaces?",
  "Where can I find student support facilities?",
  "Location of the clinic",
  "Location of the registrar office",
  "Gym location",
  "Canteen location"
    ],
  
  "response": 
    "Cavite State University (CvSU) Bacoor City Campus provides a variety of academic, administrative, and student-support facilities to meet the needs of students, faculty, and staff.\n\nACADEMIC FACILITIES\n• Regular Classrooms – Located from the 1st Floor to the 4th Floor.\n• Computer Laboratories – Located on the 3rd Floor.\n• School Gymnasium/Court – Located on the Ground Floor; used for physical education classes, events, seminars, and university activities.\n• Specialized Laboratories – Located on the 5th Floor for program-specific practical exercises and laboratory work.\n• Faculty Rooms and Consultation Areas – Located on the Ground Floor.\n\nSTUDENT LEARNING FACILITIES\n• Library – Located on the 2nd Floor and provides academic resources, books, and study spaces.\n• Thesis, Capstone, and Project Defense Venues – Available depending on schedule and room assignment.\n\nADMINISTRATIVE OFFICES\n(Most offices are located on the Ground Floor, while some administrative functions may be found in the New Building.)\n• Office of the Campus Administrator – Near the Registrar's Area.\n• Registrar's Office – Ground Floor.\n• Cashier's Office – Ground Floor.\n• Admissions Office – Ground Floor.\n• Office of Student Affairs and Services (OSAS) – Ground Floor.\n• Guidance and Counseling Office – Ground Floor.\n\nSTUDENT SUPPORT FACILITIES\n• Campus Clinic – Located on the Ground Floor near the campus exit.\n• Student Organization and Leadership Development Offices – Ground Floor.\n\nSTUDENT ACTIVITY AND CAMPUS FACILITIES\n• Multipurpose Rooms and Meeting Areas.\n• Student Gathering and Activity Spaces.\n• Canteen – Located on the Ground Floor and serves as a common area for students.\n\nMost facilities are accessible to students during official campus hours, subject to university policies and scheduling.\n\nIf you are looking for a specific room, office, laboratory, or facility, you may inquire at the Information Desk, Registrar's Office, or the Office of Student Affairs and Services (OSAS) for directions and availability."

},
  {
  
  "patterns": [
    "What degrees are available?",
    "List of degrees in CvSU Bacoor",
    "What bachelor's degrees do you offer?",
    "Available degree programs",
    "What degree programs are offered?",
    "What can I take in CvSU Bacoor?",
    "What undergraduate programs are available?",
    "What courses are offered?",
    "Can you give me the list of courses?",
    "What can I study here?",
    "courses in cvsu",
    "Courses available in the campus",
    "What programs can I enroll in?",
    "What academic programs are available?",
    "What fields of study are offered?",
    "List of undergraduate courses",
    "Available programs in campus",
    "Degrees to choose from",
    "What degree programs are currently available?",
    "Which degrees can I take up?",
    "Undergraduate programs offered",
    "What are the available courses to enroll in?"
  ],
  "response": 
    "CvSU Bacoor offers several undergraduate degree programs for students who want to build careers in education, business, technology, social sciences, hospitality, and law enforcement.\n\nAvailable programs include:\n\n• Bachelor of Secondary Education (BSEd) – For students who want to become professional teachers.\n• Bachelor of Science in Business Management (BSBM) – Focuses on business operations, entrepreneurship, and management.\n• Bachelor of Science in Computer Science (BSCS) – Covers software development, programming, and computer systems.\n• Bachelor of Science in Criminology (BSCrim) – Prepares students for careers in law enforcement, public safety, and criminal justice.\n• Bachelor of Science in Hospitality Management (BSHM) – Focuses on hotel, restaurant, tourism, and hospitality services.\n• Bachelor of Science in Information Technology (BSIT) – Covers information systems, networking, web development, and IT support.\n• Bachelor of Science in Psychology (BSPsych) – Studies human behavior, mental processes, and psychological assessment.\n\nEach program includes a combination of general education subjects, major courses, practical activities, laboratory work (if applicable), and on-the-job training or internships.\n\nIf you'd like to know more about a specific course, such as its curriculum, career opportunities, or admission requirements, feel free to ask."
},
  {
  "patterns": [
 "Who handles OJT concerns?",
    "Who is the OJT person",
    "Who can i contact about OJT",
    "Who do I talk to about my internship?",
    "Where can I ask about OJT requirements?",
    "Who is the OJT coordinator?",
    "OJT concerns"
  ],
  "response": [
    "The Coordinator of the Campus OJT and Job Placement Unit is Ana Rose M. Rupido.\n\nFor OJT-related matters, students may coordinate with their assigned department, OJT adviser, or the Campus OJT and Job Placement Unit.\n\nIf you have questions about internship requirements, OJT hours, company placement, endorsement letters, documents, or other internship concerns, your OJT adviser can provide guidance and clarification.\n\nTo complete OJT requirements, students are typically required to prepare:\n• Updated Resume\n• Endorsement Letter\n• Other documents required by the department or OJT adviser\n\nStudents are encouraged to follow all OJT guidelines and complete the required hours to avoid delays or issues with their final grade. For the most accurate and updated instructions, please consult your OJT adviser or department office."
  ]
},
  {
 
    "patterns": [
      "I lost my items on campus",
      "Where is the lost and found?",
      "What to do if I lose something?",
      "How to report a lost belonging?",
      "What should I do if I lost something on campus",
    "Lost and found services",
      "Lost and found",
    "missing items",
    "lose keys",
    "I lost my belongings",
    "Where can I report lost items",
    "recover lost items",
    "How do I recover lost property",
    "Where can I claim a lost item?",
"Someone took my item",
"I misplaced my things on campus",
"I can't find my belongings",
"I lost my wallet",
"I lost my phone",
"I lost my bag",
"I lost my keys",
"I left my bag in a room",
"Who should I contact for lost items?",
"Who handles lost and found concerns?",
"Where do found items go?",
"Is there a lost and found office?",
"Can security help me recover my belongings?",
"How do I report a missing item?",
"Where should I go if I lose something?",
"I lost something in the campus",
"Missing personal belongings",
"Lost property assistance",
"Report lost property",
"Retrieve lost belongings",
"Claim lost property",
"Found and lost items",
"How to claim found items?"

    ],
  "response": 
    "If you have lost a personal belonging on campus, you may take the following steps to help recover it:\n\n1. Ask the security guard on duty.\nSecurity personnel are often informed when lost items are found and turned in.\n\n2. Visit the Office of Student Affairs and Services (OSAS).\nProvide a detailed description of the item, including its appearance, the date it was lost, and the last location where you remember having it.\n\n3. Check campus announcements.\nFound items may sometimes be reported through official campus announcements or student communication channels.\n\n4. Ask classmates, friends, or instructors.\nSomeone may have seen or picked up the item and can provide information about its whereabouts.\n\n5. File a lost item report.\nIf the item has not been located, you may report it to the campus security office. This allows security personnel to monitor and match any found items with reported losses.\n\nIt is recommended to report lost belongings as soon as possible. The sooner a report is made, the greater the chance of recovering the item.\n\nFor further assistance, you may approach the Office of Student Affairs and Services (OSAS) or the campus security personnel."
},
  {
  "patterns": [
    "Contact information",
    "Email address",
    "Phone number",
    "How do I contact CvSU Bacoor?",
    "Campus contact",
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
    "Students, applicants, parents, and stakeholders may contact CvSU Bacoor through its official communication channels for inquiries, concerns, and requests.\n\n**CvSU Bacoor Campus Contact Information**\n\n📍 Cavite State University – Bacoor City Campus\nLily Street, Phase II, Soldiers Hills IV, Bacoor City, Cavite, Philippines\n\n📞 Telephone: (046) 476-5029\n📧 Email: cvsubacoor@cvsu.edu.ph\n\nFor additional university contact details, visit:\nhttps://cvsu.edu.ph/contact-us/\n\nThese official contact channels may be used for administrative, academic, admissions, registrar, enrollment, student services, and other university-related concerns."
},
  {
   
    "patterns": [
  "How many OJT hours per department?",
  "How many hours for internship?",
  "Required OJT hours for my course",
  "OJT hours",
  "How many hours is OJT in CvSU?",
  "How long is internship in CvSU?",
  "What is the required internship hours?",
  "Internship hours requirement",
  "OJT requirement per program",
  "How many hours do I need to complete OJT?",
  "How many hours of OJT for IT students?",
  "How many hours for BSIT internship?",
  "How many hours for BSCS internship?",
  "How many hours for BSHM internship?",
  "How many hours for BSBM internship?",
  "How many hours for BS Psychology internship?",
  "How many hours for BSEd internship?",
  "Required training hours for OJT",
  "OJT duration per course",
  "Internship duration requirement",
  "OJT hours needed to graduate",
  "Minimum OJT hours per program",
  "CvSU internship hours",
  "CvSU OJT requirement",
  "How many practicum hours are required?",
  "Practicum hours requirement",
  "Work immersion hours (OJT)",
  "How long is practicum in college?",
  "How many hours is work immersion in CvSU?",
  "Internship length per department"
],
  "response": 
    "The required number of On-the-Job Training (OJT) hours at CvSU Bacoor Campus depends on your degree program and the curriculum set by your department.\n\nMinimum OJT hour requirements per program are generally as follows:\n\n• Bachelor of Science in Information Technology (BSIT): minimum of 360 hours\n• Bachelor of Science in Computer Science (BSCS): minimum of 240 hours\n• Bachelor of Science in Business Management (BSBM): minimum of 200 hours\n• Bachelor of Science in Hospitality Management (BSHM): minimum of 200 hours\n• Bachelor of Science in Psychology (BS Psych): minimum of 200 hours\n• Bachelor of Secondary Education (BSEd): minimum of 200 hours\n\nPlease note that these are minimum requirements and may still vary depending on your curriculum, year level, or specific department policies.\n\nFor the most accurate and updated requirement for your program, it is best to coordinate with your OJT coordinator, program adviser, or department chair.\n\nMake sure to complete all required hours and submit necessary documentation within the assigned schedule to avoid delays in graduation processing."
},
{
  "patterns": [
    "How much is the statistician fee?",
    "What are the research fees?",
    "Fee for the statistician",
    "How much do I pay for capstone evaluation?",
    "How much is the capstone defense fee?",
    "What is the defense fee for capstone?",
    "How much do we pay for capstone defense?",
    "What is the estimated capstone defense fee?",
    "How much should we prepare for the defense fee?",
    "Is there a fee for capstone defense?",
    "How much is the panel fee for capstone defense?",
    "What are the defense expenses for capstone?",
    "How much is the payment for capstone panelists?",
    "What is the cost of defending our capstone project?",
    "How much is the thesis defense fee?",
    "What is the defense fee for thesis?",
    "How much do we pay for thesis defense?",
    "How much is the panel fee for thesis?",
    "What is the estimated thesis defense fee?",
    "How much is the TA and TC fee?",
    "Technical adviser fee",
    "Technical critic fee",
    "Statistician fee",
    "How much do we pay the technical critic?",
    "Panel fees for capstone"
  ],
  "response": 
    "At CvSU Bacoor Campus, the fees associated with Capstone and Research evaluation may include the following:\n\n• Technical Adviser (TA) Fee: ₱1,500.00\n• Technical Critic (TC) Fee: ₱800.00\n• Statistician Fee: ₱500.00\n\nFor Capstone or Thesis Defense, fees are not fixed and may vary depending on the number of panelists assigned and their availability. In most cases, the defense fee ranges from ₱200.00 to ₱500.00 per panelist.\n\nFor example, if the total defense fee is ₱1,000.00 and a group has three members, each member may contribute approximately ₱333.33.\n\nPlease note that these fees may vary depending on the department, degree program, academic policies, and current university guidelines. Students are advised to verify the exact fees with their department office, research coordinator, capstone coordinator, adviser, subject instructor, or the Cashier's Office before making any payment.\n\nStudents should also settle all required fees within the prescribed deadlines to avoid delays in evaluation, defense schedules, and completion of academic requirements."
  
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
    "At CvSU Bacoor Campus, thesis, capstone, and research defenses are usually conducted in designated classrooms, laboratories, conference rooms, or other venues assigned by the department or program.\n\nThe exact venue may vary depending on:\n• Your degree program or department\n• The type of defense (proposal, pre-oral, final oral, or capstone defense)\n• The number of groups scheduled for the day\n• Room availability and administrative arrangements\n\nTo know your exact schedule and venue, always check the official announcements from your course instructor, research adviser, capstone coordinator, or department office. These details are typically released before the scheduled defense date.\n\nIf you are unsure about your assigned venue, you may also contact your department chairperson, technical adviser, or class representative for confirmation.\n\nMake sure to arrive on time and prepare all required documents and presentation materials for your defense."
},
  {
   
    "patterns": [
      "What subjects are offered for first year students?",
      "First year college subjects",
      "What will I study in my first year?",
      "Freshman curriculum subjects"
    ],
    "response": 
      "As a first-year student, you'll be excited to begin your academic journey with a variety of subjects designed to build a strong foundation in your chosen program.<br><br><br>The subjects you will take during your first year depend on your degree program.<br>CvSU Bacoor Campus offers programs such as:<br><br>🎓 Bachelor of Science in Information Technology (BSIT)<br> Bachelor of Science in Computer Science (BSCS)<br>🎓 Bachelor of Science in Psychology (BS Psych)<br> Bachelor of Science in Business Management (BSBM)<br> Bachelor of Science in Hospitality Management (BSHM)<br>🎓 Bachelor of Secondary Education (BSEd)<br><br>For first-year students, common subjects may include:<br><br> General Education (GE) Courses<br>• Understanding the Self<br>• Purposive Communication<br>• Mathematics in the Modern World<br>• Science, Technology, and Society<br>• Readings in Philippine History<br>• The Contemporary World<br>• Art Appreciation<br>• Ethics<br><br>💻 Program-Specific Courses<br><br>For BSIT and BSCS students:<br>• Introduction to Computing<br>• Computer Programming<br>• Fundamentals of Information Technology<br><br>🧠 For BS Psychology students:<br>• <br>Introduction to Psychology<br>• Psychological Statistics<br>• Understanding Human Behavior<br><br> For BS Business Management students:<br>• Fundamentals of Business Management<br>• Principles of Marketing<br>• Financial Management Basics<br><br> For BS Hospitality Management students:<br>• Introduction to Hospitality Management<br>• Tourism and Hospitality Operations<br>• Food and Beverage Service Fundamentals<br><br> For BSEd students:<br>• The Teaching Profession<br>• Foundations of Education<br>• Child and Adolescent Development<br><br>Please note that the exact subjects and schedules may vary depending on your curriculum and year of admission.<br><br><br>For the most accurate and updated information, you may consult your department chairperson, program adviser, or the Registrar's Office.<br>We wish you a successful and enjoyable first year at CvSU Bacoor Campus!<br> If you have any questions about enrollment, schedules, or campus services, feel free to ask.<br>"
},
  {
   
    "patterns": [
      "Where is the library located?",
      "How do I find the library?",
      "What floor is the library on?",
      "Library location in campus"
    ],
    "response": 
      "The library is an important resource for your studies, providing access to books, references, research materials, and a quiet place for learning.<br><br><br> The CvSU Bacoor Campus Library is located on the second floor of the old campus building.<br>Simply proceed to the old campus building and head up to the second floor, where you will find the library and its available services for students.<br> The library is open during regular campus operating hours.<br>However, schedules may vary depending on academic activities, holidays, or special events.<br>It is always a good idea to check with the library staff for the latest updates regarding operating hours and available services.<br> The library offers various resources and facilities to support your academic needs, including reference materials, study spaces, and research assistance.<br>If you have any more questions or need further assistance, feel free to ask.<br>"
},
  {
   
    "patterns": [
      "How much is the OJT fee?",
      "Do I need to pay for OJT?",
      "Payment for internship",
      "Where do I pay the OJT fee?"
    ],
    "response": 
      "The On-the-Job Training (OJT) fee is **₱100.00**. However, please note that the amount **may vary depending on your department, program, or course requirements**.<br> It is recommended to confirm the exact fee with your department or OJT coordinator before making any payment.<br>To pay your OJT fee, you may visit the University's Cashier's Office during office hours.<br> You can also check with your department for any updated payment procedures and deadlines.<br>Additionally, don't forget to prepare the required documents for your OJT, which may include:<br><br> Updated Resume<br> Endorsement Letter<br> Other supporting documents (as required by your department)<br><br>Make sure to submit all required documents to your OJT coordinator or department office to complete your OJT requirements.<br><br><br>If you have any further questions or concerns, feel free to ask, and I'll be happy to assist you.<br> Wishing you a successful and productive OJT experience. "
},
  {
   
    "patterns": [
      "What is TA and TC?",
    "Meaning of TA and TC in capstone",
    "What is a Technical Adviser?",
    "What is a Technical Critic?",
    "What is TA",
    "What is TC",
    "What does TA stand for?",
    "What does TC stand for?",
    "Who is the TA in capstone?",
    "Who is the TC in capstone?",
    "What is the role of a Technical Adviser?",
    "What is the role of a Technical Critic?",
    "Explain TA and TC",
    "Can you explain TA and TC?",
    "Who are TA and TC?",
    "What do TA and TC mean?",
    "What are TA and TC in research?",
    "What are TA and TC in capstone defense?",
    "What is the meaning of TA?",
    "What is the meaning of TC?",
    "What does Technical Adviser mean?",
    "What does Technical Critic mean?",
    "Who guides students during capstone?",
    "Who evaluates the capstone project?",
    "Who is responsible for guiding the capstone group?",
    "Who checks our capstone project?",
    "Who critiques the capstone project?",
    "Who mentors the capstone team?",
    "Who advises students in capstone?",
    "Who reviews the capstone work?",
    "Difference between TA and TC",
    "What's the difference between a Technical Adviser and Technical Critic?",
    "How are TA and TC different?",
    "TA versus TC",
    "Compare TA and TC",
    "What are the responsibilities of TA and TC?",
    "What does a TA do?",
    "What does a TC do?",
    "What is the job of a Technical Adviser?",
    "What is the job of a Technical Critic?",
    "Functions of TA and TC",
    "Purpose of TA and TC",
    "Why do we need a Technical Adviser?",
    "Why do we need a Technical Critic?",
    "What is a capstone adviser?",
    "Is TA the capstone adviser?",
    "Who helps us during capstone development?",
    "Who monitors our capstone progress?",
    "Who provides technical guidance in capstone?",
    "Who assesses the technical quality of a project?",
    "What is the work of a Technical Critic?",
    "What is the work of a Technical Adviser?",
    "What are the duties of TA and TC?",
    "Can you define TA and TC?",
    "Define Technical Adviser",
    "Define Technical Critic",
    "Technical Adviser meaning",
    "Technical Critic meaning",
    "TA meaning in capstone",
    "TC meaning in capstone",
    "TA abbreviation meaning",
    "TC abbreviation meaning",
    "What does TA mean in research defense?",
    "What does TC mean in research defense?",
    "Who gives feedback during capstone defense?",
    "Who asks questions during capstone defense?",
    "Who evaluates the feasibility of the project?",
    "Who ensures project standards are met?",
    "What is the responsibility of a capstone TA?",
    "What is the responsibility of a capstone TC?",
    "Tell me about TA and TC",
    "I want to know about TA and TC",
    "Can you tell me the meaning of TA and TC?",
    "What are TA and TC roles?",
    "What do Technical Advisers and Technical Critics do?",
    "Who supervises the capstone project?",
    "Who examines the capstone project?",
    "What is a technical adviser in capstone?",
    "What is a technical critic in capstone?",
    "Role of technical adviser",
    "Role of technical critic",
    "Technical adviser duties",
    "Technical critic duties",
    "TA and TC responsibilities",
    "Meaning of technical adviser and technical critic"
      
    ],
    "response": 
      "In the context of Capstone Defense, **TA** and **TC** are important members of the evaluation panel.<br>📝<br><br>**TA** stands for **Technical Adviser**. The Technical Adviser is the faculty member who guides and mentors the group throughout the development of the Capstone project.<br>They provide technical expertise, monitor the project's progress, ensure that academic and technical standards are met, and help the students address challenges encountered during the research and development process.<br><br><br>On the other hand, **TC** stands for **Technical Critic**. The Technical Critic serves as an evaluator who reviews the project from a critical and technical perspective.<br>They assess the quality, feasibility, functionality, methodology, and overall technical soundness of the project.<br>During the defense, the Technical Critic may ask questions, provide recommendations, and identify areas for improvement to ensure that the project meets the required standards.<br><br><br>During the Capstone Defense, both the **Technical Adviser (TA)** and the **Technical Critic (TC)** play significant roles in evaluating and improving the quality of your project.<br> They will provide feedback, ask questions, and assess your team's ability to explain and defend the work you have completed.<br><br><br>I hope this helps you understand the roles of the **TA (Technical Adviser)** and **TC (Technical Critic)** in the Capstone Defense at CvSU Bacoor Campus.<br>If you have any further questions or concerns, feel free to ask!<br>"
},
{
  
    "patterns": [
      "Who is the current campus administrator?",
      "Name of the campus head",
      "Bacoor campus administrator",
      "Who runs the campus operations?",
       "campus admin ",
    "new campus administrator",
    "new campus admin",
    "cvsu bacoor campus director",
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
      "The current Campus Administrator of CvSU Bacoor is Ms. Menvyluz S. Macalalad. MBA She oversees the overall operations, academic services, and administrative functions of the campus, ensuring that students receive quality education and a supportive learning environment.<br>Under her leadership, the campus continues to improve its programs, facilities, and student services."
},


  {
   
    "patterns": [
      "Who is the research coordinator?",
      "Name of the campus research head",
      "Who handles research initiatives?",
      "Contact for research activities"
    ],
    "response": 
      "The current Research Coordinator of CvSU Bacoor is Mr.  Ronan M. Cajigal, MAEd. He is responsible for guiding the campus’ research initiatives, supporting faculty and student researchers, and ensuring that all research activities align with the university’s academic standards and goals.<br>Through his leadership, the research culture of the campus continues to grow and strengthen."
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
    "who is the department chairperson",
    "who is the chairperson",
    "department chairperson",
    "department head",
    "who is the department head",
    "who leads the academic department",
    "current department chair",
    "cvsu bacoor department chairperson",
    "who is the department chair",
    "department chair of cvsu bacoor",
    "head of academic department cvsu bacoor",
    "program chair cvsu bacoor",
    "cvsu bacoor program head",
    "who is the chair"
    ],
    "response": 
      "CvSU Bacoor has multiple department chairpersons. Please specify the department: Computer Studies, Criminology, Arts and Sciences, Management Studies, or Teacher Education."
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
      "The current president of Cavite State University is Dr. Ma. Agnes P. Nuestro. She officially became the fourth university president in 2025. As the current leader of the university, she continues to guide CvSU in providing quality education, promoting research and innovation, and supporting the growth and welfare of students, faculty, and staff.<br>Her administration focuses on maintaining academic excellence, strengthening community engagement, and preparing students to become globally competitive professionals and responsible citizens."
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
" for Secondary Education major in Mathematics?",
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
" for Secondary Education major in English?",
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
" of the Instructional Materials Development Unit?",
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
" for student misdemeanor cases?",
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
" of Student Development Services?",
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
"who handles student program",
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
},
{

"patterns": [
"Who is the MIS coordinator?",
"Who manages the Management Information System?",
"Who handles MIS concerns?",
"Who is responsible for the MIS office?",
"Can you tell me the MIS coordinator?"
],
"response": 
"The Coordinator of the Management Information System (MIS) is Danilo C. Borreros."
},
{

"patterns": [
"Who is the campus canvasser?",
"Who handles canvassing for procurement?",
"Who works as the campus canvasser?",
"Who assists the Procurement Office with canvassing?",
"Can you tell me the campus canvasser?"
],
"response": 
"The Campus Canvasser of the Procurement Office is Jayson L. Gorospe."
},
{

"patterns": [
"Who is the Cash and Disbursement Officer?",
"Who handles cash disbursements?",
"Who manages cash transactions?",
"Who is responsible for disbursement services?",
"Can you tell me the Cash and Disbursement Officer?"
],
"response": 
"The Cash and Disbursement Officer is Sherryl Anne R. Saliba."
},
{

"patterns": [
"Who is in charge of Special Projects?",
"Who handles special projects?",
"Who manages special project activities?",
"Who is responsible for special projects?",
"Can you tell me who is in charge of Special Projects?"
],
"response": 
"Ma. Christie B. Taco is in charge of Special Projects."
},
{

"patterns": [
"Who is in charge of the Supply Office?",
"Who manages the Supply Office?",
"Who handles supply concerns?",
"Who is responsible for supply management?",
"Can you tell me who is in charge of the Supply Office?"
],
"response": 
"Gilbert E. Magano is in charge of the Supply Office."
},
{

"patterns": [
"Who is the campus inspector?",
"Who conducts campus inspections?",
"Who is responsible for inspection activities?",
"Who handles campus inspection concerns?",
"Can you tell me the campus inspector?"
],
"response": 
"The Campus Inspector is Gilbert E. Magano."
},
{

"patterns": [
"Who is the campus liaison officer?",
"Who handles liaison activities?",
"Who serves as the campus driver?",
"Who is responsible for liaison services?",
"Can you tell me the campus liaison officer?"
],
"response": 
"The Campus Liaison Officer and Driver is Dante R. Español."
},
{

"patterns": [
"Who is the Vice President for Academic Affairs?",
"Who oversees academic affairs?",
"Who manages academic programs at the university?",
"Who is responsible for academic affairs?",
"Can you tell me the Vice President for Academic Affairs?"
],
"response": 
"The Vice President for Academic Affairs is Cristina M. Signo."
},

{
 
  "patterns": [
    "Are organizations open to all students?",
    "Do student organizations charge fees?",
    "What are the benefits of joining organizations?",
    "What student organizations are available?",
    "List of student organizations",
    "Recognized student organizations",
    "What organizations can I join?",
    "Student clubs in CvSU Bacoor",
    "List all organizations",
    "What are student organizations?",
    "Available organizations",
    "What are the campus organizations?",
    "Student organizations in CvSU Bacoor",
    "Organizations and clubs",
    "what are student org",
    "student org",
    "Are there student organizations in CvSU?",
    "Can I join a student organization?",
    "Student clubs and organizations",
    "How can I join a campus organization?",
    "What clubs can I join?",
    "Are there student organizations in the university?",
    "Can you list student organizations?",
    "What extracurricular organizations are available?",
    "What student groups exist in CvSU?",
    "What organizations are recognized by the university?",
    "Do you have academic organizations?",
    "Are there leadership organizations in CvSU?",
    "What campus clubs are available?",
    "Tell me about student organizations",
    "What are the active student organizations?",
    "What groups can students join?",
    "Are there any university clubs?",
    "Can freshmen join organizations?",
    "What extracurricular activities are offered?"
  ],
  "response": 
    "CvSU Bacoor offers various recognized student organizations. Students may join organizations during recruitment periods, and membership requirements vary by organization. Joining organizations helps develop leadership, networking, and academic skills.<br><br>The recognized student organizations for A.Y. 2025-2026 are:<br><br>ACADEMIC ORGANIZATIONS<br>• Le Managers Societè<br>• IT Society<br>• Alliance of Computer Scientists<br>• HM Society<br>• La Ciencia de Crimines Sociedad<br>• Teacher Education Society<br>• La Liga Psicologia<br>• Societas Humana Resource<br><br>NON-ACADEMIC ORGANIZATIONS<br>• Education, Sports Promotion and Anti-Delinquency Association (ESPADA)<br>• COMSELEC<br><br>PERFORMING ARTS ORGANIZATIONS<br>• ConAces Dance Tribe<br>• CvSU-Bacoor Teatrong Padayon<br>• Harmonic Voices Chorale<br><br>RELIGIOUS STUDENT ORGANIZATION<br>• Christian Brotherhood International<br><br>STUDENT COUNCIL<br>• Central Student Government<br><br>STUDENT PUBLICATION<br>• The Cornerstone<br><br>Students may inquire with the Office of Student Affairs and Services (OSAS) for additional information regarding membership, activities, and recruitment schedules. For information about a specific organization, you may ask for its adviser, activities, or purpose."
  },
{

  "patterns": [
    "Who are the organization advisers?",
    "List all organization advisers",
    "Student organization advisers",
    "Who advises the student organizations?",
    "Organization adviser list"
  ],
  "response": 
    "The advisers of recognized student organizations are:<br><br>• Le Managers Societè — Janice A. Nealega<br>• IT Society — Jovelyn D. Ocampo<br>• Alliance of Computer Scientists — Steffanie M. Bato<br>• HM Society — Ryan S. Acojedo<br>• La Ciencia de Crimines Sociedad — Michael John C. Sullano<br>• Teacher Education Society — Jolina Razell M. Mindoro<br>• La Liga Psicologia — Kathy J. Gumboc<br>• Societas Humana Resource — Janice A. Nealega<br>• ESPADA — James E. Dalis<br>• COMSELEC — Kathy J. Gumboc<br>• ConAces Dance Tribe — Ana Rose M. Rupido<br>• CvSU-Bacoor Teatrong Padayon — Steffanie M. Bato<br>• Harmonic Voices Chorale — Zannie I. Gamuyao<br>• Christian Brotherhood International — Donnalyn B. Montallana<br>• Central Student Government — Zannie I. Gamuyao<br>• The Cornerstone — Jolina Razell M. Mindoro"
  },

{

  "patterns": [
    "What are the academic organizations?",
    "List academic student organizations",
    "What academic clubs are available?",
    "What organizations can I join for my program?",
    "Show me the academic organizations"
  ],
  "response": 
    "The recognized academic organizations are Le Managers Societe, IT Society, Alliance of Computer Scientists, HM Society, La Ciencia de Crimines Sociedad, Teacher Education Society, La Liga Psicologia, and Societas Humana Resource."
  },
{
 
  "patterns": [
    "What student organizations are available?",
    "List all student organizations",
    "What organizations can students join?",
    "Show all recognized student organizations",
    "What clubs are recognized by the campus?"
  ],
  "response": 
    "CvSU Bacoor recognizes academic organizations, non-academic organizations, performing arts organizations, religious organizations, the Central Student Government, and the student publication."
  },

{

"patterns": [
"What is IT Society?",
"What does IT Society do?",
"Tell me about IT Society.",
"What is the purpose of IT Society?",
"What activities does IT Society conduct?"
],
"response": 
"IT Society is the recognized academic organization for Information Technology students. It promotes technological skills, professional development, leadership, collaboration, and participation in IT-related activities and events."
},
{

"patterns": [
"What is Alliance of Computer Scientists?",
"Tell me about ACS.",
"What does ACS do?",
"What is the purpose of Alliance of Computer Scientists?",
"What activities does ACS conduct?"
],
"response": 
"Alliance of Computer Scientists is the recognized academic organization for Computer Science students. It supports learning, innovation, programming, research, and professional growth through various academic and technology-related activities."
},
{

"patterns": [
"What is HM Society?",
"Tell me about HM Society.",
"What does HM Society do?",
"What is the purpose of HM Society?",
"What activities does HM Society conduct?"
],
"response": 
"HM Society is the recognized academic organization for Hospitality Management students. It promotes hospitality excellence, leadership, professionalism, and practical learning experiences through various hospitality-related activities and programs."
},
{

"patterns": [
"What is Teacher Education Society?",
"Tell me about Teacher Education Society.",
"What does TES do?",
"What is the purpose of Teacher Education Society?",
"What activities does Teacher Education Society conduct?"
],
"response": 
"Teacher Education Society is the recognized academic organization for education students. It supports professional growth, teaching excellence, leadership development, and participation in educational programs and community activities."
},
{
"patterns": [
"What is the Central Student Government?",
"Tell me about CSG.",
"What does the student government do?",
"What is the purpose of CSG?",
"What are the responsibilities of CSG?"
],
"response": 
"The Central Student Government (CSG) is the official student governing body that represents the interests and welfare of students, organizes campus activities, and serves as a bridge between the student body and university administration."
},



  {
   
    "patterns": [
      "When is wash day in CvSU Bacoor?",
      "What are the wash days?",
      "Schedule for wearing civilian clothes",
      "What days can we wear non-uniform?"
    ],
    "response": 
      "At Cavite State University – CvSU Bacoor, the designated wash days are Wednesday and Saturday.<br>On these days, students are allowed to wear civilian clothes instead of the regular school uniform.<br>However, students are still expected to wear decent and appropriate clothing that follows the university’s dress code and campus regulations."
},
  {
    "patterns": [
      "When is uniform day in CvSU Bacoor?",
      "What days are we required to wear uniform?",
      "Schedule of uniform days",
      "Uniform policy schedule"
    ],
    "response": 
      "At Cavite State University – CvSU Bacoor, the official uniform days are Monday, Tuesday, Thursday, and Friday.<br>During these days, students are expected to wear their complete and proper school uniform while attending classes and entering the campus.<br>Wearing the prescribed uniform helps promote discipline, professionalism, and unity among students."
},
  {
   
    "patterns": [
      "What is the dress code in CvSU?",
      "Proper attire in campus",
      "What should I wear to school?",
      "Dress code policy"
    ],
    "response": 
      "The dress code in Cavite State University – CvSU Bacoor requires students to wear their proper school uniform during uniform days.<br>Students usually wear the official yellowish CvSU uniform paired with black pants, along with black shoes.<br>Wearing the proper uniform helps maintain discipline, professionalism, and proper student identification inside the campus.<br>Students are also encouraged to follow the university’s guidelines regarding proper grooming and appropriate attire at all times."
},
  {
   
    "patterns": [
      "What courses are offered in CvSU Bacoor?",
      "List of undergraduate programs",
      "What degrees are available here?",
      "Programs offered"
    ],
    "response": 
      "Cavite State University – CvSU Bacoor offers several undergraduate programs for students pursuing different career paths:<br>*Bachelor of Secondary Education (BSEd)<br>*Bachelor of Science in Business Management (BSBM)<br>*Bachelor of Science in Computer Science (BSCS)<br>*Bachelor of Science in Criminology (BSCrim)<br>*Bachelor of Science in Hospitality Management (BSHM), formerly known as BS Hotel and Restaurant Management (BSHRM)<br>*Bachelor of Science in Information Technology (BSIT)<br>*Bachelor of Science in Psychology (BSPsych)<br><br>These programs are designed to help students gain knowledge, practical skills, and professional experience needed <br>for their future careers and chosen industries."
},
  {
    
    "patterns": [
      "What is the official logo of CvSU?",
      "Meaning of the CvSU logo",
      "What do the colors in the logo mean?",
      "Describe the university logo"
    ],
    "response": 
      "The official logo of Cavite State University mainly features the colors green, gold, white, and yellow.<br>The green color represents growth, life, and progress, while gold and yellow symbolize excellence, honor, and quality education.<br>The logo also contains important symbols related to knowledge, leadership, and service which reflect the mission and vision of the university.<br>The CvSU logo serves as the official identity of the institution and represents pride, unity, and academic excellence among students, faculty, and alumni."
},
  {
   
    "patterns": [
      "What are the core values of CvSU?",
      "CvSU core values",
      "What principles does the university follow?",
      "University values"
    ],
    "response": 
      "The core values of Cavite State University are Truth, Integrity, Excellence, and Service.<br>These values guide the students, faculty, and staff in their academic and personal lives.<br>Truth encourages honesty and transparency, Integrity promotes strong moral principles and accountability, Excellence inspires everyone to give their best in all aspects of learning and service, while Service emphasizes helping the community and contributing positively to society.<br>These core values are expected to be practiced by every CvSU student and employee both inside and outside the university."
},
  {
   
    "patterns": [
      "What type of institution is CvSU Bacoor?",
      "Is CvSU a public or private school?",
      "Information about CvSU Bacoor",
      "What kind of university is CvSU?"
    ],
    "response": 
      "Cavite State University – CvSU Bacoor is a public state university and one of the satellite campuses of Cavite State University.<br>It provides affordable and quality higher education for students in Bacoor and nearby areas.<br>The campus offers different undergraduate programs focused on academic excellence, professional development, and community service.<br>CvSU Bacoor aims to produce competent, responsible, and globally competitive graduates through quality instruction and student-centered learning."
},
  {
  
    "patterns": [
      "What happens if I cannot complete my OJT hours?",
      "Failing to finish OJT",
      "Incomplete OJT hours penalty",
      "What if I lack internship hours?"
    ],
    "response": 
      "Failure to complete the required hours or violating company guidelines may result in an incomplete or failing grade. Students must repeat their OJT the next semester to graduate."
},
  {
 
    "patterns": [
      "Is online OJT allowed?",
      "Can we do work from home internship?",
      "Are remote OJTs accepted?",
      "Online internship policy"
    ],
    "response": 
      "No.<br>Cavite State University – CvSU Bacoor no longer accepts or provides online OJT.<br>All students are required to complete their On-the-Job Training (OJT) in an on-site or face-to-face setup.<br>This means you must be physically present and deployed to an approved partner company or institution to complete the required training hours, as online or remote OJT arrangements are not permitted anymore."
},
{
 
  "patterns": [
    "What is OJT",
    "What is internship",
    "How does on-the-job training work",
    "Do students need internship",
    "Explain OJT requirements"
  ],
  "response": 
    "On-the-Job Training (OJT) or internship is a supervised learning experience that allows students to apply classroom knowledge in an actual work environment.<br><br>Students assigned to OJT must comply with the requirements established by their academic program, host institution, and the University."
  },
  {
    
    "patterns": [
    "What are the requirements for OJT?",
    "What documents are required for OJT?",
    "What should I submit for OJT?",
    "Documents needed for OJT",
    "What do I need to prepare for OJT?",
    "What are the internship requirements?",
    "What are the practicum requirements?",
    "What do I need before taking OJT?",
    "Requirements before starting OJT",
    "What are the official OJT requirements?",
    "What are the requirements before deployment?",
    "What are the requirements to be deployed for OJT?",
    "What is the complete list of OJT requirements?"
    ],
    "response": 
      "To complete your OJT requirements, you will need to prepare the following documents:<br><br>Updated Resume<br>Endorsement Letter from Department<br>Parent’s Consent<br>MOA (Memorandum of Agreement) with the company<br>Medical Certificate (if required by the company)<br>School ID &amp;<br>Registration Form<br>Good Moral Certificate (if needed)<br><br>All documents must be processed in the department office.<br>Note: Online OJT is no longer accepted."
},
  {
  
    "patterns": [
      "How can I get a COR?",
      "Where do I claim my Certificate of Registration?",
      "Steps to get my COR",
      "Getting a copy of COR"
    ],
    "response": 
      "Students can obtain a COR after completing enrollment through the registrar’s office or online student portal. Some campuses require <br>clearance or payment confirmation first."
},
{
  "patterns": [
    "What is COR?",
    "How do I get a COR?",
    "What is COG?",
    "Meaning of COG",
    "What does COG stand for?",
    "Explain COG",
    "COG definition",
    "How can I request my grades?",
    "Can COR be used as proof of enrollment?",
     "What is the COR used for?",
      "Why do I need a COR?",
      "Purpose of Certificate of Registration",
      "Where is the COR required?"
  ],
  "response": [
    "COR stands for Certificate of Registration and serves as proof of enrollment. It contains the subjects you are enrolled in, your schedule, section, and other enrollment details for the current semester.<br><br>COG stands for Certificate of Grades. It is an official record of your academic performance and contains the grades you received for a specific semester, term, or school year. It is commonly requested for scholarships, applications, transferring to another school, and other academic purposes.<br><br>Both COR and COG may be requested through the Registrar's Office or other authorized student services."
  ]
},
  {
  
    "patterns": [
      "What is wash day?",
      "Wash day rules",
      "Can I wear civilian clothes on wash day?",
      "What to wear during wash day?"
    ],
    "response": 
      "At Cavite State University – CvSU Bacoor, students are allowed to wear civilian clothes during wash days.<br>The designated wash days are Wednesday and Saturday, so you don’t need to wear your school uniform on those days.<br>However, make sure your outfit is still decent and follows the campus dress code guidelines."
},
  {
   
    "patterns": [
      "Does attendance guarantee passing?",
      "How many absences are allowed?",
      "Attendance policy to pass a subject",
      "What happens if I have too many absences?"
    ],
    "response": 
      "Pupils/Students are required to attend their classes and campus events promptly and regularly.<br>Attendance alone does not guarantee passing; students must also complete and pass the projects, activities, and requirements given by the instructor.<br>If a university student accumulates absences equivalent to 20% or more of the total class hours without an excusable reason, they may be dropped from the roll.<br>Additionally, if a student’s academic performance is poor, they may receive a failing grade of 5.0."
},
  {
 
  "patterns": [
    "What is the minimum and maximum academic load per semester",
    "How many units can I take per semester",
    "What is the allowed academic load",
    "Minimum academic units",
    "Maximum academic units"
  ],
  "response": 
    "The number of academic units a student may enroll in depends on the curriculum year and academic standing.<br><br>Typically, students may enroll between 18 and 24 units per semester.<br><br>Students in good academic standing generally take the standard curriculum load, while students with academic deficiencies may be assigned a lighter load.<br><br>Graduating students may be allowed to take an overload of units if they meet the necessary requirements and receive approval from the appropriate academic authorities.<br><br>Students are encouraged to consult their academic adviser or program coordinator before enrollment."
  },
  {
    "patterns": [
      "What is program accreditation?",
      "AACCUP accreditation in CvSU",
      "Are the programs accredited?",
      "Accreditation of degree courses"
    ],
    "response": 
      "The university shall as much as possible, submit all programs for accreditation particularly by Accrediting Agency of Chartered Colleges and Universities in the Philippines (AACCUP) or any accrediting agency prescribed by CHED and the Philippine Association of State Universities and Colleges"
},
  {
   
    "patterns": [
      "Who can suspend classes?",
      "When are classes suspended?",
      "Rules on class suspension",
      "Class suspension authority"
    ],
    "response": 
      "At CvSU, the University President who has final authority to suspend classes throughout the University including all units or branches.<br>The university president may suspend classes in specific units or campuses for specified periods of units.<br>Suspension of classes does not mean that faculty and employee will not report for duty<br><br>but in emergencies such as typhoons or floods, class suspension may also follow alerts from PAGASA or official orders from the city mayor."
},
  {
    
    "patterns": [
      "What college program can I take based on my SHS strand?",
      "Courses for STEM students",
      "Courses for ABM students",
      "Which degrees fit my senior high strand?"
    ],
    "response": 
      "At Cavite State University, the college program you can take usually depends on your SHS strand.<br>If you are from the STEM strand, you can pursue programs like BS Computer Science, BS Information Technology, BS Information Systems, various Engineering courses such as Civil or Electrical Engineering, as well as BS Biology, BS Mathematics, and BS Psychology.<br>If your strand is ABM, you can take business-related courses such as BS Accountancy, BS Business Administration with majors like Marketing or Financial Management, BS Entrepreneurship, and BS Management Accounting.<br>For HUMSS students, suitable programs include BA Communication or Journalism, BS Psychology, BA Political Science, and BA English Language Studies.<br>If you are from the GAS strand, you have more flexibility and can choose programs from different fields like Education, Business, IT, or Psychology depending on your interest.<br>For TVL students, you can take more skill-based and technical programs such as BS Industrial Technology, BS Hospitality Management, BS Tourism Management, or other related courses aligned with your specialization.<br>Keep in mind that some programs may require additional requirements like entrance exams or bridging subjects, and availability may vary depending on the CvSU campus."
},
  
  {
    
    "patterns": [
      "What is the grading system?",
      "How are grades calculated?",
      "CvSU grading scale",
      "What does a grade of 1.00 mean?"
    ],
    "response": 
    "The University adopts a numerical grading system from 1.00 to 5.00, where 1.00 is the highest grade and 5.00 is a failing grade.<br><br>Grade Equivalents:<br>1.00 - Excellent (Highest Grade)<br>1.50 - Very Good<br>2.00 - Good<br>2.50 - Satisfactory<br>3.00 - Passing Grade<br>4.00 - Conditional Grade. This must be removed through a removal examination to obtain a grade of 3.00 or become 5.00.<br>INC - Incomplete. The student is passing but has not completed other course requirements.<br>5.00 - Failed.<br><br>Each college may establish its own grading procedures and weight distributions for examinations, laboratory work, and other requirements, subject to review and approval by the Vice President for Academic Affairs."
  },
  {
   
    "patterns": [
      "Who are you?",
      "What is your identity?",
      "Are you a stingray?",
      "What is Sting?"
    ],
    "response": 
      "You are not other animals from other satellite school, you are STING a Stingray represent the soul, the body, the spirit, and the mind of Cavite State University Bacoor City Campus."
},
  {
    
    "patterns": [
      "What is the CvSU website?",
      "Official Bacoor campus website URL",
      "Where can I find announcements online?",
      "Website link of CvSU Bacoor",
      "cvsu website",
      "cavite state university website"
    ],
    "response": 
      "https://cvsu.edu.ph/bacoor/<br><br>can access important announcements, events, and downloads."
},
  {
  
    "patterns": [
      "What is the campus Facebook page?",
      "CvSU Bacoor FB page link",
      "Where is the official Facebook account?",
      "Do you have a Facebook page?",
      "cvsu bacoor facebook",
      "cvsu bacoor page",
      "cavite state university facebook"
    ],
    "response": 
      "https://www.facebook.com/CvSUBacoorCityCampus"
},
  {
  
    "patterns": [
      "What is the campus YouTube channel?",
      "CvSU Bacoor YouTube link",
      "Does the school have a YouTube account?",
      "Official YouTube channel"
    ],
    "response": 
      "https://www.youtube.com/channel/UCM7bcOjhtVVbBXMlS2ZwIxA"
},
{

"patterns": [
"Important links",
"Useful links",
"Official links",
"Website links",
"CvSU Bacoor links",
"Online services",
"Official resources",
"Where can I find official information?",
"Student resources",
"Campus links"
],
"response": 
"Here are the official online resources of CvSU Bacoor:<br><br>🌐 Official CvSU Bacoor Website<br>https://cvsu.edu.ph/bacoor/<br><br>👥 Campus Officials<br>https://cvsu.edu.ph/bacoor-campus-officials/<br><br>📄 Downloadable Forms<br>https://cvsu.edu.ph/downloadable-forms/<br><br>📞 Contact Information<br>https://cvsu.edu.ph/contact-us/<br><br>💻 CvSU e-Learning Portal<br>https://elearning.cvsu.edu.ph/<br><br>🏛️ CvSU Main Website<br>https://cvsu.edu.ph/<br><br>🎥 CvSU Bacoor Virtual Tour<br>https://[www.youtube.com/watch?v=bzDx6Q9KUOc<br><br>📚](http://www.youtube.com/watch?v=bzDx6Q9KUOc<br><br>📚) Academic Programs and Campus Information<br>https://cvsu.edu.ph/bacoor/<br><br>If you are looking for a specific service such as admissions, enrollment, forms, courses, student organizations, scholarships, or contact information, feel free to ask."
},
{

  "patterns": [
    "I need a link",
    "Where can I find it?",
    "Website resources",
    "Official website",
    "Useful websites",
    "Online services"
  ],
  "response": 
    "What information are you looking for?<br><br>• Admissions<br>• Enrollment<br>• Student Organizations<br>• Courses Offered<br>• Downloadable Forms<br>• Campus Officials<br>• Contact Information<br>• e-Learning Portal<br>• Virtual Tour<br><br>I can provide the appropriate official link for any of these services."
  },
  
{
 
  "patterns": [
    "Student portal",
    "Portal link",
    "Login portal",
    "Access my portal",
    "Student account",
    "Portal website"
  ],
  "response": 
    "You may access the CvSU Bacoor Student Portal here:<br>https://studentportal.cvsu-bacoor.com/<br><br>If you are a new student, register through:<br>https://studentportal.cvsu-bacoor.com/sign-up"
  },
{
  
  "patterns": [
    "Download forms",
    "Student forms",
    "Registrar forms",
    "Pre-registration form",
    "Add drop form",
    "Download documents"
  ],
  "response": 
    "Official CvSU downloadable forms can be accessed here:<br>https://cvsu.edu.ph/downloadable-forms/"
  },
{
 
  "patterns": [
    "Virtual tour",
    "Campus tour",
    "Show me the campus",
    "Campus video",
    "Explore the campus"
  ],
  "response": 
    "You can view the official CvSU Bacoor virtual tour on the campus website:<br>https://cvsu.edu.ph/bacoor/"
  },

{
 
  "patterns": [
    "What courses are offered?",
    "Can you give me the list of courses?",
    "What can I study here?",
    "Courses available in the campus",
    "What programs can I enroll in?",
    "What academic programs are available?",
    "What fields of study are offered?",
    "List of undergraduate courses",
    "Available programs in campus",
    "Degrees to choose from"
  ],
  "response": [
    "CvSU Bacoor offers a variety of undergraduate academic programs for students.<br><br>Available courses:<br>• Bachelor of Secondary Education (BSEd)<br>• BS Business Management (BSBM)<br>• BS Computer Science (BSCS)<br>• BS Criminology (BSCrim)<br>• BS Hospitality Management (BSHM) (formerly BS Hotel and Restaurant Management)<br>• BS Information Technology (BSIT)<br>• BS Psychology (BSPsych)<br><br>Students may choose from programs in Education, Business, Information Technology, Computer Science, Psychology, Criminology, and Hospitality Management."
  ]
},
  {
   
    "patterns": [
      "What are the eligibility conditions for honors?",
      "How to qualify for cum laude?",
      "Can I get honors with a 4.00 grade?",
      "Honors disqualification rules"
    ],
    "response": 
      "A grade of 4.00 (conditional) in any subject disqualifies a student from honors.<br>Students with failing grades or disciplinary records are also disqualified.<br>Transferees must have taken 75% of required units at CvSU and must not have received grades of 5.00 4.00 or below the minimum thresholds from their previous school."
},
  {
   
    "patterns": [
      "Who governs the university?",
      "What is the Board of Regents?",
      "Who makes major policies in CvSU?",
      "University governance structure",
      "how is the university governed",
      "university governed"
    ],
    "response": 
      "The University is governed by the Board of Regents (BOR) which serves as the approving authority for rules scholarships curriculum revisions major policies and other university-wide matters."
},
  {
   
    "patterns": [
      "What are the academic units of the university?",
      "List of branch campuses",
      "What colleges are in CvSU?",
      "Does CvSU have a Science High School?"
    ],
    "response": 
      "Major academic units include colleges offering degree and non-degree programs the Science High School (SHS) and the Graduate School-Open Learning College (GS-OLC) with branch campuses in Naic Rosario Cavite City Carmona Imus Trece Martires Silang Tanza and Bacoor."
},
  {
   
    "patterns": [
      "What is the definition of a university student?",
      "Who is considered a student of CvSU?",
      "University student classification",
      "Am I an official student?"
    ],
    "response": 
      "Those enrolled in and regularly attending graduate degree non-degree high school or any other level program of the University including those in the distance education program."
},
  {
  
    "patterns": [
      "What is a full-time student?",
      "Definition of full-time enrollment",
      "How many units make me a full-time student?",
      "Full load student meaning"
    ],
    "response": 
      "A full-time student is one who is registered for formal academic credit units and carries <br>the full load for a given semester under the curriculum in which they are enrolled including graduating students who may carry less than the full load to complete current semester requirements."
},
  {
   
    "patterns": [
      "What is a part-time student?",
      "Definition of part-time enrollment",
      "Am I a part-time student?",
      "Taking less than full load"
    ],
    "response": 
      "A part-time student is one who is registered for formal credits but carries less than the full load for a given semester."
},
  {
   
    "patterns": [
      "What is a student assistant?",
      "Requirements to be a student assistant",
      "Working hours for student assistants",
      "Maximum academic load for student assistant"
    ],
    "response": 
      "A student assistant is one who is employed on a full-time basis at the University rendering service of at least 100 hours a month with a maximum academic load of 18 units."
},
  {
    
    "patterns": [
      "Who handles foreign students?",
      "Foreign student definition",
      "Rules for international students",
      "Adviser for foreign students"
    ],
    "response": 
      "A University student who is not a citizen of the Philippines.<br>If there are more than five foreign students an adviser is designated for them.<br>If five or fewer the Dean of Student Affairs handles their advisorship."
},
  {
   
    "patterns": [
      "What is curricular classification?",
      "How do I know if I am a sophomore or junior?",
      "Classification of year level",
      "Determining curricular year"
    ],
    "response": 
      "Classification is based on the actual number of academic units completed as required for a particular curricular year (Freshman Sophomore Junior Senior) as determined by the University Registrar."
},
  
  {
   
    "patterns": [
      "How long is a scholarship valid?",
      "Scholarship renewal conditions",
      "Can I have two scholarships?",
      "Validity of financial aid"
    ],
    "response": 
      "A scholarship is valid for one semester only but is renewable for the succeeding semester if the student meets the prescribed conditions.<br>Students supported by another agency are not eligible for University scholarships."
},
  {
    
    "patterns": [
      "Who has the authority to suspend classes?",
      "Who decides class suspensions?",
      "Final authority on class cancellations",
      "Class suspension policy"
    ],
    "response": 
      "The University President has the final authority to suspend classes.<br>In the President's absence the next person in the hierarchy of command succession decides."
},
  {
   
    "patterns": [
      "What are the grounds for class suspension?",
      "Reasons to cancel classes",
      "Can a bomb threat suspend classes?",
      "Suspension due to force majeure"
    ],
    "response": 
      "Classes may be suspended due to typhoons earthquakes tsunamis fires epidemics bomb threats and other force majeure or fortuitous events.<br>Classes may also be suspended for pre-scheduled University convocations or special gatherings."
},
  {
  
    "patterns": [
      "What are the typhoon signal suspension rules?",
      "Is college suspended at Signal No. 2?",
      "What signal number suspends collegiate classes?",
      "Typhoon class cancellation rules"
    ],
    "response": 
      "Typhoon Signal No. 2 automatically suspends elementary classes.<br>Signal No. 3 suspends all levels including high school and collegiate.<br>The President may suspend classes even below Signal 3 if accompanied by unabated torrential rains causing heavy floods and/or landslides."
},
  {
   
    "patterns": [
      "What are the rules for earthquake suspension?",
      "Will classes be suspended after an earthquake?",
      "Earthquake intensity for class cancellation",
      "Post-earthquake suspension policy"
    ],
    "response": 
      "Classes are suspended for 24 hours when earthquake intensity reaches Level V or higher."
},
  {
   
    "patterns": [
      "Do faculty members report during class suspension?",
      "Are offices open when classes are suspended?",
      "Employee attendance during suspensions",
      "Faculty duty on cancelled classes"
    ],
    "response": 
      "Suspension of classes does not mean faculty and employees will not report for duty.<br>They are still required to report to work."
},
  {
   
    "patterns": [
      "How do I shift courses?",
      "Process for changing degree programs",
      "When is the deadline to shift?",
      "Forms needed for shifting"
    ],
    "response": 
      "Students must accomplish a prescribed form approved by the Dean of the College they wish to shift to not later than 10 working days before the start of the regular registration period.<br>A copy must be forwarded to the University Registrar's Office."
},
  {
   
    "patterns": [
      "What is the registration schedule?",
      "Fine for late registration",
      "How many days is late registration allowed?",
      "Can I register late for summer classes?"
    ],
    "response": 
      "Regular registration occurs as scheduled by the University Registrar.<br>Late registration is allowed within seven school days after the regular registration schedule with a fine of ₱100.00 regardless of the number of days delayed or units carried.<br>No late registration is allowed for summer."
},
  {

    "patterns": [
      "What is the normal academic load?",
      "Can graduating students take more units?",
      "Maximum units per semester",
      "Academic load regulations"
    ],
    "response": 
      "Normal academic load is the full load prescribed in the curriculum.<br>Graduating students may take up to 26 units in the last two semesters with a GPA of 2.50 or better certified by the University Registrar."
},
  {
   
    "patterns": [
      "How do I add a subject?",
      "Deadline for adding subjects",
      "Who needs to approve subject changes?",
      "Process for adding classes"
    ],
    "response": 
      "Adding or changing subjects must be done within three (3) weeks of regular classes with consent of the registration adviser and instructor and approved by the College Dean."
},
  {
   
    "patterns": [
      "How do I drop a subject?",
      "Deadline for dropping subjects",
      "Can I drop a class after midterms?",
      "Process for officially dropping"
    ],
    "response": 
      "Dropping subjects requires filing a prescribed form at the Office of the College Registrar within six weeks after the start of regular classes with consent of the instructor and Dean.<br>Dropping after the midterm examination is not allowed except due to illness or change of residence."
},
  {
   
    "patterns": [
      "What grade will I get if I drop a subject?",
      "Dropping after 75% of hours elapsed",
      "What happens if I stop attending without dropping?",
      "Unofficially dropped penalty"
    ],
    "response": 
      "The word Dropped is reflected if dropped before 75% of prescribed hours have elapsed.<br>If dropped after 75% a corresponding performance grade is given.<br>Students who stop attending without officially dropping may receive a grade of 5.00."
},
  {
    
    "patterns": [
      "What are the school fees?",
      "Which fees are refundable?",
      "Non-refundable university fees",
      "Breakdown of student fees"
    ],
    "response": 
      "Refundable fees include: tuition laboratory fee student resources fund student facilities development fund library fee college publication fee guidance fee SCUAA/athletic fee student handbook fee cultural fee and student publication fee.<br>Non-refundable fees include: identification card medical and dental registration insurance and mutual aid."
},
  {
   
    "patterns": [
      "Can I pay in installment?",
      "Installment payment schedule",
      "How much to pay during midterms?",
      "Payment terms for tuition"
    ],
    "response": 
      "Fees may be paid in installment: 50% upon registration 25% two weeks before midterm examination and 25% two weeks before the final examination."
},
  {
   
    "patterns": [
      "What is the refund policy?",
      "Can I get a refund if I withdraw?",
      "Deadline for tuition fee refund",
      "Where to file a refund request?"
    ],
    "response": 
      "Students who withdraw within three weeks or 15 school days from the start of regular classes shall be refunded in full except medical and dental fees.<br>No refund is given to those who withdraw after this period.<br>Refund requests must be filed at the Accounting Section within the refund period."
},
  {
   
    "patterns": [
      "What is the class attendance policy?",
      "Maximum allowable absences",
      "Penalty for exceeding absences limit",
      "Grade for poor attendance"
    ],
    "response": 
      "The maximum number of allowable absences is 20% of the total number of hours scheduled for the class.<br>If absences exceed 20% the student shall be dropped from the rolls.<br>If the majority of absences are unexcused and performance is poor the student receives a grade of 5.00."
},
  {
    
    "patterns": [
      "Are excused absences counted in the limit?",
      "How to get an excuse slip?",
      "Maximum hours for excused absences",
      "Process for consecutive absences"
    ],
    "response": 
      "Excused absences (not to exceed 10 lecture hours or 9 laboratory hours) count toward the 20% limit.<br>An excuse slip from the Office of Student Affairs is required upon return to class after at least two consecutive absences. <br><br>If a student's absences exceed this limit, the instructor or University administration may drop the student from the course.<br><br>Students who encounter unavoidable circumstances should immediately communicate with their instructors and provide any necessary supporting documentation"
},
  {
   
    "patterns": [
      "What are the rules for classroom conduct?",
      "Can a teacher kick me out of class?",
      "Rules on noise and discipline",
      "Classroom behavior policies"
    ],
    "response": 
      "Students must attend promptly and regularly refrain from making unnecessary noise and comply with all dress code ID and conduct rules.<br>A teacher may exclude a student for ungentlemanly conduct and must immediately report the action to the Dean."
},
  {
  
    "patterns": [
      "When do I wear the school uniform?",
      "Exceptions to wearing uniform",
      "Uniform policy guidelines",
      "Is uniform required every day?"
    ],
    "response": 
      "All students must wear the prescribed school uniform during school days except on designated wash day or declared field/special days."
},
  {
 
    "patterns": [
      "What is the ID card policy?",
      "Do I need to wear my ID?",
      "Entering campus without ID",
      "Rules on wearing identification cards"
    ],
    "response": 
      "ID cards shall be worn by students upon entry and whenever they are within University premises.<br>Students shall not be allowed to enter or use any facilities or services without an ID card."
},
  {
  
    "patterns": [
      "What is the mobile phone policy?",
      "Can I use my cellphone in class?",
      "Penalty for unauthorized phone use",
      "Rules on phones during lectures"
    ],
    "response": 
      "The University discourages bringing cellphones into classrooms.<br>Unauthorized use during class is a punishable offense — reprimand for the first offense and exclusion for subsequent offenses."
},
  {
  
    "patterns": [
      "What are the types of examinations?",
      "What tests are conducted in CvSU?",
      "Special removal examinations",
      "Midterm and final exams"
    ],
    "response": 
      "Examinations conducted include regular class examinations midterm examinations final examinations and special removal examinations for grades of 4.00 and INC."
},
  {
 
    "patterns": [
      "How to apply for a special examination?",
      "Fee for special removal exam",
      "Process for missing an exam",
      "Steps to take a makeup test"
    ],
    "response": 
      "To apply for a special removal examination a student must file a request form from the University Registrar's Office addressed to the College Dean state the reason for missing the exam have it endorsed by the registration adviser and approved by the Dean then pay the special examination fee of ₱10.00 per unit."
},
  {
   
    "patterns": [
      "What does an Incomplete (INC) grade mean?",
      "Deadline to complete an INC grade",
      "What happens if I don't finish my INC?",
      "How to convert INC to a passing grade"
    ],
    "response": 
      "INC means Incomplete — the student <br>is passing but has not completed all course requirements. The student must complete the INC within one (1) year from when the grade was incurred or it is automatically converted to 5.00 by the University Registrar."
},
  {
   
    "patterns": [
      "What are considered minor offenses?",
      "Examples of minor disciplinary violations",
      "Is smoking on campus a minor offense?",
      "Penalties for littering and loitering"
    ],
    "response": 
      "Minor offenses include: non-wearing of ID/prescribed uniform use of another student's ID unauthorized cellphone use during class using a fictitious name smoking on campus cursing/derogatory remarks indecent acts littering loitering in corridors during class hours violations of traffic/posted signs and unauthorized raising of animals on campus."
},
  {
  
    "patterns": [
      "What are considered major offenses?",
      "Examples of severe disciplinary violations",
      "Is hacking a major offense?",
      "Rules against physical violence and drugs"
    ],
    "response": 
      "Major offenses include: fighting/physical violence possession/selling of regulated drugs or paraphernalia unauthorized possession or use of deadly weapons <br>hacking cheating in examinations plagiarism fabrication of data sexual assault serious/less serious/slight physical injury trespassing unauthorized assembly violation of curfew production of seditious/libelous materials and being accused in a criminal case."
},
  {
  
    "patterns": [
      "What counts as academic dishonesty?",
      "Plagiarism rules for graduating students",
      "Cheating and fabrication of data",
      "Consequences of stealing someone's work"
    ],
    "response": 
      "Academic dishonesty includes cheating in any test or examination plagiarism (copying lifting stealing or illegal use of another's work) and fabrication of data.<br>A graduating student found guilty of plagiarism will not be allowed to graduate."
},
  {
   
    "patterns": [
      "What is the penalty for cheating?",
      "First offense for cheating in an exam",
      "Subsequent cheating offenses",
      "Will I fail if I cheat?"
    ],
    "response": 
      "First offense: Disciplinary Sanction and a grade of 0 or no grade in the subject.<br>Subsequent offense: Exclusion for not more than one semester and a grade of 5 in the subject."
},
  {
  
    "patterns": [
      "Who handles disciplinary cases?",
      "What is the Board of Student Discipline?",
      "Role of the Committee on Misdemeanor",
      "Who chairs the disciplinary bodies?"
    ],
    "response": 
      "Two disciplinary bodies exist: (1) Committee on Misdemeanor handles offenses with penalties of exclusion for not more than one semester chaired by the Dean of Student Affairs.<br>(2) Board of Student Discipline handles offenses with penalties of exclusion for not less than one semester chaired by the Vice President for Administrative and Support Services."
},
  {
 
    "patterns": [
      "What is the disciplinary due process?",
      "Right to a hearing in disciplinary cases",
      "Appealing a suspension or expulsion decision",
      "How long do I have to answer a complaint?"
    ],
    "response": 
      "Students receive a copy of the complaint must file an answer within 72 hours are entitled to a hearing and may be represented by a counsel or representative.<br>Decisions can be appealed. Cases involving exclusion of more than one semester or expulsion are elevated to the University President whose decision is final 15 days after receipt."
},
  

  {
   
    "patterns": [
      "What are the qualifications to be an organization officer?",
      "Can I have failing grades if I am an officer?",
      "Holding positions in multiple organizations",
      "Rules for student leaders"
    ],
    "response": 
      "Officers must have no failing grades in any subject in the previous semester and while in office and must not have been involved in any disciplinary case.<br>A student may hold a major position (President or Vice President) in one organization and a minor position in another — maximum of two organizations."
},
  {
  
    "patterns": [
      "What are the financial rules for student organizations?",
      "Collecting membership fees",
      "Where should organizations open a bank account?",
      "Submitting financial reports to SOSCA"
    ],
    "response": 
      "Organizations may collect a reasonable semestral/annual membership fee covered by official receipts.<br>Organizations with funds exceeding ₱1000.00 must open a bank account at CvSU Cooperative Bank Inc. A financial report must be submitted to SOSCA within one week after each activity."
},
  {
  "patterns": [
    "What are the graduation requirements?",
    "Residence requirement for graduation",
    "Do I need to complete NSTP to graduate?",
    "Clearance of deficiencies for graduation",
    "What are the requirements for graduation",
    "How do I qualify for graduation",
    "Graduation requirements",
    "What do I need before graduating",
    "How can I graduate from CvSU",
    "Am I eligible for graduation?",
    "Who can graduate?",
    "Can I graduate this year?",
    "Graduation evaluation",
    "How do I apply for graduation?",
    "How to apply for graduation?",
    "When should I file my graduation application?",
    "How can I check if I am eligible to graduate?",
    "When is the tentative list of candidates published?",
    "Can I graduate with an INC grade?",
    "Who certifies graduation eligibility?"
  ],
  "response": 
    "To qualify for graduation, a student must successfully complete all academic, curricular, and institutional requirements prescribed by the University.\n\nRequirements generally include:\n- Completion of all required courses and academic units\n- Passing grades in all subjects\n- Completion of NSTP and other institutional requirements\n- Completion of practicum, internship, thesis, capstone, or other program requirements when applicable\n- Clearance of academic, financial, and administrative deficiencies\n- Settlement of all university obligations\n- Submission of all required graduation documents\n\nStudents who intend to graduate must submit an Application for Graduation form and complete all academic and administrative requirements before the prescribed deadline.\n\nThe College Dean submits the list of tentative candidates two weeks after second semester registration. The Registrar publishes the qualified list ten weeks before the end of the semester.\n\nThe University Registrar certifies graduation eligibility in consultation with the Deans concerned. Students with INC (Incomplete) grades cannot graduate.\n\nStudents must also undergo graduation evaluation to verify their eligibility. Only students who have satisfied all academic requirements and university obligations will be cleared for graduation.\n\nFor graduation assessment, application procedures, and confirmation of eligibility, students should coordinate with their Program Adviser, academic department, and the Registrar's Office."
},
  {
    
    "patterns": [
      "What are the academic honors awarded?",
      "GPA requirement for Summa Cum Laude",
      "GPA needed for Magna Cum Laude and Cum Laude",
      "Are NSTP grades included in honors evaluation?"
    ],
    "response": 
      "Academic honors awarded at graduation are: <br><br>Summa Cum Laude (GPA 1.00–1.21 no grade lower than 2.00) <br>Magna Cum Laude (GPA 1.22–1.45 no grade lower than 2.25) <br>and Cum Laude (GPA 1.46–1.75 no grade lower than 2.50).<br><br><br>NSTP grades are included in the evaluation."
},
  {

    "patterns": [
      "What is the residency requirement for honors?",
      "Time limit to complete degree for honors",
      "Exceptions to honors residency rules",
      "Can a working student still get academic honors?"
    ],
    "response": 
      "Candidates must complete all academic requirements within the prescribed period: 4 years for a 4-year course 5 years for a 5-year course 6 years for a 6-year course.<br>Exceptions may be granted for health reasons working students or force majeure with proper documentation."
},

  

{

"patterns": [
"When is the enrollment deadline?",
"What is the last day of enrollment?",
"Until when can I enroll?",
"When does enrollment end?"
],
"response": 
"Enrollment deadlines vary every semester and academic year. Please refer to the official announcements from CvSU Bacoor Campus or the Registrar's Office for the latest enrollment schedule. Students are encouraged to complete their enrollment before the deadline to avoid delays or additional requirements."
},

{

"patterns": [
"How can I check my enrollment status?",
"Am I already enrolled?",
"Can I verify my enrollment?",
"How do I know if my enrollment is approved?"
],
"response": 
"You may check your enrollment status through the official student portal or by contacting the Registrar's Office. Please prepare your student number for verification. If your enrollment is still being processed, kindly wait for further updates."
},

{

"patterns": [
"Can I still enroll after the deadline?",
"What is the process for late enrollment?",
"I missed the enrollment period, what should I do?",
"Is late enrollment allowed?"
],
"response": 
"Late enrollment may be permitted only under special circumstances and subject to approval by university authorities. Students requesting late enrollment may need to submit additional documents and secure approval from the appropriate offices. Please contact the Registrar's Office immediately for assistance."
},

{

"patterns": [
"What is cross enrollment?",
"Can I take subjects in another school?",
"How do I apply for cross enrollment?",
"Am I allowed to cross enroll?",
 "Can I enroll in another school while studying at CvSU",
    "How does cross enrollment work",
     "Explain cross enrollment"
],
"response": 
"Cross enrollment allows a student to take approved subjects in another institution while remaining enrolled at CvSU Bacoor Campus. Prior approval from the College Dean, Registrar, and other authorized officials is required before processing a cross-enrollment request."
},

{

"patterns": [
"Why can't I enroll in a subject?",
"What are subject prerequisites?",
"Do I need to complete another subject first?",
"Why is my subject enrollment restricted?"
],
"response": 
"Some courses require prerequisite subjects to be completed before enrollment is allowed. If you have not yet passed the required prerequisite course, the enrollment system may restrict your registration. Please consult your Program Adviser or Department Chairperson for assistance."
},

{

"patterns": [
"What does waitlisted mean?",
"Why am I waitlisted?",
"How do waitlisted subjects work?",
"Can I still get a slot if I am waitlisted?"
],
"response": 
"A waitlisted subject means that the section has reached its maximum capacity and you are currently waiting for an available slot. Additional slots may become available if enrolled students drop the course or if the department opens more slots. Please monitor official announcements for updates."
},

{

"patterns": [
"How can I change my section?",
"Can I transfer to another section?",
"What is the process for section changing?",
"How do I request a section change?"
],
"response": 
"Section changes may be requested during the designated adding, dropping, and changing period. Approval from the appropriate academic officials may be required, and requests are subject to slot availability in the preferred section."
},

{

"patterns": [
"How do I verify my enrollment?",
"How can I confirm that I am enrolled?",
"Where can I get proof of enrollment?",
"How do I know if my enrollment is official?"
],
"response": 
"You may verify your enrollment through your Certificate of Registration (COR), student portal, or official records from the Registrar's Office. If your enrolled subjects are reflected in your records and your registration has been approved, you are officially enrolled."
},



{
 
  "patterns": [
    "What are the requirements for the Dean's List?",
    "How can I qualify for the Dean's List?",
    "What grades do I need to be on the Dean's List?",
    "Am I eligible for the Dean's List?",
    "Who can become a Dean's Lister?",
    "What is the minimum GPA for the Dean's List?",
    "How do I become a Dean's Lister?",
    "Dean's List qualifications",
    "What GPA is needed for Dean's List?",
    "What are the qualifications for Dean's List?",
    "Can I qualify for the Dean's List?",
    "How do I know if I'm a Dean's Lister?",
    "What academic standing is required for Dean's List?",
    "What average do I need for Dean's List?",
    "How is Dean's List eligibility determined?",
    "Who is eligible for academic honors?",
    "What are the criteria for Dean's List?",
    "Can freshmen qualify for the Dean's List?",
    "How many units are required for Dean's List?",
    "Do I need a certain GPA to be a Dean's Lister?"
  ],
  "response": 
    "To qualify for the Dean's List, a student must meet the academic requirements established by the University and their respective college. Students are generally expected to maintain a high academic average, complete the prescribed academic load, and have no failing grades, incomplete grades, or disciplinary sanctions during the evaluation period. Specific qualifications may vary by college or academic unit. For the most accurate and updated requirements, please refer to the Student Handbook or consult your College Dean's Office."
  },

{

"patterns": [
"How are Latin honors computed?",
"What GPA is needed for Latin honors?",
"How do I qualify for Cum Laude?",
"What are the requirements for Magna Cum Laude?",
"Can I still qualify for Latin honors?",
"How is my General Weighted Average calculated for honors?"
],
"response": 
"Latin honors are awarded based on the student's General Weighted Average (GWA) and compliance with university policies. Eligibility may also depend on academic standing, residency requirements, and the absence of disqualifying grades or disciplinary records. Please consult the Student Handbook or Registrar's Office for the official guidelines."
},

{

"patterns": [
"What is academic probation?",
"Why was I placed on academic probation?",
"How can I remove my academic probation status?",
"What happens if I fail several subjects?",
"What are the consequences of academic probation?",
"How do I know if I am on probation?"
],
"response": 
"Academic probation is a status assigned to students whose academic performance falls below the university's required standard. Students under probation are encouraged to improve their academic standing and may be subject to certain enrollment conditions. Please consult your academic adviser or department for guidance regarding your status."
},

{

"patterns": [
"Where can I find the academic calendar?",
"What is the academic calendar?",
"When does the semester start?",
"When are the important school dates?",
"What are the university's academic schedules?",
"When does the current semester end?"
],
"response": 
"The Academic Calendar contains important dates such as enrollment periods, start and end of classes, examinations, holidays, and other academic activities. Students are advised to regularly check official university announcements for the latest academic calendar."
},

{

"patterns": [
"When are the examinations?",
"What is the examination schedule?",
"When is the midterm exam?",
"When is the final exam?",
"Where can I find the exam schedule?",
"What are the dates of our examinations?"
],
"response": 
"Examination schedules are released by the university and may vary depending on the academic calendar. Students should regularly check official announcements from their college, department, or instructors for the latest examination schedules."
},

{

"patterns": [
"Can I take a make-up examination?",
"What is the process for a make-up exam?",
"I missed my examination, what should I do?",
"Are make-up exams allowed?",
"How do I request a special examination?",
"Can I retake a missed exam?"
],
"response": 
"Make-up examinations may be granted under valid and documented circumstances, subject to approval by the instructor and university authorities. Students must submit the necessary supporting documents and follow the prescribed procedures to request a make-up examination."
},

{

"patterns": [
"What are special classes?",
"How can I request a special class?",
"Are special classes available?",
"Who qualifies for special classes?",
"Can I take a subject through a special class?",
"What is the procedure for opening a special class?"
],
"response": 
"Special classes may be offered to qualified students who need specific subjects to complete academic requirements. The availability of special classes depends on university policies, faculty availability, and approval from the concerned academic offices."
},

{

"patterns": [
"Are summer classes available?",
"What subjects are offered during summer?",
"How do I enroll in summer classes?",
"When is the summer term?",
"Can I take subjects during summer?",
"What are the requirements for summer enrollment?",
"Is there a summer semester at CvSU Bacoor?",
 "Does CvSU offer summer classes",
    "Are summer classes available",
    "Can I enroll during summer",
        "How do summer classes work"
],
"response": 
"Summer classes may be offered depending on university policies, student demand, and faculty availability. The list of available subjects, enrollment schedules, and requirements are announced before the start of the summer term. Students are encouraged to coordinate with their department for details."
},

{

"patterns": [
"How can I request my transcript of records?",
"How do I get my TOR?",
"How can i request a TOR",
"How do i request a TOR",
"What are the requirements for a transcript request?",
"Can I request my transcript online?",
"Where do I request my Transcript of Records?",
"How long does it take to process a transcript request?"
],
"response": 
"Students and alumni may request a Transcript of Records (TOR) through the Registrar's Office. Applicants may be required to submit a request form, valid identification, and other supporting documents. Processing time and applicable fees may vary depending on the nature of the request."
},

{

"patterns": [
"How can I claim my diploma?",
"When can I get my diploma?",
"Is my diploma ready for claiming?",
"What are the requirements for diploma claiming?",
"Where do I claim my diploma?",
"Can someone claim my diploma on my behalf?"
],
"response": 
"Graduates may claim their diploma from the Registrar's Office after completing all graduation requirements and clearance procedures. Please bring a valid ID and comply with any additional requirements specified by the university before claiming your diploma."
},

{

"patterns": [
"How do I request authentication of documents?",
"Can my school documents be authenticated?",
"What is the process for document authentication?",
"How can I get my records certified?",
"Where can I request authenticated documents?",
"Can I authenticate my TOR or diploma?"
],
"response": 
"Authentication requests for academic documents may be processed through the Registrar's Office. Students or alumni must submit the original or requested documents along with any required forms and fees. Processing procedures may vary depending on the document being authenticated."
},

{

  "patterns": [
    "How can I request my student records",
    "How do I get my academic records",
    "Where can I request school records",
    "How can I obtain my records",
    "What is the process for requesting records"
  ],
  "response": 
    "Students may request official academic records through the Registrar's Office.<br><br>Requested records may include transcripts, certificates, certifications, and other academic documents.<br><br>Applicants may be required to complete a request form, present valid identification, settle applicable fees, and comply with University requirements before records are released."
  },


{

"patterns": [
"How long does document processing take?",
"When will my requested document be released?",
"How many days does it take to process school documents?",
"What is the processing time for certificates?",
"How long will my TOR request take?",
"When can I claim my requested document?"
],
"response": 
"Document processing times vary depending on the type of document requested, the volume of requests being handled, and university procedures. For the most accurate processing timeline, please contact the Registrar's Office directly."
},

{

"patterns": [
"Can alumni request school records?",
"How do I access my alumni records?",
"I graduated years ago, can I still request documents?",
"How can alumni obtain academic records?",
"Can former students request records?",
"Where can alumni request school documents?"
],
"response": 
"Alumni may request academic records such as transcripts, certifications, and other official documents through the Registrar's Office. Valid identification and supporting documents may be required for verification purposes."
},

{

"patterns": [
"How do I get my clearance?",
"What is a student clearance?",
"What are the requirements for clearance?",
"How can I process my clearance?",
"Do I need a clearance before graduation?",
"Why is my clearance important?",
    "What is the purpose of student clearance",
    "Explain student clearance",
     "Why do I need clearance"


],
 "response": 
    "Student clearance is an official verification process confirming that a student has fulfilled academic, administrative, financial, and institutional obligations.<br><br>Clearance may be required for graduation, transfer, release of records, scholarship processing, and other official transactions.<br><br>Students must secure approval from the designated offices before their clearance can be considered complete."
  },

{

"patterns": [
"I lost my school ID.",
"What should I do if my ID is lost?",
"How do I report a lost student ID?",
"Can I still enter the campus without my ID?",
"What are the requirements for reporting a lost ID?",
"Who should I contact regarding my lost ID?",
"Lost ID"
],
"response": 
"Students who lose their school ID should immediately report the incident to the appropriate university office. Additional requirements such as an affidavit of loss, valid identification, or other supporting documents may be required depending on university policy."
},

{

"patterns": [
"How can I replace my school ID?",
"What are the requirements for ID replacement?",
"Can I request a new ID?",
"My ID is damaged, how do I replace it?",
"How much is the ID replacement fee?",
"Where do I apply for ID replacement?",
"Replacement of ID"
],
"response": 
"Students requesting a replacement ID may be required to submit the necessary documents and pay the applicable replacement fee. Requirements may vary depending on whether the ID was lost, stolen, or damaged. Please contact the designated university office for complete instructions."
},

{

"patterns": [
"How can I change my personal information?",
"How do I correct my name in the records?",
"Can I update my personal details?",
"How do I request correction of my records?",
"My birth date is incorrect, how can I update it?",
"What documents are needed to change personal information?"
],
"response": 
"Students who need to update or correct personal information in university records must submit a formal request along with supporting legal documents. Requests are subject to verification and approval by the Registrar's Office."
},

{

"patterns": [
"How can I access the campus WiFi?",
"What is the campus WiFi password?",
"Is there free WiFi on campus?",
"How do I connect to the university WiFi?",
"Can students use the campus internet?",
"Who can access the campus WiFi?",
    "What is the WiFi password?",
    "Why can't I connect to the WiFi?",
    "Can visitors use the WiFi?"
],
"response": 
"Students, faculty, and staff may access the campus WiFi subject to university policies. Connection procedures, login credentials, and access requirements are provided by the university's Information and Communications Technology Office. Please contact the ICT Office for assistance with connectivity concerns."
},

{

"patterns": [
"Where can I park on campus?",
"Are there parking spaces for students?",
"What are the campus parking rules?",
"Can visitors park inside the campus?",
"Do I need a parking permit?",
"What are the parking guidelines?"
],
"response": 
"Students, employees, and visitors are expected to follow campus parking regulations. Parking is only permitted in designated areas and may be subject to university policies. Please coordinate with the Security Office for parking-related concerns and updated guidelines."
},

{

  "patterns": [
    "Who handles campus security",
    "Campus security services",
    "How is campus safety maintained",
    "What should I do during emergencies",
    "Security personnel information",
    "How can I contact campus security?",
    "What should I do if I notice a security concern?",
    "Is there campus security available?",
    "Who handles security issues on campus?",
    "How do I report suspicious activity?",
    "What security services are available?"
  ],
  "response": 
    "The Campus Security Office is responsible for maintaining safety, order, and security within the university premises.<br><br>Campus security personnel assist students, employees, and visitors in emergencies, safety concerns, and security-related matters.<br><br>Students are encouraged to cooperate with security personnel and immediately report suspicious activities, emergencies, or any security concerns to the designated university office."
  },

{

"patterns": [
"What should I do during an emergency?",
"What are the university's emergency procedures?",
"How do I respond to a campus emergency?",
"What happens during an emergency situation?",
"Where can I find emergency guidelines?",
"What are the emergency response protocols?"
],
"response": 
"In case of an emergency, remain calm and follow the instructions of university officials, faculty members, and emergency responders. Students should familiarize themselves with evacuation routes, emergency exits, and campus safety procedures to ensure their safety."
},

{

"patterns": [
"What is the fire evacuation plan?",
"Where are the fire exits located?",
"What should I do during a fire emergency?",
"How do I evacuate during a fire drill?",
"Where is the evacuation area?",
"What are the fire safety procedures?"
],
"response": 
"During a fire emergency or drill, immediately proceed to the nearest designated exit and move to the assigned evacuation area. Follow instructions from university personnel and avoid using elevators if applicable. Students are encouraged to familiarize themselves with campus evacuation routes and fire safety procedures."
},

{

"patterns": [
"Is first aid available on campus?",
"Where can I get medical assistance?",
"What should I do if I get injured?",
"Does the university have a clinic?",
"Where is the first aid station?",
"Who can help during a medical emergency?"
],
"response": 
"Basic first aid and medical assistance may be available through the university clinic or designated health personnel. Students who require medical attention should immediately seek assistance from the clinic, faculty members, or campus security personnel."
},

{

"patterns": [
"Does the university provide mental health support?",
"Where can I get help for stress or anxiety?",
"Are there mental health programs for students?",
"How can I access mental health services?",
"Who can I talk to about personal struggles?",
"Is mental health assistance available on campus?"
],
"response": 
"The university supports student well-being through mental health programs, counseling services, and student support initiatives. Students experiencing emotional, psychological, or personal concerns are encouraged to seek assistance from the Guidance and Counseling Office."
},

{

"patterns": [
"How can I schedule a counseling session?",
"Does the university offer counseling services?",
"Can I talk to a counselor?",
"Where is the Guidance and Counseling Office?",
"Are counseling services confidential?",
"How do I get counseling support?"
],
"response": 
"The Guidance and Counseling Office provides counseling services to students for academic, personal, career, and emotional concerns. Students may contact the office directly to inquire about appointments, schedules, and available support services."
},

{

"patterns": [
"Where can I study on campus?",
"Are there designated study areas?",
"What are the best places to study in the university?",
"Can I use the library for studying?",
"Is there a quiet study area available?",
"Where can students review between classes?"
],
"response": 
"Students may use designated study areas such as the library, learning resource centers, and other approved academic spaces within the campus. Availability of study areas may vary depending on operating hours and university policies."
},

{

  "patterns": [
    "Where is CvSU Bacoor located?",
    "What is the address of CvSU Bacoor?",
    "How can I get to CvSU Bacoor?",
    "Where is Cavite State University Bacoor Campus?",
    "What is the exact location of CvSU Bacoor?",
    "Can you give me directions to CvSU Bacoor?",
    "What barangay is CvSU Bacoor in?",
    "Where can I find CvSU Bacoor Campus?"
  ],
  "response": 
    "Cavite State University - Bacoor Campus is located at Soldiers Hills IV, Molino VI, Bacoor City, Cavite, Philippines. The campus is accessible through major transportation routes within Bacoor City. For updated directions, transportation options, and campus maps, students and visitors may contact the campus administration or visit the university's official website."
  },

{

"patterns": [
"How much is the tuition fee in CvSU?",
"What is the tuition fee per semester?",
"How much do I need to pay for tuition?",
"What are the school fees in CvSU?",
"How much does it cost to study in CvSU?",
"Is CvSU expensive?"
],
"response": 
"Qualified undergraduate students of Cavite State University may avail of free tuition and other school fee subsidies under the Universal Access to Quality Tertiary Education Act (Republic Act No. 10931), subject to government and university policies. Additional fees may apply for certain services, documents, or special programs."
},

{

  "patterns": [
    "Is CvSU tuition free?",
    "Why is CvSU free?",
    "Do students pay tuition?",
    "What is RA 10931?",
    "Am I eligible for free tuition?",
    "Is tuition free in CvSU?",
    "Do students pay tuition fees?",
    "Is CvSU free?",
    "Can I study in CvSU for free?",
    "Does CvSU have free education?",
    "Who qualifies for free tuition?",
    "Does CvSU offer free tuition",
    "Is tuition free at CvSU",
    "What is the free tuition policy",
    "Is CvSU covered by free tuition"
  ],
  "response": 
    "Yes. Qualified undergraduate students enrolled at Cavite State University may enjoy free tuition and exemption from other mandatory fees under Republic Act No. 10931, also known as the Universal Access to Quality Tertiary Education Act.<br><br>This applies to qualified Filipino students pursuing their first bachelor's degree, subject to existing government and university regulations."
  },

{
  "patterns": [
    "How can I join a student organization?",
    "What is the procedure for joining a student organization?",
    "How do I become a member of a campus organization?",
    "What are the requirements for joining an organization?",
    "Can I join a student organization in CvSU Bacoor?"
    
  ],
  "response": 
    "🤝 Student Organization Membership Procedure<br><br><br><br>Students who wish to join a student organization may apply through accredited organizations during their recruitment activities.<br><br><br><br>Procedure:<br><br><br><br>* Watch for recruitment periods, organization fairs, and membership drives conducted by accredited student organizations.<br><br>* Choose the organization that matches your interests, skills, and academic goals.<br><br>* Inquire about the organization's membership requirements and application process.<br><br>* Complete and submit the required application forms and supporting documents, if applicable.<br><br>* Participate in interviews, orientations, screenings, or other membership activities required by the organization.<br><br>* Wait for the evaluation and approval of your application.<br><br>* Attend the organization's orientation and official activities upon acceptance.<br><br><br><br>Please note that membership requirements and application procedures may vary depending on the organization. For further information and assistance, students may coordinate with the Office of Student Affairs and Services (OSAS)."
},

{

  "patterns": [
    "What are the requirements for Latin Honors",
    "How can I graduate with honors",
    "What GPA is needed for Latin Honors",
    "How do I qualify for Cum Laude",
    "Requirements for academic honors"
  ],
  "response": 
    "Students may qualify for Latin Honors based on their final academic performance and compliance with University requirements.<br><br>Generally, students must:<br>- Meet the required General Weighted Average (GWA)<br>- Have no failing grades or unresolved academic deficiencies<br>- Complete the prescribed curriculum within the allowable period<br>- Satisfy all University graduation requirements<br><br>The specific GWA requirements for Cum Laude, Magna Cum Laude, and Summa Cum Laude are determined by University policies."
  },

{

"patterns": [
"Does CvSU have a library?",
"What services are available in the library?",
"Can I borrow books?",
"What are the library hours?",
"How do I access library resources?",
"Is the library open to students?",
    "What services does the library offer",
    "What can I do in the library",
    "Library services",
    "What resources are available in the library",
    "Can students use the library"
],
"response": 
"The university library provides access to books, journals, research materials, and other learning resources to support academic activities. Students may visit the library and follow its policies regarding borrowing, access, and resource utilization."
},
  {
  "patterns": [
    "What are the medical requirements?",
    "Medical requirements for enrollment",
    "What medical documents are needed?",
    "Medical clearance requirements",
    "Requirements for medical examination",
    "What do I need for the medical assessment?",
    "Medical requirements for admission",
    "What are the health requirements for enrollment?",
    "Medical exam requirements",
    "Medical requirements in CvSU Bacoor",
    "What should I bring for the medical examination?",
    "Requirements for medical clearance",
    "Documents needed for medical assessment",
    "What are the requirements for medical clearance?",
    "Medical assessment requirements",
    "Health requirements for enrollment",
    "Requirements before medical examination",
    "What should I prepare for my medical exam?",
    "Medical requirements please",
    "Required documents for medical clearance"
  ],
  "response": [
    "For the medical assessment and clearance, students are generally required to present their Medical Referral Slip, Notice of Admission (if applicable), and any other documents requested by the Campus Clinic. Additional laboratory tests or medical certificates may be required depending on the student's condition and the clinic's assessment. Please coordinate with the Campus Clinic for the complete and updated list of medical requirements."
  ]
},
{
  "patterns": [
    "Is X-ray enough?",
    "Is chest X-ray enough?",
    "Do I only need an X-ray?",
    "Is CBC enough?",
    "Is urinalysis enough?",
    "Do I only need a medical certificate?",
    "Do I need all medical requirements?",
    "Can I submit only my X-ray?",
    "Is one medical requirement enough?",
    "Do I need additional medical documents?",
    "Can I proceed with only my laboratory results?",
    "What if I only have an X-ray?"
  ],
  "response": [
    "The required medical documents depend on the guidelines of the Campus Clinic. A single document, such as a chest X-ray, may not be sufficient if other medical requirements are also requested. Please coordinate with the Campus Clinic to verify the complete list of required medical documents and examinations."
  ]
},
{

"patterns": [
"When is the medical assessment schedule?",
"When should I complete my medical examination?",
"What is the schedule for medical clearance?",
"What happens during medical assessment?",
"Medical clearance process",
"Health assessment requirements",
"How do I get medical clearance?",
"Do I need a medical examination before enrollment?",
"When is the health assessment schedule?"
],
"response": 
"As part of the enrollment process, qualified applicants are required to complete the Medical Requirements and Assessment before final registration.<br><br>The medical assessment may include submission of required medical documents, physical examination, health evaluation, and issuance of medical clearance by authorized medical personnel.<br><br>Medical Assessment Schedule:<br><br>June 29 – July 03, 2026<br>• BS Hospitality Management (BSHM)<br>• BS Business Administration (BSBA)<br>• BS Information Technology (BSIT)<br>• BS Computer Science (BSCS)<br><br>July 06 – July 10, 2026<br>• BS Criminology (BSCrim)<br>• BS Psychology (BSPsych)<br>• Bachelor of Secondary Education (BSEd)<br><br>Students must complete all medical requirements and obtain medical clearance before proceeding with final enrollment and registration. Please visit the campus clinic during the schedule assigned to your program."
},

{

"patterns": [
"How do I access the student portal?",
"What is the CvSU Bacoor student portal?",
"How can I log in to the student portal?",
"Where can I access my student portal account?",
"What are the login credentials for the student portal?"
],
"response": 
"The CvSU Bacoor Student Portal is the official digital platform designed to enhance student services and provide easier access to essential campus resources. It is accessible to all bona fide students of CvSU-Bacoor.<br><br>Student Portal Link:<br>https://studentportal.cvsu-bacoor.com<br><br>For Newly Registered Students:<br>Username: [StudentNumber]firstname<br>Example: 20252026juanmiguel<br>Password: The password you registered during account creation.<br><br>For Old Students (2nd–4th Year):<br>Username: [StudentNumber]firstname<br>Example: 20252026juanmiguel<br>Password: cvsubacoor[StudentNumber]<br>Example: cvsubacoor20252026<br><br>Students are encouraged to register and activate their accounts to avoid delays in the release of grades and to access important academic services."
},
{

"patterns": [
"What is the student portal link?",
"Where can I access the student portal?",
"Give me the student portal website.",
"What is the URL of the student portal?",
"How do I open the student portal?"
],
"response": 
"You can access the official CvSU Bacoor Student Portal through:<br>https://studentportal.cvsu-bacoor.com"
},
{

"patterns": [
"How do newly registered students log in to the student portal?",
"What are the credentials for new students?",
"How can first-year students access the student portal?",
"What is the username and password for newly registered students?",
"Student portal login for new students"
],
"response": 
"For newly registered students:<br><br>Username: [StudentNumber]firstname<br>Example: 20252026juanmiguel<br><br>Password: The password you registered during account creation."
},
{

"patterns": [
"How do old students log in to the student portal?",
"What are the credentials for 2nd year students?",
"What is the student portal password for old students?",
"How can returning students access the student portal?",
"Student portal login for old students"
],
"response": 
"For old students (2nd–4th Year):<br><br>Username: [StudentNumber]firstname<br>Example: 20252026juanmiguel<br><br>Password: cvsubacoor[StudentNumber]<br>Example: cvsubacoor20252026"
},

{
  "patterns": [
   "What is a second courser?",
    "another bachelor's degree",
    "graduate applying again"
  ],
  "response": 
    "A Second Courser is an applicant who has already completed a Bachelor's degree and wants to pursue another degree program."
  },
{

  "patterns": [
    "tcp applicant",
    "teacher certificate program",
    "tcp requirements"
  ],
  "response": 
    "TCP Applicants are graduates of any Bachelor's degree program who wish to take the required Education units for teaching."
  },

{
 
  "patterns": [
    "upload requirements",
    "scan documents",
    "document submission",
    "upload files"
  ],
  "response": 
    "Applicants must scan or take clear screenshots of their documentary requirements. Each file must be in JPEG, PNG, or BMP format and should not exceed the size limit required by the admission system."
  },
{

  "patterns": [
    "Is there an entrance exam for CvSU Bacoor",
    "Do I need to take an entrance exam",
    "Does CvSU require an entrance test",
    "Is admission based on an exam",
    "Are freshmen required to take an entrance examination"
  ],
  "response": 
    "Yes. CvSU Bacoor typically requires incoming freshmen and transferees to take an entrance examination as part of the admission process.<br><br>The examination is designed to assess academic readiness and generally covers subjects such as English, Mathematics, and Science. The exact coverage may vary depending on University policies and the academic year."
  },
{

  "patterns": [
    "What are important reminders before taking the entrance exam",
    "What should I bring to the entrance exam",
    "Entrance exam guidelines",
    "What do I need for the admission test",
    "Important entrance exam reminders"
  ],
  "response": 
    "Important reminders for examinees:<br><br>- Arrive at the testing venue at least 30 minutes before your scheduled examination time.<br>- Bring your examination permit, a valid ID, two pencils, and an eraser.<br>- Mobile phones, calculators, and other electronic devices are not allowed inside the examination room.<br>- Wear comfortable and appropriate attire that follows University dress code guidelines.<br>- Observe all applicable health and safety protocols.<br>- Verify your examination schedule and assigned testing location before the exam date.<br><br>Stay focused, remain confident, and do your best during the examination."
  },
{

  "patterns": [
    "Where can I take the CvSU entrance exam",
    "Where is the entrance exam conducted",
    "Can I take the exam at Bacoor campus",
    "Entrance exam location",
    "Where do I take the admission test"
  ],
  "response": 
    "Applicants may take the entrance examination at CvSU Bacoor Campus or at the Main Campus in Indang, depending on the examination schedule and assigned testing venue."
  },
{
 
  "patterns": [
    "exam permit",
    "print permit",
    "admission permit",
    "permit for examination"
  ],
  "response": 
    "Applicants must print their Exam Permit on bond paper and bring it on the examination day. Applicants without a physical copy of the permit will not be allowed to take the exam."
  },
{
 
  "patterns": [
    "requirements for exam",
    "requirements for examination",
    "what to bring during exam",
    "exam guidelines",
    "exam materials"
  ],
  "response": 
    "Bring your printed Exam Permit, a valid ID, a 1x1 ID picture, and two No. 2 pencils. Electronic devices such as calculators and cellphones are not allowed during the examination."
  },
{
 
  "patterns": [
    "reminders for examination",
    "important reminders before exam",
    "exam reminders",
    "entrance test info"
  ],
  "response": 
    "Arrive on time, wear appropriate attire, bring all required documents, and follow examination rules. The use of electronic devices is prohibited and may result in disqualification."
  },
{

  "patterns": [
    "exam results",
    "where can i see exam results",
    "admission result",
    "result of examination",
    "When will entrance exam results be released",
"How can I check my exam results",
"When are CvSU-CAT results available",
"How do I know if I passed",
"Entrance exam result release"
  ],
  "response": 
    "The results of the admission examination will be announced through the official CvSU Bacoor Guidance and Admission Services Facebook page."
  },
{
  "patterns": [
    "Can I retake the entrance exam",
    "Is retaking CvSU-CAT allowed",
    "May I take the admission test again",
    "Retake entrance examination",
    "Can I apply for another exam schedule",
    "What happens if I fail the entrance exam",
    "Can I still enroll if I fail",
    "What should I do if I do not pass CvSU-CAT",
    "Failed admission test"
  ],
  "response": [
    "Applicants who do not meet the required admission criteria may explore other available academic programs, apply during future admission periods if permitted, or inquire about alternative admission opportunities based on University policies.<br><br>Retaking the entrance examination is subject to University admission policies. Applicants should consult the Admissions Office regarding eligibility, available examination schedules, and other admission options."
  ]
},
{
 
  "patterns": [
    "When does the entrance exam usually take place",
    "What is the entrance exam schedule",
    "When is CvSU-CAT conducted",
    "When can I take the admission test",
    "Entrance exam dates"
  ],
  "response": 
    "Entrance examinations are typically conducted between February and June before the start of the academic year. Applicants should monitor official announcements for exact schedules."
  },
{
  
  "patterns": [
    "What subjects are included in the entrance exam",
    "What is the coverage of CvSU-CAT",
    "What topics are in the entrance exam",
    "Entrance exam subjects",
    "What should I review for the admission test"
  ],
  "response": 
    "The entrance examination generally covers English, Mathematics, Science, and General Information."
  },

{
  
  "patterns": [
    "What are the grade requirements for CvSU?",
    "What grade is required for BSCS?",
    "What grades do I need for BSIT?",
    "Are there grade requirements for Psychology?",
    "What grades are needed for Education?"
  ],
  "response": 
    "Grade requirements vary by program. BSCS and Education usually recommend grades of 85+ in relevant subjects. BSIT requires a matching SHS strand such as STEM or TVL-ICT. Other programs may evaluate your SHS report card and available slots."
  },
{
 
  "patterns": [
    "What is a unit load?",
    "What does unit load mean?",
    "How many units can I take?",
    "What is the normal unit load in CvSU?",
    "What is the maximum load allowed?"
  ],
  "response": 
    "Unit load refers to the total number of academic units a student enrolls in during a semester. Most students take 15 to 21 units per semester. Taking more than the normal load may require approval."
  },
{
 
  "patterns": [
    "How do I get a student ID?",
    "When will student IDs be released?",
    "I lost my student ID",
    "Can I use COR instead of an ID?",
    "Do I need to bring my ID every day?"
  ],
  "response": 
    "Student IDs are issued after enrollment and campus processing. Students should carry their IDs for identification and campus transactions. If your ID is lost, report it to the registrar and request a replacement."
  },
{
 
  "patterns": [
    "Is there a Student ID in CvSU Bacoor",
    "Do students have IDs",
    "Is there a student ID",
    "Can I get a student ID",
    "Are student IDs available"
  ],
  "response": 
    "Currently, many students do not yet have their student IDs because the University is still processing them. In the meantime, the Certificate of Registration (COR) is accepted as proof of enrollment."
  },
{
 
  "patterns": [
    "Why don't we have our Student IDs yet",
    "Why is my student ID delayed",
    "Why are student IDs not available yet",
    "Why haven't we received our IDs",
    "What caused the ID delay"
  ],
  "response": 
    "The University is still in the process of producing student IDs for all students. Delays may occur due to the large number of requests and processing requirements."
  },
{
  "patterns": [
    "Why don't we have IDs yet?",
    "When will IDs be released?",
    "Why is my ID delayed?",
    "Student ID release schedule",
    "ID availability",
    "When will the Student IDs be available",
    "When can I get my student ID",
    "When are student IDs ready",
    "What is the ID release schedule"
  ],
  "response": 
    "Student IDs are released after enrollment verification and administrative processing. The University will announce the release schedule once the student IDs are ready.<br><br>Students are advised to regularly check official announcements and updates from the Registrar's Office regarding ID availability and release dates."
  },
{

  "patterns": [
    "How can I get my Student ID",
    "How do I get my student ID",
    "What is the process for claiming my ID",
    "Where can I claim my student ID",
    "How is the student ID issued"
  ],
  "response": 
    "Student Identification Cards (IDs) are issued to enrolled students after they have successfully completed the enrollment process.<br><br>The distribution schedule and instructions are typically announced by the Registrar's Office through official University communication channels.<br><br>Students may be required to present proof of enrollment, such as a registration form or enrollment slip, along with any other required documents when claiming their ID.<br><br>Students should regularly monitor official announcements for updates regarding ID release schedules and claiming procedures."
  },

{
 
  "patterns": [
    "What is the vision of CvSU?",
    "What is the mission of CvSU?",
    "What are the core values of CvSU?",
    "What does the CvSU logo mean?",
    "Explain the CvSU seal"
  ],
  "response": 
    "CvSU's vision focuses on excellence in character development, academics, research, innovation, and community engagement. Its core values are Truth, Excellence, and Service."
  },
{
 
  "patterns": [
    "Is there parking area in CvSU Bacoor?",
    "Can students park inside the campus?",
    "Is parking free?",
    "Where can I park my motorcycle?",
    "Is overnight parking allowed?",
    "Where can I park my vehicle",
    "Can students use the campus parking area",
    "Is parking available inside the campus"
  ],
  "response": 
    "Yes. The designated parking area at CvSU Bacoor is located near the Vehicle Guard House entrance.<br><br>For safety and security, students are advised to properly lock their vehicles and avoid leaving their keys inside."
  },
{
  
  "patterns": [
    "How do I shift courses?",
    "Can I change my program?",
    "What are the requirements for shifting?",
    "How can I transfer to another course?",
    "What is the shifting process?",
    "How can I shift courses",
    "How do I change my program",
    "What is the process for shifting courses",
    "Can I transfer to another course",
    "How do I shift to a different degree program"
  ],
  "response": 
    "Students who wish to shift programs must complete the required forms, obtain approvals from relevant departments, and submit the documents to the registrar. Approval depends on academic standing and slot availability."
  },
{
 
  "patterns": [
    "What happens if I fail a subject?",
    "Can I retake a failed subject?",
    "How do I appeal a failing grade?",
    "Will a failed subject affect graduation?",
    "Can I still pass if I fail quizzes?",
     "I failed a subject",
    "What should I do if I fail a course",
    "Can I continue if I fail a prerequisite",
    "How does failing a subject affect me"
  ],
  "response": 
    "If you fail a subject, you must retake and pass it before enrolling in any subject that requires it as a prerequisite.<br><br>If the failed subject is only offered once per academic year, you may need to wait until the following school year to retake it, which may delay your academic progress.<br><br>Even students in higher year levels are still required to complete any lower-year subjects that they have not passed.<br><br>Students are encouraged to seek academic support and regularly consult with academic advisers to avoid delays in completing their degree requirements."
  },
{
 
  "patterns": [
    "Is student ID required on campus?",
    "Do I need to wear a uniform?",
    "Can I enter without an ID?",
    "What happens if I am not in uniform?",
    "Are IDs mandatory?"
  ],
  "response": 
    "Students are expected to wear their official ID and prescribed uniform while on campus. Failure to comply may result in restricted access to campus facilities or classrooms."
  },
{

  "patterns": [
    "When is graduation?",
    "When is recognition day?",
    "Who can attend graduation?",
    "Do I need to attend rehearsals?",
    "How do I know if I am eligible to graduate?"
  ],
  "response": 
    "Graduation and recognition schedules are announced by the university. Eligible students must complete academic requirements and follow instructions regarding rehearsals, attire, and ceremony participation."
  },
{
  
  "patterns": [
    "How do I request a COG?",
    "Where can I get my Certificate of Grades?",
    "Can I request grades online?",
    "How much is COG processing?",
    "When can I request my grades?"
  ],
  "response": 
    "Students may request a Certificate of Grades through the registrar or official student services after grades have been officially released."
  },
{
  
  "patterns": [
    "What can I use as proof of enrollment?",
    "Can I use COR as proof of enrollment?",
    "Is student ID enough as proof of enrollment?",
    "What document proves I am enrolled?",
    "Do I need a certificate of enrollment?"
  ],
  "response": 
    "The Certificate of Registration (COR) is the primary proof of enrollment. Student IDs may also be accepted for certain transactions."
  },
{
 
  "patterns": [
    "I lost my student ID",
    "How do I replace my ID?",
    "What should I do if my ID is missing?",
    "Can I get a replacement ID?",
    "Lost school ID"
  ],
  "response": 
    "Report the loss to the registrar immediately and follow the replacement process. Additional requirements or fees may apply."
  },
{

  "patterns": [
    "Is there motorcycle parking?",
    "Where can I park my motorcycle?",
    "Motorcycle parking area",
    "Can motorcycles enter the campus?",
    "Parking for motorcycles"
  ],
  "response": 
    "CvSU Bacoor provides designated motorcycle parking areas. Students should park only in authorized zones."
  },
{
 
  "patterns": [
    "Is parking free?",
    "Do I pay for parking?",
    "Parking fee in CvSU",
    "How much is parking?",
    "Campus parking charges"
  ],
  "response": 
    "Campus parking is generally free, but policies may change during special events or according to campus regulations."
  },
{
 
  "patterns": [
    "What is the WiFi password?",
    "Where can I get the WiFi password?",
    "Campus WiFi credentials",
    "How do I access WiFi?",
    "WiFi login information"
  ],
  "response": 
    "WiFi passwords are distributed through authorized offices such as the IT Office or other official campus channels."
  },
{
  
  "patterns": [
    "I can't connect to WiFi",
    "WiFi is not working",
    "Campus internet problem",
    "WiFi connection failed",
    "Why can't I access the internet?"
  ],
  "response": 
    "Connection issues may be caused by incorrect credentials, weak signal, or network congestion. Contact the IT Office if the problem continues."
  },
{
  
  "patterns": [
    "Am I eligible for graduation?",
    "Who can graduate?",
    "Graduation requirements",
    "Can I graduate this year?",
    "Graduation evaluation"
  ],
  "response": 
    "Students must complete all academic requirements, pass required subjects, and satisfy university obligations before being cleared for graduation."
  },

{
 
  "patterns": [
    "What grade is required for BSCS?",
    "BSCS grade requirement",
    "Can I take BSCS with 80 in Math?",
    "Required grade for Computer Science",
    "BSCS admission grades"
  ],
  "response": 
    "BSCS applicants are recommended to have grades of 85 or higher in Math, Science, and English. STEM or TVL-ICT strands are preferred."
  },
{
 
  "patterns": [
    "What grade is required for BSIT?",
    "BSIT requirements",
    "Required grades for Information Technology",
    "Can I take BSIT?",
    "BSIT admission grade"
  ],
  "response": 
    "BSIT applicants are encouraged to come from STEM or TVL-ICT strands. Admission depends on available slots and academic evaluation."
  },
{
 
  "patterns": [
    "When is wash day?",
    "What day is wash day?",
    "Wash day schedule",
    "Can I wear civilian clothes today?",
    "Which days are wash days?"
  ],
  "response": 
    "Wednesday and Saturday are commonly observed as wash days where students may wear permitted casual attire."
  },

{
  
  "patterns": [
    "What should I wear for research defense?",
    "Research defense attire",
    "Defense dress code",
    "What is the required outfit for defense?",
    "Formal attire for defense"
  ],
  "response": 
    "Students are expected to wear formal or business attire during research defenses and academic presentations."
  },

{
 
  "patterns": [
    "How do I get a Certification of Registration",
    "How do I get a COR",
    "Where can I get my COR",
    "How can I obtain a COR",
    "How is COR issued"
  ],
  "response": 
    "A Certificate of Registration (COR) is provided after you successfully enroll in your course program. The COR form is available upon request."
  },
{
 
  "patterns": [
    "What is a Certification of Registration used for",
    "What is a COR used for",
    "Why do I need a COR",
    "What can I use COR for",
    "Is COR important"
  ],
  "response": 
    "The Certificate of Registration (COR) is used to prove that a student is officially enrolled in the University.<br><br>It may also be used when entering the University, especially if a student has not yet received a student ID or has forgotten it.<br><br>COR is required of every student. Students may not be allowed to enter or use University facilities without a COR or Student ID. Visitors may sign the visitor handbook at the guard post.<br><br>The COR form is available upon request."
  },
{

  "patterns": [
    "How long is COR valid?",
    "How long is the COR valid?",
    "Is my COR still valid?",
    "Does COR expire?",
    "Can I use last semester's COR?",
    "When should I get a new COR?",
    "How long does COR Form valid",
    "When does COR expire?",
    "What is the validity of COR",
    "Validity of Certificate of Registration",
    "How long can I use my COR",
    "When do I need a new COR?"
  ],
 "response":
    "The Certificate of Registration (COR) is valid only for the semester in which it was issued.<br><br>Students must obtain a new COR for each subsequent semester or once enrollment for the next semester begins. A COR from a previous semester cannot be used as a current enrollment document."
  },
{
  "patterns": [
    "Can COR forms be used as proof of enrollment",
    "Is COR proof of enrollment",
    "Can I use COR as enrollment proof",
    "Does COR verify enrollment",
    "Can COR be used officially"
  ],
  "response": 
    "Yes. The Certificate of Registration (COR) is an official document that can be used as proof that a student is enrolled in the University."
  },

{

  "patterns": [
    "How can I request a Certificate of Grades",
    "How do I request a COG",
    "Where can I get my COG",
    "How can I obtain a Certificate of Grades",
    "What is the process for requesting COG"
  ],
  "response": 
    "You can request a Certificate of Grades through the Registrar's Office. Typically, you will need to complete a request form and pay the corresponding processing fee."
  },

{
 
  "patterns": [
    "When can I request a Certificate of Grades",
    "When can I get my COG",
    "When is COG available",
    "When may I request a Certificate of Grades",
    "Can I request COG after the semester"
  ],
  "response": 
    "You may request a Certificate of Grades after the semester has officially ended and all grades have been submitted and finalized by your professors."
  },

{
 
  "patterns": [
    "what is tor",
    "what is transcript of records",
    "meaning of tor",
    "tor definition",
    "explain tor",
    "What does Transcript of Records mean",
    "Explain Transcript of Records",
    "What information is in a TOR"
  ],
  "response": 
    "A Transcript of Records (TOR) is an official academic document issued by the University containing a student's complete academic history.<br><br>It includes the subjects taken, grades received, units earned, and other academic information required for employment, transfer, further studies, licensure examinations, and other official purposes."
  },
{
 
  "patterns": [
    "how to request tor",
    "tor request process cvsu",
    "how can i get my tor",
    "steps to request tor",
    "tor application process",
    "How do I obtain a TOR"
    
  ],
 "response": 
    "Students and graduates may request a Transcript of Records through the Registrar's Office.<br><br>Applicants must submit the required request form, provide valid identification, comply with University requirements, and settle any applicable processing fees before the document can be released."
  },
{
  "patterns": [
    "tor requirements",
    "tor requirement",
    "documents needed for tor",
    "requirements for transcript of records",
    "what documents are needed for tor",
    "tor documentary requirements",
    "transcript of records",
    "second courser requirements",
    "diploma holder requirements"
  ],
  "response": 
    "Transcript of Records (TOR) requirements typically include a completed clearance, valid ID or student ID, TOR request form, and proof of payment. Additional requirements may apply depending on your student status.<br><br>Second-Course Applicants, TCP Applicants, and Associate/Certificate/Vocational/Diploma Degree Holders must submit a Transcript of Records (TOR) indicating their graduation date."
  },
{

  "patterns": [
    "tor processing time",
    "how long is tor processing",
    "when will my tor be released",
    "tor release schedule",
    "how many days for tor"
  ],
  "response": 
    "TOR processing usually takes 5 to 15 working days. Processing may take longer during peak periods such as enrollment and graduation."
  },
{

  "patterns": [
    "can i request tor while studying",
    "tor request as current student",
    "can enrolled students request tor",
    "can i get tor before graduation",
    "tor for current students"
  ],
  "response": 
    "Yes. Current students may request a TOR for scholarship, transfer, or other academic purposes. Only completed and encoded subjects will appear on the document."
  },
{

  "patterns": [
    "can someone else claim my tor",
    "claiming tor by representative",
    "authorized representative for tor",
    "can my parent claim my tor",
    "proxy claiming tor"
  ],
  "response": 
    "Yes. A representative may claim your TOR if they present an authorization letter, their valid ID, a copy of your ID, and any additional requirements requested by the Registrar."
  },
{

  "patterns": [
    "tor fee cost",
    "how much is tor",
    "tor payment",
    "tor processing fee",
    "cost of transcript of records"
  ],
  "response": 
    "TOR fees vary by campus and current university policies. Students should verify the latest rates with the Registrar or Cashier's Office."
  },

{

  "patterns": [
    "Do I need to maintain attendance to pass the school year",
    "Is attendance required",
    "Do I need regular attendance",
    "What happens if I have many absences",
    "Can I fail because of absences"
  ],
  "response": 
    "Yes. Pupils and students are required to attend their classes promptly and regularly.<br><br>If a university student accumulates absences without an excusable reason amounting to 20 percent or more of the total class hours, the student may be dropped from the roll.<br><br>If the student's academic performance is poor, a grade of 5.0 may be given."
  },
{
 
  "patterns": [
    "What is the passing grade of CvSU Bacoor",
    "What is the passing grade",
    "What grade is considered passing",
    "What is the grading system of CvSU",
    "What is the minimum passing grade"
  ],
  "response": 
    "The passing grade at CvSU Bacoor is 3.00, while 5.00 is the failing grade.<br><br>Grading System:<br>1.00 - Excellent (Highest Grade)<br>1.50 - Very Good<br>2.00 - Good<br>2.50 - Satisfactory<br>3.00 - Passing Grade<br>4.00 - Conditional Grade. This must be removed by taking a removal examination to obtain a grade of 3.00 or become 5.00.<br>INC - Incomplete. The student is passing but has not completed other course requirements.<br>5.00 - Failed.<br><br>Each college may adopt its own method of assigning grades and weighting examinations, laboratory work, and other requirements, subject to review and approval by the Vice President for Academic Affairs."
  },

{

  "patterns": [
    "How can I appeal a failing grade",
    "Can I appeal a failing grade",
    "What should I do if I fail a subject unfairly",
    "How do I request a grade appeal",
    "How can I contest my grade"
  ],
  "response": 
    "If you receive a failing grade, the first step is to speak directly with your instructor. Schedule a meeting to discuss your performance and ask for specific feedback.<br><br>If you believe there was a grading error or that the grade was unfair, present supporting evidence such as completed assignments, examinations, or other relevant records.<br><br>If the issue remains unresolved, you may file a formal grade appeal according to University procedures. Submit a written appeal along with supporting documents and wait for the official review and decision."
  },

{

  "patterns": [
    "What is the Process of Phase Out Program",
    "What is a phase out program",
    "How does a phase out program work",
    "What happens when a curriculum is replaced",
    "Explain the phase out process"
  ],
  "response": 
    "A phase-out program should be anticipated when implementing new or revised academic programs.<br><br>If a new program replaces an existing curriculum, implementation should begin with incoming freshmen only, while the old curriculum continues until the current students complete and graduate from it.<br><br>For revised courses, the compulsory requirements for newly introduced or revised subjects shall apply only to students who are scheduled to take those courses in the current academic year. In no case shall introduced or revised courses be required as back subjects for students."
  },
{

  "patterns": [
    "How do I apply for a leave of absence",
    "What is the process for leave of absence",
    "Can I file a leave of absence",
    "How can I request an LOA",
    "What should I do if I need to stop studying temporarily"
  ],
  "response": 
    "Students who need to temporarily stop their studies may apply for a Leave of Absence (LOA).<br><br>The request should be submitted to the appropriate University office together with the necessary supporting documents.<br><br>Approval of the request is subject to University policies and evaluation by the concerned authorities."
  },
{

  "patterns": [
    "How can I return after being absent from school",
    "What is student reinstatement",
    "How do I get reinstated",
    "Can I return after stopping my studies",
    "What is the reinstatement process"
  ],
  "response": 
    "Students who have discontinued their studies and wish to return may apply for reinstatement subject to University policies.<br><br>Applicants may be required to submit a written request, undergo academic evaluation, and comply with all requirements prescribed by the University before enrollment is permitted."
  },
{

  "patterns": [
    "What is the student council",
    "What does the student council do",
    "Who represents the students",
    "Student council information",
    "Purpose of the student council"
  ],
  "response": 
    "The Student Council is the official representative body of the student population.<br><br>It serves as a link between students and the University administration, promotes student welfare, organizes activities, and advocates for the interests and concerns of students while upholding University policies and values."
  },
{

  "patterns": [
    "What are community extension programs",
    "Does CvSU have extension programs",
    "Community outreach activities",
    "Can students join extension programs",
    "What are extension services"
  ],
  "response": 
    "Community extension programs are initiatives designed to share knowledge, skills, and services with communities.<br><br>These programs may involve training, outreach activities, livelihood projects, environmental programs, educational assistance, and other community development efforts that support the University's extension mandate."
  },
{

  "patterns": [
    "Can students participate in research",
    "Research opportunities for students",
    "How can I join research projects",
    "Does CvSU support student research",
    "Student research programs"
  ],
  "response": 
    "Yes. Students may participate in research activities and projects as part of their academic requirements or through faculty-led initiatives.<br><br>Research participation helps students develop critical thinking, analytical skills, problem-solving abilities, and practical experience in their field of study."
  },

{

  "patterns": [
    "How can I file a complaint",
    "Where do I report a concern",
    "Student complaint procedure",
    "How do I submit a grievance",
    "What should I do if I have a complaint"
  ],
  "response": 
    "Students who wish to raise concerns, complaints, or grievances should follow the University's established procedures.<br><br>Concerns should first be addressed to the appropriate instructor, office, or department. If unresolved, the matter may be elevated to higher University authorities for proper review and action."
  },

{

  "patterns": [
    "What health services are available",
    "Campus clinic services",
    "Can students receive medical assistance",
    "What does the campus clinic provide",
    "Health services for students"
  ],
  "response": 
    "The University Clinic provides basic health services to students, faculty members, employees, and other authorized individuals.<br><br>Services may include health consultations, medical assessments, first aid, referrals, and other health-related assistance in accordance with University policies."
  },
{

  "patterns": [
    "What happens during emergency class suspension",
    "How are emergency class suspensions announced",
    "Will classes be suspended during emergencies",
    "Emergency suspension policy",
    "How does the University suspend classes during emergencies"
  ],
  "response": 
    "The University may suspend classes during emergencies, disasters, severe weather conditions, public health concerns, or other situations that may endanger the safety and welfare of students and personnel.<br><br>Official announcements regarding class suspensions are released through authorized University communication channels."
  },
{

  "patterns": [
    "Where can I find official announcements",
    "How do I get University updates",
    "Where are announcements posted",
    "Official school announcements",
    "How can I stay updated"
  ],
  "response": 
    "Students are encouraged to monitor official University communication channels for announcements, advisories, schedules, academic updates, enrollment information, and other important notices.<br><br>Official announcements may be released through the University's website, social media pages, campus bulletin boards, and authorized offices."
  },
{

  "patterns": [
    "What services does the Registrar's Office provide",
    "Registrar Office services",
    "What can I request from the Registrar",
    "What does the Registrar handle",
    "Registrar information"
  ],
  "response": 
    "The Registrar's Office is responsible for maintaining student academic records and processing official academic documents.<br><br>Services may include enrollment assistance, record verification, issuance of certifications, transcript requests, graduation evaluation, and other academic record-related transactions."
  },
{

  "patterns": [
    "What does the Admissions Office do",
    "Admissions Office services",
    "Who handles admission applications",
    "Admission concerns",
    "What services are provided by the Admissions Office"
  ],
  "response": 
    "The Admissions Office manages the admission process for prospective students.<br><br>Its responsibilities may include application processing, evaluation of admission requirements, entrance examination coordination, applicant verification, and dissemination of admission-related information."
  },

{

  "patterns": [
    "What languages can the chatbot understand",
    "Can the chatbot understand Filipino",
    "Does the chatbot support English",
    "What languages are supported",
    "Can I ask questions in Filipino and English"
  ],
  "response": 
    "The chatbot can understand and respond to inquiries in both English and Filipino.<br><br>Users may communicate using either language when asking questions related to University information, services, policies, admissions, enrollment, and student concerns."
  },
{
  "patterns": [
    "Tell me about CvSU Bacoor",
    "What is CvSU Bacoor",
    "Information about CvSU Bacoor",
    "Introduce CvSU Bacoor",
    "What should I know about the campus"
  ],
  "response": 
    "CvSU Bacoor is one of the campuses of Cavite State University dedicated to providing quality education, research, extension, and community service.<br><br>The campus offers academic programs designed to develop competent, responsible, and globally competitive graduates while supporting the University's mission of excellence in instruction, research, extension, and production."
  
},
{

  "patterns": [
    "What are the rules and regulations during exams?",
    "What are the exam guidelines in CvSU Bacoor?",
    "What should I follow during examinations?",
    "Are there rules for taking exams in CvSU Bacoor?",
    "What are the examination policies?"
  ],
 "response":
    "📚 Examination Rules and Regulations<br><br><br><br>To ensure a fair and orderly examination process, all students are expected to observe the following rules:<br><br><br><br>* Arrive at the examination room on time.<br><br>* Present your valid student ID when required.<br><br>* Bring only the materials permitted by your instructor.<br><br>* Keep mobile phones and other electronic devices switched off and stored away during the examination.<br><br>* Maintain silence and avoid disturbing other examinees.<br><br>* Do not communicate, share answers, or engage in any form of cheating.<br><br>* Follow all instructions given by the proctor or instructor.<br><br>* Submit your examination papers and materials before leaving the room.<br><br>* Any form of academic dishonesty may result in disciplinary action in accordance with CvSU Bacoor policies.<br><br><br><br>For specific examination guidelines, students are encouraged to consult their instructors or the campus administration."
  },
{
  
  "patterns": [
    "What are the rules and regulations in CvSU Bacoor?",
    "What policies should students follow in CvSU Bacoor?",
    "Tell me the student rules in CvSU Bacoor",
    "What are the campus regulations?",
    "What are the general rules for students?"
  ],
 "response":
    "🏫 CvSU Bacoor Student Rules and Regulations<br><br><br><br>All students are expected to uphold the values and standards of Cavite State University - Bacoor Campus by following these guidelines:<br><br><br><br>* Wear the prescribed school uniform and identification card when required.<br><br>* Show respect and courtesy to fellow students, faculty members, staff, and visitors.<br><br>* Maintain proper conduct within the campus premises.<br><br>* Keep the campus clean and dispose of waste properly.<br><br>* Protect and properly use university facilities, equipment, and resources.<br><br>* Observe classroom policies and attend classes regularly.<br><br>* Refrain from engaging in bullying, harassment, discrimination, or disruptive behavior.<br><br>* Follow all university policies regarding academic integrity and student discipline.<br><br>* Comply with campus safety and security regulations.<br><br>* Participate responsibly in university activities and programs.<br><br><br><br>Students are encouraged to refer to the official Student Handbook for the complete list of university rules, regulations, and disciplinary procedures."
  },
{
 
  "patterns": [
    "Can I smoke in school?",
    "Is smoking allowed in CvSU Bacoor?",
    "Can I use a vape on campus?",
    "Is vaping allowed in school?",
    "Can students drink alcohol in school?",
    "Is alcohol allowed in CvSU Bacoor?",
    "Can I bring cigarettes to school?",
    "Can I bring a vape inside the campus?",
    "What is the school's policy on smoking?",
    "Are tobacco products allowed on campus?"
  ],
 "response":
    "🚭 Smoking, Vaping, and Alcohol Policy<br><br><br><br>To maintain a safe, healthy, and conducive learning environment, the following rules are observed within the campus:<br><br><br><br>* Smoking is strictly prohibited within the campus premises.<br><br>* The use of electronic cigarettes (e-cigarettes), vapes, and similar devices is not allowed on campus.<br><br>* Possession, consumption, or distribution of alcoholic beverages within the university premises is prohibited unless specifically authorized for official purposes.<br><br>* Students must not report to school under the influence of alcohol or prohibited substances.<br><br>* Bringing illegal drugs, dangerous substances, or drug paraphernalia into the campus is strictly prohibited.<br><br>* Students are expected to comply with all university health, safety, and disciplinary regulations.<br><br>* Violations of these policies may result in disciplinary action in accordance with university rules and regulations.<br><br><br><br>For complete information regarding student conduct and disciplinary policies, please refer to the official CvSU Student Handbook or contact the campus administration."
  },
{
 
  "patterns": [
    "What activities are prohibited in school?",
    "What are not allowed in CvSU Bacoor?",
    "What behaviors are prohibited on campus?",
    "What can get me into trouble in school?",
    "What actions are not allowed in the university?"
  ],
 "response":
    "⚠️ Prohibited Activities on Campus<br><br><br><br>Students are expected to maintain proper conduct and avoid activities that may disrupt the learning environment. The following are generally prohibited:<br><br><br><br>* Smoking and vaping within the campus premises.<br><br>* Possession or consumption of alcoholic beverages without proper authorization.<br><br>* Possession, use, or distribution of illegal drugs and dangerous substances.<br><br>* Cheating, plagiarism, and other forms of academic dishonesty.<br><br>* Bullying, harassment, discrimination, and acts of violence.<br><br>* Damaging, vandalizing, or misusing university property.<br><br>* Possession of weapons or dangerous items that may threaten campus safety.<br><br>* Disruptive behavior during classes, examinations, or university activities.<br><br>* Unauthorized use of university facilities, equipment, or resources.<br><br>* Any action that violates university policies, rules, and regulations.<br><br><br><br>Students are encouraged to review the official CvSU Student Handbook for detailed policies and disciplinary procedures."
  },
{
 
  "patterns": [
    "Can I bring cigarettes to school?",
    "Can I bring a vape to campus?",
    "Can I bring alcohol to school?",
    "What items are prohibited in school?",
    "What things are not allowed inside the campus?"
  ],
 "response":
    "🎒 Prohibited Items on Campus<br><br><br><br>For the safety and well-being of the university community, students should avoid bringing prohibited items to campus, including:<br><br><br><br>* Cigarettes, tobacco products, and vaping devices for use within the campus.<br><br>* Alcoholic beverages and intoxicating substances.<br><br>* Illegal drugs and drug-related paraphernalia.<br><br>* Weapons, explosives, or other dangerous items.<br><br>* Materials that may disrupt classes, university activities, or campus operations.<br><br><br><br>Students found in possession of prohibited items may be subject to disciplinary action based on university policies and regulations."
  },
{
 
  "patterns": [
    "Can I smoke in school?",
    "Is smoking allowed in CvSU Bacoor?",
    "Can I use a vape on campus?",
    "Is vaping allowed in school?",
    "Can students drink alcohol in school?",
    "Is alcohol allowed in CvSU Bacoor?",
    "Can I bring cigarettes to school?",
    "Can I bring a vape inside the campus?",
    "What is the school's policy on smoking?",
    "Are tobacco products allowed on campus?"
  ],
 "response":
    "🚭 Smoking, Vaping, and Alcohol Policy<br><br><br><br>To maintain a safe, healthy, and conducive learning environment, the following rules are observed within the campus:<br><br><br><br>* Smoking is strictly prohibited within the campus premises.<br><br>* The use of electronic cigarettes (e-cigarettes), vapes, and similar devices is not allowed on campus.<br><br>* Possession, consumption, or distribution of alcoholic beverages within the university premises is prohibited unless specifically authorized for official purposes.<br><br>* Students must not report to school under the influence of alcohol or prohibited substances.<br><br>* Bringing illegal drugs, dangerous substances, or drug paraphernalia into the campus is strictly prohibited.<br><br>* Students are expected to comply with all university health, safety, and disciplinary regulations.<br><br>* Violations of these policies may result in disciplinary action in accordance with university rules and regulations.<br><br><br><br>For complete information regarding student conduct and disciplinary policies, please refer to the official CvSU Student Handbook or contact the campus administration."
  },
{
 
  "patterns": [
    "What activities are prohibited in school?",
    "What are not allowed in CvSU Bacoor?",
    "What behaviors are prohibited on campus?",
    "What can get me into trouble in school?",
    "What actions are not allowed in the university?"
  ],
 "response":
    "⚠️ Prohibited Activities on Campus<br><br><br><br>Students are expected to maintain proper conduct and avoid activities that may disrupt the learning environment. The following are generally prohibited:<br><br><br><br>* Smoking and vaping within the campus premises.<br><br>* Possession or consumption of alcoholic beverages without proper authorization.<br><br>* Possession, use, or distribution of illegal drugs and dangerous substances.<br><br>* Cheating, plagiarism, and other forms of academic dishonesty.<br><br>* Bullying, harassment, discrimination, and acts of violence.<br><br>* Damaging, vandalizing, or misusing university property.<br><br>* Possession of weapons or dangerous items that may threaten campus safety.<br><br>* Disruptive behavior during classes, examinations, or university activities.<br><br>* Unauthorized use of university facilities, equipment, or resources.<br><br>* Any action that violates university policies, rules, and regulations.<br><br><br><br>Students are encouraged to review the official CvSU Student Handbook for detailed policies and disciplinary procedures."
  },
  {
  "patterns": [
    "Can I bring cigarettes to school?",
    "Can I bring a vape to campus?",
    "Can I bring alcohol to school?",
    "What items are prohibited in school?",
    "What things are not allowed inside the campus?"
  ],
 "response":
    "🎒 Prohibited Items on Campus<br><br><br><br>For the safety and well-being of the university community, students should avoid bringing prohibited items to campus, including:<br><br><br><br>* Cigarettes, tobacco products, and vaping devices for use within the campus.<br><br>* Alcoholic beverages and intoxicating substances.<br><br>* Illegal drugs and drug-related paraphernalia.<br><br>* Weapons, explosives, or other dangerous items.<br><br>* Materials that may disrupt classes, university activities, or campus operations.<br><br><br><br>Students found in possession of prohibited items may be subject to disciplinary action based on university policies and regulations."
},

{
  "patterns": [
    "What is NSTP?",
    "Can you explain NSTP?",
    "What does NSTP mean?",
    "What is the purpose of NSTP?",
    "Why do students take NSTP?"
  ],
 "response":
    "🎓 National Service Training Program (NSTP)<br><br><br><br>The National Service Training Program (NSTP) is a program mandated by Republic Act No. 9163 for tertiary-level students in the Philippines. It aims to develop civic consciousness, leadership, patriotism, and social responsibility among students through community service and nation-building activities.<br><br><br><br>NSTP helps students become active contributors to society by encouraging volunteerism, community involvement, disaster preparedness, and values formation.<br><br><br><br>Students typically complete two semesters of NSTP as part of their academic requirements. Depending on the institution, students may choose from different NSTP components such as ROTC or CWTS.<br><br><br><br>Through NSTP, students gain valuable experiences that promote personal growth, community engagement, and responsible citizenship."
  
},
{
  "patterns": [
    "What is ROTC?",
    "Can you explain ROTC?",
    "What does ROTC mean?",
    "What is the purpose of ROTC?",
    "What happens in ROTC?"
  ],
 "response":
    "🪖 Reserve Officers' Training Corps (ROTC)<br><br><br><br>The Reserve Officers' Training Corps (ROTC) is one of the components of the National Service Training Program (NSTP). It is designed to provide students with military-oriented training that promotes discipline, leadership, patriotism, and preparedness for national defense.<br><br><br><br>ROTC activities may include:<br><br><br><br>* Leadership and teamwork training<br><br>* Military customs and courtesies<br><br>* Basic military instruction<br><br>* Physical fitness activities<br><br>* Disaster preparedness and emergency response training<br><br>* Citizenship and nation-building programs<br><br><br><br>The program aims to develop responsible citizens who are prepared to contribute to national security, public service, and community development. ROTC also helps students strengthen their confidence, discipline, and leadership skills that can be applied in both academic and professional settings."
  
},
{
 
  "patterns": [
    "What is the difference between NSTP and ROTC?",
    "Is ROTC the same as NSTP?",
    "How are NSTP and ROTC different?",
    "What is NSTP ROTC?",
    "Explain NSTP and ROTC"
  ],
 "response":
    "📚 Difference Between NSTP and ROTC<br><br><br><br>NSTP (National Service Training Program) is the overall program required for college students to promote civic responsibility, leadership, and nation-building.<br><br><br><br>ROTC (Reserve Officers' Training Corps) is one of the components or options under NSTP that focuses on military training, discipline, leadership, and national defense preparedness.<br><br><br><br>In simple terms:<br><br><br><br>* NSTP is the program.<br><br>* ROTC is one of the NSTP components.<br><br><br><br>Students who choose ROTC fulfill their NSTP requirement through military-oriented training and related activities."
  
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
