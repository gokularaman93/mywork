# import textwrap

def wrap(string, max_width):
    s = ""
    for i in range(0, len(string), max_width):
        s += string[i:i+max_width] + "\n"
    return s

if __name__ == '__main__':
    string = input("Enter the string: ")
    max_width = int(input("Enter the max width: "))
    print(wrap(string, max_width))