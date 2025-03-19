def div53by(number):
    try:
        return 53 / number
    except ZeroDivisionError:
        return("Error: The number you passed zero")

print(div53by(10))
print(div53by(5))
print(div53by(3.5))
print(div53by(0))