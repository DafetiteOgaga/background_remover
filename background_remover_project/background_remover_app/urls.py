from django.urls import path
from . import views

app_name = "background_remover_app"

urlpatterns = [
	# Create your urlpatterns here.
	path('api/test/', views.test_api),
	path("", views.remove_background, name="remove-background"),
    path("bulk/", views.remove_background_bulk, name="remove-background-bulk"),
    path("bulk-wurl/", views.remove_background_bulk_wurl, name="remove-background-bulk-wurl"),
]
