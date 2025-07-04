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
            const days = day.split("_").join(", ");
            tooltip.innerHTML = `${code} ${number} ${section} <br> Start: ${start} <br> End: ${end} <br> Day: ${days}` || "<p> Description not available</p>";
            tooltip.style.display = "block";
            
            // Position the tooltip near the mouse cursor
            // tooltip.style.top = (e.clientY + 1000) + "px";
            // tooltip.style.left = (e.clientX + 234523459872345987) + "px";
            // const rect = course.getBoundingClientRect();
            // tooltip.style.top = (rect.top - window.scrollY - 10) + "px";
            // tooltip.style.left = (rect.right + window.scrollX + 30) + "px";
            
            // Ensure tooltip doesn't go off-screen
            const tooltipRect = tooltip.getBoundingClientRect();
            if (tooltipRect.right > window.innerWidth) {
                tooltip.style.left = (rect.left + window.scrollX - tooltipRect.width - 10) + "px";
            }
            if (tooltipRect.top < 0) {
                tooltip.style.top = (rect.bottom + window.scrollY + 10) + "px";
            }
        });

        course.addEventListener("mouseleave", () => {
            tooltip.style.display = "none";
        });
        
        // Optional: Update tooltip position on mouse move for better UX
        course.addEventListener("mousemove", (e) => {
            if (tooltip.style.display === "block") {
                tooltip.style.top = (e.clientY) + "px";
                tooltip.style.left = (e.clientX + 50) + "px";
                
                // Ensure tooltip doesn't go off-screen
                // const tooltipRect = tooltip.getBoundingClientRect();
                // if (tooltipRect.right > window.innerWidth) {
                //     tooltip.style.left = (e.pageX - tooltipRect.width - 10) + "px";
                // }
                // if (tooltipRect.top < 0) {
                //     tooltip.style.top = (e.pageY + 10) + "px";
                // }
            }
        });
    });
});