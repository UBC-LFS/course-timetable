from django.test import TestCase
from datetime import datetime
from scheduler.forms import CourseForm, CourseSchedulingForm, TimeslotForm
from scheduler.models import (
    CourseCode, CourseNumber, CourseSection, CourseTerm,
    CourseYear, CourseDay, CourseTime, Course, Timeslot
)


class CourseFormTest(TestCase):

    def setUp(self):
        self.code = CourseCode.objects.create(name="TEST_V", color="#123456")
        self.number = CourseNumber.objects.create(name="100")
        self.section = CourseSection.objects.create(name="001")
        self.term = CourseTerm.objects.create(name="T1")
        self.year = CourseYear.objects.create(name="2025")

        self.monday = CourseDay.objects.create(name="Mon")
        self.tuesday = CourseDay.objects.create(name="Tue")
        self.wednesday = CourseDay.objects.create(name="Wed")
        self.thursday = CourseDay.objects.create(name="Thu")
        self.friday = CourseDay.objects.create(name="Fri")

        # Times
        self.t0800 = CourseTime.objects.create(name="08:00")
        self.t0900 = CourseTime.objects.create(name="09:00")

    def test_required_fields(self):
        form = CourseForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)
        self.assertIn("number", form.errors)
        self.assertIn("section", form.errors)
        self.assertIn("term", form.errors)
        self.assertIn("academic_year", form.errors)

    def test_day_ordering(self):
        form = CourseForm()
        day_names = [d.name for d in form.fields["day"].queryset]
        self.assertEqual(day_names, ["Mon", "Tue", "Wed", "Thu", "Fri"])

    def test_end_time_must_be_after_start_time(self):
        form = CourseForm(data={
                "code": self.code.id,
                "number": self.number.id,
                "section": self.section.id,
                "term": self.term.id,
                "academic_year": self.year.id,
                
                # wrong order
                "start_time": self.t0900.id,
                "end_time": self.t0800.id,  
            })

        self.assertFalse(form.is_valid())
        self.assertIn("End time must be later than start time.", form.errors["__all__"])

    def test_time_validation_passes_when_valid(self):
        form = CourseForm(data={
                "code": self.code.id,
                "number": self.number.id,
                "section": self.section.id,
                "term": self.term.id,
                "academic_year": self.year.id,
                "start_time": self.t0800.id,
                "end_time": self.t0900.id,
            })

        self.assertTrue(form.is_valid())

    def test_form_valid_with_all_fields(self):
        form = CourseForm(data={
                "code": self.code.id,
                "number": self.number.id,
                "section": self.section.id,
                "term": self.term.id,
                "academic_year": self.year.id,
                "day": [self.monday.id, self.wednesday.id],
                "start_time": self.t0800.id,
                "end_time": self.t0900.id,
            })

        self.assertTrue(form.is_valid())
        obj = form.save()

        self.assertEqual(obj.code, self.code)
        self.assertEqual(obj.number, self.number)
        self.assertEqual(obj.section, self.section)
        self.assertEqual(obj.term, self.term)
        self.assertEqual(obj.academic_year, self.year)
        self.assertIn(self.monday, obj.day.all())
        self.assertIn(self.wednesday, obj.day.all())

