from django.http import HttpResponse
from django.contrib import admin
from django.shortcuts import render,redirect, get_object_or_404
from django.db import connection, transaction
from webapp.forms import UserForm,ReviewForm,AdminForm,ChatPairForm
from webapp.models import  Users,Review,Admin,ChatPair
from chatterbot import ChatBot
from django.utils.safestring import mark_safe
from chatterbot.trainers import ListTrainer
from django.templatetags.static import static
from django.contrib import messages
"""{% load static %}"""
import datetime
cursor = connection.cursor()

# You should NOT reinitialize your ChatBot inside the view.
# Instead, initialize it once at the top level of your module (global scope)
def getResponse(request):
    user_message = request.GET.get('userMessage')
    
    if not user_message:
        return HttpResponse("No message received.", status=400)

    try:
        response = bot.get_response(user_message)
        return HttpResponse(mark_safe(str(response).replace('\n', '<br>')))
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

#from django.core.mail import send_mail
#from django.conf import settings



def train_from_db():
    chat_data = ChatPair.objects.all()
    trainer = ListTrainer(bot)
    for pair in chat_data:
        trainer.train([pair.question, pair.answer])
     
def home_page(request,):
    
    #if request.method == 'POST':
        #name = request.POST['name']
        #email = request.POST['email']
       # message = request.POST['message']
       
       # send_mail(
           # name,#title
          #  message,#message
          #  'settings.EMAIL_HOST_USER', #sender if not available
          #  [email], #receiver email
          #  fail_silently=False)
    return render(request, 'pages/home.html')


def chatbot_page(request):
    
    return render(request, 'pages/chatbot.html')

def blog_page(request):
    return render(request, 'pages/blog.html')

def dashboard_page(request):
    return render(request, 'pages/dashboard.html')

def faq_page(request):
    return render(request, 'pages/FAQ.html')

def contact_page(request):
    return render(request, 'pages/contact.html')

def rizz(request):
    return render(request, 'pages/rizz.html')

def explorePage(request):
    return render(request, 'pages/explore.html')

def signupPage(request):
    return render(request, 'pages/signup.html')

def loginPage(request):
    return render(request, 'pages/login.html')

def chatbot_front(request):
    return render(request, 'pages/chatbot_front.html')




def chatbot_list(request):
    chatpairs = ChatPair.objects.all()
    return render(request, 'pages/chatbot_list.html', {'chatpairs': chatpairs})

# Add new
def chatbot_add(request):
    if request.method == 'POST':
        form = ChatPairForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Chat entry added.")
            return redirect('chatbot_list')
    else:
        form = ChatPairForm()
    return render(request, 'pages/chatbot_form.html', {'form': form})

# Edit
def chatbot_edit(request, pk):
    chatpair = get_object_or_404(ChatPair, pk=pk)
    if request.method == 'POST':
        form = ChatPairForm(request.POST, instance=chatpair)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Chat entry updated.")
            return redirect('chatbot_list')
    else:
        form = ChatPairForm(instance=chatpair)
    return render(request, 'pages/chatbot_form.html', {'form': form})

# Delete
def chatbot_delete(request, pk):
    chatpair = get_object_or_404(ChatPair, pk=pk)
    if request.method == 'POST':
        chatpair.delete()
        messages.success(request, "🗑️ Entry deleted.")
        return redirect('chatbot_list')
    return render(request, 'pages/chatbot_confirm_delete.html', {'chatpair': chatpair})

def userHomePage(request):
    return render(request, 'pages/userHome.html')
     
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


def review_list(request):
    reviews = Review.objects.all()
    return render(request, 'pages/review_list.html', {'reviews': reviews})

