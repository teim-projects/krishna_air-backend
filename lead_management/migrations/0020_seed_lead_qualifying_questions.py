from django.db import migrations


def forwards(apps, schema_editor):
    LeadFAQ = apps.get_model("lead_management", "LeadFAQ")

    questions = [
        (
            1,
            "What type of service do you need today?",
        ),
        (
            2,
            "What type of AC system is this for? (Select all that apply)",
        ),
        (
            3,
            "If your AC is having trouble, what symptoms are you noticing? (Select all that apply)",
        ),
        (
            4,
            "Roughly how old is your current AC unit?",
        ),
        (
            5,
            "What is the current warranty status and operational state of the machine?",
        ),
        (
            6,
            "Please provide any additional details, specific brand preferences, or symptoms our technicians should know before reaching out.",
        ),
    ]

    for sort_order, question in questions:
      LeadFAQ.objects.update_or_create(
          question=question,
          defaults={
              "is_active": True,
              "sort_order": sort_order,
          },
      )


def backwards(apps, schema_editor):
    LeadFAQ = apps.get_model("lead_management", "LeadFAQ")

    questions = [
        "What type of service do you need today?",
        "What type of AC system is this for? (Select all that apply)",
        "If your AC is having trouble, what symptoms are you noticing? (Select all that apply)",
        "Roughly how old is your current AC unit?",
        "What is the current warranty status and operational state of the machine?",
        "Please provide any additional details, specific brand preferences, or symptoms our technicians should know before reaching out.",
    ]

    LeadFAQ.objects.filter(question__in=questions).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("lead_management", "0019_add_qualifying_fields"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]