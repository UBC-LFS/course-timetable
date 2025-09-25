from django import forms
from .models import (
    Course, CourseTerm, CourseCode, CourseNumber,
    CourseSection, CourseYear, CourseTime, CourseDay
)

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = []  # IMPORTANT: don't let ModelForm auto-assign FK fields

    # User inputs
    code = forms.CharField(max_length=20, required=True, label="Code *")
    number = forms.CharField(max_length=20, required=True, label="Number *")
    section = forms.CharField(max_length=20, required=True, label="Section *")
    term = forms.CharField(max_length=20, required=True, label="Term *")
    academic_year = forms.CharField(max_length=20, required=True, label="Academic Year *")

    day = forms.CharField(max_length=50, required=False, label="Day")
    start_time = forms.CharField(max_length=20, required=False, label="Start Time")
    end_time = forms.CharField(max_length=20, required=False, label="End Time")

    def save(self, commit=True):
        """
        Create/update a Course by mapping the user strings to FK instances.
        """
        data = self.cleaned_data
        instance = self.instance if self.instance.pk else Course()

        # Required FKs
        instance.code, _ = CourseCode.objects.get_or_create(name=data["code"].strip())
        instance.number, _ = CourseNumber.objects.get_or_create(name=data["number"].strip())
        instance.section, _ = CourseSection.objects.get_or_create(name=data["section"].strip())
        instance.term, _ = CourseTerm.objects.get_or_create(name=data["term"].strip())
        instance.academic_year, _ = CourseYear.objects.get_or_create(name=data["academic_year"].strip())

        # Optional FKs
        if data.get("day"):
            instance.day, _ = CourseDay.objects.get_or_create(name=data["day"].strip())
        else:
            instance.day = None

        if data.get("start_time"):
            instance.start_time, _ = CourseTime.objects.get_or_create(name=data["start_time"].strip())
        else:
            instance.start_time = None

        if data.get("end_time"):
            instance.end_time, _ = CourseTime.objects.get_or_create(name=data["end_time"].strip())
        else:
            instance.end_time = None

        if commit:
            instance.save()
        return instance