def review_create(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('review_list')
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

		if utype == "Admin":
			for a in Admin.objects.raw('SELECT * FROM TB_Admin WHERE AdminId="%s" AND AdminPass="%s"' % (uid, upass)):
				if a.AdminId == uid:
					request.session['AdminId'] = uid
					return render(request, "pages/base.html")
			else:
				messages.error(request, "Incorrect username or password")
				return redirect("home")

		if utype == "User":
			for a in Users.objects.raw('SELECT * FROM TB_Users WHERE userEmail="%s" AND userPass="%s"' % (uid, upass)):
				if a.userEmail == uid:
					request.session['CustId'] = uid
					request.session['user_name'] = a.userName
					request.session['user_image'] = a.userImage.url if a.userImage else '/media/profile_images/default.png'
					return render(request, "pages/chatbot.html")
			else:
				messages.error(request, "Incorrect username or password")
				return redirect("home")

# views.py
def edit_profile(request):
    user_email = request.session.get('CustId')
    user = Users.objects.get(userEmail=user_email)

    if request.method == 'POST':
        user.userName = request.POST.get('userName')
        if 'userImage' in request.FILES:
            user.userImage = request.FILES['userImage']
        user.save()
        request.session['user_name'] = user.userName
        request.session['user_image'] = user.userImage.url
        return redirect('chatbot')  # Or wherever you'd like to redirect

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
        return redirect('pages/user_list')
    return render(request, 'user_confirm_delete.html', {'user': user})














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

















bot = ChatBot('chatbot', read_only=False,
            logic_adapters=[
                {

                    'import_path':'chatterbot.logic.BestMatch',
                    'maximun_similarity_threshold':0.95

                }
                ])
    
list_to_train = [

    " ",
     "Hello",
#What is CVSU
     #"What is CVSU",
     #"Cavite State University",

     #"what is CVSU",
     #"Cavite State University",

     "what is cvsu",
     """Cavite State University 
     """,
################################################################################
#Enrollment     (ADDS)

    

    "How to enroll (Old Student)",
    """ Certainly, If you are old student, first of all you need to get a CoG or (Certificate of Grades) at the registrar, after that the University will announce where/when the Enrollment will happen. <br><br>" 
    Step 1: Society Fee. It should be announce at your Department. <br><br>
    Step 2: Fill-out Curriculum Checklist. Curriculum checklist are available at your society. Must be placed at long brown folder. It should be labeled properly by their name, course and student number. <br><br>
    Step 3: Evaluation of grades & Advising of Subjects to enroll. Wait for an  Announcement at your department where it will be held. <br><br>
    Step 4: Issuance of Queuing Number (per program) <br><br>"
    Step 5: Encoding of Subjects. Your department will announce where it will be held. """,

    "How to enroll (New Student)",
     " Absolutely, If you are a New student you should follow these easy steps:<br><br>" 
    """  * First, you need Admission Form then Fill-out and Download the application Form. 
         <a href="https://drive.google.com/file/d/1zoG0QutodBOX_iegsrPdtaXlgBs8Gn0a/view?fbclid=IwAR0cxxbPFag9mCOKcdWDrqd4Og8ytmJL_WFJYA5M4l_guRogSN7Ds-GBgoo" alt="admission.pdf" style="cursor: pointer;">Application Form</a>
         <br><br>
         * Secondly: Printing of Admission form: Download and print the accomplished the online application form and attached the 1x1 photo in the printed application with affixed signature.<br><br>
         * After you attached it, place it all at a short white folder with all the required requirements.<br><br>
         * Next, Bring 2 white short folder and 2 photocopies of all your original requirements.<br><br>
         * After that you should submit the requirements at the Guidance office of CvSU-Bacoor city.<br><br>
         * Lastly wait for further information for Examination Date: you will be given a permit and a schedule for the date of the Examination.""",

    "How to enroll (Transferee)",
      """ Ofcourse, Transferee (Those who started college level from other University/School) <br><br>"
    "  * Accomplished Application form for Admission  <a href="https://drive.google.com/file/d/1zoG0QutodBOX_iegsrPdtaXlgBs8Gn0a/view?fbclid=IwAR0cxxbPFag9mCOKcdWDrqd4Og8ytmJL_WFJYA5M4l_guRogSN7Ds-GBgoo" alt="admission.pdf" style="cursor: pointer;">Click Here</a><br><br>
    "  * Photocopy of transcript of records/certificate of Grades <br><br>
    "Other requirements after Evaluation: <br><br>
    "  * Honorable Dismissal <br><br>
    "  * Certificate of Good Moral Character <br><br>
    "  * NBI or Police Clearance""",


#################################################################################
#Requirements        (ADDS)
    "What are the requirements for New students",
    "First year Applicants (Grade 12 Students) <br><br>"
    """  * Accomplished Application form for Admission <br><br>  <a href="https://drive.google.com/file/d/1zoG0QutodBOX_iegsrPdtaXlgBs8Gn0a/view?fbclid=IwAR0cxxbPFag9mCOKcdWDrqd4Og8ytmJL_WFJYA5M4l_guRogSN7Ds-GBgoo" alt="admission.pdf" style="cursor: pointer;">Admission Form</a>""" 
    "  * Photocopy of Grade 11 card <br><br>"
    "  * Certificate from the principal or adviser indicating that the applicant is currently enrolled as grade 12 student with strand indicated <br><br>"
    "  ✓ The certificate must be originally signed. E-signature is NOT allowed",



##################################################################################
#SHS Graduate
    "What are the requirements for SHS Graduate",
    "First year Applicants (for SHS Graduate) <br><br>"
    """  * Accomplished Application form for Admission    <a href="https://drive.google.com/file/d/1zoG0QutodBOX_iegsrPdtaXlgBs8Gn0a/view?fbclid=IwAR0cxxbPFag9mCOKcdWDrqd4Og8ytmJL_WFJYA5M4l_guRogSN7Ds-GBgoo" alt="admission.pdf" style="cursor: pointer;">Application Form</a><br><br>"""
    "  * Photocopy of completed grade 12 report card <br><br>"
    "  * Certificate of non-issuance of Form 137 for college admission",



##################################################################################
#ALS Passer
    "What are the requirements for ALS Passer",
    "First year Applicants (ALS Passer) <br><br>"
    """  * Accomplished Application form for Admission    <a href="https://drive.google.com/file/d/1zoG0QutodBOX_iegsrPdtaXlgBs8Gn0a/view?fbclid=IwAR0cxxbPFag9mCOKcdWDrqd4Og8ytmJL_WFJYA5M4l_guRogSN7Ds-GBgoo" alt="admission.pdf" style="cursor: pointer;">Application Form</a> <br><br>""" 
    "  * Photocopy of Certificate of Rating(COR) with eligibility to enroll in College",



##################################################################################
#Transferee
    "What are the requirements for Transferee",
    "Transferee (Those who started college level from other University/School) <br><br>"
    "  * Accomplished Application form for Admission <br><br>"
    "  * Photocopy of transcript of records/certificate of Grades <br><br>"
    "Other requirements after Evaluation: <br><br>"
    "  * Honorable Dismissal <br><br>"
    "  * Certificate of Good Moral Character <br><br>"
    "  * NBI or Police Clearance",


##################################################################################
#Second course applicants
    "What are the requirements for Second course Applicants",
    "Second course Applicants(Those who finished a two-year program or four-year degree program) <br><br>"
    "  * Accomplished Application form for Admission <br><br>"
    "  * Photocopy of transcript of records with graduation date <br><br>" 
    "    Other requirements from evaluation <br><br>"
    "  * Honorable Dismissal <br><br>"
    "  * Certificate of Good Moral Character  <br><br>"
    "  * NBI or Police Clearance",



##################################################################################
#Foreign Students
    "What are the requirements for foreign student",
    """If you are foreign student you should follow these steps:<br><br>
    
    * Submit an approved permit to study from concerned embassy<br><br>
    
    * Pay a non-refundable foreign student fee of $36 dollars(may be changed without prior notice)<br><br>
    
    * Submit a Certificate of English Profiency from the Department of Language and Humanities<br><br>
    
    * Police Clearance from country of origin"""



##################################################################################
#CVSU Mission

    "What is CvSU Mission",
    "Cavite State University shall provide excellent, equitable and relevant educational opportunities in the arts, sciences and technology through quality instruction and responsive research and development activities. It shall produce professional, skilled and morally upright individuals for global competitiveness.",
    




##################################################################################
#CVSU Vision
    "What is CvSU Vision",
    "The premier University in historic Cavite recognized for excellence in the development of globally competitive and morally upright individuals.",

   



##################################################################################
#CVSU Mission and Vision

    "What is CvSU Mission and Vision",
    "Cavite State University shall provide excellent, equitable and relevant educational opportunities in the arts, sciences and technology through quality instruction and responsive research and development activities. It shall produce professional, skilled and morally upright individuals for global competitiveness.<br><br>"
    "The premier University in historic Cavite recognized for excellence in the development of globally competitive and morally upright individuals.",





##################################################################################
#CVSU Bacoor quality policy
    "What is CvSU Bacoor Quality Policy",
    "We Commit to the highest standards of education, value our stakeholders, Strive for continual improvement of our products and services, and Uphold the University’s tenets of Truth, Excellence, and Service to produce globally competitive and morally upright individuals.",

   



##################################################################################
#CVSU President
    "Who is the current president of CvSU?",
    """Dr. Ma. Agnes P. Nuestro has been named as the fourth president of Cavite State University (CvSU).

The members of the CvSU Board of Regents elected Dr. Nuestro to become the next president of the University, succeeding Dr. Hernando D. Robles who retired in October 2024. 

Having served as the University’s Vice President for Academic Affairs, Dr. Nuestro envisions CvSU as a premier global university by 2028.

In her presentation during the Public Forum for the Search for the 4th CvSU President, Dr. Nuestro emphasized her administration’s goals centered on IDEAL: Inclusive and Accessible Education, Dynamic and Competitive Research and Innovation, Empowered Communities and Stronger Partnership, Accountable and Client-Centered Governance, and Long-lasting/Sustainable Resource Generation. """



##################################################################################
#Major CvSU Bacoor Offers
    "What majors does CvSU Bacoor offers",
    "CvSU Bacoor offers various majors including Computer Science, Information Technology, Business Administration, Education, Pychology, and Criminology",

   



##################################################################################
#Authority to suspends classes
    "Who have authority to suspends classes",
    """The University President who has final authority to suspend classes throughout the University including all units or branches. 
    or he may suspend classes in specific units or campuses for specified periods of units.
    Suspension of classes does not mean that faculty and employee will not report for duty <br><br>
    
    With respect to typhoons, classes will be suspended upon advice of Philippine Atmospheric Geophysical and Astronomici Services Authority (PAG-ASA) whenever the typhoon is sufficient intensity to make it advisable to suspend classes the elementary grade and moreover when the approach of the University because of typhoon becomes more definitely pronounced as to required suspension of classes in the high school and collegiate level as well. Aside from such official announcements to be made classes may be considered automatically suspended in the elementary grades when reports throughout the mass medi confirm the raising of typhoon Signal No.2, the suspension apply furthermore to all high school and collegiate levels if typhos signal is raised to Typhoon Signal No. 3""",



##################################################################################
#What is program accreditation
    "What is Program Accreditation",
    "The university shall as much as possible, submit all programs for accreditation particularly by Accrediting Agency of Chartered Colleges and Universities in the Philippines (AACCUP) or any accrediting agency prescribed by CHED and the Philippine Association of State Universities and Colleges",


##################################################################################
#Academic load
    "What is Academic Load",
    "No student shall be alowed to take more than the maximum credit units per semester. A graduating student may be allowed to enroll more than the maximum allowable may be allowed to enroll more than the maximum allowable credit units not to exceed 26 units during the last two semesters of his course provided that he has a GPA of 2.50 or better in the previous two semesters as certified by the University Registrar. A graduating student petitioning for registrating up to maximum allowable academic load must secure a certification from the University Registrar that he is a graduating student.",


##################################################################################
#Class Attendance

    "Do I need to maintain attendance to pass the school year?",
    "Yes, Pupils/Students are required to attend their classes promptly and regularly. <br>"
    "If a university student is absent without excusable reason is 20 percent or more of the number of hours he shall be dropped from the roll."
    """If his performance is poor he shall be given a grade of "5.0" """,
    


##################################################################################
#What is the passing grade of CVSU   
    "What is the passing grade of CvSU Bacoor",
    """The passing grade of 3.00 while 5.00 is the failing grade. Here is the grading system of CvSU Bacoor. <br><br>
    
    
    <table class="grade-table" style="width: 100%; border: 1px solid white; padding: 30px; color: ">
    <tr >
       <td style="padding: 15px;"> 1.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Excellent (Highest Grade) </td>
    </tr>
    <tr>
        <td>1.25</td>
    </tr>
    <tr>
       <td> 1.50 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Very Good </td>
    </tr>
    <tr>
        <td>1.75</td>
    </tr>
     <tr>
       <td> 2.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Good </td>
    </tr>
    <tr>
        <td>2.25</td>
    </tr>
     <tr>
       <td> 2.50 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Satisfactory </td>
    </tr>
        <td>2.75</td>
    </tr>
     <tr>
       <td> 3.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Passing Grade </td>
    </tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
     <tr>
       <td> 4.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Conditional Grade has to be removed by taking a removal examination either to obtain a grade of "3.00" or slide to 5.00" </td>
    </tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
     <tr>
       <td> INC </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Grade of incomplete. The student is passing but has not completed other requirement of the course </td>
    </tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr>
        <td> 5.00 </td>
        <td style="border-bottom: 1px solid var(--text-color);"> The student failed the course. The numberical grade of "5.00" must be written in red ink by the teacher </td>
     </tr>
    
    
    
    
    </table><br><br>
    
    Each College shall endeavor to formulate and adopt a uniform method or system of assigning grades to scores and the assignment of weights to different types of test, requirements, laboratory exercises, and the like. This should be forwarded to the Vice President for Academic Affairs for his review and corrections before final adoption of the College concerned.
    """,



##################################################################################
#Re-enrollment of subjects
    "What happen in re-enrollment of subjects",
    """No student shall be allowed to repeat or re-enroll a subject for more than three (3)  times. <br><br>
    
    A student who fails a subject for the third time hsall be permanently disqualified from further registration in the University""",



##################################################################################
#Prerequisite Subjects
    "What is Prerequisite Subjects",
    """ A student shall not be allowed to register an advanced subject without passing/satisfying the requirements of the prerequisite subject(s) specified in the curriculum. <br>
    Passing grades obtained in the advanced course without first satisfying the prerequisites shall be considered null and void by the University Registrar""",


##################################################################################
#Leave of absence
    "What is Leave of Absence",
    """ A student who is granted leave of absence (LOA) within "75%" of the time devoted to a semester/term shall be given a corresponding grade by the instructor concerned for record purposes only but this will not be reflected in his Permanent Record.""",



##################################################################################
#Honorable Dismissal
    "What is Honorable Dismissal",
    """ Horable dismissal shall be issued by the University Registrar to a student who stopped schooling in the University provided that he was not found guilty of misdemeanor defined under the University Students' Norm of Conduct. If a student left the University for reasons of misdemeanor and/or academic delinquency, no certification of honorable dismissal shall be issued.""",



##################################################################################
#Grades and Grading System
"""What is the Grading System of CvSU Bacoor""",
 """The University shall adopt the numerical grading system of "1.00" to "5.00" where "1.00" is the highest grade and "5.00" is a failing grade.
 The system of grading is as follows:<br><br>
 
 <table class="grade-table" style="width: 100%; border: 1px solid white; padding: 30px; color: ">
    <tr >
       <td style="padding: 15px;"> 1.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Excellent (Highest Grade) </td>
    </tr>
    <tr>
        <td>1.25</td>
    </tr>
    <tr>
       <td> 1.50 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Very Good </td>
    </tr>
    <tr>
        <td>1.75</td>
    </tr>
     <tr>
       <td> 2.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Good </td>
    </tr>
    <tr>
        <td>2.25</td>
    </tr>
     <tr>
       <td> 2.50 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Satisfactory </td>
    </tr>
        <td>2.75</td>
    </tr>
     <tr>
       <td> 3.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Passing Grade </td>
    </tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
   <tr></tr>
     <tr>
       <td> 4.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Conditional Grade has to be removed by taking a removal examination either to obtain a grade of "3.00" or slide to 5.00" </td>
    </tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
     <tr>
       <td> INC </td>
       <td style="border-bottom: 1px solid var(--text-color);"> Grade of incomplete. The student is passing but has not completed other requirement of the course </td>
    </tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr></tr>
    <tr>
        <td> 5.00 </td>
        <td style="border-bottom: 1px solid var(--text-color);"> The student failed the course. The numberical grade of "5.00" must be written in red ink by the teacher </td>
     </tr>
    
    
    
    
    </table><br><br>
    
    Each College shall endeavor to formulate and adopt a uniform method or system of assigning grades to scores and the assignment of weights to different types of test, requirements, laboratory exercises, and the like. This should be forwarded to the Vice President for Academic Affairs for his review and corrections before final adoption of the College concerned.""",
      





##################################################################################
#Grade Requirements and Retention   
    "What is the Grade Requirements and Retention",
    """ In order to qualify for the general comprehensive examination, a student must obtain a GPA of 2.00 or better for all the courses taken. Courses listed under "others" shall be excluded from the computation but grades in these subjects must be passing.<br><br>

Failure to pass a subject twice shall disqualify the student from the graduate program.<br><br>

Similarly, a graduate student must maintain a GPA of 2.00 or better every term in order to qualify to continue with his program """,



##################################################################################
#Process of Phase Out Program
    "What is the Process of Phase Out Program",
    """A phase-out program should be anticipated in the implementation of new or revised programs.<br><br>

        If the new program is designed to replace an existing curriculum, the implementation should start from the incoming freshmen only and the old curriculum should end with the graduation of the current students taking it.<br><br>

In the revised courses, the compulsory requirement for students for the introduced/revised courses should start only in the current year they are supposed to take course. In no case shall the introduced/revised courses be required as back subjects for students.
""",


##################################################################################
#What is Unit Load
    "What is Unit Load?",
    "A non-working student may enroll a maximum load of 12 credit units if classes are conducted during regular days. However, for Saturday/summer classes, a graduate student may enroll a maximum load of nine (9) units for non-laboratory subjects and six (6) units for subjects with laboratory. CvSU full-time faculty members and staff who are admitted in the GS-OLC shall be allowed to enroll a maximum of six (6) units per semester.",


##################################################################################
#table of grade of conversion
    "What is the table of conversion",
    """ All units earned in other colleges or universities shall be evaluated on the basis of the following "table of conversion" <br><br>
    
    
    <table style="width: 100%; border: 1px solid var(--text-color);; padding: 30px;">
  <tr>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;">Grade</td>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);  padding: 5px;">Grade</td>
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color); padding: 5px;">Equivalent</td>
  </tr>
    <tr >
       <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 1.00 </td>
       <td style="border-bottom: 1px solid var(--text-color);"> 95%' </td>
       <td style="border-bottom: 1px solid var(--text-color);"> 1+ or A+' </td>
    </tr>
    <tr >
      <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 1.25 </td>
      <td style="border-bottom: 1px solid var(--text-color);"> 93%' </td>
      <td style="border-bottom: 1px solid var(--text-color);"> 1 or A' </td>
   </tr>
   <tr >
    <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 1.50 </td>
    <td style="border-bottom: 1px solid var(--text-color);"> 90%' </td>
    <td style="border-bottom: 1px solid var(--text-color);"> 1- or A-' </td>
 </tr>
 <tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 1.75 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 89%' </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 2+ or B+' </td>
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 2.00 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 85%' </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 2 or B' </td>
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 2.25 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 83%' </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 2- or B-' </td>
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 2.50 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 80%' </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 3+ or C+' </td>
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 2.75 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 78%' </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 3 or C' </td>
</tr>
<tr >
  <td style="padding: 15px; border-bottom: 1px solid var(--text-color);"> 3.00 </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 75%' </td>
  <td style="border-bottom: 1px solid var(--text-color);"> 3- or C-' </td>
</tr>
   
   
    
    
    
    </table>""",


##################################################################################
#Reason for refund
    "What is the valid reason for refunds",
    """Reason for Refund<br><br>

    The reasons for which refund of school fees other than deposit are allowed shall include any of the following:<br><br>

    * Withdrawal of registration <br>
    * Dropping of enrolled subject  <br>
    * Scholarship  <br>
    * Overpayment  <br>


    For reason of "overpayment", refund of the excess amount shall be considered only if the total fees for the semester is paid in "cash" or "in full" during registration. If "in installment", the excess amount shall be credited to the students for the next payment period. <br><br>

    Withdrawal/refund of deposit shall be allowed only for reasons of graduation from the University or transfer to another school, as the case maybe. """,



##################################################################################
#Dress code
    "What is the dress code of CvSU Bacoor",
    """All bona fide students of the University are expected and required to strictly comply with the institution’s dress code policy by wearing the officially prescribed school uniform during all regular school days. This policy applies to all students without exception, as wearing the proper uniform promotes discipline, unity, and a strong sense of belonging within the academic community.""",    



##################################################################################
#When is wash day?
    "Which day usually is wash day",
    """The washday is usually on Wednesday and Saturday where you can wear anything other than uniform.""",


##################################################################################
#when is uniform day?
    "Which day usually is uniform day",
    """Uniform day is usually Monday, Tuesday, Thursday, Friday and Sunday"""


##################################################################################
#Display of ID
    "What is COR",
    "Certification of Registrations. also known as a Certificate of Enrollment or Proof of School Enrollment, is an official document provided by the school confirming that the student is enrolled in that school.",


##################################################################################
#How to get COR
    "How do I get a Certification of Registration",
    "COR is given after you enroll in your specific course program. The COR Form is available upon request. ",


##################################################################################
#COR used for
    "What is a Certification of Registration is used for",
    "The Certification of Registration Form is used to prove that the student is enrolled in the University. You can also use the COR before you enter in the university, if there comes a circumtances that you forgot your ID/ or your ID hasnt been process yet. The COR Form is available upon request. ",



##################################################################################
#COR long lasted
    "How long does COR Form valid",
    "The Certificate of Registration (COR) is only valid until the end of the semester. You may request a new COR once the enrollment period for the new semester begins.",

##################################################################################
#COR Proof of Enrollment
    "Can COR forms be used as proof of enrollment",
    "Yes, the Certificate of Registration Form is an official document that can be used to prove that the student is enrolled in the university.",

##################################################################################
#is COR required
    "Is COR required to bring",
    "Yes, COR is required of every student. The students shall no be allowed to enter and use any facilities without COR or Student ID. If you're a visitor then you can write in the visitor handbook in Guard Post",


##################################################################################
#What is COG
    "What is the COG",
    "The Certificate of Grades is an official document issued by the university that shows a student's final grades for a specific semester or academic year. It is often used for academic verification, scholarships, or transfer applications.",


##################################################################################
#How COG
    "How can I request a Certificate of Grades?",
    "You can request it through the school’s registrar’s office, usually by filling out a request form and paying a society fee.",


##################################################################################
#When COG
    "When can I request a Certificate of Grades?",
    "You may request it after the semester has officially ended and all grades have been submitted and finalized by your professors.",



##################################################################################
#Is there Student ID
    "Is there an Student ID in CvSU Bacoor",
    "Currently, most students do not have their student IDs yet as the university is still processing them. However, the Certificate of Registration (COR) is accepted in the meantime.",



##################################################################################
#No ID Issue
    "Why don’t we have our Student IDs yet",
    "The university is still in the process of producing Student IDs for all students. Delays may happen due to the high volume of requests or processing requirements.",



##################################################################################
#When ID Available
    "When will the Student IDs be available",
    "The university will announce the release schedule once the IDs are ready. It’s best to regularly check official announcements or the registrar’s office for updates.",


##################################################################################
#When COR is lost
    "What should I do if I lose my COR before getting my Student ID",
    "You should request a reprint from the registrar’s office, usually for a small fee. Some universities may require a small processing fee for duplicate copies.",



##################################################################################
#Free Tuition
    "Does CvSU offer free tuition",
    """Yes. CvSU is one of the state universities in the Philippines covered under the Republic Act 10931 or the Universal Access to Quality Tertiary Education Act.
Qualified Filipino undergraduate students (new and continuing) can enjoy free tuition and other school fees in CvSU, provided they meet the following conditions:
<br><br>
-Must not have a previous undergraduate degree.
<br>
-Must pass the admission requirements.
<br>
-Must not exceed the maximum residency rule set by the university.
<br><br>
However, students may still need to pay minimal fees for other requirements like ID processing, uniforms, insurance, and special activities."""


##################################################################################
#Meaning of the CvSU logo

    "What is the meaning of the CvSU logo",
    "The book and the torch at the center of the seal symbolizes knowledge and wisdom.",

   

##################################################################################
#Parking advisory of cvsu parking
    "Can i park at anywhere near of CvSU Bacoor",
    """We strictly advise student NOT to park around the vicinity of CVSU - Bacoor City Campus and along Solidarity Route along Soldiers Hills IV(4) <br><br>

    The BTMO conducts continuous clearing operations to avoid blocking the driveways in the surrounding areas of Cavite State University - Bacoor City 𝗖𝗮𝗺𝗽𝘂𝘀. In connection with this, parking in the vicinity of the 𝗰𝗮𝗺𝗽𝘂𝘀 is strictly prohibited in pursuance of the policy.
    Students are encouraged to park in the right parking areas to avoid receiving parking tickets or violations.""",



##################################################################################
#Parking in parking area
    "Can i park at parking area of CvSU Bacoor",
    "Yes, the designated parking area at CvSU Bacoor is situated near the Vehicle Guard House entrance. For your safety and security, please ensure that your vehicle is properly locked and that you do not leave your keys inside.",



##################################################################################
#Entrance Exam For CvSU Bacoor
    "Is there an entrance exam for CvSU Bacoor",
    "Yes, Cavite State University (CvSU) Bacoor Campus typically requires incoming freshmen and transferees to take an entrance examination as part of the admission process. The entrance exam is designed to assess the applicants' academic readiness and ensure they are placed in programs where they can succeed. It usually covers fundamental subjects such as English, Mathematics, and Science, but the exact coverage can vary slightly depending on the academic year and any new policies set by the university.",




##################################################################################
#Reminder For Entrance Exam For CvSU Bacoor
    "What are important reminder before taking entrance exam for CvSU Bacoor",
    """ Here is the important reminder before taking entrance exam for CvSU Bacoor:<br><br>
To all examinees:<br>

Please be reminded of the following important guidelines to help ensure an orderly, smooth, and successful examination day:<br><br>

- Arrive at the testing venue at least thirty (30) minutes before your scheduled examination time.<br><br>

- Bring the following essential items: your examination permit, a valid identification card (ID), two (2) pencils, and an eraser.<br><br>

- Mobile phones, calculators, and other electronic devices are strictly prohibited inside the examination room.<br><br>

- Wear comfortable yet appropriate attire in accordance with the University's dress code.<br><br>

- Observe and comply with all health and safety protocols in place, if applicable.<br><br>

- Please ensure you have checked your assigned schedule and examination location prior to the exam day.<br><br>

- We extend our best wishes to all examinees. Believe in your abilities, stay focused, and perform to the best of your potential.<br>

""",



##################################################################################
#Shift Courses
    "How can I shift courses",
    """Students who wish to shift from their current academic program to another must carefully follow the official process set by the University. First, the student must prepare and submit a formal Letter of Intent to Shift, addressed to the head of their current department, clearly stating their reasons and motivations for requesting a program transfer.<br><br>

Following the submission of the letter, the student must secure a clearance from their current department. This clearance ensures that the student has no outstanding academic or financial obligations and is in good standing with the University. All necessary signatures and endorsements must be obtained as part of this step.<br><br>

After securing clearance, the student must seek approval from the Program Coordinator of the intended (receiving) academic program. The Program Coordinator will evaluate the student's academic records, credentials, and eligibility based on the specific requirements and standards of the program. Only after receiving formal approval from the receiving program will the shift be considered official.<br><br>

Students are highly encouraged to strictly follow these steps to avoid delays and ensure a smooth transition to their new program of study.""",



##################################################################################
#Mininum and Maximum academic load
    "What is the minimum and maximum academic load per semester",
    """The number of academic units a student is allowed to enroll in per semester generally depends on two main factors: the specific curriculum year they are following and their current academic standing within the University. Typically, students are permitted to enroll in a course load ranging from eighteen (18) to twenty-four (24) units per semester.
<br><br>
For students who are in good academic standing and are following the regular flow of their curriculum, it is common to enroll in the standard maximum number of units prescribed for their program, which often approaches twenty-four units. However, students with academic deficiencies, such as those on academic probation or who have received warnings, may be limited to a lighter load — sometimes closer to eighteen units — in order to help them focus on improving their academic performance.
<br><br>
In some cases, graduating students may also be allowed to take an overload of units, provided they meet certain requirements and obtain approval from their respective academic department or program head.
<br><br>
It is always advisable for students to consult with their academic adviser or program coordinator each enrollment period to ensure they are enrolling in the appropriate number of units based on their individual situation and the University's policies.""",


##################################################################################
#Get Student ID
    "How can I get my Student ID",
    """Student Identification Cards (IDs) are officially issued to enrolled students after they have successfully completed the enrollment process. The distribution schedule and related instructions are typically announced by the Registrar’s Office through official University communication channels, such as bulletin boards, the University's website, or official social media pages.
<br><br>
The issuance of the student ID serves as an important step in formally recognizing the student's active status within the University. It also provides students with access to various campus facilities, services, and academic resources. Students are advised to regularly monitor announcements from the Registrar’s Office to stay updated on the specific dates, venues, and requirements for claiming their IDs.
<br><br>
To ensure a smooth process, students may be required to present proof of enrollment, such as a copy of their registration form or enrollment slip, along with other necessary documents when claiming their ID. It is important for students to follow the given instructions carefully to avoid any delays or inconveniences.""",



##################################################################################
#Failed a prerequisite subject
    "What happens if I fail a subject",
    """If you fail a subject, you are required to retake and pass the course before you are allowed to enroll in any subsequent subject that depends on it. Prerequisites are carefully set by the University to ensure that students have the necessary background and skills to succeed in higher-level courses.
<br><br>
In many cases, if the failed prerequisite subject is only offered once per academic year, you may have to wait until the following school year to retake it. This can cause a delay in your academic progress, especially if the prerequisite is critical for a series of other subjects.
<br><br>
It is also important to understand that even if you are already classified as a 4th-year student, you may still be required to enroll in and complete lower-year (1st-year) subjects that you were not able to pass previously. Your academic year standing (e.g., 2nd year, 3rd year, 4th year) does not exempt you from completing all required courses under your curriculum.
<br><br>
For this reason, students are strongly advised to prioritize passing all prerequisite courses early in their studies and to seek academic support if they are struggling. Regular consultation with academic advisers or program coordinators can also help you plan your subjects carefully and avoid unnecessary delays in your journey toward graduation.""",


##################################################################################
#Many Absences are allowed
    "How many absences are allowed",
    """Students are required to maintain regular and consistent attendance in all their enrolled classes as part of their academic responsibilities. Absences must not exceed twenty percent (20%) of the total number of class hours scheduled for each subject throughout the semester.
<br><br>
Should a student's total number of absences go beyond this 20 percent limit, regardless of the reason, the instructor or the University administration reserves the right to officially drop the student from the course. Being dropped due to excessive absences may negatively affect your academic record and could also delay your progress toward fulfilling the requirements for graduation.
<br><br>
It is therefore strongly advised that students attend all classes diligently and, if unavoidable circumstances arise (such as illness or emergencies), promptly communicate with their instructors and submit any necessary documentation to explain their absences. Staying proactive and responsible in managing attendance is essential for maintaining good academic standing and ensuring successful completion of your courses.""",


##################################################################################
#Uniform CvSU
    "Is there a school uniform at CvSU Bacoor",
    """Yes, all students are required to wear the officially prescribed school uniforms on designated school days as part of the University's dress code policy. Wearing the proper uniform fosters a sense of discipline, equality, and school identity among the student body. Students must strictly adhere to this policy during regular academic days, from Monday to Saturday.
<br><br>
However, the University also designates specific days known as "wash days," during which students are allowed to wear appropriate civilian attire instead of their school uniforms. At Cavite State University Bacoor Campus, Wednesdays and Saturdays are officially recognized as wash days. On these days, while uniforms are not required, students are still expected to dress neatly and modestly, in accordance with the University's guidelines for proper attire.
<br><br>
Students are reminded to observe these dress code rules carefully and to always present themselves in a manner that reflects the dignity and values of the institution.""",



##################################################################################
#Stricly ID and Uniforms
    "Are IDs and uniforms strictly required inside the campus",
    """Yes, Student Identification Cards (IDs) and the officially prescribed uniforms are both strictly required within the campus at all times, as part of the University’s efforts to maintain a disciplined, professional, and cohesive environment for all students. The wearing of the student ID is essential for several reasons, including providing access to various campus facilities, ensuring security, and confirming the student’s enrollment status. The ID also helps faculty and staff easily identify students, which contributes to the overall safety and orderliness of the campus.
<br><br>
As for the uniform, it is an integral part of the University’s dress code policy and is designed to promote equality and foster a sense of pride and identity among students. Students are expected to wear their uniforms during regular school days, except on designated “wash days,” which are usually Wednesdays and Saturdays, when students may opt to wear casual attire, though still following the University’s guidelines for neatness and appropriateness.
<br><br>
Failure to wear the required uniform or carry the student ID while on campus may result in the student being denied entry into certain areas, such as classrooms, libraries, or laboratories, and could even lead to disciplinary actions. Therefore, it is essential for students to always carry their IDs and wear their uniforms correctly when on campus, as this is part of upholding the values of discipline, respect, and professionalism that the University seeks to instill in its students.
<br><br>
Students who have lost their IDs or have issues with their uniforms are encouraged to immediately report to the Registrar’s Office or the appropriate campus authorities to resolve these matters and avoid any disruptions to their academic activities.""",



##################################################################################
#Join Student Organization
    "How do I join student organizations",
    """Joining a student organization at the University is an excellent way to enhance your academic experience, develop new skills, and build a network of peers who share your interests and passions. The process for joining student organizations generally involves several steps, which are designed to help you find the best fit for your personal and academic goals.
<br><br>
First and foremost, it’s important to research the different student organizations available at the University. These organizations cover a wide range of interests, from academic clubs, leadership groups, and volunteer organizations, to hobby-based, cultural, and sports clubs. Many student organizations host interest meetings or orientation events at the beginning of each semester where you can learn more about their objectives, activities, and membership requirements. These meetings are an excellent opportunity to ask questions and determine if the organization aligns with your interests.
<br><br>
Once you’ve found an organization that you would like to join, you typically need to fill out a membership application form. This form is often available through the organization’s official social media pages, the Student Affairs Office, or the student organization’s booth during university events like organization fairs. The application may ask for basic personal information, academic standing, and your reasons for wanting to join the group.
<br><br>
After submitting your application, some organizations may require interviews, entrance exams, or other selection processes to ensure that members are fully committed and capable of contributing to the group’s activities. However, many organizations welcome all students, regardless of experience or background, and simply ask that you attend a few initial meetings or participate in an introductory event before officially becoming a member.
<br><br>
It’s also essential to remember that active participation is key in student organizations. Once you become a member, you will be expected to attend regular meetings, participate in events, and contribute to projects or activities, depending on the organization’s purpose. Some organizations may also ask for a nominal membership fee to help fund their events, activities, or initiatives, but this fee is generally affordable and goes towards the upkeep of the club’s operations.
<br><br>
Lastly, it’s important to stay informed about upcoming opportunities to join organizations, especially during Club Week or Student Organization Recruitment events held at the beginning of each semester. Keep an eye on campus bulletin boards, official university websites, and social media accounts for announcements about these events.
<br><br>
Joining a student organization is an enriching part of university life that offers a chance to meet like-minded individuals, develop valuable skills, and contribute to the campus community. Don’t hesitate to get involved and explore the many opportunities available to you!

""",



##################################################################################
#Appeal Failing Grade
    "How can I appeal a failing grade",
    """If you receive a failing grade, the first step is to talk directly with your teacher. Schedule a meeting to discuss your performance and ask for specific feedback on what went wrong. Be respectful and open to suggestions for improvement. If you feel the grade was unfair or there was a grading error, provide supporting evidence, like completed assignments or tests, to clarify your case.
<br><br>
If the issue isn’t resolved after discussing it with your instructor, you may consider filing a formal grade appeal. Review the University’s grade appeal policy, submit a written appeal with your reasons and any relevant documents, and wait for the decision. However, starting with a conversation with your teacher is often the best way to address the situation.""",



##################################################################################
#Wi-Fi in Campus
    "Is there Wi-Fi on campus",
    """Yes, there is Wi-Fi available on campus for students, faculty, and staff. To access it, you'll need to use login credentials that are provided by the IT department. These credentials are typically given to you when you enroll, and they help ensure that only authorized users can connect to the network. If you have any trouble accessing the Wi-Fi or need new login details, you can contact the IT department for assistance.""",



##################################################################################
#Dormitories in CvSU
    "Are there dormitories available at CvSU Bacoor",
    """Currently, there are no dormitories provided directly on the CvSU Bacoor campus. However, students who need accommodation for their studies typically find boarding houses or rentals in the nearby areas. These boarding houses are usually located within a short distance from the campus, making them convenient for students who prefer to live off-campus while attending classes.
<br><br>
These nearby boarding houses offer various types of living arrangements, with options to fit different budgets and preferences. Some may offer shared rooms, while others provide private rooms, and many also include basic amenities such as internet access, furniture, and access to kitchen facilities. It’s advisable for students to visit and inspect these boarding houses before committing to a rental agreement to ensure that the accommodations meet their needs in terms of comfort, safety, and accessibility to the campus.
<br><br>
While the University does not offer on-campus dormitories, it does provide information and support to help students find suitable housing options. Students can check with the Student Affairs Office or local real estate listings for recommendations on reputable boarding houses in the vicinity of the campus.
<br><br>
For those who are new to the area or living away from home for the first time, it’s important to consider factors such as transportation, security, and proximity to essential services when choosing a place to stay.""",



##################################################################################
#Vehicle in Campus
    "Can I bring my vehicle to campus",
    """Yes, students and faculty are allowed to bring their vehicles to campus. However, it’s important to note that the number of available parking slots is limited, and during peak hours or busy days, finding an available space might be challenging. The University strives to accommodate as many vehicles as possible, but due to the limited parking capacity, it’s advisable to arrive early to secure a spot, especially if you are driving during high-traffic times such as the start of the school day or when major events are taking place on campus.
<br><br>
In addition to the limited availability, students who wish to park their vehicles on campus may be required to pay a parking fee. This fee helps maintain the campus infrastructure and ensures that parking spaces are properly managed and monitored. The exact cost of parking may vary, so it is advisable to check with the campus authorities or parking office for the latest rates and payment methods.
<br><br>
On the other hand, if you choose to use a bicycle to get to campus, parking for bicycles is free. The University encourages eco-friendly modes of transportation, and there are designated bicycle racks and parking areas available around the campus for students who prefer this sustainable option. Bicycles offer a convenient and cost-effective way to navigate the campus, especially for those living nearby or for those looking to avoid the hassle of finding a parking spot.
<br><br>
For students planning to bring a vehicle, it’s also a good idea to familiarize yourself with the campus parking rules and regulations to ensure a smooth and trouble-free experience. Be sure to park in designated areas and follow any signage regarding parking restrictions to avoid fines or towing.""",


##################################################################################
#Official Receipt for Payment
    "Where can I get my Official Receipt for payments",
    """After making any payment at the University, whether it’s for tuition, fees, or other expenses, you can obtain your Official Receipt from the Cashier’s Office. The Official Receipt is an important document that serves as proof of your payment and is often required for record-keeping, verification, and future reference.
<br><br>
To get your Official Receipt, simply proceed to the Cashier’s Office after completing your payment. The office is typically located in a central area of the campus, and the staff there will assist you in issuing the receipt. Be sure to bring a valid payment slip or transaction details to help the cashier quickly locate your payment record in their system.
<br><br>
In most cases, the Cashier’s Office will issue the Official Receipt immediately after processing your payment. If you made an online payment, you may be required to present a copy of the transaction confirmation or receipt of the online transfer before receiving the official document.
<br><br>
It’s always a good idea to keep your Official Receipt in a safe place, as you may need it for various administrative purposes, such as claiming refunds, submitting financial reports, or resolving any payment discrepancies. If you ever lose your Official Receipt, you can go back to the Cashier’s Office, where they can assist in issuing a duplicate copy based on the payment record.
<br><br>
For more specific details about payment methods or the Cashier’s Office schedule, it’s advisable to check the University’s website or contact the office directly.""",


##################################################################################
#Graduate with academic deficiencies
    "Can I graduate with academic deficiencies",
    """No, you cannot graduate with academic deficiencies. In order to be eligible for graduation, it is essential that all subjects, including any back subjects (courses that you may have failed or not completed within the required time), must be successfully cleared. This means that you are required to retake and pass any subjects that were either failed or left incomplete during your academic journey before you can officially graduate.
<br><br>
Clearing these subjects is important because the University’s graduation requirements are designed to ensure that students have met all the necessary academic standards and have gained the knowledge and skills expected for their degree program. Academic deficiencies are viewed as obstacles to fulfilling these standards, and the University cannot award a degree until all the required coursework is completed.
<br><br>
If you have back subjects, it is your responsibility to work with the academic department or course instructors to make arrangements for retaking the courses. This might include enrolling in special summer classes, attending remedial classes, or following the proper procedures to resolve any incomplete grades.
<br><br>
Students who have academic deficiencies are encouraged to address them promptly to avoid delays in their graduation timeline. The University often has academic advisors or counselors who can provide guidance on how to clear these deficiencies and how to manage your course load in subsequent semesters.
<br><br>
In cases where clearing back subjects is not possible within the usual timeline, it’s important to discuss your options with the Registrar’s Office or your program coordinator. They can help you understand how to proceed with the necessary steps to ensure that you are on track for graduation.
<br><br>
Ultimately, clearing academic deficiencies is a necessary part of the graduation process, and students must take proactive steps to complete all required courses to earn their degree.""",

##################################################################################
#When is Graduation
    "When is the CvSU Bacoor Recognition or Graduation ceremony",
    """The CvSU Bacoor Recognition or Graduation Ceremony is typically held around June to September, though the exact date may vary depending on the academic calendar for that year. The ceremony marks an important milestone in the academic journey of students who have successfully completed their degree programs, and it is a highly anticipated event for graduates, their families, and the entire University community.
<br><br>
The specific timing of the ceremony is determined by several factors, including the University’s academic schedule, the completion of final grades, and the availability of key personnel who participate in the event. The academic calendar may shift slightly each year due to various reasons such as holidays, administrative decisions, or changes in the school year schedule. Therefore, it’s important for graduating students to keep an eye on official announcements from the University, particularly from the Registrar’s Office or the Student Affairs Office, as they will provide the official date and detailed information regarding the ceremony.
<br><br>
In the months leading up to the ceremony, students who are set to graduate will receive information about graduation requirements, such as clearance from departments, the submission of final academic records, and the payment of necessary fees. Graduates will also be informed about the procedures for participating in the ceremony, including the rehearsals, dress code, and other logistical details to ensure a smooth and memorable event.
<br><br>
The Recognition Ceremony is an exciting occasion not only for the graduates themselves but also for their families and friends who are present to celebrate their achievements. It’s a time to reflect on the hard work and dedication that led to this accomplishment and to officially mark the end of one chapter while beginning a new one.
<br><br>
To ensure you have all the necessary details for the ceremony, it is highly recommended to regularly check the official announcements from the University and follow any instructions provided for graduates.""",



##################################################################################


##################################################################################
#
]  
#corpus
#ChatterBotCorpusTrainer = ChatterBotCorpusTrainer(bot)
#corpusend
list_trainer = ListTrainer(bot)
list_trainer.train(list_to_train)
#corpus
#ChatterBotCorpusTrainer.train('chatterbot.corpus.english')
#corpusend