from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='kind',
            field=models.CharField(
                choices=[
                    ('MCQ', 'Multiple choice'),
                    ('MULTI_SELECT', 'Multiple select'),
                    ('TRUE_FALSE', 'True / false'),
                    ('BLANKS', 'Fill in the blank'),
                    ('WRITTEN', 'Written'),
                ],
                default='MCQ',
                max_length=12,
            ),
        ),
    ]
