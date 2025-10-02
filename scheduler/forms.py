from django import forms
from datetime import datetime 
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

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end   = cleaned.get("end_time")

        # Only validate the order if both are provided
        if start and end:
            try:
                s_dt = datetime.strptime(start.strip(), "%H:%M")
            except ValueError:
                # should not come here
                self.add_error("start_time", "Use HH:MM (e.g., 08:00).")
                return cleaned

            try:
                e_dt = datetime.strptime(end.strip(), "%H:%M")
            except ValueError:
                # should not come here
                self.add_error("end_time", "Use HH:MM (e.g., 09:30).")
                return cleaned

            if not e_dt > s_dt:
                self.add_error("end_time", "End time must be later than start time.")

        return cleaned


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


class CourseTermForm(forms.ModelForm):
    class Meta:
        model = CourseTerm
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. T1"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        # enforce case-insensitive uniqueness
        qs = CourseTerm.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Term with this name already exists.")
        return name
    

class CourseCodeForm(forms.ModelForm):
    class Meta:
        model = CourseCode
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. LFS"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = CourseCode.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Code with this name already exists.")
        return name
    

class CourseNumberForm(forms.ModelForm):
    class Meta:
        model = CourseNumber
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 100"}),
        }

    def clean_name(self):
        raw = self.cleaned_data["name"].strip()
        if not raw.isdigit():
            raise forms.ValidationError("Course Number must contain digits only (e.g. 100).")
        qs = CourseNumber.objects.filter(name__exact=raw)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Number with this value already exists.")
        return raw


class CourseSectionForm(forms.ModelForm):
    class Meta:
        model = CourseSection
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 001"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = CourseSection.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Section with this value already exists.")
        return name


