#!/usr/bin/env python3
"""
Test script to verify graceful shutdown handling for systemd service.
This simulates what happens when systemctl stop/restart is called.
"""

import subprocess
import time
import signal
import sys
import os

def test_sigterm_handling():
    """Test that the service handles SIGTERM gracefully."""
    print("Starting test of SIGTERM handling...")
    
    # Start the main.py process from parent directory
    print("Starting main.py process...")
    main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
    process = subprocess.Popen(
        [sys.executable, main_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        universal_newlines=True,
        cwd=os.path.dirname(main_path)  # Run from project root
    )
    
    # Give it time to initialize
    print("Waiting for process to initialize...")
    time.sleep(3)
    
    # Check if process is running
    if process.poll() is not None:
        print("ERROR: Process died during initialization")
        stdout, stderr = process.communicate()
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False
    
    print(f"Process started with PID: {process.pid}")
    
    # Send SIGTERM (same as systemctl stop/restart)
    print("Sending SIGTERM signal...")
    process.send_signal(signal.SIGTERM)
    
    # Wait for process to terminate (with timeout)
    try:
        stdout, stderr = process.communicate(timeout=5)
        print("\nProcess output:")
        print("STDOUT:")
        for line in stdout.split('\n'):
            if line.strip():
                print(f"  {line}")
        if stderr:
            print("STDERR:")
            for line in stderr.split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        # Check exit code
        if process.returncode == 0:
            print(f"\n✓ Process exited cleanly with code: {process.returncode}")
            return True
        else:
            print(f"\n✗ Process exited with non-zero code: {process.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n✗ Process did not terminate within 5 seconds")
        process.kill()
        return False

def test_multiple_signals():
    """Test handling multiple signals in quick succession."""
    print("\n\nTesting multiple signals in quick succession...")
    
    # Start the process from parent directory
    main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
    process = subprocess.Popen(
        [sys.executable, main_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
        cwd=os.path.dirname(main_path)  # Run from project root
    )
    
    time.sleep(2)
    
    if process.poll() is not None:
        print("ERROR: Process died during initialization")
        return False
    
    print(f"Process started with PID: {process.pid}")
    
    # Send multiple SIGTERM signals
    print("Sending multiple SIGTERM signals...")
    for i in range(3):
        if process.poll() is None:
            print(f"  Sending SIGTERM #{i+1}")
            process.send_signal(signal.SIGTERM)
            time.sleep(0.1)
    
    # Wait for termination
    try:
        process.communicate(timeout=5)
        print("✓ Process handled multiple signals gracefully")
        return True
    except subprocess.TimeoutExpired:
        print("✗ Process hung after multiple signals")
        process.kill()
        return False

if __name__ == "__main__":
    print("=== Testing systemd shutdown behavior ===\n")
    
    # Check if main.py exists in parent directory
    main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
    if not os.path.exists(main_path):
        print(f"ERROR: main.py not found at {main_path}")
        sys.exit(1)
    
    # Run tests
    test1_passed = test_sigterm_handling()
    test2_passed = test_multiple_signals()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"SIGTERM handling: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Multiple signals: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n✓ All tests passed! The service should handle systemctl stop/restart correctly.")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed. Check the implementation.")
        sys.exit(1)
