from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0007_jobapplication_unique_active_job_application_per_applicant'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='jobapplication',
            name='unique_active_job_application_per_applicant',
        ),
        migrations.AddConstraint(
            model_name='jobapplication',
            constraint=models.UniqueConstraint(
                condition=models.Q(('deleted_at__isnull', True))
                & ~models.Q(status__in=['rejected', 'withdrawn']),
                fields=('job', 'applicant'),
                name='unique_active_job_application_per_applicant',
            ),
        ),
    ]
