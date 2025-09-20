def log(message, fg=None, verbose_only=True, verbose=False):
    if not verbose_only or verbose:
        if fg == "red":
            print(f"\033[91m{message}\033[0m")
        elif fg == "green":
            print(f"\033[92m{message}\033[0m")
        elif fg == "yellow":
            print(f"\033[93m{message}\033[0m")
        else:
            print(message)
