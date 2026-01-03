#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yandex Transport Proxy - Run All Tests
Запуск всех unit тестов проекта
"""

import sys
import os
import subprocess

# ANSI цвета для красивого вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Печать заголовка"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def run_test_file(test_file):
    """Запустить один тестовый файл"""
    print(f"{YELLOW}Running: {test_file}{RESET}")
    
    # Абсолютный путь к тестовому файлу
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_path = os.path.join(script_dir, test_file)
    
    if not os.path.exists(test_path):
        print(f"{RED}✗ File not found: {test_path}{RESET}\n")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, test_path],
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"{GREEN}✓ {test_file} passed{RESET}\n")
            return True
        else:
            print(f"{RED}✗ {test_file} failed{RESET}\n")
            return False
    except subprocess.TimeoutExpired:
        print(f"{RED}✗ {test_file} timed out{RESET}\n")
        return False
    except Exception as e:
        print(f"{RED}✗ {test_file} error: {e}{RESET}\n")
        return False

def main():
    """Запустить все тесты"""
    print_header("Yandex Transport Proxy - Test Suite")
    
    # Список unit тестов (старые тесты требуют pytest, пропускаем)
    test_files = [
        "tests/test_preload_cache.py"
    ]
    
    # Проверяем наличие pytest для старых тестов
    try:
        import pytest
        test_files.extend([
            "tests/test_transport_proxy.py",
            "tests/test_yandex_transport_core.py",
        ])
    except ImportError:
        print(f"{YELLOW}Note: pytest not installed, skipping old tests{RESET}")
        print(f"      Install: pip install pytest\n")
    
    results = {}
    
    # Запускаем каждый тест
    for test_file in test_files:
        results[test_file] = run_test_file(test_file)
    
    # Итоговый отчет
    print_header("Test Results Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_file, success in results.items():
        status = f"{GREEN}PASS{RESET}" if success else f"{RED}FAIL{RESET}"
        print(f"  {status}  {test_file}")
    
    print(f"\n{'-'*70}")
    print(f"  Total:  {total} test files")
    print(f"  {GREEN}Passed: {passed}{RESET}")
    if failed > 0:
        print(f"  {RED}Failed: {failed}{RESET}")
    print(f"{'-'*70}\n")
    
    # Информация об integration тестах
    print(f"{YELLOW}Note:{RESET} Integration tests are skipped by default.")
    print(f"      Run them manually: python tests/test_preload_integration.py --run-slow\n")
    
    # Возвращаем код выхода
    return 0 if all(results.values()) else 1

if __name__ == '__main__':
    sys.exit(main())
