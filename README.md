# PersonalAssistantBot

A Discord bot powered by Google's Generative AI (GenAI) designed to provide conversational AI capabilities, automated welcome/goodbye messages, and utility commands within your Discord server.

## Features

*   **Conversational AI:** Engage in conversations by mentioning the bot or replying to its messages. It uses reply chains for context.
*   **AI-Powered Welcome Messages:** Automatically generates and sends a unique welcome message when a new member joins the server.
*   **AI-Powered Goodbye Messages:** Automatically generates and sends a goodbye message when a member leaves the server.
*   **Slash Commands:**
    *   `/help`: Displays a list of commands and bot features.
    *   `/tags [user]`: Sends a link to the Danbooru tag group wiki, optionally mentioning a specified user.
*   **Configurable AI Models:** Choose different Google AI models for different tasks (general chat, welcome/goodbye messages).
*   **Model Fallback:** Automatically attempts to use a secondary AI model if the primary one fails.
*   **(Hidden) Timeout Command:** Includes a mechanism for timing out users (triggered via specific bot replies - see code for details).

## Prerequisites

*   **Python 3.10+**
*   **Discord Bot Token:** You need to create a Discord Application and get a bot token. See the Discord Developer Portal.
    *   **Required Intents:** Ensure your bot has the following Privileged Gateway Intents enabled in the Developer Portal:
        *   `Server Members Intent` (Required for `on_member_join`/`on_member_remove` and fetching members)
        *   `Message Content Intent` (Required for reading message content for AI context and commands)
*   **Google AI Studio API Key:** You need an API key from Google AI Studio.

## Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Sorro123/DiscordBot.git
    cd DiscordBot
    ```

2.  **Configure API Keys (`variables/keys.json`):**
    Rename `keys.EXAMPLE.json` to `keys.json` inside the `variables` directory with your API keys:
    ```json
    {
      "client_key": "YOUR_DISCORD_BOT_TOKEN",
      "ai_studio_key": "YOUR_GOOGLE_AI_STUDIO_API_KEY"
    }
    ```

3.  **Configure Prompts (`variables/prompts.json`):**
    Rename `prompts.EXAMPLE.json` to `prompts.json` inside the `variables` directory. This defines the instructions given to the AI. Adjust the prompts to shape the bot's personality and responses.
    - An example system prompt is provided, either replace all of the text between backticks ` with the appropriate value or write your own.

5.  **Configure General Settings (`variables/general.json`):**
    General variables are controlled by a file named `general.json` inside the `variables` directory.
    *   Make sure the model names listed in `"ai_studio"` are valid models accessible via your API key. Check the Google AI documentation for available models.
    *   Make sure to change "owner_id" to **YOUR** discord ID.

6.  **Install and start the bot:**

    Run
    ```bash
    UpdateAndStart.bat
    ```
    in the terminal or just open `UpdateAndStart.bat` to finish installation and start the bot.

## Running the Bot

*   **Auto Update:**
    Repeat step 5 of the installation.

*   **No Update:**
    Repeat step 5 of the installation but using `start.bat` instead of `UpdateAndStart.bat`

## Usage

*   **Chat:** Mention the bot (`@YourBotName`), use its display name or reply directly to one of its messages to start or continue a conversation.
*   **Commands:** Use the slash commands registered with Discord:
    *   `/help`: Get help information.
    *   `/tags`: Get the Danbooru tag wiki link.
    *   `/tags user:@SomeUser`: Get the link and mention the specified user.
*   **Welcome/Goodbye:** These messages are triggered automatically when members join or leave the server, provided the bot has permission to see these events and post in the configured system channel.

## Contributing

Contributions are welcome! If you have suggestions for improvements or find bugs, please feel free to open an issue or submit a pull request.

## License

**[DiscordBot](https://github.com/Sorro123/DiscordBot) by [UrBoiTom\_](https://github.com/Sorro123) is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/?ref=chooser-v1)** License - see the `LICENSE.md` file for details.
