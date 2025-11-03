cd`# How to Use the Bash Console on PythonAnywhere

## What is a Bash Console?

A **Bash console** (also called a terminal or command line) is a text-based interface where you can type commands to control your computer or server. It's like typing commands instead of clicking buttons.

## Step-by-Step: Opening the Bash Console

### 1. Log into PythonAnywhere
- Go to [www.pythonanywhere.com](https://www.pythonanywhere.com)
- Click **"Log in"** and enter your credentials

### 2. Find the Consoles Tab
- Look at the top navigation bar
- You'll see tabs like: **Files**, **Web**, **Tasks**, **Consoles**, etc.
- Click on **"Consoles"**

### 3. Open a Bash Console
- On the Consoles page, you'll see a button that says **"Bash"**
- Click it (or click **"New console"** → select **"Bash"**)
- A terminal window will appear at the bottom of your screen

### 4. What You'll See
The console will look something like this:
```
16:30 ~ $ 
```
- The `~` means you're in your home directory
- The `$` is the prompt - it's waiting for you to type a command

## Basic Commands You'll Need

### Check where you are:
```bash
pwd
```
*Shows your current directory (should be `/home/yourusername`)*

### List files in current directory:
```bash
ls
```
*Shows all files and folders*

### See files with details:
```bash
ls -la
```
*Shows files including hidden ones*

### Navigate to a directory:
```bash
cd ~
```
*Goes to your home directory (the `~` is short for home)*

### Check Python version:
Try these commands in order until one works:

1. First, try direct version commands:
```bash
python3.10 --version
python3.11 --version
python3.9 --version
python3.8 --version
```

2. Or check what commands are available:
```bash
which python3
which python
```

3. Or see all Python executables:
```bash
compgen -c python
```

4. Or check PythonAnywhere's specific location:
```bash
ls -la ~/python*
```

5. If none work, just try running Python directly:
```bash
python3.10
```
(Then type `exit()` to quit if it opens)

*One of these will help you find your Python version*

### Install packages:
```bash
pip3.10 install --user discord.py pandas openpyxl flask
```
*Installs Python packages (replace `3.10` with your version)*

### Run your bot:
```bash
python3 bot.py
```
*Starts your Discord bot*

## Tips & Tricks

### Copy/Paste in Console:
- **Windows/Linux**: Right-click in the console to paste
- **Or**: Ctrl+Shift+V to paste, Ctrl+Shift+C to copy

### Stop a Running Program:
- Press **Ctrl + C** to stop whatever is running

### Clear the Screen:
```bash
clear
```
*Or just press Ctrl+L*

### See Your Command History:
- Press the **Up Arrow** to see previous commands
- Press **Down Arrow** to go forward

### Run Command in Background:
```bash
python3 bot.py &
```
*The `&` runs it in the background (but console must stay open)*

## Example Session

Here's what a complete session might look like:

```
~ $ pwd
/home/myusername

~ $ ls
bot.py  requirements.txt  'Copy of Twilight BATs'\'' WWE Champions Tier List.xlsx'

~ $ python3.10 --version
Python 3.10.12

~ $ which python3
/usr/bin/python3.10

~ $ pip3.10 install --user discord.py pandas openpyxl flask
Collecting discord.py...
Installing collected packages...
Successfully installed...

~ $ export DISCORD_BOT_TOKEN="my-secret-token-123"

~ $ python3 bot.py
📂 Loading Excel file...
✅ Loaded sheet: Sheet1 (100 rows, 15 columns)
✅ Web server started on port 8080
✅ Logged in as MyBot#1234

[Bot is now running - don't close this console!]
```

## Common Issues

**Problem:** "Command not found"
- **Solution:** Check spelling, make sure you're in the right directory

**Problem:** "Permission denied"
- **Solution:** Some commands need `sudo`, but PythonAnywhere free tier has limitations

**Problem:** "No module named 'discord'"
- **Solution:** Install it with `pip3 install --user discord.py`

**Problem:** Bot stops when I close the console
- **Solution:** That's normal on free tier. Keep console open or use `screen`/`tmux`

## Next Steps

Once you're comfortable with the Bash console:
1. Upload your files
2. Install dependencies
3. Set your bot token
4. Run the bot
5. Keep the console open!

For more details, see `PYTHONANYWHERE_SETUP.md`

