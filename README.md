# Discord Unban Request Bot

This bot allows users to submit unban requests to a specified database. It also provides administrators with tools to manage these requests through interaction buttons directly in Discord.

## Features

- **User Requests:** Users can submit unban requests with their SteamID, FaceIT nickname, hub, and reason.
- **Admin Tools:** Administrators can review requests and use interaction buttons to mark a request as "Not Connected" or "Leave".
- **Admin Logging:** The bot logs which administrator handled each request and updates the database accordingly.
- **Automated Channel Management:** Automatically manages help channels by creating a private room for users to submit their requests, complete with instructions.
- **FaceIT API Integration:** Integrates with the FaceIT API to validate SteamID and FaceIT account linkage.
- **Database Integration:** Stores all requests and admin actions in a MySQL database for tracking and reporting.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.7 or later installed on your machine.
- MySQL server running and accessible.
- A Discord bot token. [How to create a Discord bot](https://discordpy.readthedocs.io/en/stable/discord.html).
- FaceIT API key. [How to get a FaceIT API key](https://developers.faceit.com/).
- Basic knowledge of setting up and managing MySQL databases.

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/discord-unban-bot.git
   cd discord-unban-bot

1. Install dependencies:
   ```bash
   py -m pip install -r requirements.txt

## Set up the MySQL database:

Create a database in your MySQL server.
Run the following SQL script to create the necessary tables:

CREATE DATABASE unban_requests_db;

USE unban_requests_db;

CREATE TABLE unban_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    steamid VARCHAR(17) NOT NULL,
    faceit_nickname VARCHAR(255) NOT NULL,
    hub VARCHAR(255) NOT NULL,
    reason TEXT NOT NULL,
    request_count INT DEFAULT 1,
    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bans VARCHAR(255),
    admin VARCHAR(255)
);


## Run the bot:
py bot.py


## Usage
Submit Unban Request: Users can submit an unban request using the following command in a help channel:

!unban <steamid> <faceit_nickname> <hub> <reason>

## Example:
!unban 12345678901234567 blueye redhog crash

Admin Interaction:

After a request is submitted, admins can interact with the buttons provided in the request message to mark the request as "Not Connected" or "Leave". The bot will update the database with the action taken and the admin's username.


## Permissions
To ensure the bot functions correctly, it requires the following permissions:

Manage Channels
Manage Messages
Read Message History
Send Messages
Embed Links
Use External Emojis
Manage Roles (Optional but recommended for full functionality)
For enhanced security, it's advised to only grant the bot the permissions it strictly needs rather than the Administrator permission.

## Contributing
Contributions are welcome! Please fork this repository and submit a pull request with your changes. For major changes, please open an issue first to discuss what you would like to change.

## Acknowledgements
Discord.py - Python wrapper for the Discord API.
FaceIT API - For FaceIT player data integration.
steam web API- for Steam integration
MySQL - For database management.


This `README.md` provides a clear, step-by-step guide for setting up, configuring, and running your Discord Unban Request Bot. It also includes information about prerequisites, usage, and contributing to the project.
