from django.urls import path, include
from . import views
urlpatterns = [
    path ('', views.home_page, name="home"),
    path ('sting/', views.chatbot_page, name="chatbot"),
    path ('dashboard/', views.dashboard_page, name="dashboard"),
    path ('userHome/', views.userHomePage, name="userHome"),
    path('addUser',views.userAdd),
    path('dologin',views.doLogin, name="dologin"),
    path('logout',views.doLogout, name="logout"),
    path ('getResponse', views.getResponse, name="getResponse"),
    path('getUser/<int:userId>',views.getUser),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('base/', views.user_list, name='base'),
    path('base/users/', views.user_list, name='user_list'),
    path('base/users/add/', views.user_add, name='user_add'),
    path('base/users/edit/<int:id>/', views.user_edit, name='user_edit'),
    path('base/users/delete/<int:id>/', views.user_delete, name='user_delete'),
    path('addReview',views.userReview, name="addReview"),
    path('reviews/', views.review_list, name='review_list'),
    path('reviews/add/', views.review_create, name='review_add'),
    path('reviews/edit/<int:pk>/', views.review_update, name='review_edit'),
    path('reviews/delete/<int:pk>/', views.review_delete, name='review_delete'),
    path('reviews/send-email/<int:pk>/', views.send_review_email, name='send_review_email'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path("save_chat/", views.save_chat_history, name="save_chat"),
    path("get_chats/", views.get_chat_histories, name="get_chats"),
    path("chat_page/", views.chat_page, name="chat_page"),
    path("chatbot/", views.chatbot_response, name="chatbot"),

 
]


	
   
   

   
   
  
   
   
   



    