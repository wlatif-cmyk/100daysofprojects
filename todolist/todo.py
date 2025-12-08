import json
import os

DATA_FILE = "tasks.json"


def load_tasks():
    """Load tasks from the JSON file."""
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []


def save_tasks(tasks):
    """Save tasks to the JSON file."""
    with open(DATA_FILE, "w") as file:
        json.dump(tasks, file, indent=4)


def list_tasks(tasks):
    """Display all tasks."""
    if not tasks:
        print("\n📭 No tasks found.\n")
        return

    print("\n Your Tasks:")
    for i, task in enumerate(tasks, start=1):
        status = "✔ Done" if task["done"] else "❗ Not Done"
        print(f"{i}. {task['title']} — {status}")
    print()


def add_task(tasks):
    """Add a new task."""
    title = input("Enter task name: ").strip()
    if title:
        tasks.append({"title": title, "done": False})
        save_tasks(tasks)
        print("✔ Task added!")
    else:
        print("Task name cannot be empty.")


def remove_task(tasks):
    list_tasks(tasks)
    try:
        index = int(input("Enter task number to remove: ")) - 1
        if 0 <= index < len(tasks):
            removed = tasks.pop(index)
            save_tasks(tasks)
            print(f"🗑 Removed: {removed['title']}")
        else:
            print("Invalid task number.")
    except ValueError:
        print("Please enter a number.")


def mark_done(tasks):
    list_tasks(tasks)
    try:
        index = int(input("Enter task number to mark done: ")) - 1
        if 0 <= index < len(tasks):
            tasks[index]["done"] = True
            save_tasks(tasks)
            print("✔ Task marked as done!")
        else:
            print("Invalid task number.")
    except ValueError:
        print("Please enter a number.")


def menu():
    tasks = load_tasks()

    while True:
        print("""
======== TO-DO LIST APP ========
1. View tasks
2. Add task
3. Remove task
4. Mark task as done
5. Exit
""")

        choice = input("Choose an option (1–5): ").strip()

        if choice == "1":
            list_tasks(tasks)
        elif choice == "2":
            add_task(tasks)
        elif choice == "3":
            remove_task(tasks)
        elif choice == "4":
            mark_done(tasks)
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    menu()
