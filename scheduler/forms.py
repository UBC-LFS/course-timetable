from django import forms
from datetime import datetime 
from .models import (
    Course, CourseTerm, CourseCode, CourseNumber,
    CourseSection, CourseYear, CourseTime, CourseDay, Role
)
from .models import ProgramName
from django.core.exceptions import ValidationError

class CourseForm(forms.ModelForm):
    # Required dropdowns (add * in labels)
    code          = forms.ModelChoiceField(
        queryset=CourseCode.objects.all().order_by("name"),
        required=True, empty_label="Select Code",
        label="Code *",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"required": "Code field is required."},
    )
    number        = forms.ModelChoiceField(
        queryset=CourseNumber.objects.all().order_by("name"),
        required=True, empty_label="Select Number",
        label="Number *",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"required": "Number field is required."},
    )
    section       = forms.ModelChoiceField(
        queryset=CourseSection.objects.all().order_by("name"),
        required=True, empty_label="Select Section",
        label="Section *",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"required": "Section field is required."},
    )
    term          = forms.ModelChoiceField(
        queryset=CourseTerm.objects.all().order_by("name"),
        required=True, empty_label="Select Term",
        label="Term *",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"required": "Term field is required."},
    )
    academic_year = forms.ModelChoiceField(
        queryset=CourseYear.objects.all().order_by("name"),
        required=True, empty_label="Select Year",
        label="Academic Year *",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"required": "Academic Year field is required."},
    )

    # Optional dropdowns
    day = forms.ModelMultipleChoiceField(
        queryset=CourseDay.objects.filter(name__in=["Mon", "Tues", "Wed", "Thurs", "Fri"]).order_by("id"),
        required=False,
        widget=forms.CheckboxSelectMultiple,   # renders 5 checkboxes
        label="Days"
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
                s = datetime.strptime(start.name[:5], "%H:%M")
                e = datetime.strptime(end.name[:5], "%H:%M")
                if not e > s:
                    raise ValidationError(
                        "End time must be later than start time."
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
        qs = CourseTerm.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Term with this name already exists.")
        return name
    

class CourseCodeForm(forms.ModelForm):
    color = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. #2BB1D6"
        }),
        label="Color"
    )

    class Meta:
        model = CourseCode
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. APBI"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"] .strip()
        qs = CourseCode.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Code with this name already exists.")
        return name

    def clean_color(self):
        color = self.cleaned_data["color"].strip()
        qs = CourseCode.objects.filter(color__exact=color)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Code with this color already exists.")
        return color
    

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


YEAR_CHOICES = [(str(y), str(y)) for y in range(2024, 2043)]  # 2024..2042 inclusive, change if needed
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


class ProgramNameForm(forms.ModelForm):
    class Meta:
        model = ProgramName
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Food Science"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = ProgramName.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Program Name with this value already exists.")
        return name
    

class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Admin"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Role.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Role with this name already exists.")
        return name