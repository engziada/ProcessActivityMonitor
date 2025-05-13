"""
GUI utilities for handling input in windowed mode.
"""
import tkinter as tk
from tkinter import simpledialog

def gui_input(prompt=None):
    """
    A GUI replacement for the standard input() function.
    
    Args:
        prompt (str, optional): The prompt to display to the user.
        
    Returns:
        str: The user's input, or an empty string if canceled.
    """
    # Create a root window but hide it
    root = tk.Tk()
    root.withdraw()
    
    # Make sure the window appears on top
    root.attributes('-topmost', True)
    
    # Show a simple dialog and get input
    result = simpledialog.askstring("Input", prompt or "Press OK to continue...", parent=root)
    
    # Destroy the root window
    root.destroy()
    
    # Return the result or an empty string if canceled
    return result or ""
