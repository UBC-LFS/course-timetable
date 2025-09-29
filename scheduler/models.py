from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

import datetime as dt    

class CourseTerm(models.Model):
    name = models.CharField(max_length=20, unique=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class CourseCode(models.Model):
    name = models.CharField(max_length=20, unique=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class CourseNumber(models.Model):
    name = models.CharField(max_length=20, unique=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class CourseSection(models.Model):
    name = models.CharField(max_length=20, unique=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class CourseTime(models.Model):
    name = models.CharField(max_length=20, unique=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class CourseDay(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class CourseYear(models.Model):
    name = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
        
class ProgramYearLevel(models.Model):
    name = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name    

class Course(models.Model):
    term = models.ForeignKey(CourseTerm, on_delete=models.SET_NULL, null=True, blank=True)
    code = models.ForeignKey(CourseCode, on_delete=models.SET_NULL, null=True, blank=True)
    number = models.ForeignKey(CourseNumber, on_delete=models.SET_NULL, null=True, blank=True)
    section = models.ForeignKey(CourseSection, on_delete=models.SET_NULL, null=True, blank=True)
    academic_year = models.ForeignKey(CourseYear, on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.ForeignKey(CourseTime, on_delete=models.SET_NULL, null=True, blank=True, related_name="start_time")
    end_time = models.ForeignKey(CourseTime, on_delete=models.SET_NULL, null=True, blank=True, related_name="end_time")
    day = models.ForeignKey(CourseDay, on_delete=models.SET_NULL, null=True, blank=True)
    slug = models.SlugField(max_length=256, unique=True)    # URL-friendly identifier

    def save(self, *args, **kwargs):
        self.slug = slugify(
            f"{self.code.name}-{self.number.name}-{self.section.name}-"
            f"{self.academic_year.name}-{self.term.name}"
        )
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.code.name} {self.number.name} {self.section.name} ({self.academic_year.name}, {self.term.name})"
    
    
class Program(models.Model):
    name = models.CharField(max_length=50) # only one AANB, no need foreign key
    year_level = models.ForeignKey(ProgramYearLevel, on_delete=models.SET_NULL, null=True, blank=True)
    courses = models.ManyToManyField(Course, related_name="programs")  # many-to-many
    
    class Meta:
        unique_together = ("name", "year_level")  # composite uniqueness
        
    def __str__(self):
        return f"{self.name} {self.year_level.name}"
    



    
    

    
