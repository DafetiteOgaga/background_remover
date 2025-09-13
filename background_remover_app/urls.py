from django.urls import path
from . import views

app_name = "background_remover_app"

urlpatterns = [
	# Create your urlpatterns here.
	path("", views.test_api),
	path("background-remover/", views.remove_background, name="remove-background"),
    path("background-remover/bulk/", views.remove_background_bulk, name="remove-background-bulk"),
    path("background-remover/bulk-wurl/", views.remove_background_bulk_wurl, name="remove-background-bulk-wurl"),
]
