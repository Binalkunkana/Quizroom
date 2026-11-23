from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='is_approved',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='course',
            name='admin_suggestion',
            field=models.TextField(blank=True),
        ),
    ]
