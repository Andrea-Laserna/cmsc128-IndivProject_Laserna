document.addEventListener("DOMContentLoaded", () => {
    const openTaskPopup = document.getElementById('open-task-btn');
    const closeTaskPopup = document.getElementById('close-add-btn');
    const addTaskPopup = document.getElementById('add-task-popup');

    const openEditPopup = document.querySelectorAll('.edit-btn');
    const closeEditPopup = document.getElementById('close-edit-btn');
    const editTaskPopup = document.getElementById('edit-task-popup');
    const editForm = document.getElementById("edit-task-form");

    const deleteBtn = document.querySelectorAll(".delete-btn");
    const confirmPopup = document.getElementById('confirm-delete-popup');
    const confirmDelBtn = document.querySelectorAll('.confirm-delete-btn');
    const cancelDelBtn = document.querySelectorAll('.cancel-delete-btn');

    const toastPopup = document.querySelector('.toast');

    const profileBtn = document.querySelector('.profileBtn');
    const profileDropdown = document.querySelector('.profile-container');
    const closeProfile = document.querySelector('.close-profile-btn');

    const collabBtn = document.querySelector('.collabBtn');
    const collabDropdown = document.querySelector('.collab-container');
    const closeCollab = document.querySelector('.close-collab-btn');

    // === toast ===
    if (toastPopup) {
        toastPopup.classList.add('active');
        setTimeout(() => toastPopup.classList.remove('active'), 5000);
    }

    // === profile dropdown ===
    if (profileBtn && profileDropdown && closeProfile) {
        profileBtn.addEventListener("click", () => profileDropdown.classList.toggle('active'));
        closeProfile.addEventListener("click", () => profileDropdown.classList.remove('active'));
    }

    // === collab dropdown ===
    if (collabBtn && collabDropdown && closeCollab) {
        collabBtn.addEventListener("click", () => collabDropdown.classList.toggle('active'));
        closeCollab.addEventListener("click", () => collabDropdown.classList.remove('active'));
    }

    // === add task popup ===
    if (openTaskPopup && closeTaskPopup && addTaskPopup) {
        openTaskPopup.addEventListener("click", () => addTaskPopup.classList.add("active"));
        closeTaskPopup.addEventListener("click", () => addTaskPopup.classList.remove("active"));
    }

    // === edit task popup ===
    const taskInput = document.getElementById("edit-task");
    const priorityInput = document.getElementById("edit-priority");
    const deadlineInput = document.getElementById("edit-deadline");

    if (openEditPopup && taskInput && priorityInput && deadlineInput && editForm && editTaskPopup) {
        openEditPopup.forEach(button => {
            button.addEventListener("click", () => {
                // retrieve details
                const task_id = button.dataset.taskid;
                const task_name = button.dataset.taskname;
                const priority = button.dataset.priority;
                const deadline = button.dataset.deadline;

                // display details
                taskInput.value = task_name;
                priorityInput.value = priority;
                deadlineInput.value = deadline;

                editForm.action = `/update_task/${task_id}`;
                editTaskPopup.classList.add("active");
            });
        });

        closeEditPopup.addEventListener("click", () => editTaskPopup.classList.remove("active"));
    }

    // === delete confirmation ===
    let targetUrl = "";
    if (deleteBtn && confirmPopup && confirmDelBtn && cancelDelBtn) {
        deleteBtn.forEach(button => {
            button.addEventListener("click", (e) => {
                e.preventDefault();
                targetUrl = `/delete_task/${button.dataset.taskid}`;
                confirmPopup.classList.add("active");
            });
        });

        confirmDelBtn.forEach(button => {
            button.addEventListener("click", () => {
                window.location.href = targetUrl;
            });
        });

        cancelDelBtn.forEach(button => {
            button.addEventListener("click", () => confirmPopup.classList.remove("active"));
        });
    }
});

// === toggle task ===
function toggleTask(task_id, checked){
    const isChecked = checked ? 1 : 0;
    fetch(`/toggle_task/${task_id}`, {
        method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: `isChecked=${isChecked}`
    });
}
