def split_and_join(sentence):
    sentence = sentence.split(" ")
    sentence = "-".join(sentence)
    return sentence

if __name__ == '__main__':
    sentence = input()
    result = split_and_join(sentence)
    print(result)