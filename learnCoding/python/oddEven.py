#!/bin/python3

import math
import os
import re
import sys

if __name__ == '__main__':
    user_input = input().strip()
    if not user_input or not user_input.isdigit():
        print("Enter an integer")
        sys.exit(1)
    
    n = int(user_input)
    if n % 2 != 0:
        print("Weird")
    if n % 2 == 0 and n in range(2,5):
        print("Not Weird")
    if n % 2 == 0 and n in range(6,21):
        print("Weird")
    #If  is even and greater than 20, print Not Weird
    if n % 2 == 0 and n > 20:
        print("Not Weird")

