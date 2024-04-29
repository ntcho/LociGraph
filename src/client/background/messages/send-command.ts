import type { PlasmoMessaging } from "@plasmohq/messaging";


const handler: PlasmoMessaging.MessageHandler<RequestBody, ResponseBody> = (req, res) => {

  console.debug("Received request to send commands", req)

  if (req.body.commands.length === 0) {
    res.send({ error: "No commands to execute" })
    return
  }

  const targetTab = { tabId: req.sender.tab.id }

  chrome.debugger.attach(targetTab, "1.3", async function () {

    const results = []

    // execute each command
    for (const command of req.body.commands) {
      const response = await chrome.debugger.sendCommand(
        targetTab,
        command.method,
        command.commandParams
      )

      results.push({ request: command, response: response })
    }

    res.send({ error: null, response: JSON.stringify(results) })
  })
}

export type Command = {
  method: string
  commandParams?: any
}

export type RequestBody = {
  commands: Command[]
}

export type ResponseBody = {
  error: string | null
  response?: string
}

export default handler
