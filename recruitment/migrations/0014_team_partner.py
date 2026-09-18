from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('recruitment', '0013_alter_application_cv')]
    operations = [
        migrations.AddField(
            model_name='team',
            name='partner',
            field=models.CharField(
                blank=True, max_length=40,
                help_text='Partner society that runs this sub-team, e.g. "UGA". '
                          'Leave blank for HFR-run teams.',
            ),
        ),
    ]
