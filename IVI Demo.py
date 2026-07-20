from Test import (
    init_driver,
    Click_By_Image,
    Click_By_Text,
    Swipe_Down,
    Compare_Screen_By_Text
)
import time

def main():
    init_driver()
    time.sleep(5)

    print(Click_By_Image(r"C:\Users\yuvraj.s.MTPA332-L\Documents\Menu.png,10"))
    print(Click_By_Text("All Apps,10"))

    for i in range(3):
        print(Swipe_Down("hi,10"))

    print(Click_By_Text("Settings,10"))
    print(Swipe_Down("hi,10"))
    print(Click_By_Text("System,10"))
    print(Click_By_Text("About,10"))

    result = Compare_Screen_By_Text("R11 35,10")
    print(result)

    output, _ = result.split("#")

    if output == "Ok":
        print("System Software version matches the required version 11.35")
    else:
        print("System Software version does not match the required version 11.35")


if __name__ == "__main__":
    main()