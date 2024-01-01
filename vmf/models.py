from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator,RegexValidator
from django.utils import timezone

class Vendor(models.Model):
    name = models.CharField(max_length=100)
    contact_details = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    vendor_code = models.CharField(max_length=50, unique=True)
    vendor_code = models.CharField(max_length=6, unique=True, 
            validators=[RegexValidator(regex='^[A-Z0-9]*$',
     message='Vendor code must consist of uppercase letters and numbers only.'),
     MinValueValidator(6, message='Vendor code must be exactly 6 characters long.'),
    ])
    on_time_delivery_rate = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    quality_rating_avg = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    average_response_time = models.FloatField(default=0, validators=[MinValueValidator(0)])
    fulfillment_rate = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    def calculate_on_time_delivery_rate(self):
        completed_pos = self.purchaseorder_set.filter(status='completed')
        on_time_delivered_pos = completed_pos.filter(delivery_date__lte=timezone.now())
        
        if completed_pos.exists():
            self.on_time_delivery_rate = (on_time_delivered_pos.count() / completed_pos.count()) * 100
        else:
            self.on_time_delivery_rate = 0

    def update_quality_rating_avg(self):
        completed_pos = self.purchaseorder_set.filter(status='completed', quality_rating__isnull=False)
        
        if completed_pos.exists():
            quality_rating_sum = completed_pos.aggregate(models.Avg('quality_rating'))['quality_rating__avg']
            self.quality_rating_avg = quality_rating_sum
        else:
            self.quality_rating_avg = 0

    def calculate_average_response_time(self):
        acknowledged_pos = self.purchaseorder_set.filter(acknowledgment_date__isnull=False)
        
        if acknowledged_pos.exists():
            response_times = [(po.acknowledgment_date - po.issue_date).total_seconds() / 3600 for po in acknowledged_pos]
            average_response_time = sum(response_times) / len(response_times)
            self.average_response_time = average_response_time
        else:
            self.average_response_time = 0

    def calculate_fulfillment_rate(self):
        all_pos = self.purchaseorder_set.all()
        successful_pos = all_pos.filter(status='completed', quality_rating__isnull=True)
        
        if all_pos.exists():
            self.fulfillment_rate = (successful_pos.count() / all_pos.count()) * 100
        else:
            self.fulfillment_rate = 0

    def clean(self):
        if self.quality_rating_avg > 5:
            raise ValidationError("Quality rating should be between 0 and 5.")

class PurchaseOrder(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    po_number = models.CharField(max_length=50, unique=True)
    order_date = models.DateTimeField(default=timezone.now)
    delivery_date = models.DateTimeField()
    items = models.JSONField()
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=50)
    quality_rating = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
    issue_date = models.DateTimeField(default=timezone.now)
    acknowledgment_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.vendor.calculate_on_time_delivery_rate()
        self.vendor.update_quality_rating_avg()
        self.vendor.calculate_average_response_time()
        self.vendor.calculate_fulfillment_rate()
        self.vendor.save()

class HistoricalPerformance(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    on_time_delivery_rate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    quality_rating_avg = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    average_response_time = models.FloatField(validators=[MinValueValidator(0)])
    fulfillment_rate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])



# from django.db import models
# from django.utils import timezone
# from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
# from django.core.exceptions import ValidationError
# from django.db.models.signals import post_save
# from django.dispatch import receiver

# class Vendor(models.Model):
#     name = models.CharField(max_length=100)
#     contact_details = models.TextField()
#     address = models.TextField()
#     vendor_code = models.CharField(max_length=6, unique=True, validators=[RegexValidator(regex='^[A-Z0-9]*$', message='Vendor code must consist of uppercase letters and numbers only.')])

#     on_time_delivery_rate = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
#     quality_rating_avg = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
#     average_response_time = models.FloatField(default=0, validators=[MinValueValidator(0)])
#     fulfillment_rate = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

#     def clean(self):
#         if len(self.vendor_code) != 6:
#             raise ValidationError("Vendor code must be exactly 6 characters long.")

# @receiver(post_save, sender=Vendor)
# def create_vendor_metrics(sender, instance=None, created=False, **kwargs):
#     if created:
#         instance.on_time_delivery_rate = 0
#         instance.quality_rating_avg = 0
#         instance.average_response_time = 0
#         instance.fulfillment_rate = 0
#         instance.save()

# class PurchaseOrder(models.Model):
#     vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
#     po_number = models.CharField(max_length=50, unique=True)
#     order_date = models.DateTimeField(default=timezone.now)
#     delivery_date = models.DateTimeField()
#     items = models.JSONField()
#     quantity = models.IntegerField(validators=[MinValueValidator(1)])
#     status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('cancelled', 'Cancelled')])
#     quality_rating = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
#     issue_date = models.DateTimeField(default=timezone.now)
#     acknowledgment_date = models.DateTimeField(null=True, blank=True)

#     def clean(self):
#         if self.delivery_date and self.delivery_date < self.order_date:
#             raise ValidationError("Delivery date cannot be earlier than order date.")
#         if self.status == 'completed' and not self.acknowledgment_date:
#             raise ValidationError("Completed orders must have an acknowledgment date.")

# @receiver(post_save, sender=PurchaseOrder)
# def update_vendor_metrics(sender, instance=None, created=False, **kwargs):
#     if created or instance.status == 'completed':
#         instance.vendor.calculate_on_time_delivery_rate()
#         instance.vendor.update_quality_rating_avg()
#         instance.vendor.calculate_average_response_time()
#         instance.vendor.calculate_fulfillment_rate()
#         instance.vendor.save()

# class HistoricalPerformance(models.Model):
#     vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
#     date = models.DateTimeField(default=timezone.now)
#     on_time_delivery_rate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
#     quality_rating_avg = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)])
#     average_response_time = models.FloatField(validators=[MinValueValidator(0)])
#     fulfillment_rate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
