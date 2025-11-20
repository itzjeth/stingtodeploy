from django.contrib import admin
from django.urls import path, include
from webapp import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webapp/', include('webapp.urls')),
    path('addReview',views.userReview),
    path('addUser',views.userAdd),
    path('dologin',views.doLogin, name="dologin"),
    path('logout',views.doLogout),
    path('getUser/<int:userId>',views.getUser),
    path('editprofile/<int:userId>',views.showUserInfo),
   #path('editUser/<int:userId>',views.updateUser),



  



] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

