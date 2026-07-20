import uuid

from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    Card = apps.get_model('card', 'Card')
    for card in Card.objects.all():
        card.uuid = uuid.uuid4()
        card.save(update_fields=['uuid'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('card', '0016_servicerequest_latitude_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='uuid',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(populate_uuids, noop_reverse),
        migrations.AlterField(
            model_name='card',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
