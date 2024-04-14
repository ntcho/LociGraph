import type { PlasmoMessaging } from "@plasmohq/messaging";


const handler: PlasmoMessaging.MessageHandler<RequestBody, ResponseBody> = (req, res) => {
  // console.log("req", req)

  chrome.debugger.attach({ tabId: req.sender.tab.id }, "1.3", async function () {

    const response = await chrome.debugger.sendCommand(
      { tabId: req.sender.tab.id },
      req.body.method,
      req.body.commandParams
    )

    console.info("sendCommand", req.body, response);

    res.send({ error: null })
  })
}

export type RequestBody = {
  method: string
  commandParams?: Object
}

export type ResponseBody = {
  error: string | null
}

export default handler
