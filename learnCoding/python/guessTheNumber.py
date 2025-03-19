print("Hello Whats your name")
name = input()
print("Hello " + name  + ": lets play a game to guess the secret number in 6 guesses bwn 1 to 20")

import random 
secret_number = random.randint(1,20)

#6 guesses
for num in range(1,7):
    print("Enter a number:")
    guess = int(input())
    if guess < secret_number:
        print("try guessing a higher number")
    elif guess > secret_number:
        print("try guessing a smaller number")
    else:
        break

if guess == secret_number:
    print("Congrats you guessed the secret number " + str(secret_number) + " right")
else:
    print ("oops. you missed guessing it. the secret number is "+ str(secret_number) + " you want to replay?")

    
