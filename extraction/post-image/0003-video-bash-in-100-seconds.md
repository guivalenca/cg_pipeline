---
id: "3"
title: "Bash in 100 Seconds"
source_url: "https://www.youtube.com/watch?v=I4EWvMFj37g"
fetch_url: "https://www.youtube.com/watch?v=I4EWvMFj37g"
resolved_url: "https://www.youtube.com/watch?v=I4EWvMFj37g"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T04:38:24.373753Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "4d680fe0195061d1a1bee061959e6f4255d6b3349ab0eb7648aedccfdb5d95a4"
cache_keys:
  - "4d680fe0195061d1a1bee061959e6f4255d6b3349ab0eb7648aedccfdb5d95a4"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 153.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "cdad33de39a8a7e1cdd8fd18095eed6e26612736056e328c3f6185c51db14ea2"
word_count: 1302
char_count: 7766
content_sha256: "53e1a42c317177e712378cb3c1de4bccb45898beca4a28c078b6d7a609f47bf9"
image_count: 21
link_count: 0
total_token_count: 12680
estimated_input_tokens: 8228
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## 00:00 Bash: Command Language Interpreter

**Spoken content:** Bash, a command language interpreter for interacting with a computer from the command line.

**On-screen content:** A glowing white cube with a dollar sign on one face, against a dark background.
![diagram: glowing cube with dollar sign](video-frame://3@00:00)

## 00:05 The Shell Concept

**Spoken content:** It's also called a shell because it surrounds the operating system kernel to hide its intricate details, while allowing you, the programmer, to do important stuff like access data and write files by typing simple commands.

**On-screen content:** A stylized shell (like a conch shell) sits on a circuit board. A terminal window opens, showing `touch file.txt` and `cat file.txt` commands being typed.
![diagram: shell on circuit board with terminal commands](video-frame://3@00:09)

## 00:17 History of Shells

**Spoken content:** This was a revolutionary concept when it was developed in the early 70s, back when programmers were still using punch cards. The shell concept evolved over the years, with the Bourne Shell being the most popular version. That is, until 1989, when the Bourne-Again Shell, or Bash, came about.

**On-screen content:**
*   **00:17** "THOMPSON SHELL" with "Ken Thompson 1971" and an image of Ken Thompson. Below, a punch card is shown.
    ![image: Ken Thompson and punch card](video-frame://3@00:17)
*   **00:23** "BOURNE SHELL" with "Stephen Bourne 1979" and a terminal showing `sh` commands.
    ![image: Stephen Bourne and terminal output](video-frame://3@00:23)
*   **00:27** "BASH THE BOURNE-AGAIN SHELL" with "Brian Fox 1989" and an image of a person emerging from water, symbolizing "born again".
    ![image: Brian Fox and "born-again" imagery](video-frame://3@00:27)

## 00:31 Bash as a Default Shell

**Spoken content:** When you open up the terminal on a Unix machine, like macOS and most Linux distros, the default shell is usually Bash. It provides a prompt where you can type a command, which will then be interpreted by the shell and executed on the operating system.

**On-screen content:** A terminal window with `bash` as the shell. `echo hi mom` is typed, and `hi mom` is output. A finger points to the prompt.
![terminal: echo command and prompt](video-frame://3@00:39)

## 00:45 Checking Your Shell

**Spoken content:** To find out if you're running Bash, type in `which $SHELL` from the command line. It's like any other application that lives in the binaries directory.

**On-screen content:** A terminal window showing `which $SHELL` typed, and the output `/usr/bin/bash`.
![terminal: which $SHELL command](video-frame://3@00:47)

## 00:52 Bash as a Programming Language

**Spoken content:** But Bash is also a programming language that allows us to write scripts, which means anything we type manually into the command line can be automated with code.

**On-screen content:** A code editor showing a Bash script named `beerme.sh` with a `while true` loop and `case` statement.
![code: beerme.sh script with while loop](video-frame://3@00:57)

## 01:00 Startup Scripts

**Spoken content:** When you first launch the shell, it actually runs a startup script that's defined in the `.bash_profile` or `.bashrc` file on your system. This allows you to customize the behavior and appearance of the shell whenever you start a new session.

**On-screen content:** A dashboard with "STARTUP SCRIPT" and `.bashrc` and `.bash_profile` files. Then, a terminal showing a customized prompt and output from `git status`.
![terminal: customized prompt and git status](video-frame://3@01:08)

## 01:12 Creating a Bash Script

**Spoken content:** You can add your own custom Bash scripts to any project by creating a file that ends in `.sh` or no file extension at all. The first line in that file should always be a shebang, followed by the path to the application that should run it. Below that, we can start writing commands, like `echo` to print something, and they'll be interpreted line by line.

**On-screen content:**
*   **01:12** A terminal showing `touch beerme.sh`.
    ![terminal: touch beerme.sh](video-frame://3@01:12)
*   **01:17** A VS Code editor showing `beerme.sh` in the file explorer.
    ![code editor: beerme.sh file](video-frame://3@01:17)
*   **01:19** The `beerme.sh` file content: `#!/usr/bin/bash` (shebang) and `echo "my first bash script ✨"`.
    ![code: shebang and echo command](video-frame://3@01:24)

## 01:30 Variables in Bash

**Spoken content:** To create a variable, type a name in all caps, followed by the equal sign, then reference it later in the script using a dollar sign in front of the name.

**On-screen content:** The `beerme.sh` script with a variable `GREET="Howdy Partner"` and its usage `echo $GREET`.
![code: Bash variable definition and usage](video-frame://3@01:31)

## 01:38 Running a Script

**Spoken content:** Now to execute the script, simply type the file name into the shell.

**On-screen content:** A terminal showing `./beerme.sh` being typed and executed.
![terminal: executing beerme.sh](video-frame://3@01:39)

## 01:41 Positional Arguments

**Spoken content:** That was easy, but what if we want to pass in some arguments when we run the script? Positional arguments will automatically be assigned variable names of 1, 2, 3, and so on.

**On-screen content:**
*   **01:43** A terminal showing `./beerme.sh name age` as arguments.
    ![terminal: script with positional arguments](video-frame://3@01:43)
*   **01:46** The `beerme.sh` script showing `echo "Name: $1"` and `echo "Age: $2"`.
    ![code: positional arguments $1 and $2](video-frame://3@01:46)

## 01:51 User Input and Loops

**Spoken content:** Now in other cases, you may need additional user input in the middle of a script. You can create loops in Bash, like a do-while loop here, that will prompt the user to continue the script on a yes answer or exit on a no answer.

**On-screen content:**
*   **01:52** A terminal showing user input for "Name" and "Age", then a prompt "Do you wish to drink a beer?".
    ![terminal: user input and prompt](video-frame://3@01:52)
*   **01:55** The `beerme.sh` script showing a `while true; do ... done` loop with `read -p` for user input and a `case` statement for 'Yy' or 'Nn' answers.
    ![code: while loop with read and case statement](video-frame://3@01:56)

## 02:03 Conditional Logic

**Spoken content:** From there we can implement conditional logic with an if statement, which will test if the value on the left side is less than the value on the right side. If true, then run this command, otherwise run the else command.

**On-screen content:** The `beerme.sh` script showing an `if` statement: `if [ $2 -lt 21 ]; then echo "You are too young to use this script" else fi`.
![code: if-else statement with -lt operator](video-frame://3@02:04)

## 02:14 Running in Background

**Spoken content:** Another cool feature is that if you have multiple long running processes, you can run them in parallel in the background by adding an ampersand after the command.

**On-screen content:** The `beerme.sh` script showing multiple commands followed by an ampersand `&` to run them in the background: `long_process &`, `slow_stuff &`, `async_job &`, `background_task &`.
![code: commands running in background with ampersand](video-frame://3@02:15)

## 02:22 Conclusion

**Spoken content:** This has been Bash, the Bourne-Again Shell, in 100 seconds. If you want to see more short videos like this, make sure to hit the like button and subscribe. Thanks for watching, and I will see you in the next one.

**On-screen content:** The glowing cube with a dollar sign from the intro, then the "BASH THE BOURNE-AGAIN SHELL" logo.
![logo: Bash The Bourne-Again Shell](video-frame://3@02:24)
