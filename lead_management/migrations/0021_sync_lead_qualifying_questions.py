from django.db import migrations


def rename_question(LeadFAQ, old_question, new_question, sort_order):
    old_faq = LeadFAQ.objects.filter(question=old_question).first()
    new_faq = LeadFAQ.objects.filter(question=new_question).first()

    if old_faq and not new_faq:
        old_faq.question = new_question
        old_faq.is_active = True
        old_faq.sort_order = sort_order
        old_faq.save(update_fields=["question", "is_active", "sort_order"])
        return

    if new_faq:
        new_faq.is_active = True
        new_faq.sort_order = sort_order
        new_faq.save(update_fields=["is_active", "sort_order"])

    LeadFAQ.objects.filter(question=old_question).delete()


def forwards(apps, schema_editor):
    LeadFAQ = apps.get_model("lead_management", "LeadFAQ")

    rename_question(
        LeadFAQ,
        "What type of service do you need today?",
        "Where is the AC unit installed/to be installed?",
        1,
    )
    rename_question(
        LeadFAQ,
        "Please provide any additional details, specific brand preferences, or symptoms our technicians should know before reaching out.",
        "Additional Details & Pipe/Duct Distance.",
        6,
    )


def backwards(apps, schema_editor):
    LeadFAQ = apps.get_model("lead_management", "LeadFAQ")

    rename_question(
        LeadFAQ,
        "Where is the AC unit installed/to be installed?",
        "What type of service do you need today?",
        1,
    )
    rename_question(
        LeadFAQ,
        "Additional Details & Pipe/Duct Distance.",
        "Please provide any additional details, specific brand preferences, or symptoms our technicians should know before reaching out.",
        6,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("lead_management", "0020_seed_lead_qualifying_questions"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]