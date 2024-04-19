import unittest
from unittest.mock import patch, call
import llm_communication
from llm_communication import logging
from llm_communication import (
    todo_add,
    todo_mark_as_done,
    reset_todocli,
    llama_generate,
    execution_process,
    parse_llm_output,
    get_tasks_data,
)
from itertools import permutations
from functools import reduce

# Reading config variables
with open("./aws_api.key", "r") as f:
    AWS_API_KEY = f.readlines()[0].strip()

with open("./base_prompt.txt", "r") as f:
    BASE_PROMPT = f.read()


def setup_testing_env():
    reset_todocli()
    # Add some tasks to further run some tests on them.
    todo_add(title="Elden Ring", context="games", priority=5)  # ID:1
    todo_add(title="Rust", context="games_wishlist", priority=1)  # ID:2
    todo_add(title="Study Math", context="study", priority=2)  # ID:3
    todo_add(title="Planning", context="work", priority=3)  # ID:4
    todo_add(title="Write Test", context="work", priority=4)  # ID:5
    todo_add(title="Write Diary", context="personal", priority=2)  # ID:6
    todo_add(title="cleaning", context="home", priority=5)  # ID:7
    todo_add(title="water the pots", context="home", priority=3)  # ID:8
    todo_add(title="bananas", context="shoppinglist", priority=1)  # ID:9
    todo_add(title="apples", context="shoppinglist", priority=1)  # ID:a
    todo_add(title="Deutsch Schreiben", context="homework", priority=1)  # ID:b
    todo_add(title="Apply", context="work", priority=3)  # ID:c
    todo_add(title="washing the dishes", context="home", priority=5)  # ID:d

    # todo_add(title="Planning", context="work", priority=3)
    # todo_add(title="Write Test", context="work", priority=4)
    # todo_add(title="Apply", context="work", priority=3)
    # todo_add(title="Ride to office", context="work", priority=1)


class TestLLMCommunication(unittest.TestCase):
    def test_todo_rm_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you remove "elden ring" from my items?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call("todo rm 1", "todo_rm")

    def test_todo_rm_mult_tasks(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you remove "bananas" and "rust" from my items?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            assert (
                call("todo rm 2 b", "todo_rm") in mock_log_and_exec_process.mock_calls
                or call("todo rm b 2", "todo_rm")
                in mock_log_and_exec_process.mock_calls
            )

    def test_todo_add_mult_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: I want to add some new tasks. add "mamala" and "coding session" to my homeworks?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_has_calls(
                any_order=True,
                calls=[
                    call(
                        """todo add "Coding Session" --context "homework" --priority 1""",
                        "todo_add",
                    ),
                    call(
                        """todo add "mamala" --context "homework" --priority 1""",
                        "todo_add",
                    ),
                ],
            )

    def test_todo_list_context(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you list my items in games list?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call("""todo \"games\"""", "todo")

    def test_todo_move_from_ctx_to_ctx(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you move the items in study context to homework context?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo mv 'study' 'homework'""", "todo_mv"
            )

    def test_todo_task_rename_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you change the name of "elden ring" to "elden lord"? """
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo task 1 --title \"Elden Lord\"""", "todo_task"
            )

    def test_todo_task_change_priority_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you change the priority of elden ring to 7?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo task 1 --priority 7""", "todo_task"
            )

    def test_todo_task_change_priority_mult_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you change the priority of elden ring and cleaning to 10?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_has_calls(
                any_order=True,
                calls=[
                    call(
                        """todo task 1 --priority 10""",
                        "todo_task",
                    ),
                    call(
                        """todo task 7 --priority 10""",
                        "todo_task",
                    ),
                ],
            )

    def test_todo_task_change_context_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you change the context of "writing test" to homework?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo task 5 --context \"homework\"""", "todo_task"
            )

    def test_todo_task_set_deadline_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you set the deadline of study math to September 10 2025?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo task 3 --deadline \"2025-09-10\"""", "todo_task"
            )

    def test_todo_task_set_start_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you set the start of planning to 2024/10/11 12:34:22?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo task 4 --start \"2024-10-11 12:34:22\"""", "todo_task"
            )

    def test_todo_done_mult_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you mark elden ring, writing test and water the pots as done?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            ids = [1, 5, 8]
            perms = [" ".join([str(j) for j in i]) for i in list(permutations(ids))]
            perms = [f"todo done {i}" for i in perms]
            perms_exist = [
                call(i, "todo_mark_as_done") in mock_log_and_exec_process.mock_calls
                for i in perms
            ]
            assert reduce(lambda a, b: a or b, perms_exist)

    def test_todo_rmctx_mult_ctx(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: remove my home, work, and shoppinglist contexts please."""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_has_calls(
                calls=[
                    call("""todo rmctx "work" --force""", "todo_rmctx"),
                    call("""todo rmctx "home" --force""", "todo_rmctx"),
                    call("""todo rmctx "shoppinglist" --force""", "todo_rmctx"),
                ],
                any_order=True,
            )

    def test_todo_search(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: I am looking for undone tasks having study in them. can you do that for me please? I neeeeeeeeeed taht really"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                "todo search 'study' --undone", "todo_search"
            )

    def test_todo_done_based_on_order(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Mark the first and third items on my 'work' context as done."""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            ids = ["5", "c"]
            perms = [" ".join([str(j) for j in i]) for i in list(permutations(ids))]
            perms = [f"todo done {i}" for i in perms]
            perms_exist = [
                call(i, "todo_mark_as_done") in mock_log_and_exec_process.mock_calls
                for i in perms
            ]
            assert reduce(lambda a, b: a or b, perms_exist)

    def test_portfolio_case_1(self):

        reset_todocli()
        todo_add(title="LLM Homework", context="homework_list")  # ID:1
        todo_add(title="NLP Homework", context="homework_list")  # ID:2
        todo_add(title="Math Homework", context="homework_list")  # ID:3
        todo_add(title="ML Homework", context="homework_list")  # ID:4

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Mark the first and third items on my homework_list as done"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            ids = [1, 3]
            perms = [" ".join([str(j) for j in i]) for i in list(permutations(ids))]
            perms = [f"todo done {i}" for i in perms]
            perms_exist = [
                call(i, "todo_mark_as_done") in mock_log_and_exec_process.mock_calls
                for i in perms
            ]
            assert reduce(lambda a, b: a or b, perms_exist)

    def test_portfolio_case_2(self):
        reset_todocli()
        todo_add(title="Two bottles of milk", context="shopping_list")  # ID:1
        todo_add(title="Three cans of SinaCola", context="shopping_list")  # ID:2
        todo_add(title="Fifty eggs", context="shopping_list")  # ID:3

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Prioritize the first item in my shopping list"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                "todo task 1 --priority 5", "todo_task"
            )

    def test_portfolio_case_3(self):
        reset_todocli()
        todo_add(title="NLP Project", context="project_list")  # ID:1
        todo_add(title="Math Project", context="project_list")  # ID:2
        todo_add(title="ML Project", context="project_list")  # ID:3
        todo_add(title="Algebra I Project", context="archive_list")  # ID:3
        todo_mark_as_done([1, 2])

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Move all completed tasks from my project_list to an archive_list"""
            logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_has_calls(
                calls=[
                    call('todo task 1 --context "archive_list"', "todo_task"),
                    call('todo task 2 --context "archive_list"', "todo_task"),
                ],
                any_order=True,
            )


if __name__ == "__main__":
    unittest.main()
    # setup_testing_env()
