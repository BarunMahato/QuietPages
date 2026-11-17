from rest_framework import serializers
from .models import Book, BookCopy, BorrowLog


class BookCopySerializer(serializers.ModelSerializer):
    location = serializers.CharField(source="current_location_display", read_only=True)

    class Meta:
        model = BookCopy
        fields = ["id", "barcode", "book", "status", "location"]


class BookSerializer(serializers.ModelSerializer):
    total_copies = serializers.IntegerField(source="total_copies_count", read_only=True)
    available_copies = serializers.IntegerField(source="available_copies_count", read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "isbn",
            "credit_cost",
            "home_shelf_code",
            "total_copies",
            "available_copies",
        ]


class BorrowLogSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="copy.book.title", read_only=True)
    barcode = serializers.CharField(source="copy.barcode", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    due_date = serializers.DateTimeField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = BorrowLog
        fields = [
            "id",
            "user",
            "username",
            "copy",
            "barcode",
            "book_title",
            "planned_days",
            "credits_charged",
            "borrowed_at",
            "due_date",
            "returned_at",
            "is_overdue",
        ]
        read_only_fields = ["id", "credits_charged", "borrowed_at", "returned_at"]