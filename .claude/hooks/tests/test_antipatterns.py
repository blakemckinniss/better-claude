#!/usr/bin/env python3
"""Test file with critical anti-patterns to verify detection."""

import os
import subprocess

# Test 1: Exposed API Key
API_KEY = "sk-proj-abcdef1234567890abcdef1234567890"
aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"
github_token = "ghp_1234567890abcdef1234567890abcdef12"


# Test 2: SQL Injection
def bad_query(user_input):
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    return query


def another_bad_query(request):
    sql = f"DELETE FROM products WHERE id = {request.params['id']}"
    return sql


# Test 3: Command Injection
def bad_command(user_input):
    os.system(f"echo {user_input}")


def bad_subprocess(params):
    subprocess.run(f"ls {params}", shell=True)


# Test 4: Path Traversal
def bad_file_read(request):
    filename = request.params["file"]
    with open(filename) as f:
        return f.read()


# Test 5: Hardcoded Password
password = "super_secret_password_123"
DATABASE_URL = "postgres://admin:mypassword@localhost/db"


# Test 6: Destructive Operations
def dangerous_delete():
    import shutil

    shutil.rmtree("/tmp")  # This would delete everything in /tmp


def bad_sql_delete():
    # This deletes ALL rows!
    query = "DELETE FROM important_table"
    return query


# Test 7: Infinite Loop
def infinite_loop():
    while True:
        print("processing...")  # No break condition!


# Test 8: Memory Leak
global_cache = {}


def leaky_function(data):
    global global_cache
    # This keeps growing forever
    global_cache[data.id] = data


# Test 9: Blocking in Async
async def bad_async():
    import time

    time.sleep(5)  # Should use asyncio.sleep

    import requests

    response = requests.get("http://example.com")  # Should use aiohttp
