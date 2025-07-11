# Generated by Django 5.2.1 on 2025-05-27 16:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CourseCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=5, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CourseDay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CourseName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CourseNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=5, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CourseSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=12, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CourseTerm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
            ],
        ),
        migrations.CreateModel(
            name='CourseTime',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=10, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, null=True, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=256, unique=True)),
                ('code', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='scheduler.coursecode')),
                ('day', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='scheduler.courseday')),
                ('name', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='scheduler.coursename')),
                ('number', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='scheduler.coursenumber')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='scheduler.coursesection')),
                ('term', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='scheduler.courseterm')),
                ('end', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='courses_end', to='scheduler.coursetime')),
                ('start', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='courses_start', to='scheduler.coursetime')),
            ],
        ),
    ]
