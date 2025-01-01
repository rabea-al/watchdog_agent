# Watchdog Agent


---

## Overview
 
This **Watchdog Agent** fetches weather data for requested cities periodically. It comes with tools to write and read from the database, retrieve weather data, and send messages to Slack. The agent runs locally using Gradio and has separate files for interactive use and scheduled tasks.
---

## Prerequisites
Before running the agent, ensure the following are installed and configured:

### Required Libraries:
Install the necessary Python libraries:

`Gradio` and `Agent`  components library 


and install requirement file :

```bash
pip install -r requirement.txt
```

---

## Configuration

### 1. **OpenAI API Key**:
Add your OpenAI API key as litral secrets


### 2. **Slack Bot Token**:
Add your Slack Bot Token as litral secrets

### 3. **Slack Channel ID**:
Specify the Slack Channel ID where the bot will send and receive messages.


### 4. **Server URL**:
Define the server URL for handling Slack events.

`

---

## How to Run the Agent

You can interact with the agent through the Gradio interface by running the example:
`GradioWeatherAgent`

You can also interact with the agent through the `WeatherAgent` example, which works with Flask at regular intervals.  

You can modify the tasks you want the agent to perform by editing the agent's literal chat configuration.

---

### Note:
Sometimes, the agent needs to be reminded to use its available tools to execute the desired request. This may require slight adjustments in the **system prompt** to ensure proper functionality.

