document.addEventListener("DOMContentLoaded", () => {
    const openTaskPopup = document.getElementById('open-task-btn');
    const closeTaskPopup = document.getElementById('close-add-btn');
    const addTaskPopup = document.getElementById('add-task-popup');
    const openEditPopup = document.querySelectorAll('.edit-btn');
    const closeEditPopup = document.getElementById('close-edit-btn');
    const editForm = document.getElementById("edit-task-form");
    const editTaskPopup = document.getElementById("edit-task-popup");
    const deleteBtn = document.querySelectorAll(".delete-btn");
    const confirmPopup= document.getElementById('confirm-delete-popup');
    const confirmDelBtn = document.querySelectorAll('.confirm-delete-btn');
    const cancelDelBtn = document.querySelectorAll('.cancel-delete-btn');
    const toastPopup = document.querySelector('.toast');

    if (toastPopup) {
        toastPopup.classList.add('active');
        
        setTimeout(()=>{
            toastPopup.classList.remove('active');
        }, 5000);
    }

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
            // retrieve existing data
            const id = button.dataset.id;
            const task = button.dataset.task;
            const priority = button.dataset.priority;
            const deadline = button.dataset.deadline;

            // display existing data
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

    // target url for deleting task
    let targetUrl = "";

    deleteBtn.forEach(button => {
        button.addEventListener("click", (e) => {
            e.preventDefault();
            const taskId = button.dataset.id;
            targetUrl = `/delete_task/${taskId}`;
            confirmPopup.classList.add("active");
        });
    });

    confirmDelBtn.forEach(button => {
        button.addEventListener("click", () => {
            window.location.href = targetUrl;
        });
    });

    cancelDelBtn.forEach(button => {
        button.addEventListener("click", () => {
            confirmPopup.classList.remove("active");
        });
    });
});

function toggleTask(id, checked){
    const isChecked = checked ? 1:0;
    fetch(`/toggle_task/${id}`, {
        method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: `isChecked=${isChecked}`
    });
}