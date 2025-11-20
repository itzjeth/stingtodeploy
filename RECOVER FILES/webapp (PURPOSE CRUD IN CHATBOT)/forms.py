from django import forms  
from webapp.models import Review, Users, Admin, ChatPair


            
class ReviewForm(forms.ModelForm):  
    class Meta:  
        model = Review
        exclude = ['status']  # ✅ Exclude status from the form

class UserForm(forms.ModelForm):  
    class Meta:  
        model = Users
        fields = "__all__"  

class AdminForm(forms.ModelForm):
	class Meta:
		model = Admin
		fields  = "__all__"		
          

class ChatPairForm(forms.ModelForm):
    class Meta:
        model = ChatPair
        fields = ['question', 'answer']



