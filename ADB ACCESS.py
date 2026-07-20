import wexpect

USERNAME = "root"
PASSWORD = "oelinux123"

def adb_login_and_run(command="ls"):
    try:
        child = wexpect.spawn("adb shell")
        child.expect("login:")
        child.sendline(USERNAME)

        child.expect("Password:")
        child.sendline(PASSWORD)

        # Wait for root prompt
        child.expect("#")

        # Run your command
        child.sendline(command)
        child.expect("#")

        output = child.before.strip()

        child.sendline("exit")
        child.close()

        return f"OK#{output}"

    except Exception as e:
        return f"NOT_OK#{str(e)}"


# if __name__ == "__main__":
#     result = adb_login_and_run("ifconfig")
#     print(result)