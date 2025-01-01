from xai_components.base import InArg, OutArg, InCompArg, Component, BaseComponent, secret, xai_component
import openai
from openai import OpenAI

import os
import requests
import shutil


class Conversation:
    def __init__(self):
        self.conversation_history = []

    def add_message(self, role, content):
        message = {"role": role, "content": content}
        self.conversation_history.append(message)

    def display_conversation(self, detailed=False):
        for message in self.conversation_history:
            print(f"{message['role']}: {message['content']}\n\n")

@xai_component
class OpenAIMakeConversation(Component):
    """Creates a conversation object to hold conversation history.
    """

    prev: InArg[Conversation]
    system_msg: InArg[str]
    user_msg: InArg[str]
    assistant_msg: InArg[str]
    function_msg: InArg[str]

    conversation: OutArg[Conversation]

    def execute(self, ctx) -> None:
        conv = Conversation()
        if self.prev.value is not None:
            conv.conversation_history.extend(self.prev.value.conversation_history)
        if self.system_msg.value is not None:
            conv.add_message("system", self.system_msg.value)
        if self.user_msg.value is not None:
            conv.add_message("user", self.user_msg.value)
        if self.assistant_msg.value is not None:
            conv.add_message("assistant", self.assistant_msg.value)
        if self.function_msg.value is not None:
            conv.add_message("function", self.function_msg.value)

        self.conversation.value = conv


@xai_component
class OpenAIAuthorize(Component):
    """Sets the organization and API key for the OpenAI client and creates an OpenAI client.

    This component checks if the API key should be fetched from the environment variables or from the provided input.
    It then creates an OpenAI client using the API key and stores the client in the context (`ctx`) for use by other components.

    #### Reference:
    - [OpenAI API](https://platform.openai.com/docs/api-reference/authentication)

    ##### inPorts:
    - organization: Organization name id for OpenAI API.
    - api_key: API key for the OpenAI API.
    - from_env: Boolean value indicating whether the API key is to be fetched from environment variables.

    """
    organization: InArg[secret]
    base_url: InArg[str]
    api_key: InArg[secret]
    from_env: InArg[bool]

    def execute(self, ctx) -> None:
        openai.organization = self.organization.value
        openai.base_url= self.base_url.value
        if self.from_env.value:
            openai.api_key = os.getenv("OPENAI_API_KEY")
        else:
            openai.api_key = self.api_key.value

        client = OpenAI(api_key=self.api_key.value)
        ctx['client'] = client
        ctx['openai_api_key'] = openai.api_key


import os
import ssl
import re
import requests
import threading
from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from xai_components.base import InArg, OutArg, InCompArg, BaseComponent, Component, xai_component, secret


@xai_component
class SlackClient(Component):
    """
    A component that initializes a Slack WebClient with the provided `slack_bot_token`. The created client is then added to the context for further use by other components.

    ## Inputs
    - `slack_bot_token` (optional): The Slack bot token used to authenticate the WebClient. If not provided, it will try to read the token from the environment variable `SLACK_BOT_TOKEN`.

    ## Outputs
    - Adds the `slack_client` object to the context for other components to use.
    """
    slack_bot_token: InArg[secret]

    def execute(self, ctx) -> None:
        slack_bot_token = os.getenv("SLACK_BOT_TOKEN") if self.slack_bot_token.value is None else self.slack_bot_token.value
        slack_client = WebClient(slack_bot_token)
        ctx.update({'slack_client':slack_client})

@xai_component
class SlackSendMessageToServerAndChannel(Component):
    """
    A component that sends a message to a specific server and channel in Slack.

    ## Inputs
    - `server_url`: The URL of the server to send the message to.
    - `channel_id`: The ID of the channel in the server to send the message to.
    - `message`: The message content to be sent.

    ## Requirements
    - `slack_client` instance in the context (created by `SlackClient` component).
    """
    server_url: InArg[str]
    channel_id: InArg[str]
    message: InArg[str]

    def execute(self, ctx) -> None:
        slack_client = ctx['slack_client']
        server_url = self.server_url.value
        channel_id = self.channel_id.value
        message = self.message.value

        response = slack_client.chat_postMessage(channel=channel_id, text=message)
        print(f"Message sent to server {server_url} and channel {channel_id}: {message}")



from xai_components.base import InArg, OutArg, InCompArg, Component, BaseComponent, xai_component, dynalist, SubGraphExecutor

import requests
from datetime import datetime, timezone

@xai_component
class GetWeather(Component):
    """Fetches current weather information for a specified city.

    ##### inPorts:
    - city (str): The name of the city to retrieve weather for.
    - api_key (str): The API key for authentication.
    - url (str): The base URL of the weather API.

    ##### outPorts:
    - weather_info (str): The weather information as a JSON string.
    """
    city: InArg[str]
    api_key: InArg[str]
    url: InArg[str]
    weather_info: OutArg[str]

    def execute(self, ctx) -> None:
        try:
            city_name = self.city.value
            api_key = self.api_key.value
            base_url = self.url.value

            if not city_name:
                raise ValueError("City name is required.")
            if not api_key:
                raise ValueError("API key is required.")
            if not base_url:
                raise ValueError("API base URL is required.")

            url = f"{base_url}?q={city_name}&appid={api_key}&units=metric&lang=en"

            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            weather_description = data['weather'][0]['description']
            temperature = data['main']['temp']
            humidity = data['main']['humidity']

            weather_info = {
                "city": city_name,
                "description": weather_description,
                "temperature": temperature,
                "humidity": humidity,
            }

            self.weather_info.value = str(weather_info)

        except requests.RequestException as e:
            self.weather_info.value = f"Error fetching data: {str(e)}"
        except KeyError as e:
            self.weather_info.value = f"Missing key in the received data: {str(e)}"
        except ValueError as e:
            self.weather_info.value = f"Input error: {str(e)}"

