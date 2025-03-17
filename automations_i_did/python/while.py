#basic
number = 0
while number < 5:
    print("Your number is " + str(number))
    number = number + 1


#type your name
name = ''
while name != 'your name':
    print("Please type your name")
    name = input()
print("Thank you for entering your name 😂")


#type your name with break
name = ''
while True:
    print("Enter your name")
    name = input()
    if name == "your name":
        break
print("Thanks again")

#while with break
number = 0
print("number is " + str(number))
while number < 5:
    number += 1
    if number == 3:
        continue
    print("number is " + str(number))

    