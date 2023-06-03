# Generated by Django 4.2.1 on 2023-05-31 13:47

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BusinessHours',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.BigIntegerField()),
                ('dayOfWeek', models.IntegerField()),
                ('start_time_local', models.CharField(max_length=40)),
                ('end_time_local', models.CharField(max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='StoreStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.BigIntegerField()),
                ('timestamp_utc', models.CharField(max_length=40)),
                ('status', models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='StoreTimezone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.BigIntegerField()),
                ('timezone_str', models.CharField(max_length=30)),
            ],
        ),
    ]