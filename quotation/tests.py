from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta

from .models import (
    ServiceManagementRecord,
    TechnicianWorkRecord,
    AMCContract,
    AMCServiceVisit,
)
from api.models import Role

User = get_user_model()


class CompletedWorkListTestCase(TestCase):
    """Test completed work list functionality."""

    def setUp(self):
        """Create test data."""
        # Create roles
        self.technician_role, _ = Role.objects.get_or_create(name='technician')
        self.admin_role, _ = Role.objects.get_or_create(name='admin')

        # Create users
        self.technician = User.objects.create_user(
            email='tech@test.com',
            mobile_no='9876543210',
            password='testpass123',
            role=self.technician_role
        )

        self.admin = User.objects.create_user(
            email='admin@test.com',
            mobile_no='9876543211',
            password='testpass123',
            role=self.admin_role,
            is_staff=True
        )

        # Create test service
        self.service = ServiceManagementRecord.objects.create(
            customer_name='Test Customer',
            customer_phone='9876543210',
            customer_email='test@test.com',
            customer_address='123 Test St',
            contract_type='one_time',
            service_type='Installation',
            contract_status='active',
            service_frequency_count=1,
            service_start_date=date.today(),
            service_end_date=date.today() + timedelta(days=5),
        )

        # Setup API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_work_record_completion_adds_to_list(self):
        """Test that marking a work record as completed adds it to list."""
        # Create work record
        work = TechnicianWorkRecord.objects.create(
            technician=self.technician,
            service_record=self.service,
            customer_name=self.service.customer_name,
            customer_phone=self.service.customer_phone,
            customer_address=self.service.customer_address,
            work_date=date.today(),
            payment_status='pending',
        )

        # Initially not in completed list
        response = self.client.get('/api/amc/completed-work/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.json()
        work_ids = [item['id'] for item in items]
        self.assertNotIn(f'w-{work.id}', work_ids)

        # Mark as completed
        response = self.client.patch(
            f'/api/amc/technician-work-records/{work.id}/',
            {'payment_status': 'completed'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Now should be in list
        response = self.client.get('/api/amc/completed-work/')
        items = response.json()
        work_ids = [item['id'] for item in items]
        self.assertIn(f'w-{work.id}', work_ids)

    def test_service_closes_when_all_work_completed(self):
        """Test service auto-closes after all work marked completed."""
        # Create 2 work records for service
        work1 = TechnicianWorkRecord.objects.create(
            technician=self.technician,
            service_record=self.service,
            customer_name=self.service.customer_name,
            customer_phone=self.service.customer_phone,
            customer_address=self.service.customer_address,
            work_date=date.today(),
            payment_status='pending',
        )

        work2 = TechnicianWorkRecord.objects.create(
            technician=self.technician,
            service_record=self.service,
            customer_name=self.service.customer_name,
            customer_phone=self.service.customer_phone,
            customer_address=self.service.customer_address,
            work_date=date.today(),
            payment_status='pending',
        )

        # Mark first as completed
        self.client.patch(
            f'/api/amc/technician-work-records/{work1.id}/',
            {'payment_status': 'completed'},
            format='json'
        )

        # Service should still be active
        self.service.refresh_from_db()
        self.assertEqual(self.service.contract_status, 'active')

        # Mark second as completed
        self.client.patch(
            f'/api/amc/technician-work-records/{work2.id}/',
            {'payment_status': 'completed'},
            format='json'
        )

        # Service should now be closed
        self.service.refresh_from_db()
        self.assertEqual(self.service.contract_status, 'closed')

        # Service should appear in completed list
        response = self.client.get('/api/amc/completed-work/')
        items = response.json()
        service_ids = [item['id'] for item in items if item['kind'] == 'one_time_service']
        self.assertIn(f's-{self.service.id}', service_ids)

    def test_service_does_not_close_with_pending_work(self):
        """Test service doesn't close if work records remain pending."""
        # Create 2 work records
        TechnicianWorkRecord.objects.create(
            technician=self.technician,
            service_record=self.service,
            customer_name=self.service.customer_name,
            customer_phone=self.service.customer_phone,
            customer_address=self.service.customer_address,
            work_date=date.today(),
            payment_status='pending',
        )

        work2 = TechnicianWorkRecord.objects.create(
            technician=self.technician,
            service_record=self.service,
            customer_name=self.service.customer_name,
            customer_phone=self.service.customer_phone,
            customer_address=self.service.customer_address,
            work_date=date.today(),
            payment_status='pending',
        )

        # Mark only one as completed
        self.client.patch(
            f'/api/amc/technician-work-records/{work2.id}/',
            {'payment_status': 'completed'},
            format='json'
        )

        # Service should remain active
        self.service.refresh_from_db()
        self.assertEqual(self.service.contract_status, 'active')

        # Service should NOT appear in completed list
        response = self.client.get('/api/amc/completed-work/')
        items = response.json()
        service_ids = [item['id'] for item in items if item['kind'] == 'one_time_service']
        self.assertNotIn(f's-{self.service.id}', service_ids)

    def test_amc_contract_closes_when_all_visits_completed(self):
        """Test AMC contract auto-closes after all visits completed."""
        # Create AMC contract
        contract = AMCContract.objects.create(
            customer_id=1,
            amc_type='Quarterly',
            amc_start_date=date.today(),
            amc_end_date=date.today() + timedelta(days=365),
            amc_value=50000,
            status='ACTIVE',
        )

        # Create 2 service visits
        visit1 = AMCServiceVisit.objects.create(
            amc_contract=contract,
            visit_number=1,
            planned_date=date.today(),
            status=AMCServiceVisit.STATUS_SCHEDULED,
        )

        visit2 = AMCServiceVisit.objects.create(
            amc_contract=contract,
            visit_number=2,
            planned_date=date.today() + timedelta(days=90),
            status=AMCServiceVisit.STATUS_SCHEDULED,
        )

        # Create work records for both visits
        work1 = TechnicianWorkRecord.objects.create(
            technician=self.technician,
            service_record=self.service,
            customer_name='AMC Customer',
            customer_phone='9876543210',
            customer_address='123 AMC St',
            work_date=date.today(),
            payment_status='pending',
            amc_service_visit=visit1,
        )

        work2 = TechnicianWorkRecord.objects.create(
            technician=self.technician,
            service_record=self.service,
            customer_name='AMC Customer',
            customer_phone='9876543210',
            customer_address='123 AMC St',
            work_date=date.today() + timedelta(days=90),
            payment_status='pending',
            amc_service_visit=visit2,
        )

        # Complete first work
        self.client.patch(
            f'/api/amc/technician-work-records/{work1.id}/',
            {'payment_status': 'completed'},
            format='json'
        )

        # Contract should still be ACTIVE
        contract.refresh_from_db()
        self.assertEqual(contract.status, 'ACTIVE')

        # Complete second work
        self.client.patch(
            f'/api/amc/technician-work-records/{work2.id}/',
            {'payment_status': 'completed'},
            format='json'
        )

        # Contract should now be CLOSED
        contract.refresh_from_db()
        self.assertEqual(contract.status, 'CLOSED')

        # Contract should appear in completed list
        response = self.client.get('/api/amc/completed-work/')
        items = response.json()
        contract_ids = [item['id'] for item in items if item['kind'] == 'amc_contract']
        self.assertIn(f'c-{contract.id}', contract_ids)

    def test_frequency_count_validation(self):
        """Test service only closes when frequency count is met."""
        service = ServiceManagementRecord.objects.create(
            customer_name='Multi-Visit Customer',
            customer_phone='9876543210',
            customer_email='multi@test.com',
            customer_address='456 Multi St',
            contract_type='one_time',
            service_type='Maintenance',
            contract_status='active',
            service_frequency_count=3,  # Expecting 3 visits
            service_start_date=date.today(),
            service_end_date=date.today() + timedelta(days=30),
        )

        # Create 3 work records
        works = []
        for i in range(3):
            work = TechnicianWorkRecord.objects.create(
                technician=self.technician,
                service_record=service,
                customer_name=service.customer_name,
                customer_phone=service.customer_phone,
                customer_address=service.customer_address,
                work_date=date.today() + timedelta(days=i*10),
                payment_status='pending',
            )
            works.append(work)

        # Mark 1st and 2nd as completed
        for work in works[:2]:
            self.client.patch(
                f'/api/amc/technician-work-records/{work.id}/',
                {'payment_status': 'completed'},
                format='json'
            )

        # Service should still be active (need 3 visits)
        service.refresh_from_db()
        self.assertEqual(service.contract_status, 'active')

        # Mark 3rd as completed
        self.client.patch(
            f'/api/amc/technician-work-records/{works[2].id}/',
            {'payment_status': 'completed'},
            format='json'
        )

        # Service should now be closed
        service.refresh_from_db()
        self.assertEqual(service.contract_status, 'closed')


class CompletedWorkDetailTestCase(TestCase):
    """Test completed work detail view."""

    def setUp(self):
        """Create test data."""
        self.admin_role, _ = Role.objects.get_or_create(name='admin')
        self.technician_role, _ = Role.objects.get_or_create(name='technician')
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            mobile_no='9876543211',
            password='testpass123',
            role=self.admin_role,
            is_staff=True
        )

        self.technician = User.objects.create_user(
            email='tech@test.com',
            mobile_no='9876543210',
            password='testpass123',
            role=self.technician_role
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_get_completed_work_detail(self):
        """Test retrieving detail of completed work."""
        # Create work record
        service = ServiceManagementRecord.objects.create(
            customer_name='Test Customer',
            customer_phone='9876543210',
            customer_email='test@test.com',
            customer_address='123 Test St',
            contract_type='one_time',
            service_type='Installation',
            contract_status='active',
            service_start_date=date.today(),
            service_end_date=date.today() + timedelta(days=5),
        )

        work = TechnicianWorkRecord.objects.create(
            technician=self.technician,
            service_record=service,
            customer_name=service.customer_name,
            customer_phone=service.customer_phone,
            customer_address=service.customer_address,
            work_date=date.today(),
            payment_status='completed',
        )

        # Get detail
        response = self.client.get(f'/api/amc/completed-work/w-{work.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['id'], f'w-{work.id}')
        self.assertEqual(data['kind'], 'service')
        self.assertEqual(data['customer_name'], 'Test Customer')