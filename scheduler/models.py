from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
    

class CourseTerm(models.Model):
    name = models.CharField(max_length=20, unique=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class CourseCode(models.Model):
    name = models.CharField(max_length=20, unique=True)
    color = models.CharField(max_length=20, unique=True)
    
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
    name = models.CharField(max_length=20, unique=True)
    
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
    day = models.ManyToManyField(CourseDay, blank=True, related_name="courses")
    slug = models.SlugField(max_length=256, unique=True)    # URL-friendly identifier

    class Meta:
        unique_together = ['code', 'number', 'section', 'academic_year', 'term']

    def save(self, *args, **kwargs):
        def part(obj):
            return getattr(obj, "name", None) or "None"
        
        creating = self.pk is None  # check if this is a new object
        
        if creating:
            super().save(*args, **kwargs)  # save first so pk is assigned
            self.slug = slugify(
                f"{part(self.code)}-{part(self.number)}-{part(self.section)}-"
                f"{part(self.academic_year)}-{part(self.term)}-{self.pk}"
            )
            # update only the slug field
            super().save(update_fields=["slug"])
        else:
            self.slug = slugify(
                f"{part(self.code)}-{part(self.number)}-{part(self.section)}-"
                f"{part(self.academic_year)}-{part(self.term)}-{self.pk}"
            )
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code.name} {self.number.name} {self.section.name} ({self.academic_year.name}, {self.term.name})"
    
    
class Program(models.Model):
    name = models.ForeignKey(ProgramName, on_delete=models.CASCADE)
    year_level = models.ForeignKey(ProgramYearLevel, on_delete=models.CASCADE)
    courses = models.ManyToManyField(Course, blank=True, related_name="programs")  # many-to-many
        
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

def _cleanup_or_reslug_after_delete(instance):
    ids = getattr(instance, "_affected_course_ids", [])
    if not ids:
        return
    # delete any courses now have BOTH code & number null
    Course.objects.filter(id__in=ids, code__isnull=True, number__isnull=True).delete()
    # re-slug the still-existing courses
    remaining = Course.objects.filter(id__in=ids)
    _reslug_courses(remaining)

@receiver(post_delete, sender=CourseCode)
def _code_post_delete(sender, instance, **kwargs):
    # _reslug_after_delete(instance)
    _cleanup_or_reslug_after_delete(instance)

@receiver(post_delete, sender=CourseNumber)
def _number_post_delete(sender, instance, **kwargs):
    # _reslug_after_delete(instance)
    _cleanup_or_reslug_after_delete(instance)

@receiver(post_delete, sender=CourseSection)
def _section_post_delete(sender, instance, **kwargs):
    # _reslug_after_delete(instance)
    _cleanup_or_reslug_after_delete(instance)

@receiver(post_delete, sender=CourseYear)
def _year_post_delete(sender, instance, **kwargs):
    # _reslug_after_delete(instance)
    _cleanup_or_reslug_after_delete(instance)

@receiver(post_delete, sender=CourseTerm)
def _term_post_delete(sender, instance, **kwargs):
    # _reslug_after_delete(instance)
    _cleanup_or_reslug_after_delete(instance)


class HistoryTopic(models.TextChoices):
    COURSE_TERM   = "course_term", "Course Term"
    COURSE_CODE   = "course_code", "Course Code"
    COURSE_NUMBER = "course_number", "Course Number"
    COURSE_SECTION= "course_section", "Course Section"
    COURSE_TIME   = "course_time", "Course Time"
    COURSE_YEAR   = "course_year", "Course Year"
    PROGRAM_NAME  = "program_name", "Program Name"


class HistoryAction(models.TextChoices):
    CREATED = "created", "created"
    EDITED  = "edited", "edited"
    DELETED = "deleted", "deleted"


class HistoryLog(models.Model):
    topic       = models.CharField(max_length=20, choices=HistoryTopic.choices)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action      = models.CharField(max_length=20, choices=HistoryAction.choices)
    before_value= models.CharField(max_length=100, blank=True)
    after_value = models.CharField(max_length=100, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        if self.action == HistoryAction.EDITED:
            return f"{getattr(self.user, 'username', 'None')} edited {self.before_value} to {self.after_value}"
        if self.action == HistoryAction.DELETED:
            return f"{getattr(self.user, 'username', 'None')} deleted {self.before_value}"
        return f"{getattr(self.user, 'username', 'None')} created {self.after_value}"


class Role(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"
