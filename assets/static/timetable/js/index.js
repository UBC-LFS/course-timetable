// Updated JavaScript code - replace your existing JS file content with this
document.addEventListener("DOMContentLoaded", function () {
    // Create a tooltip element and append it to the body (not to individual course items)
    const tooltip = document.createElement("div");
    tooltip.className = "course-tooltip";
    document.body.appendChild(tooltip); // Append to body instead of course item
    
    // List of all course items
    const courses = document.querySelectorAll(".course-item");
    
    // Add event listeners to each course item
    courses.forEach(course => {
        course.addEventListener("mouseenter", (e) => {
            const code = course.getAttribute("data-code");
            const section = course.getAttribute("data-section");
            const number = course.getAttribute("data-number");
            const start = course.getAttribute("data-start");
            const end = course.getAttribute("data-end");
            const day = course.getAttribute("data-day");
            const academic_year = course.getAttribute("data-academic-year")
            const term = course.getAttribute("data-term")
            tooltip.innerHTML = `${code} ${number} ${section} ${academic_year} ${term} <br> Start: ${start} <br> End: ${end} <br> Day: ${day}`;
            tooltip.style.display = "block";
            
        });

        course.addEventListener("mouseleave", () => {
            tooltip.style.display = "none";
        });
        
        // Optional: Update tooltip position on mouse move for better UX
        course.addEventListener("mousemove", (e) => {
            if (tooltip.style.display === "block") {
                tooltip.style.top = (e.clientY) + "px";
                tooltip.style.left = (e.clientX + 50) + "px";
            }
        });
    });
});

// Display dropdown selections
document.addEventListener("DOMContentLoaded", function() {

  document.querySelectorAll(".dropdown-select").forEach(dropdown => {
    const button = dropdown.querySelector("button");
    const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]');
    const defaultText = button.getAttribute("data-default");

    checkboxes.forEach(cb => {
      cb.addEventListener("change", () => {
        const selected = Array.from(checkboxes)
          .filter(c => c.checked)
          .map(c => c.value);

        button.textContent = selected.length
          ? selected.join(", ")
          : defaultText;
      });
    });
  });
});

const searchTable = () => {
    let input = document.getElementById("searchInput").value.toLowerCase();
    let rows = document.querySelectorAll("#courseTable tbody tr");

    
    for (let i = 1; i < rows.length; i++) {
            let cells = rows[i].getElementsByTagName("td");
            let match = false;

            for (let i = 0; i < cells.length; i++) {
                if (i === cells.length - 1){
                    continue; // skip Job column
                    
                }

                if (cells[i].textContent.toLowerCase().includes(input)) {
                    match = true;
                    break;
                }
            }

            rows[i].style.display = (input === "" || match) ? "" : "none";
        }
}


document.querySelectorAll('.year-checkbox').forEach(cb => {
        cb.addEventListener('change', function() {
            console.log("submitted")
            document.querySelector('.year-form').submit();
        });
    });

