import time
import functools
import sys

def time_execution(label=None):
    """
    Decorator to measure and log execution time of functions.
    
    Args:
        label (str, optional): Custom label for the log message. If None, 
                               uses the function name.
    
    Returns:
        Function decorator that measures and logs execution time.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create message prefix from label or function name
            message_prefix = label if label else f"Executing {func.__name__}"
            
            # Log start message
            print(f"{message_prefix}...")
            
            # Measure execution time
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            # Calculate duration and log result
            duration = end_time - start_time
            print(f"{message_prefix}: {duration:.2f} seconds")
            
            return result
        return wrapper
    return decorator
