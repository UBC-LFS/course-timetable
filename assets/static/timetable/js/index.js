// reload website by ctrl shift r to see changes because you need to refresh static files

// const course_items = document.getElementsByClassName("course-item")

// Array.from(course_items).forEach(course => {
//     course.addEventListener("mouseenter", () => {
//         course.classList.toggle("selected");
//     });
//     course.addEventListener("mouseleave", () => {
//         course.classList.toggle("selected");
//     });
// })

// const selected_course = document.getElementsByClassName("selected")

document.addEventListener("DOMContentLoaded", function () {
    // create a tooltip element
  const tooltip = document.createElement("div");
  tooltip.className = "course-tooltip";
  
  // list of all course items
  const courses = document.querySelectorAll(".course-item");
  
  // add event listeners to each course item
  courses.forEach(course => {
      course.addEventListener("mouseenter", (e) => {
      course.appendChild(tooltip);
      const description = course.getAttribute("data-description");
      tooltip.textContent = description;
      tooltip.style.display = "block";

    //   const rect = course.getBoundingClientRect();
    //   tooltip.style.top = window.scrollY + rect.top - 10 + "px";
    //   tooltip.style.left = window.scrollX + rect.right + 10 + "px";
    });

    // course.addEventListener("mousemove", (e) => {
    //   tooltip.style.top = e.pageY + 10 + "px";
    //   tooltip.style.left = e.pageX + 10 + "px";
    // });

    course.addEventListener("mouseleave", () => {
      tooltip.style.display = "none";
    });
  });
});
