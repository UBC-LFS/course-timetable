from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

import datetime as dt    

class CourseTerm(models.Model):
    name = models.CharField(max_length=256)
    
    def __str__(self):
        return self.name

class CourseCode(models.Model):
    """ Create a CourseCode model """
    name = models.CharField(max_length=5, unique=True)
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class CourseNumber(models.Model):
    """ Create a CourseNumber model """
    name = models.CharField(max_length=5, unique=True)
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class CourseSection(models.Model):
    """ Create a CourseSection model """
    name = models.CharField(max_length=12, unique=True)
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class CourseTime(models.Model):
    name = models.CharField(max_length=10, unique=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class CourseDay(models.Model):
    name = models.CharField(max_length=256, unique=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name



class Course(models.Model):
    name = models.CharField(max_length=50, unique=True)
    term = models.ForeignKey(CourseTerm, on_delete=models.DO_NOTHING)
    code = models.ForeignKey(CourseCode, on_delete=models.DO_NOTHING)
    number = models.ForeignKey(CourseNumber, on_delete=models.DO_NOTHING)
    section = models.ForeignKey(CourseSection, on_delete=models.DO_NOTHING)
    start = models.ForeignKey(CourseTime, on_delete=models.DO_NOTHING, related_name='courses_start')
    end = models.ForeignKey(CourseTime, on_delete=models.DO_NOTHING, related_name='courses_end')
    day = models.ForeignKey(CourseDay, on_delete=models.DO_NOTHING)
    slug = models.SlugField(max_length=256, unique=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.code.name  + '-' + self.number.name + '-' + self.section.name + '-' + '-' + self.term.name)
        super(Course, self).save(*args, **kwargs)


class Program(models.Model):
    name = models.CharField(max_length=256, unique=True, null=True)
    
    
    def __str__(self):
        return self.name
    



    
    

    
