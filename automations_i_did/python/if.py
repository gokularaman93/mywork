name="baby"
if name == "baby":
    print ("Hi " + name)


name = input()
age = int(input())
# name = "gocool"
if name == "gocool":
    print(name + " is a good name")
    print(age + " is your age")
elif age > 18:
    print("atleast you are major" )
else:
    print(name + " is a bad name and " + age + " bad age")

print("*"*40)
print("Program Completed")
print("*"*40)