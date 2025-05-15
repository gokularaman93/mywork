"""
You are given a string and your task is to swap cases. In other words, convert all lowercase letters to uppercase letters and vice versa.

For Example:

Www.HackerRank.com → wWW.hACKERrANK.COM
Pythonist 2 → pYTHONIST 2  
"""
def swap_case(s):
    result = ""
    for item in s:
        if item.islower():
            result += item.upper()
        elif item.isupper():
            result += item.lower()
        else:
            result += item
    return result

if __name__ == '__main__':
    s = input()
    result = swap_case(s)
    print(result)