from django.test import TestCase
from django.contrib.auth import get_user_model
from api.models import Notification
from lead_management.models import lead_management, Customer
from quotation.models import Quotation
import datetime

User = get_user_model()

class NotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword",
            first_name="Test",
            last_name="User"
        )
        self.staff_user = User.objects.create_user(
            email="staffuser@example.com",
            password="staffpassword",
            first_name="Staff",
            last_name="User",
            is_staff=True
        )
        self.customer = Customer.objects.create(
            name="Test Customer",
            email="customer@example.com",
            contact_number="1234567890"
        )

    def test_notification_creation(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type="OTHER",
            title="Test Title",
            description="Test Description",
            tag="TEST"
        )
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.title, "Test Title")
        self.assertFalse(notification.is_read)

    def test_lead_signal_on_creation(self):
        lead = lead_management.objects.create(
            customer=self.customer,
            lead_source="other",
            status="open",
            assign_to=self.user
        )
        notif = Notification.objects.filter(recipient=self.user, notification_type="LEAD").first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.title, "New Enquiry / Lead Added")
        self.assertEqual(notif.reference_id, lead.id)
        
        staff_notif = Notification.objects.filter(recipient=self.staff_user, notification_type="LEAD").first()
        self.assertIsNotNone(staff_notif)

    def test_lead_signal_on_reassignment(self):
        lead = lead_management.objects.create(
            customer=self.customer,
            lead_source="other",
            status="open"
        )
        staff_notif = Notification.objects.filter(recipient=self.staff_user, notification_type="LEAD").first()
        self.assertIsNotNone(staff_notif)

        lead.assign_to = self.user
        lead.save()

        user_notif = Notification.objects.filter(recipient=self.user, notification_type="LEAD", tag="ASSIGNED").first()
        self.assertIsNotNone(user_notif)
        self.assertEqual(user_notif.title, "New Lead Assigned")

    def test_overdue_checks(self):
        lead = lead_management.objects.create(
            customer=self.customer,
            lead_source="other",
            status="open",
            assign_to=self.user,
            followup_date=datetime.date.today() - datetime.timedelta(days=2)
        )
        
        from api.views import NotificationViewSet
        view = NotificationViewSet()
        
        view.check_and_create_overdue_followups(self.user)
        notif = Notification.objects.filter(recipient=self.user, tag='OVERDUE', reference_id=lead.id).first()
        self.assertIsNotNone(notif)
        
        # update followup date to future
        lead.followup_date = datetime.date.today() + datetime.timedelta(days=2)
        lead.save()
        
        view.check_and_create_overdue_followups(self.user)
        notif = Notification.objects.filter(recipient=self.user, tag='OVERDUE', reference_id=lead.id).first()
        self.assertIsNone(notif)
