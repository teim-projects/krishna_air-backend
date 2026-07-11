from django.core.management.base import BaseCommand
from quotation.models import ServiceCategory, ServiceSubCategory, ServiceMaster
from product_management.models import item

class Command(BaseCommand):
    help = 'Populate service categories, subcategories and masters'

    def handle(self, *args, **options):
        self.stdout.write('Populating service data...')

        # Create Service Categories
        categories_data = [
            {'name': 'REFRIGERANT PIPING', 'sequence': 1},
            {'name': 'CONTROL CABLING', 'sequence': 2},
            {'name': 'ELECTRICAL WORK', 'sequence': 3},
            {'name': 'INSTALLATION & COMMISSIONING', 'sequence': 4},
            {'name': 'CIVIL WORK', 'sequence': 5},
        ]

        for cat_data in categories_data:
            category, created = ServiceCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'sequence': cat_data['sequence']}
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Create Subcategories
        subcategories_data = [
            # REFRIGERANT PIPING subcategories
            {'category': 'REFRIGERANT PIPING', 'name': 'between IDU to ODU', 'sequence': 1},
            {'category': 'REFRIGERANT PIPING', 'name': 'with Insulation', 'sequence': 2},
            {'category': 'REFRIGERANT PIPING', 'name': 'Copper Pipes', 'sequence': 3},
            
            # CONTROL CABLING subcategories
            {'category': 'CONTROL CABLING', 'name': 'Control Wire Installation', 'sequence': 1},
            {'category': 'CONTROL CABLING', 'name': 'Cable Tray Work', 'sequence': 2},
            
            # ELECTRICAL WORK subcategories
            {'category': 'ELECTRICAL WORK', 'name': 'Power Supply Connection', 'sequence': 1},
            {'category': 'ELECTRICAL WORK', 'name': 'MCB Installation', 'sequence': 2},
            
            # INSTALLATION & COMMISSIONING subcategories
            {'category': 'INSTALLATION & COMMISSIONING', 'name': 'Indoor Unit Installation', 'sequence': 1},
            {'category': 'INSTALLATION & COMMISSIONING', 'name': 'Outdoor Unit Installation', 'sequence': 2},
            {'category': 'INSTALLATION & COMMISSIONING', 'name': 'System Commissioning', 'sequence': 3},
            
            # CIVIL WORK subcategories
            {'category': 'CIVIL WORK', 'name': 'Wall Mounting', 'sequence': 1},
            {'category': 'CIVIL WORK', 'name': 'Concrete Work', 'sequence': 2},
        ]

        for subcat_data in subcategories_data:
            try:
                category = ServiceCategory.objects.get(name=subcat_data['category'])
                subcategory, created = ServiceSubCategory.objects.get_or_create(
                    category=category,
                    name=subcat_data['name'],
                    defaults={'sequence': subcat_data['sequence']}
                )
                if created:
                    self.stdout.write(f'Created subcategory: {subcategory.name}')
            except ServiceCategory.DoesNotExist:
                self.stdout.write(f'Category not found: {subcat_data["category"]}')

        # Create Service Masters (linking to existing items where possible)
        service_masters_data = [
            # REFRIGERANT PIPING services
            {
                'category': 'REFRIGERANT PIPING',
                'subcategory': 'Copper Pipes',
                'name': 'Copper Pipe 1/2" Installation',
                'service_type': 'MATERIAL',
                'unit': 'Mtr',
                'labor_rate': 50.00,
                'sequence': 1
            },
            {
                'category': 'REFRIGERANT PIPING',
                'subcategory': 'with Insulation',
                'name': 'Insulation Work',
                'service_type': 'LABOR',
                'unit': 'Mtr',
                'labor_rate': 25.00,
                'sequence': 2
            },
            
            # CONTROL CABLING services
            {
                'category': 'CONTROL CABLING',
                'subcategory': 'Control Wire Installation',
                'name': 'Control Wire Installation',
                'service_type': 'MATERIAL',
                'unit': 'Mtr',
                'labor_rate': 15.00,
                'sequence': 1
            },
            
            # ELECTRICAL WORK services
            {
                'category': 'ELECTRICAL WORK',
                'subcategory': 'Power Supply Connection',
                'name': 'Power Connection Work',
                'service_type': 'LABOR',
                'unit': 'Nos',
                'labor_rate': 500.00,
                'sequence': 1
            },
            
            # INSTALLATION & COMMISSIONING services
            {
                'category': 'INSTALLATION & COMMISSIONING',
                'subcategory': 'Indoor Unit Installation',
                'name': '1.5 TR Indoor Unit Installation',
                'service_type': 'LABOR',
                'unit': 'Nos',
                'labor_rate': 1500.00,
                'sequence': 1
            },
            {
                'category': 'INSTALLATION & COMMISSIONING',
                'subcategory': 'Outdoor Unit Installation',
                'name': '1.5 TR Outdoor Unit Installation',
                'service_type': 'LABOR',
                'unit': 'Nos',
                'labor_rate': 2000.00,
                'sequence': 2
            },
            {
                'category': 'INSTALLATION & COMMISSIONING',
                'subcategory': 'System Commissioning',
                'name': 'System Testing & Commissioning',
                'service_type': 'LABOR',
                'unit': 'Lot',
                'labor_rate': 1000.00,
                'sequence': 3
            },
            
            # CIVIL WORK services
            {
                'category': 'CIVIL WORK',
                'subcategory': 'Wall Mounting',
                'name': 'Wall Mounting Bracket Installation',
                'service_type': 'LABOR',
                'unit': 'Nos',
                'labor_rate': 300.00,
                'sequence': 1
            },
        ]

        for service_data in service_masters_data:
            try:
                category = ServiceCategory.objects.get(name=service_data['category'])
                subcategory = ServiceSubCategory.objects.get(
                    category=category,
                    name=service_data['subcategory']
                )
                
                service_master, created = ServiceMaster.objects.get_or_create(
                    category=category,
                    subcategory=subcategory,
                    name=service_data['name'],
                    defaults={
                        'service_type': service_data['service_type'],
                        'unit': service_data['unit'],
                        'labor_rate': service_data['labor_rate'],
                        'sequence': service_data['sequence']
                    }
                )
                if created:
                    self.stdout.write(f'Created service master: {service_master.name}')
                    
            except (ServiceCategory.DoesNotExist, ServiceSubCategory.DoesNotExist) as e:
                self.stdout.write(f'Error creating service master {service_data["name"]}: {e}')

        self.stdout.write(self.style.SUCCESS('Successfully populated service data!'))