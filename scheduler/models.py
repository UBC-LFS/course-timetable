from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver

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

class ProgramName(models.Model):
    name = models.CharField(max_length=100, unique=True)

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
        def part(obj):
            # safely get .name even if obj is None
            return (getattr(obj, "name", None) or "None")
        self.slug = slugify(
            f"{part(self.code)}-{part(self.number)}-{part(self.section)}-"
            f"{part(self.academic_year)}-{part(self.term)}"
        )
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.code.name} {self.number.name} {self.section.name} ({self.academic_year.name}, {self.term.name})"
    
    
class Program(models.Model):
    name = models.ForeignKey(ProgramName, on_delete=models.CASCADE)
    year_level = models.ForeignKey(ProgramYearLevel, on_delete=models.CASCADE)
    courses = models.ManyToManyField(Course, related_name="programs")  # many-to-many
    
    class Meta:
        unique_together = ("name", "year_level")  # composite uniqueness
        
    def __str__(self):
        return f"{self.name} {self.year_level.name}"
    
def _reslug_courses(qs):
    qs = qs.select_related("code", "number", "section", "academic_year", "term")
    for c in qs:
        # triggers Course.save() which recomputes slug
        c.save(update_fields=["slug"])

# --- when a related 'name' changes, recompute slugs for linked courses ---

@receiver(post_save, sender=CourseCode)
def _code_changed(sender, instance, **kwargs):
    _reslug_courses(Course.objects.filter(code=instance))

@receiver(post_save, sender=CourseNumber)
def _number_changed(sender, instance, **kwargs):
    _reslug_courses(Course.objects.filter(number=instance))

@receiver(post_save, sender=CourseSection)
def _section_changed(sender, instance, **kwargs):
    _reslug_courses(Course.objects.filter(section=instance))

@receiver(post_save, sender=CourseYear)
def _year_changed(sender, instance, **kwargs):
    _reslug_courses(Course.objects.filter(academic_year=instance))

@receiver(post_save, sender=CourseTerm)
def _term_changed(sender, instance, **kwargs):
    _reslug_courses(Course.objects.filter(term=instance))

# --- when a related row is deleted (on_delete=SET_NULL), recompute slugs ---

# capture affected Course IDs before the FK row is removed
@receiver(pre_delete, sender=CourseCode)
def _code_pre_delete(sender, instance, **kwargs):
    instance._affected_course_ids = list(instance.course_set.values_list("id", flat=True))

@receiver(pre_delete, sender=CourseNumber)
def _number_pre_delete(sender, instance, **kwargs):
    instance._affected_course_ids = list(instance.course_set.values_list("id", flat=True))

@receiver(pre_delete, sender=CourseSection)
def _section_pre_delete(sender, instance, **kwargs):
    instance._affected_course_ids = list(instance.course_set.values_list("id", flat=True))

@receiver(pre_delete, sender=CourseYear)
def _year_pre_delete(sender, instance, **kwargs):
    instance._affected_course_ids = list(instance.course_set.values_list("id", flat=True))

@receiver(pre_delete, sender=CourseTerm)
def _term_pre_delete(sender, instance, **kwargs):
    instance._affected_course_ids = list(instance.course_set.values_list("id", flat=True))

# after delete, those courses have FK=NULL; re-save them to refresh slug
def _reslug_after_delete(instance):
    ids = getattr(instance, "_affected_course_ids", [])
    if ids:
        _reslug_courses(Course.objects.filter(id__in=ids))

@receiver(post_delete, sender=CourseCode)
def _code_post_delete(sender, instance, **kwargs):
    _reslug_after_delete(instance)

@receiver(post_delete, sender=CourseNumber)
def _number_post_delete(sender, instance, **kwargs):
    _reslug_after_delete(instance)

@receiver(post_delete, sender=CourseSection)
def _section_post_delete(sender, instance, **kwargs):
    _reslug_after_delete(instance)

@receiver(post_delete, sender=CourseYear)
def _year_post_delete(sender, instance, **kwargs):
    _reslug_after_delete(instance)

@receiver(post_delete, sender=CourseTerm)
def _term_post_delete(sender, instance, **kwargs):
    _reslug_after_delete(instance)
    



    
    

    
