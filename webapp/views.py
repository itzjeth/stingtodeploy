from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import admin
from django.shortcuts import render,redirect, get_object_or_404
from django.db.models import Q
from django.db import connection, transaction
from webapp.forms import UserForm,ReviewForm,AdminForm 
from webapp.models import  Users,Review,Admin,ChatHistory
#from chatterbot import ChatBot
from chatterbot.comparisons import LevenshteinDistance
from chatterbot.response_selection import get_most_frequent_response
from django.utils.safestring import mark_safe
#from chatterbot.trainers import ListTrainer
from django.templatetags.static import static
from django.contrib import messages
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
from difflib import SequenceMatcher
"""{% load static %}"""
import json
import datetime
import random
import string
cursor = connection.cursor()








     
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

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import ChatHistory
import json

@login_required
def save_chat_history(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            messages = data.get("messages", [])
            title = data.get("title", "Untitled Chat")

            chat = ChatHistory(user=request.user, title=title)
            chat.set_messages(messages)  # ✅ use model helper
            chat.save()

            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid method"}, status=400)


@login_required
def get_chat_histories(request):
    chats = ChatHistory.objects.filter(user=request.user).order_by('-created_at')
    data = []
    for chat in chats:
        try:
            messages = chat.get_messages()  # ✅ use model helper
        except (ValueError, TypeError):
            messages = []

        data.append({
            "id": chat.id,
            "title": chat.title,
            "created_at": chat.created_at.strftime("%b %d, %Y %H:%M"),
            "messages": messages
        })

    return JsonResponse(data, safe=False)













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
@transaction.atomic
def send_review_email(request, pk):
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect('review_list')

    review = get_object_or_404(Review, pk=pk)

    try:
        # 1) Generate new password and save to Review
        new_password = generate_random_password()
        review.password = new_password
        review.save()
        print(f"[send_review_email] Review {review.pk} saved with new password.")

        # 2) Create or update Users entry
        user_obj = Users.objects.filter(userEmail=review.email).first()
        if user_obj:
            user_obj.userPass = new_password
            user_obj.userName = review.user
            user_obj.save()
            created = False
            print(f"[send_review_email] Existing user updated: {user_obj.userEmail}")
        else:
            user_obj = Users.objects.create(
                userName=review.user,
                userEmail=review.email,
                userPass=new_password,
                userImage='profile_images/default.png'
            )
            created = True
            print(f"[send_review_email] New Users record created: {user_obj.userEmail}")

        # 3) Send the email
        subject = "Your Sting Chatbot Access Account"
        message = (
            f"Hello {review.user},\n\n"
            f"Your account has been {'created' if created else 'updated'} as a {review.user_status}.\n\n"
            f"Here are your login details:\n"
            f"Username: {review.email}\n"
            f"Password: {new_password}\n\n"
            f"Please keep these credentials safe.\n\n"
            f"– STING CHATBOT –"
        )

        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [review.email], fail_silently=False)
            print(f"[send_review_email] Email sent to {review.email}")
        except Exception as mail_err:
            print("[send_review_email] Email sending failed:", mail_err)
            messages.warning(request, f"Account {'created' if created else 'updated'}, but email failed to send.")

        # 4) Delete the review after sending the email
        review.delete()
        print(f"[send_review_email] Review {pk} deleted after email sent.")

        # 5) Feedback to admin UI
        messages.success(request, f"✅ Email sent and account processed for {review.email}.")

    except Exception as e:
        print("[send_review_email] ERROR:", e)
        messages.error(request, "❌ An error occurred while creating the account or sending the email.")
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

            # 1️⃣ Generate random password
            random_password = generate_random_password()

            # 2️⃣ Save password into Review record
            review.password = random_password
            review.save()

            # 3️⃣ Create a new user automatically in TB_Users
            Users.objects.create(
                userName=review.user,
                userEmail=review.email,
                userPass=random_password,  # store as plain text (or hash if desired)
                userImage='profile_images/default.png'  # default image
            )

            # 4️⃣ Send email with credentials
            subject = "Your Sting Chatbot Access Account"
            message = (
                f"Hello {review.user},\n\n"
                f"Your account has been created successfully as a {review.user_status}.\n\n"
                f"Here are your login details:\n"
                f"Username: {review.email}\n"
                f"Password: {random_password}\n\n"
                f"Please keep these credentials safe.\n\n"
                f"– STING CHATBOT –"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [review.email], fail_silently=False)

            messages.success(request, f"✅ Access request created and account generated for {review.email}.")
            return redirect('review_list')
        else:
            messages.error(request, "⚠️ Invalid form data. Please review and try again.")
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
@transaction.atomic
def edit_profile(request):
    user_email = request.session.get('CustId')
    user = get_object_or_404(Users, userEmail=user_email)

    if request.method == 'POST':
        user.userName = request.POST.get('userName')

        if 'userImage' in request.FILES:
            user.userImage = request.FILES['userImage']

        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password or confirm_password:
            if new_password != confirm_password:
                messages.error(request, "⚠️ Passwords do not match.")
                return render(request, 'pages/edit_profile.html', {'user': user})
            else:
                user.userPass = new_password
                messages.success(request, "🔒 Password updated successfully.")

        user.save()

        request.session['user_name'] = user.userName
        request.session['user_image'] = (
            user.userImage.url if user.userImage else '/media/profile_images/default.png'
        )

        messages.success(request, "✅ Profile updated successfully.")
        return render(request, 'pages/edit_profile.html', {'user': user})

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
     #ENROLLMENT REQUIREMENTS
    {
        "patterns": [
            "What are the basic enrollment requirements", "requirements for enrollment", "general requirements",
            "cvsu bacoor enrollment needs", "documents needed to enroll"
        ],
        "response": "To enroll at Cavite State University (CvSU) Bacoor Campus, applicants must secure several essential documents. These typically include a completed Application Form, original and photocopies of Form 138 (for incoming freshmen), Certified True Copy of grades (for transferees), PSA Birth Certificate, Certificate of Good Moral Character, and a 1x1 or 2x2 ID photo. Students also need to undergo confirmation of slot, pay the required school fees, and attend orientation sessions. The campus may also request additional documents depending on the program or student classification."
    },
    {
        "patterns": [
            "form 138 requirement", "report card needed", "is form 138 required",
            "high school card cvsu bacoor", "form 138 for enrollment"
        ],
        "response": "Yes, Form 138 or the Senior High School Report Card is a mandatory requirement for all incoming freshman students at CvSU Bacoor Campus. This document verifies that the student successfully completed Grade 12 and includes the learner’s academic performance, final grades, and school details. The school requires both the original and photocopy during validation. Students must ensure all grades are complete and that the form is signed by the school registrar or principal to avoid delays in enrollment."
    },
    {
        "patterns": [
            "psa birth certificate", "birth certificate requirement", "do i need my psa",
            "psa needed for enrollment", "submit birth certificate"
        ],
        "response": "CvSU Bacoor Campus requires a PSA-issued Birth Certificate for all enrolling students. This document confirms the applicant’s identity, date of birth, and citizenship, which are essential for school records. Students must present the original document for verification and submit a photocopy. The PSA Birth Certificate must be clear, unalterred, and legible. If errors exist, students may be asked to provide supporting documents or correction proof."
    },
    {
        "patterns": [
            "certificate of good moral", "good moral requirement", "is good moral needed",
            "good moral cvsu bacoor", "moral certificate"
        ],
        "response": "Yes, all applicants must submit a Certificate of Good Moral Character issued by their previous school. CvSU Bacoor uses this certificate to ensure that the applicant has exhibited proper behavior and discipline. The certificate must be signed by an authorized school official, usually the guidance counselor or principal. Expired or unsigned certificates may not be accepted, so students should request a newly issued one if needed."
    },
    {
        "patterns": [
            "id picture requirement", "photo requirement", "what size of id picture",
            "cvsu photo requirement", "2x2 picture enrollment"
        ],
        "response": "Students enrolling in CvSU Bacoor Campus must submit recent ID pictures, typically either 1x1 or 2x2 depending on the program's instructions. The photo must have a plain background, preferably white, and the student should be wearing decent attire. These photos are used for student records, forms, and identification during campus transactions. It is recommended to bring extra copies for contingencies."
    },
    {
        "patterns": [
            "requirements for transferees", "transferee enrollment cvsu", "transferee documents",
            "cvsu bacoor transferee requirements", "transfer student requirements"
        ],
        "response": "Transferees must submit several documents including an Honorable Dismissal, Transcript of Records or Certified True Copy of Grades, Certificate of Good Moral Character, PSA Birth Certificate, and ID pictures. They must also undergo an evaluation process where the campus checks which subjects can be credited. Some programs may require transferees to take an interview or qualifying exam. Once evaluated and accepted, the student may proceed with enrollment."
    },
    {
        "patterns": [
            "honorable dismissal", "do transferees need honorable dismissal", "transfer credentials",
            "honorable dismissal requirement", "leaving school document"
        ],
        "response": "Yes, an Honorable Dismissal is required for transferees enrolling at CvSU Bacoor Campus. This document certifies that the student has officially left their previous institution and is allowed to continue their studies elsewhere. It must be issued by the school registrar. Without it, the campus cannot proceed with the full admission process, especially in crediting subjects or validating academic history."
    },
    {
        "patterns": [
            "tor requirement", "transcript of records", "tor for transferee",
            "need tor for enrollment", "tor cvsu bacoor"
        ],
        "response": "Transferees must present their Transcript of Records (TOR) or at least a Certified True Copy of Grades for evaluation. CvSU Bacoor uses this document to determine whether the applicant meets the academic requirements and which subjects can be credited. The TOR must be clear, updated, and signed by the registrar. Students should check for missing grades since incomplete records may delay the evaluation process."
    },
    {
        "patterns": [
            "requirements for shifters", "shifting requirements", "cvsu shifting process",
            "shifter documents", "change course requirements"
        ],
        "response": "Shifters—students already enrolled at CvSU but seeking to change programs—must secure a Shifting Form, updated grades, evaluation from their current department, and approval from the target department. Additional requirements may include interviews or passing certain prerequisites. Shifters must also ensure they have no pending balances or academic deficiencies before the shift is approved."
    },
    {
        "patterns": [
            "requirements for foreign students", "international student", "foreign applicant cvsu",
            "foreign student documents", "alien enrollment"
        ],
        "response": "Foreign students must submit a valid passport, student visa, Alien Certificate of Registration (ACR I-Card), authenticated academic records, Certificate of Good Moral Character, and English proficiency certification depending on their background. CvSU Bacoor may also require evaluation of foreign transcripts and payment of special processing fees. All documents must be authenticated according to DFA or embassy protocols."
    },
    {
        "patterns": [
            "medical requirements", "medical certificate", "physical exam cvsu",
            "health requirements", "medical check enrollment"
        ],
        "response": "CvSU Bacoor may require a Medical Certificate for specific programs, especially those related to health sciences or technical fields. The medical assessment ensures that students are fit to participate in academic and campus activities. The certificate must come from a licensed physician and may include tests such as CBC, urinalysis, and chest X-ray depending on university guidelines."
    },
    {
        "patterns": [
            "requirements for balik aral", "returning student", "returnee enrollment",
            "balik aral documents", "come back student cvsu"
        ],
        "response": "Returning students or ‘balik-aral’ enrollees must update their records by submitting an Application for Re-admission, previous grades, and clearance from their last attended semester. They must also settle any outstanding obligations. If they have been away for several years, the department may require an interview, evaluation, or additional documentation to ensure academic continuity."
    },
    {
        "patterns": [
            "requirements for second courser", "second course enrollment", "another degree cvsu",
            "2nd coursers requirements", "taking another program"
        ],
        "response": "Second coursers must submit their TOR showing completion of their first degree, along with a Certificate of Good Moral Character, ID photos, and PSA Birth Certificate. They may also undergo evaluation depending on program prerequisites. Some subjects may be credited if aligned with the new program. Interviews or qualifying exams may be required depending on the department’s standards."
    },
    {
        "patterns": [
            "grade requirement", "minimum grade required", "grade cutoff",
            "passing grade for admission", "cvsu grade requirement"
        ],
        "response": "CvSU Bacoor Campus typically requires applicants to have passing grades in all core subjects, especially Math, English, and Science depending on their chosen program. While the university is not strict on grade cut-offs for general admission, competitive programs may impose higher academic standards. Students with failing grades may undergo additional screening or interviews."
    },
    {
        "patterns": [
            "age requirement", "minimum age enrollment", "can i enroll at this age",
            "age limit cvsu", "age requirement admission"
        ],
        "response": "CvSU Bacoor Campus does not impose strict age limits for admission. As long as the student can provide complete documents and meets academic requirements, they may enroll regardless of age. However, legal-age specifications may apply when signing documents or consent forms. Minors may need parental consent for official transactions."
    },
    {
        "patterns": [
            "is entrance exam required", "cvsu bacoor entrance exam", "do i need exam to enroll",
            "admission test requirement", "is there exam for enrollment"
        ],
        "response": "CvSU Bacoor Campus does not regularly require an entrance exam for most undergraduate programs. However, this may depend on university-wide announcements, program demand, and academic policies for the school year. Some programs with high competition may require screening, interviews, or qualifying assessments. Applicants should always check the latest updates from the campus to confirm whether an exam is needed."
    },

    {
        "patterns": [
            "is interview required", "interview for enrollment", "do i need interview cvsu",
            "program interview requirement", "screening interview"
        ],
        "response": "Certain programs at CvSU Bacoor Campus require interviews to determine if the applicant is suited for the chosen course. Interviews may evaluate communication skills, motivation, and academic readiness. The department may also ask about career goals and previous academic experiences. Not all programs require this step, but applicants should be prepared in case interviews are scheduled."
    },

    {
        "patterns": [
            "is reservation required", "slot reservation cvsu", "do I need to reserve slot",
            "reservation fee", "cvsu slot confirmation"
        ],
        "response": "CvSU Bacoor sometimes requires students to reserve their slot after admission confirmation, especially for high-demand programs. This ensures that the student secures a seat before the enrollment period. Reservation may involve submitting preliminary documents or attending orientation sessions. In some cases, a reservation form or payment of minimal campus fees may be required."
    },

    {
        "patterns": [
            "requirements for online enrollment", "online enrollment process", "what to upload online",
            "digital submission requirements", "cvsu online requirements"
        ],
        "response": "For online enrollment, students are typically required to upload scanned copies or clear photographs of essential documents such as Form 138, PSA Birth Certificate, Good Moral Certificate, and ID pictures. The files should be readable and submitted in formats like JPG or PDF. Students must follow instructions properly because blurred or incomplete submissions often lead to delays in validation."
    },

    {
        "patterns": [
            "original documents or photocopy", "is original needed", "photocopy acceptable",
            "submit original documents", "document authenticity"
        ],
        "response": "CvSU Bacoor requires both original and photocopies of major documents. Original copies are used only for verification and will be returned immediately. Photocopies are submitted for official records. The student must ensure that photocopies are clear and complete, including signatures, school stamps, and important details. Failure to present originals during verification may prevent completion of enrollment."
    },

    {
        "patterns": [
            "requirements for scholarship", "scholarship documents cvsu", "apply for scholarship",
            "scholarship requirements", "financial aid cvsu bacoor"
        ],
        "response": "Scholarship applicants must submit additional documents such as income tax returns, barangay certificates of residency or indigency, and academic records showing outstanding grades. Some scholarships require recommendation letters or proof of extracurricular achievements. The CvSU Scholarship Office also evaluates applicants through interviews or screening, depending on the type of scholarship applied for."
    },

    {
        "patterns": [
            "requirements for voucher students", "SHS voucher requirement", "voucher for cvsu",
            "does cvsu accept voucher", "voucher guidelines"
        ],
        "response": "Senior High School graduates with government vouchers must submit their voucher certificate or applicable ESC/PEAC documentation when enrolling. This document verifies their scholarship status and eligibility for certain financial assistance programs. CvSU Bacoor will validate the authenticity of the voucher and check if it applies to their program. It is important that students keep a clear digital and physical copy of the voucher."
    },

    {
        "patterns": [
            "requirements for late enrollment", "late enrollment cvsu", "can I enroll late",
            "late enrollees requirements", "enrollment deadline cvsu bacoor"
        ],
        "response": "Late enrollees must secure approval from the registrar and their department chairperson. They must present complete documents and may need to write a request letter explaining the reason for late enrollment. Availability of slots and program schedules will also affect approval. The campus may impose strict cut-off dates, so it is advised to enroll early whenever possible."
    },

    {
        "patterns": [
            "requirements for bridging subjects", "bridging program", "take bridging courses",
            "bridging subjects cvsu", "additional academic requirements"
        ],
        "response": "Some students, especially transferees or second coursers, may be required to take bridging subjects if their previous academic background does not match CvSU’s curriculum. The department evaluates their records and decides which bridging subjects are necessary. Students must enroll in these subjects before proceeding to higher-level courses. These requirements ensure that all students meet the academic standards of the program."
    },

    {
        "patterns": [
            "do i need barangay clearance", "barangay certificate requirement", "residency proof",
            "barangay card for enrollment", "community document"
        ],
        "response": "Barangay Clearance is not a standard requirement for all students enrolling at CvSU Bacoor. However, certain scholarships, financial aid programs, or specific academic requirements may request it. If requested, the certificate should confirm the student's address and good standing in the community."
    },

    {
        "patterns": [
            "parent consent requirement", "minor student requirements", "under 18 enrollment",
            "parental consent cvsu", "legal guardian consent"
        ],
        "response": "Students under 18 may need to submit a Parent or Guardian Consent Form when enrolling at CvSU Bacoor. This document allows the university to proceed with admission processes involving minors. It also ensures that parents are aware of the student’s academic obligations. The form must be signed and may require photocopies of the parent’s ID."
    },

    {
        "patterns": [
            "requirements for changing campus", "transfer campus cvsu", "shift to cvsu bacoor",
            "intercampus transfer requirements", "campus transfer cvsu"
        ],
        "response": "Students transferring from one CvSU campus to another must secure a Campus Transfer Form, updated grades, and evaluation from their current department. They must also obtain clearance from the campus they are leaving to ensure no pending obligations. The receiving campus (CvSU Bacoor) will evaluate whether slots are available and if the student meets program requirements."
    },

    {
        "patterns": [
            "do i need credentials for evaluation", "subject evaluation requirement", "crediting subjects",
            "evaluation documents", "grades needed for evaluation"
        ],
        "response": "Applicants who want to credit their previous subjects must present official documents such as a TOR, certified grade copies, and course descriptions. These documents allow CvSU Bacoor to determine which subjects align with their curriculum. Without complete documents, crediting cannot proceed. The evaluation process ensures fairness and accuracy in determining equivalent subjects."
    },

    {
        "patterns": [
            "course description requirement", "do I need syllabus", "subject description cvsu",
            "course outline required", "evaluation of subjects"
        ],
        "response": "Transferees and second coursers may be asked to submit course descriptions or syllabi of subjects taken from previous institutions. This helps the department evaluate whether the content matches CvSU’s curriculum. The documents should be official copies from the previous school and include detailed topics, units, and learning outcomes."
    },

    {
        "patterns": [
            "is ncae required", "ncae exam", "ncae requirement cvsu",
            "national career assessment exam", "need ncae"
        ],
        "response": "The National Career Assessment Examination (NCAE) is not a strict requirement for CvSU Bacoor enrollment. However, some programs may use NCAE results for guidance purposes, especially when evaluating student strengths and appropriate courses. If requested, students should present their NCAE certificate or results slip."
    },

    {
        "patterns": [
            "requirements for working students", "working student enrollment", "employed student requirements",
            "work certificate cvsu", "enroll while working"
        ],
        "response": "Working students are not required to present employment documents for enrollment unless applying for scholarships or flexible schedule arrangements. CvSU Bacoor allows working students to enroll normally as long as they meet all academic requirements. However, they should check class schedules early to avoid conflicts with their work hours."
    },

    {
        "patterns": [
            "wifi or email requirement", "email needed for enrollment", "gmail account cvsu",
            "cvsu email requirement", "communication requirement"
        ],
        "response": "Applicants need an active email address, preferably Gmail, to complete the enrollment process at CvSU Bacoor. The university uses email for sending confirmation messages, instructions, and enrollment updates. Students must ensure that their email is accessible, secure, and regularly checked for notifications."
    },

    {
        "patterns": [
            "dress code for id picture", "attire for id requirement", "what to wear for id photo",
            "id picture dress code", "photo attire cvsu"
        ],
        "response": "Students must wear decent clothing in their ID pictures. Sleeveless shirts, hats, sunglasses, or distracting accessories are not allowed. The photo should have a plain background, and the student should appear neat and presentable. Proper attire ensures that the student’s image meets the campus identification standards."
    },

    {
        "patterns": [
            "requirements for honor students", "with honors requirement", "honor graduate priority",
            "academic awardee cvsu", "honor certificate enrollment"
        ],
        "response": "Honor graduates may present their certificates or proofs of academic awards when enrolling at CvSU Bacoor, especially if applying for scholarships or priority admission. While honors are not required for general enrollment, they may qualify students for special programs or benefits. The campus may request authenticated documents to verify honors."
    },

    {
        "patterns": [
            "requirements for college freshman", "freshman documents", "grade 12 graduates enrollment",
            "requirements for first year", "new student cvsu bacoor"
        ],
        "response": "College freshmen must submit Form 138, PSA Birth Certificate, Certificate of Good Moral Character, ID pictures, and any additional documents required by their chosen program. They must complete the campus's validation and orientation procedures. Freshmen should also ensure that their academic records are complete, with all grades showing and properly signed by school officials."
    },

    {
        "patterns": [
            "requirements for als passers", "als graduate enrollment", "als certificate",
            "als equivalency", "alternative learning cvsu"
        ],
        "response": "ALS passers must submit their ALS Certificate of Completion and the official Accreditation and Equivalency (A&E) Test Results. These documents serve as proof that the student meets the equivalent qualifications of a high school graduate. Additional requirements such as Good Moral Certificate and ID pictures also apply. ALS students may undergo initial evaluation to determine readiness for college-level coursework."
    },

    {
        "patterns": [
            "requirements for cross enrollees", "cross enrollment cvsu", "take subjects in cvsu",
            "cross enrolling student", "temp student cvsu bacoor"
        ],
        "response": "Cross enrollees must present a Cross Enrollment Permit issued by their home school. This document grants permission to take certain subjects at CvSU Bacoor. They must also submit photocopies of their school ID, registration form, and endorsement letter from their department. After verification, they can proceed with subject enrollment depending on slot availability."
    },

    {
        "patterns": [
            "requirements for ojt students", "ojt enrollment", "internship requirements cvsu",
            "ojt documents", "on the job training"
        ],
        "response": "OJT students may be required to submit updated grades, medical certificates, waivers, and endorsement forms before being allowed to enroll in OJT subjects. They must also attend orientations and comply with program-specific requirements such as resume submission or NBI clearance depending on partner companies. The OJT coordinator will provide instructions regarding placements and documentation."
    },

    {
        "patterns": [
            "requirements for married students", "marriage certificate", "change surname cvsu",
            "married student document", "update civil status"
        ],
        "response": "Married students who wish to update their records must submit their Marriage Certificate from PSA along with a request form to change their surname or civil status. This update ensures accurate identification for official documents, IDs, and transcripts. The campus registrar will process the update as long as photocopies and originals are provided for verification."
    },

    {
        "patterns": [
            "what if documents incomplete", "incomplete requirements", "missing documents cvsu",
            "can i enroll without requirements", "document deficiency"
        ],
        "response": "If applicants have incomplete requirements, they must contact the admissions office to determine if temporary enrollment or conditional acceptance is possible. CvSU Bacoor may allow students to enroll conditionally while waiting for certain documents, but strict deadlines must be followed. Failure to submit missing records may result in cancellation of enrollment."
    },

    {
        "patterns": [
            "how many id pictures required", "number of photos", "id picture count",
            "how many pictures cvsu", "photo quantity requirement"
        ],
        "response": "CvSU Bacoor typically requires 2-4 pieces of 1x1 or 2x2 ID photos. These are used for enrollment forms, student identification, and university records. Students should bring extra copies in case additional documents require attachment. It is always better to prepare more than the minimum to avoid delays."
    },

    {
        "patterns": [
            "requirements for guardian enrollment", "can someone enroll for me", "proxy enrollment",
            "guardian submit documents", "representative enrollment"
        ],
        "response": "A designated guardian may enroll on behalf of the student by presenting an Authorization Letter signed by the student, along with photocopies of both the student's and guardian's valid IDs. All required documents must be complete to avoid delays. Some steps, like interviews or online account verification, may still require the student's personal appearance."
    },

    {
        "patterns": [
            "requirements for returnees with failing grades", "failed subjects", "failed student enrollment",
            "readmission failing grades", "academic deficiency"
        ],
        "response": "Students with failing grades who wish to return must undergo evaluation from their department. They may be required to retake failed subjects, attend academic counseling, or meet certain grade requirements before being allowed to re-enroll. The registrar may also request updated records to determine academic standing. Departments prioritize students who show commitment to improving their performance."
    },

    {
        "patterns": [
            "requirements for graduating shs", "grade 12 graduating", "not yet form 138",
            "enrolling without card", "pending report card"
        ],
        "response": "Students who are graduating from Senior High School but have not yet received Form 138 must wait for the official release of their report card. CvSU Bacoor requires the complete and signed Form 138 for enrollment validation. Temporary certificates or incomplete cards are usually not accepted. Students should coordinate with their SHS registrar for expedited release of documents."
    },

    {
        "patterns": [
            "requirements for special cases", "unique situations enrollment", "special documents cvsu",
            "exception cases", "special enrollment permissions"
        ],
        "response": "Special cases such as students with special needs, displaced students, or applicants with unusual circumstances may require additional documents depending on university policy. These may include medical assessments, affidavits, or special endorsements. CvSU Bacoor reviews each case individually to ensure fairness while maintaining academic standards."
    },

    {
        "patterns": [
            "do I need NBI clearance", "nbi for enrollment", "background check cvsu",
            "nbi requirement", "police clearance"
        ],
        "response": "NBI Clearance is not required for general enrollment at CvSU Bacoor. However, certain programs, OJT applications, or scholarship requirements may request NBI or Police Clearance. Students should prepare these documents only if specifically requested by their department or program coordinator."
    },

    {
        "patterns": [
            "requirements for ID issuance", "student ID cvsu", "ID card requirements",
            "school ID documents", "ID registration"
        ],
        "response": "To obtain their official CvSU student ID, students must provide their enrollment slip, recent ID pictures, and validated personal information. The ID serves as the primary proof of enrollment and is used for campus access, library transactions, and examinations. Students should double-check spelling and personal details before issuance to avoid incorrect entries."
    },

    {
        "patterns": [
            "requirements for enrollment confirmation", "confirm slot cvsu", "slot confirmation",
            "enrollment confirmation step", "how to confirm enrollment"
        ],
        "response": "Enrollment confirmation requires students to submit validated documents, settle necessary fees (if applicable), and receive confirmation from the registrar. Some programs may require attending orientation or signing acknowledgment forms before the slot is officially reserved. Confirmation ensures that the student is included in class lists and system records."
    },

    {
        "patterns": [
            "requirements for proof of identity", "what valid id needed", "valid id requirement",
            "proof of identity cvsu", "id for enrollment"
        ],
        "response": "Students must present at least one valid ID during enrollment for identity verification. Acceptable IDs include school IDs, national IDs, passports, or any government-issued card. If a student has no government ID, they may use their SHS ID along with their PSA Birth Certificate as supporting identity documents."
    },

    {
        "patterns": [
            "final list of requirements", "complete enrollment requirements", "all documents needed",
            "checklist cvsu bacoor", "what to prepare for enrollment"
        ],
        "response": "The complete set of enrollment requirements for CvSU Bacoor Campus generally includes Form 138 (for freshmen), PSA Birth Certificate, Certificate of Good Moral Character, ID pictures, valid ID, and additional documents depending on student classification (transferee, ALS passer, foreign student, etc.). Students must undergo document validation, follow the enrollment schedule, and secure confirmation from the registrar. Ensuring that all documents are complete and accurate helps prevent delays and guarantees smooth admission."
    }
]    

def fuzzy_match(user_message, threshold=0.55):
    """Compares user's message to question patterns. Returns best matching response."""
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
    """
    Original GET-based endpoint adapted to use QA_DATA with fuzzy matching.
    Returns HttpResponse with safe HTML.
    """
    user_message = request.GET.get('userMessage', '')
    if not user_message:
        return HttpResponse(mark_safe("Please provide a message."))

    # Fuzzy search for best response
    chat_response = fuzzy_match(user_message)

    if chat_response is None:
        chat_response = "I'm sorry, I couldn’t find an answer to that. " \
                        "Please try rephrasing or ask about CvSU Bacoor services."

    return HttpResponse(mark_safe(chat_response))

# Optional: POST-based JSON endpoint for AJAX requests
def chatbot_response(request):
    if request.method == "POST":
        user_message = request.POST.get("message", "")
        answer = fuzzy_match(user_message)
        if not answer:
            answer = "I'm sorry, I couldn’t find an answer to that. " \
                     "Please try rephrasing or ask about CvSU Bacoor services."
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