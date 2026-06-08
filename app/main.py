import sys


def main():
    sys.stdout.write("$ ")
    pass

    command = input()
    print(f"{command}: Command Not Found")

if __name__ == "__main__":
    main()
