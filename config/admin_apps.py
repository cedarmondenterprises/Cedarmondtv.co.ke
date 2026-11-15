from django.contrib.admin.apps import AdminConfig


class NewsroomAdminConfig(AdminConfig):
    default_site = 'config.admin_site.NewsroomAdminSite'
