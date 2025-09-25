from django import forms
from .models import (
    Course, CourseTerm, CourseCode, CourseNumber,
    CourseSection, CourseYear, CourseTime, CourseDay
)

class CourseForm(forms.Form):
    # User inputs (required fields have asterisk in label)
    code = forms.CharField(max_length=20, required=True, label="Code *")
    number = forms.CharField(max_length=20, required=True, label="Number *")
    section = forms.CharField(max_length=20, required=True, label="Section *")
    term = forms.CharField(max_length=20, required=True, label="Term *")
    academic_year = forms.CharField(max_length=20, required=True, label="Academic Year *")

    # Optional fields
    day = forms.CharField(max_length=50, required=False, label="Day")            # e.g. "Monday_Tuesday"
    start_time = forms.CharField(max_length=20, required=False, label="Start")   # "HH:MM"
    end_time = forms.CharField(max_length=20, required=False, label="End")       # "HH:MM"

    def save(self, instance: Course | None = None):
        """
        Create or update a Course by mapping the user strings to FK instances.
        """
        data = self.cleaned_data
        course = instance or Course()

        # Required FKs
        course.code, _ = CourseCode.objects.get_or_create(name=data["code"].strip())
        course.number, _ = CourseNumber.objects.get_or_create(name=data["number"].strip())
        course.section, _ = CourseSection.objects.get_or_create(name=data["section"].strip())
        course.term, _ = CourseTerm.objects.get_or_create(name=data["term"].strip())
        course.academic_year, _ = CourseYear.objects.get_or_create(name=data["academic_year"].strip())

        # Optional FKs
        if data.get("day"):
            course.day, _ = CourseDay.objects.get_or_create(name=data["day"].strip())
        else:
            course.day = None

        if data.get("start_time"):
            course.start_time, _ = CourseTime.objects.get_or_create(name=data["start_time"].strip())
        else:
            course.start_time = None

        if data.get("end_time"):
            course.end_time, _ = CourseTime.objects.get_or_create(name=data["end_time"].strip())
        else:
            course.end_time = None

        course.save()
        return course
