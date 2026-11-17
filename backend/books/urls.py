from django.urls import path
from .views import (
    BookCopyDetailAPIView,
    BookCopyGetPostAPIView,
    BookDetailAPIView,
    BookListCreateAPIView,
    BorrowLogListAPIView,
    IssueBookAPIView,
    ReturnBookAPIView,
)

app_name = "books"

urlpatterns = [
    path("", BookListCreateAPIView.as_view(), name="book-list-create"),
    path("<int:pk>/", BookDetailAPIView.as_view(), name="book-detail"),
    path("copies/", BookCopyGetPostAPIView.as_view(), name="copy-list-create"),
    path("copies/<int:pk>/", BookCopyDetailAPIView.as_view(), name="copy-detail"),
    path("transactions/", BorrowLogListAPIView.as_view(), name="transaction-list"),
    path("transactions/issue/", IssueBookAPIView.as_view(), name="book-issue"),
    path("transactions/<int:pk>/return/", ReturnBookAPIView.as_view(), name="book-return"),
]