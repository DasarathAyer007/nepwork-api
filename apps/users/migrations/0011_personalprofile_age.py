import django.core.validators
from django.db import migrations, models


def compute_age_from_date_of_birth(apps, schema_editor):
    from datetime import date

    PersonalProfile = apps.get_model("users", "PersonalProfile")

    for profile in PersonalProfile.objects.exclude(date_of_birth__isnull=True):
        dob = profile.date_of_birth
        today = date.today()
        age = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )
        profile.age = max(age, 0)
        profile.save(update_fields=["age"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        (
            "users",
            "0010_alter_user_options_user_user_accttype_joined_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="personalprofile",
            name="age",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(13),
                    django.core.validators.MaxValueValidator(120),
                ],
            ),
        ),
        migrations.RunPython(
            compute_age_from_date_of_birth,
            noop_reverse,
        ),
        migrations.RemoveField(
            model_name="personalprofile",
            name="date_of_birth",
        ),
    ]
