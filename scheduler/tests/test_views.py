from django.test import TestCase, Client
from django.urls import reverse
from scheduler.models import *
from scheduler.forms import *

class TestSchedulingEndpoint(TestCase):
    # fixtures = [
    #     "course_codes.json",
    #     "course_numbers.json",
    #     "course_sections.json",
    #     "course_terms.json",
    #     "course_years.json",
    #     "course_days.json",
    #     "course_times.json",
    # ]

    def setUp(self):
        self.admin = Role.objects.create(name="admin")
        self.user = User.objects.create(username="testuser", email="testemail@gmail.com")
        self.profile = Profile.objects.create(user=self.user, role=self.admin)

        self.off_cycle_course = Course.objects.create(
            code=CourseCode.objects.get(name="FNH_V"),
            number=CourseNumber.objects.get(name="100"),
            section=CourseSection.objects.get(name="102"),
            term=CourseTerm.objects.get(name="W1"),
            off_cycle=True,
            academic_year=CourseYear.objects.get(name="2025"),
        )

        self.timeslot = Timeslot.objects.create(
            course=self.off_cycle_course,
            day=CourseDay.objects.get(name="Mon"),
            start_time=CourseTime.objects.get(name="09:00"),
            end_time=CourseTime.objects.get(name="10:00"),
        )

    def test_existing_timeslot_not_deleted_when_scheduling_form_is_submitted(self):
        client = Client()
        client.force_login(self.user)

        post_request = {
            "term": [str(self.off_cycle_course.term.pk)],
            "off_cycle": ["on"],
            "form-TOTAL_FORMS": ["5"],
            "form-INITIAL_FORMS": ["0"],
            "form-MIN_NUM_FORMS": ["0"],
            "form-MAX_NUM_FORMS": ["5"],
            "form-0-select_day": ["on"],
            "form-0-start_time": [str(CourseTime.objects.get(name="09:00").pk)],
            "form-0-end_time": [str(CourseTime.objects.get(name="10:00").pk)],
            "form-2-select_day": ["on"],
            "form-2-start_time": [str(CourseTime.objects.get(name="11:00").pk)],
            "form-2-end_time": [str(CourseTime.objects.get(name="12:00").pk)],
            "query": [str(reverse("scheduler:landing_page"))]
        }

        # we expect 302 since we redirect the client
        response = client.post(reverse("scheduler:edit_course_schedule", kwargs={"course_id": self.off_cycle_course.pk}), post_request)
        self.assertEqual(response.status_code, 302)

        queried_course = Course.objects.get(pk=1)
        self.assertEqual(queried_course.timeslot_set.count(), 2)

        timeslot_mon = queried_course.timeslot_set.get(day__name="Mon")
        self.assertIsNotNone(timeslot_mon)
        self.assertEqual(timeslot_mon.start_time.name,"09:00")
        self.assertEqual(timeslot_mon.end_time.name,"10:00")

        timeslot_wed = queried_course.timeslot_set.get(day__name="Wed")
        self.assertIsNotNone(timeslot_wed)
        self.assertEqual(timeslot_wed.start_time.name,"11:00")
        self.assertEqual(timeslot_wed.end_time.name,"12:00")