class CourseSchedulingFormTest(TestCase):
    def setUp(self):
        self.code = CourseCode.objects.create(name="TEST_V", color="#123456")
        self.number = CourseNumber.objects.create(name="100")
        self.section = CourseSection.objects.create(name="001")
        self.t1 = CourseTerm.objects.create(name="T1")
        self.t2 = CourseTerm.objects.create(name="T2")
        self.year = CourseYear.objects.create(name="2025")

        self.monday = CourseDay.objects.create(name="Mon")
        self.tuesday = CourseDay.objects.create(name="Tue")
        self.wednesday = CourseDay.objects.create(name="Wed")
        self.thursday = CourseDay.objects.create(name="Thu")
        self.friday = CourseDay.objects.create(name="Fri")

        # Times
        self.t0800 = CourseTime.objects.create(name="08:00")
        self.t0900 = CourseTime.objects.create(name="09:00")
        self.t1000 = CourseTime.objects.create(name="10:00")
        self.t1100 = CourseTime.objects.create(name="11:00")
        
        self.scheduledCourse = Course.objects.create(
            code=self.code,
            number=self.number,
            section=self.section,
            term=self.t1,
            academic_year=self.year,
            start_time=self.t0800,
            end_time=self.t0900,
        )
        self.scheduledCourse.day.set([self.monday, self.wednesday, self.friday])
    
    def test_required_fields(self):
        form = CourseSchedulingForm(instance=self.scheduledCourse, data={})
        self.assertFalse(form.is_valid())
        self.assertIn("term", form.errors)

    def test_toggling_off_cycle(self):
        form = CourseSchedulingForm(data={"term": self.t2, "off_cycle": True}, instance=self.scheduledCourse)

        self.assertTrue(form.is_valid())
        obj = form.save()
        self.assertTrue(obj.off_cycle)

    def test_course_properly_updated(self):
        form = CourseSchedulingForm(instance=self.scheduledCourse, data={
            "term": self.t2,
            "off_cycle": False,
            "day": [self.tuesday, self.thursday],
            "start_time": self.t1000,
            "end_time": self.t1100,
        })
        self.assertTrue(form.is_valid())
        obj = form.save()

        self.assertEqual(obj.term, self.t2)
        self.assertFalse(obj.off_cycle)
        self.assertNotIn(self.monday, obj.day.all())
        self.assertIn(self.tuesday, obj.day.all())
        self.assertNotIn(self.wednesday, obj.day.all())
        self.assertIn(self.thursday, obj.day.all())
        self.assertNotIn(self.friday, obj.day.all())
        self.assertEqual(obj.start_time, self.t1000)
        self.assertEqual(obj.end_time, self.t1100)
    
    def test_time_validiation(self):
        form = CourseSchedulingForm(instance=self.scheduledCourse, data={
            "term": self.t2,
            "off_cycle": False,
            "day": [self.tuesday, self.thursday],
            "start_time": self.t1100,
            "end_time": self.t1000,
        })

        self.assertFalse(form.is_valid())

class TimeslotFormTest(TestCase):
    def setUp(self):
        self.code = CourseCode.objects.create(name="TEST_V", color="#123456")
        self.number = CourseNumber.objects.create(name="100")
        self.section = CourseSection.objects.create(name="001")
        self.term = CourseTerm.objects.create(name="T1")
        self.year = CourseYear.objects.create(name="2025")

        self.monday = CourseDay.objects.create(name="Mon")
        self.tuesday = CourseDay.objects.create(name="Tue")
        self.wednesday = CourseDay.objects.create(name="Wed")
        self.thursday = CourseDay.objects.create(name="Thu")
        self.friday = CourseDay.objects.create(name="Fri")

        # Times
        self.t0800 = CourseTime.objects.create(name="08:00")
        self.t0900 = CourseTime.objects.create(name="09:00")
        self.t1800 = CourseTime.objects.create(name="18:00")
        self.t1900 = CourseTime.objects.create(name="19:00")

        self.course = Course.objects.create(
            code=self.code,
            number=self.number,
            section=self.section,
            term=self.term,
            academic_year=self.year,
        )
    
    def test_successful_input(self):
        form = TimeslotForm(data={
            "course": self.course,
            "select_day": False,
            "start_time": self.t1800,
            "end_time": self.t1900,
        })

        self.assertTrue(form.is_valid())

    def test_incorrect_input(self):
        form = TimeslotForm(data={
            "course": self.course,
            "select_day": True,
            "start_time": self.t1800,
            "end_time": self.t0900,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("End time must be later than start time.", form.errors["__all__"])
