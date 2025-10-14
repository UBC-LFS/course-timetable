from django import forms
from datetime import datetime 
from .models import (
    Course, CourseTerm, CourseCode, CourseNumber,
    CourseSection, CourseYear, CourseTime, CourseDay
)
from .models import Program, ProgramYearLevel
from django.core.exceptions import ValidationError

class CourseForm(forms.ModelForm):
    # Required dropdowns (add * in labels)
    code          = forms.ModelChoiceField(
        queryset=CourseCode.objects.all().order_by("name"),
        required=True, empty_label="Select Code",
        label="Code *",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    number        = forms.ModelChoiceField(
        queryset=CourseNumber.objects.all().order_by("name"),
        required=True, empty_label="Select Number",
        label="Number *",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    section       = forms.ModelChoiceField(
        queryset=CourseSection.objects.all().order_by("name"),
        required=True, empty_label="Select Section",
        label="Section *",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    term          = forms.ModelChoiceField(
        queryset=CourseTerm.objects.all().order_by("name"),
        required=True, empty_label="Select Term",
        label="Term *",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    academic_year = forms.ModelChoiceField(
        queryset=CourseYear.objects.all().order_by("name"),
        required=True, empty_label="Select Year",
        label="Academic Year *",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    # Optional dropdowns
    day        = forms.ModelChoiceField(
        queryset=CourseDay.objects.all().order_by("name"),
        required=False, empty_label="Select Day",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    start_time = forms.ModelChoiceField(
        queryset=CourseTime.objects.all().order_by("name"),
        required=False, empty_label="Select Start Time",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    end_time   = forms.ModelChoiceField(
        queryset=CourseTime.objects.all().order_by("name"),
        required=False, empty_label="Select End Time",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model  = Course
        fields = ["code","number","section","term","day","start_time","end_time","academic_year"]

    # --- validations ----
    def clean(self):
        cleaned = super().clean()

        # time order (only if both provided)
        start = cleaned.get("start_time")
        end   = cleaned.get("end_time")
        if start and end:
            try:
                s = datetime.strptime(start.name[:5], "%H:%M")
                e = datetime.strptime(end.name[:5], "%H:%M")
                if not e > s:
                    self.add_error("end_time", "End time must be later than start time.")
            except Exception:
                # if times are not in HH:MM shape in DB, still give a friendly error
                self.add_error("end_time", "End time must be later than start time.")

        # duplicate protection: same Code, Number, Section, Year, Term
        code   = cleaned.get("code")
        num    = cleaned.get("number")
        sec    = cleaned.get("section")
        year   = cleaned.get("academic_year")
        term   = cleaned.get("term")
        if code and num and sec and year and term:
            qs = Course.objects.filter(
                code=code, number=num, section=sec, academic_year=year, term=term
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    "You can not have two courses with same Code, Number, Section, Academic Year and Term."
                )

        return cleaned


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
    

class CourseTimeForm(forms.ModelForm):
    class Meta:
        model = CourseTime
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),  # hidden via template; still needed for server
        }

    def clean_name(self):
        val = (self.cleaned_data.get("name") or "").strip()
        try:
            dt = datetime.strptime(val, "%H:%M")
            normalized = dt.strftime("%H:%M")
        except Exception:
            raise forms.ValidationError("Enter a valid time in HH:MM (e.g., 08:00).")

        qs = CourseTime.objects.filter(name__exact=normalized)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Time with this value already exists.")
        return normalized


YEAR_CHOICES = [(str(y), str(y)) for y in range(2024, 2043)]  # 2024..2042 inclusive
class CourseYearForm(forms.ModelForm):
    class Meta:
        model = CourseYear
        fields = ["name"]
        widgets = {
            "name": forms.Select(attrs={"class": "form-select"}, choices=YEAR_CHOICES),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = CourseYear.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Year with this value already exists.")
        return name


class ProgramNameForm(forms.Form):
    name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Food Science"}),
        label="Program Name",
    )

    def __init__(self, *args, **kwargs):
        # optional: pass current_name when editing to allow “no-op” rename
        self.current_name = kwargs.pop("current_name", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        new = self.cleaned_data["name"].strip()
        qs = Program.objects.filter(name__exact=new)
        if self.current_name:
            qs = qs.exclude(name__exact=self.current_name)
        if qs.exists():
            raise forms.ValidationError("A Program Name with this value already exists.")
        return new

