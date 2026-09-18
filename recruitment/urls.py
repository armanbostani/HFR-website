from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    # Accounts
    path('accounts/signup/', views.signup, name='signup'),
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='recruitment/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', views.account_router, name='account_router'),

    # Password reset (emails print to the console in development)
    path('accounts/password-reset/', auth_views.PasswordResetView.as_view(
        template_name='recruitment/password_reset.html',
        email_template_name='recruitment/password_reset_email.txt',
        subject_template_name='recruitment/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='password_reset'),
    path('accounts/password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='recruitment/password_reset_done.html',
    ), name='password_reset_done'),
    path('accounts/password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='recruitment/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('accounts/password-reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='recruitment/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Applicant
    path('apply/', views.applicant_dashboard, name='applicant_dashboard'),
    path('apply/form/', views.apply, name='apply'),
    path('apply/redeem/', views.redeem_code, name='redeem_code'),

    # Onboarding + members
    path('onboarding/', views.onboarding, name='onboarding'),
    path('members/', views.member_home, name='member_home'),
    path('members/dashboard/', views.member_dashboard, name='member_dashboard'),
    path('members/profile/', views.edit_profile, name='edit_profile'),

    # Forum (Discourse): the members' entry point and the single sign-on endpoint
    path('forum/', views.forum, name='forum'),
    path('forum/sso/', views.discourse_connect, name='discourse_connect'),

    # Team leads
    path('recruitment/dashboard/', views.lead_dashboard, name='lead_dashboard'),
    path('recruitment/application/<int:app_id>/cv/', views.application_cv, name='application_cv'),
    path('recruitment/application/<int:app_id>/<str:action>/', views.lead_action, name='lead_action'),
]
