import math
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, unique=True)
    credit_cost = models.PositiveIntegerField(default=5)
    home_shelf_code = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_copies(self) -> int:
        return self.copies.count()

    @property
    def available_copies(self) -> int:
        return self.copies.exclude(status=BookCopy.Status.CHECKED_OUT).count()

    def __str__(self):
        return self.title


class BookCopy(models.Model):
    class Status(models.TextChoices):
        ON_SHELF = "ON_SHELF", "On Shelf"
        UNDER_DESK = "UNDER_DESK", "Under Desk"
        CHECKED_OUT = "CHECKED_OUT", "Checked Out"

    barcode = models.CharField(max_length=64, unique=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ON_SHELF)

    @property
    def current_location_display(self) -> str:
        if self.status == self.Status.UNDER_DESK:
            return "Under Your Desk"
        if self.status == self.Status.ON_SHELF:
            return f"Shelf {self.book.home_shelf_code}"
        return "Checked Out"

    def __str__(self):
        return f"{self.barcode} - {self.book.title}"


class BorrowLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrow_logs")
    copy = models.ForeignKey(BookCopy, on_delete=models.CASCADE, related_name="borrow_logs")
    planned_days = models.PositiveIntegerField(default=10)
    credits_charged = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    borrowed_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-borrowed_at"]

    @property
    def due_date(self):
        return self.borrowed_at + timedelta(days=self.planned_days)

    @property
    def is_overdue(self) -> bool:
        return self.returned_at is None and timezone.now() > self.due_date

    def calculate_final_credits(self) -> Decimal:
        end_time = self.returned_at or timezone.now()
        elapsed_seconds = max(0.0, (end_time - self.borrowed_at).total_seconds())
        actual_days = max(1, math.ceil(elapsed_seconds / 86400))

        base = Decimal(self.copy.book.credit_cost)
        planned = Decimal(self.planned_days)
        per_day = base / planned

        if actual_days <= self.planned_days:
            total = base
        elif actual_days <= 2 * self.planned_days:
            extra_days = Decimal(actual_days - self.planned_days)
            total = base + (extra_days * per_day)
        else:
            extra_days = Decimal(actual_days - (2 * self.planned_days))
            total = (Decimal(2) * base) + (extra_days * Decimal("0.5") * per_day)

        return round(total, 2)