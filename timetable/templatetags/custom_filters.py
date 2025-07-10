from django import template

register = template.Library()

@register.filter
# Used in Landing_page to dynamically get the day data for a course
# Only allowed 2 parameters
def get_day(course, day):
    return course.day_data[day]
    