from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.archive, name="archive"),
    path("archive/", views.archive, name="archive-list"),
    path("article/new/", views.create_post, name="create_post"),
    re_path(r"^article/(?P<article_id>\d+)/$", views.get_article, name="get_article"),
    path("finance/", views.financial_dashboard, name="financial-dashboard"),
]
