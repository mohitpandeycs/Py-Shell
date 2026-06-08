import sys

def main():
    while True:
        sys.stdout.write("$ ") 
        command = input()       # User Input
        if command == "exit":
            break
        elif command.startswith("echo "):
                print(command[5:])      # Index Slicing for Skipping index 0 - 4
        else:
            print(f"{command}: command not found")

if __name__ == "__main__":
    main() 