from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsLibrarian, IsLibrarianOrReadOnly, is_librarian_user
from .models import Book, BookCopy, BorrowLog
from .serializers import BookCopySerializer, BookSerializer, BorrowLogSerializer


class BookListCreateAPIView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    def get(self, request):
        queryset = Book.objects.annotate(
            total_copies_count=Count("copies", distinct=True),
            available_copies_count=Count(
                "copies",
                filter=~Q(copies__status=BookCopy.Status.CHECKED_OUT),
                distinct=True,
            ),
        ).order_by("-id")
        if query:= request.query_params.get("search"):
            queryset = queryset.filter(Q(title__icontains=query) | Q(author__icontains=query) | Q(isbn__icontains=query))
        return Response(BookSerializer(queryset, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = BookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookDetailAPIView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    def get_object(self, pk):
        return get_object_or_404(Book.objects.prefetch_related("copies"), pk=pk)

    def get(self, request, pk):
        book = self.get_object(pk)
        return Response(BookSerializer(book).data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        book = self.get_object(pk)
        serializer = BookSerializer(book, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        book = self.get_object(pk)
        serializer = BookSerializer(book, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        self.get_object(pk).delete()
        return Response({"message" : "Content Deleted"})


class BookCopyGetPostAPIView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    def get(self, request):
        queryset = BookCopy.objects.select_related("book").order_by("-id")
        book_id = request.query_params.get("book")
        barcode = request.query_params.get("barcode")
        if book_id :
            queryset = queryset.filter(book_id=book_id)
        if barcode:
            queryset = queryset.filter(barcode__icontains=barcode)
        return Response(BookCopySerializer(queryset, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = BookCopySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookCopyDetailAPIView(APIView):
    permission_classes = [IsLibrarianOrReadOnly]

    def get_object(self, pk):
        return get_object_or_404(BookCopy.objects.select_related("book"), pk=pk)

    def get(self, request, pk):
        copy = self.get_object(pk)
        return Response(BookCopySerializer(copy).data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        copy = self.get_object(pk)
        serializer = BookCopySerializer(copy, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        copy = self.get_object(pk)
        serializer = BookCopySerializer(copy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        self.get_object(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BorrowLogListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = BorrowLog.objects.select_related("copy__book", "user")
        if not is_librarian_user(request.user):
            queryset = queryset.filter(user=request.user)
        elif user_id := request.query_params.get("user_id"):
            queryset = queryset.filter(user_id=user_id)

        active = request.query_params.get("active")
        if active == "true":
            queryset = queryset.filter(returned_at__isnull=True)
        elif active == "false":
            queryset = queryset.filter(returned_at__isnull=False)

        return Response(BorrowLogSerializer(queryset, many=True).data, status=status.HTTP_200_OK)


class IssueBookAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        if not is_librarian_user(request.user) or "user" not in data:
            data["user"] = request.user.id

        serializer = BorrowLogSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        copy_id = serializer.validated_data["copy"].id
        target_user = serializer.validated_data["user"]

        with transaction.atomic():
            copy = BookCopy.objects.select_for_update().select_related("book").get(pk=copy_id)
            if copy.status == BookCopy.Status.CHECKED_OUT:
                return Response({"message": "Copy is already checked out."}, status=status.HTTP_400_BAD_REQUEST)

            if target_user.available_credits < copy.book.credit_cost:
                return Response({"message": "Insufficient available credits."}, status=status.HTTP_400_BAD_REQUEST)

            copy.status = BookCopy.Status.CHECKED_OUT
            copy.save(update_fields=["status"])
            serializer.save()

        return Response({"message" : "Successfully issued a book"}, status=status.HTTP_201_CREATED)


class ReturnBookAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        new_status = request.data.get("status", BookCopy.Status.ON_SHELF)
        if new_status not in (BookCopy.Status.ON_SHELF, BookCopy.Status.UNDER_DESK):
            return Response({"detail": "Invalid return status."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            bookinfo = get_object_or_404(
                BorrowLog.objects.select_for_update().select_related("copy__book", "user"),
                pk=pk,
            )
            if not is_librarian_user(request.user) and bookinfo.user_id != request.user.id:
                return Response({"detail": "Not authorized to return this book."}, status=status.HTTP_403_FORBIDDEN)

            if bookinfo.returned_at is not None:
                return Response({"detail": "Already returned."}, status=status.HTTP_400_BAD_REQUEST)

            bookinfo.returned_at = timezone.now()
            bookinfo.credits_charged = bookinfo.calculate_final_credits()
            bookinfo.save(update_fields=["returned_at", "credits_charged"])

            bookinfo.user.total_credits_spent += bookinfo.credits_charged
            bookinfo.user.save(update_fields=["total_credits_spent"])

            bookinfo.copy.status = new_status
            bookinfo.copy.save(update_fields=["status"])

        return Response({"message": "Book returned successfully"}, status=status.HTTP_200_OK)
