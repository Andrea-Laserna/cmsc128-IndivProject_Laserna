document.addEventListener("DOMContentLoaded", () => {
    const openTaskPopup = document.getElementById('open-task-btn');
    const closeTaskPopup = document.getElementById('close-add-btn');
    const addTaskPopup = document.getElementById('add-task-popup');
    const openEditPopup = document.querySelectorAll('.edit-btn');
    const closeEditPopup = document.getElementById('close-edit-btn');
    const editForm = document.getElementById("edit-task-form");
    const editTaskPopup = document.getElementById("edit-task-popup");
    
    // Fields inside edit popup
    const taskInput = document.getElementById("edit-task");
    const priorityInput = document.getElementById("edit-priority");
    const deadlineInput = document.getElementById("edit-deadline");

    openTaskPopup.addEventListener("click", () => {
        addTaskPopup.classList.add("active");
    });

    closeTaskPopup.addEventListener("click", () => {
        addTaskPopup.classList.remove("active");
    });

    openEditPopup.forEach(button => {
        button.addEventListener("click", () => {
            // Get data from database in button
            const id = button.dataset.id;
            const task = button.dataset.task;
            const priority = button.dataset.priority;
            const deadline = button.dataset.deadline;

            // Prefill popup form
            taskInput.value = task;
            priorityInput.value = priority;
            deadlineInput.value = deadline;

            editForm.action = `/update_task/${id}`;

            editTaskPopup.classList.add("active");
        });
    });
    
    closeEditPopup.addEventListener("click", () => {
        editTaskPopup.classList.remove("active");
    });

});

function toggleTask(id, checked) {
    const isChecked = checked ? 1 : 0;
    fetch(`/toggle_task/${id}`, {
        method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: `isChecked=${isChecked}`
    })
}